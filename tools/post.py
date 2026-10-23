"""
post.py - la catena di post-processing, ricostruita dalla specifica YEBIS.

Non e' rifinitura. La pagina di showcase di Silicon Studio descrive cosi' l'uso
di YEBIS in 3D Dot Game Heroes (RECON §6.7):

  "Applied for vignetting and color modification to give a toy camera feel,
   and realistic defocusing effects that create the feeling of a miniature
   world. Also contributes to sparkling glare effects for light sources or
   water."

Sono quattro effetti nominati, e sono quattro passate qui dentro: **defocus**,
**glare**, **vignetting**, **color modification**. Il defocus in particolare e'
identita' visiva: e' cio' che fa leggere un mondo di voxel come un diorama in
miniatura. Senza, l'immagine e' corretta ma non somiglia al gioco.

I parametri non sono inventati: li pilota il Lua, e i suoi valori si contano.
Su 202 chiamate del disco:

    SetParamDepthofField(a, b, c)   a: 0,37 .. 3,02   mediana 0,79
                                    b: 0,20 .. 1,50   mediana 0,70
                                    c: sempre 0
    SetDofApaerture(x, 0)           x: 0,70 (14 volte), 1,2, 1,3, 1,5

`BackupDof()` e `RestoreDof()` sono chiamati 526 e 612 volte: ogni evento salva
il DOF corrente, ne impone uno suo, e alla fine lo rimette. Il fuoco quindi e'
per-scena, non globale.

**Quello che non sappiamo**: l'unita' di misura di quei numeri. Non possono
essere distanze di mondo - le mappe sono larghe centinaia di unita' - quindi
sono normalizzati o moltiplicatori di una base che sta nell'EBOOT. E' una delle
cose che la Fase 3 chiarira'. Qui i tre parametri sono esposti come fuoco,
ampiezza e apertura, con l'intervallo osservato come guida.

Struttura delle passate:

    scena  -> FBO colore + profondita'
    prep   -> mezza risoluzione: colore, e in alfa il bright pass per il glare
    blur   -> gaussiana separabile, due giri: il primo serve al defocus,
              il secondo (piu' largo) al glare
    comp   -> defocus per cerchio di confusione, glare additivo, vignetting,
              color modification, e infine a schermo
"""
from __future__ import annotations

import ctypes

from pyglet.gl import (
    GL_ARRAY_BUFFER, GL_CLAMP_TO_EDGE, GL_COLOR_ATTACHMENT0, GL_COLOR_BUFFER_BIT,
    GL_DEPTH_ATTACHMENT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_COMPONENT,
    GL_DEPTH_COMPONENT24, GL_FLOAT, GL_FRAMEBUFFER, GL_FRAMEBUFFER_COMPLETE,
    GL_LINEAR, GL_RGBA, GL_RGBA16F, GL_TEXTURE0, GL_TEXTURE1, GL_TEXTURE2,
    GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_TRIANGLES, GL_UNSIGNED_BYTE,
    GLuint, glActiveTexture, glBindFramebuffer, glBindTexture, glBindVertexArray,
    glCheckFramebufferStatus, glClear, glDeleteFramebuffers, glDeleteTextures,
    glDrawArrays, glFramebufferTexture2D, glGenFramebuffers, glGenTextures,
    glGenVertexArrays, glTexImage2D, glTexParameteri, glViewport)
from pyglet.graphics.shader import Shader, ShaderProgram

# Un triangolo che copre lo schermo, generato dal solo gl_VertexID: niente
# vertex buffer, niente attributi.
QUAD_VS = """#version 330 core
out vec2 uv;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    uv = p;
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""

PREP_FS = """#version 330 core
in vec2 uv;
uniform sampler2D scene;
uniform float threshold;
out vec4 frag;
void main() {
    vec3 c = texture(scene, uv).rgb;
    // in alfa il bright pass: e' quello che diventera' glare
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    frag = vec4(c, max(l - threshold, 0.0) / max(1.0 - threshold, 0.001));
}
"""

BLUR_FS = """#version 330 core
in vec2 uv;
uniform sampler2D src;
uniform vec2 dir;             // (1/w, 0) oppure (0, 1/h), gia' in texel
out vec4 frag;
void main() {
    // gaussiana a 9 tap con i pesi ripiegati sui campioni bilineari
    const float o[3] = float[](0.0, 1.3846153846, 3.2307692308);
    const float w[3] = float[](0.2270270270, 0.3162162162, 0.0702702703);
    vec4 sum = texture(src, uv) * w[0];
    for (int i = 1; i < 3; i++) {
        sum += texture(src, uv + dir * o[i]) * w[i];
        sum += texture(src, uv - dir * o[i]) * w[i];
    }
    frag = sum;
}
"""

COMP_FS = """#version 330 core
in vec2 uv;
uniform sampler2D scene;      // colore a piena risoluzione
uniform sampler2D blurred;    // mezza risoluzione, poco sfocato: defocus
uniform sampler2D wide;       // mezza risoluzione, molto sfocato: glare
uniform sampler2D depth;
uniform vec2 planes;          // near, far
uniform float focus;          // distanza del piano a fuoco
uniform float range;          // ampiezza della zona nitida
uniform float aperture;       // quanto sfoca fuori da quella zona
uniform float glare;
uniform float vignette;
uniform float saturation;
uniform float contrast;
uniform vec3 tint;
out vec4 frag;

float linear_depth(float d) {
    float z = d * 2.0 - 1.0;
    return 2.0 * planes.x * planes.y /
           (planes.y + planes.x - z * (planes.y - planes.x));
}

void main() {
    vec3 sharp = texture(scene, uv).rgb;
    vec3 soft  = texture(blurred, uv).rgb;

    // --- defocus: cerchio di confusione dalla distanza dal piano a fuoco
    float z = linear_depth(texture(depth, uv).r);
    float coc = clamp((abs(z - focus) / max(range, 1e-4) - 1.0) * aperture,
                      0.0, 1.0);
    vec3 c = mix(sharp, soft, coc);

    // --- glare: il bright pass sfocato largo, additivo
    c += texture(wide, uv).a * glare * texture(wide, uv).rgb;

    // --- color modification, la "toy camera": contrasto e saturazione su una
    //     dominante calda
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c = mix(vec3(l), c, saturation);
    c = (c - 0.5) * contrast + 0.5;
    c *= tint;

    // --- vignetting
    vec2 d = (uv - 0.5) * 2.0;
    c *= 1.0 - vignette * dot(d, d) * 0.5;

    frag = vec4(max(c, 0.0), 1.0);
}
"""

# Valori di partenza. Fuoco e ampiezza sono in unita' di mondo e li calcola
# chi disegna; gli altri sono di gusto, tarati per somigliare al gioco.
DEFAULTS = {
    'focus': 0.0, 'range': 0.0, 'aperture': 0.70,   # 0,70 e' il valore che il
    'glare': 0.35, 'vignette': 0.45,                # Lua usa piu' spesso
    'saturation': 1.12, 'contrast': 1.06,
    'tint': (1.03, 1.0, 0.96),
    # La soglia va tenuta alta: il fornitore parla di glare "for light sources
    # or water", non di un velo su tutta l'immagine. A 0,72 il pavimento di un
    # sotterraneo bastava a farlo brillare.
    'threshold': 0.88,
}


def _texture(w: int, h: int, internal, fmt, kind) -> int:
    tex = GLuint()
    glGenTextures(1, ctypes.byref(tex))
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexImage2D(GL_TEXTURE_2D, 0, internal, w, h, 0, fmt, kind, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    return tex.value


def _framebuffer(color: int, depth: int = 0) -> int:
    fbo = GLuint()
    glGenFramebuffers(1, ctypes.byref(fbo))
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                           GL_TEXTURE_2D, color, 0)
    if depth:
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                               GL_TEXTURE_2D, depth, 0)
    if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
        raise RuntimeError('framebuffer incompleto')
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    return fbo.value


class Post:
    """La catena. `begin()` prima di disegnare la scena, `draw()` dopo."""

    def __init__(self, w: int, h: int, scale: int = 2):
        self.scale = scale
        self.params = dict(DEFAULTS)
        self.enabled = True
        self.prep = ShaderProgram(Shader(QUAD_VS, 'vertex'),
                                  Shader(PREP_FS, 'fragment'))
        self.blur = ShaderProgram(Shader(QUAD_VS, 'vertex'),
                                  Shader(BLUR_FS, 'fragment'))
        self.comp = ShaderProgram(Shader(QUAD_VS, 'vertex'),
                                  Shader(COMP_FS, 'fragment'))
        vao = GLuint()
        glGenVertexArrays(1, ctypes.byref(vao))
        self.vao = vao.value
        self.w = self.h = 0
        self.resize(w, h)

    # -- risorse

    def _free(self) -> None:
        if not self.w:
            return
        for fbo in (self.fbo, self.fbo_a, self.fbo_b, self.fbo_c):
            f = GLuint(fbo)
            glDeleteFramebuffers(1, ctypes.byref(f))
        for tex in (self.color, self.depth, self.tex_a, self.tex_b, self.tex_c):
            t = GLuint(tex)
            glDeleteTextures(1, ctypes.byref(t))

    def resize(self, w: int, h: int) -> None:
        if (w, h) == (self.w, self.h) or w <= 0 or h <= 0:
            return
        self._free()
        self.w, self.h = w, h
        self.hw, self.hh = max(w // self.scale, 1), max(h // self.scale, 1)
        self.color = _texture(w, h, GL_RGBA16F, GL_RGBA, GL_FLOAT)
        self.depth = _texture(w, h, GL_DEPTH_COMPONENT24, GL_DEPTH_COMPONENT,
                              GL_FLOAT)
        self.tex_a = _texture(self.hw, self.hh, GL_RGBA16F, GL_RGBA, GL_FLOAT)
        self.tex_b = _texture(self.hw, self.hh, GL_RGBA16F, GL_RGBA, GL_FLOAT)
        self.tex_c = _texture(self.hw, self.hh, GL_RGBA16F, GL_RGBA, GL_FLOAT)
        self.fbo = _framebuffer(self.color, self.depth)
        self.fbo_a = _framebuffer(self.tex_a)
        self.fbo_b = _framebuffer(self.tex_b)
        self.fbo_c = _framebuffer(self.tex_c)

    # -- passate

    def begin(self) -> None:
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.w, self.h)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def _pass(self, program, fbo: int, w: int, h: int, textures) -> None:
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glViewport(0, 0, w, h)
        program.use()
        for unit, (name, tex) in enumerate(textures):
            glActiveTexture(GL_TEXTURE0 + unit)
            glBindTexture(GL_TEXTURE_2D, tex)
            program[name] = unit
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, 3)

    def draw(self, near: float, far: float) -> None:
        p = self.params
        # 1. mezza risoluzione + bright pass in alfa
        self.prep.use()
        self.prep['threshold'] = float(p['threshold'])
        self._pass(self.prep, self.fbo_a, self.hw, self.hh,
                   [('scene', self.color)])

        # 2. gaussiana separabile. Il primo giro sfoca poco e serve al defocus;
        #    il secondo riparte da quel risultato e sfoca molto, per il glare.
        #    Servono tre buffer, non due: il risultato stretto va conservato
        #    mentre quello largo lo scavalca.
        def blur(src: int, fbo: int, dx: float, dy: float) -> None:
            self.blur.use()
            self.blur['dir'] = (dx, dy)
            self._pass(self.blur, fbo, self.hw, self.hh, [('src', src)])

        blur(self.tex_a, self.fbo_b, 1.0 / self.hw, 0.0)
        blur(self.tex_b, self.fbo_c, 0.0, 1.0 / self.hh)
        soft = self.tex_c
        blur(self.tex_c, self.fbo_b, 2.5 / self.hw, 0.0)
        blur(self.tex_b, self.fbo_a, 0.0, 2.5 / self.hh)
        wide = self.tex_a

        # 3. composizione a schermo
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, self.w, self.h)
        self.comp.use()
        self.comp['planes'] = (float(near), float(far))
        for k in ('focus', 'range', 'aperture', 'glare', 'vignette',
                  'saturation', 'contrast'):
            self.comp[k] = float(p[k])
        self.comp['tint'] = tuple(float(x) for x in p['tint'])
        self._pass(self.comp, 0, self.w, self.h,
                   [('scene', self.color), ('blurred', soft),
                    ('wide', wide), ('depth', self.depth)])
        glBindVertexArray(0)
