<#
  SUPERATO da iso.py - vedi docs/extract.md. Questo script legge **ISO9660**,
  che sul disco PS3 ha i nomi troncati a 31 caratteri e maiuscolizzati
  (`d_1_1_1.ps3.pac.gz` -> `D_1_1_1_PS3_PAC.GZ`). I nomi in questo gioco sono
  dati - il materiale riferisce la texture per nome di file - quindi va usato
  `iso.py`, che legge UDF e tiene manifesto e hash.

  ATTENZIONE: il comando `index` qui sotto riscrive tools\iso_index.tsv in un
  formato diverso da quello che iso.py si aspetta.

  iso.ps1 - indicizzazione ed estrazione da ISO9660 (PS3 game disc, gia' decrittata).

  Uso:
    .\iso.ps1 index                        # scrive tools\iso_index.tsv (path<TAB>lba<TAB>size)
    .\iso.ps1 extract -Match '*.LUA' -Out d:\...\extract
    .\iso.ps1 magic   -Match '*.TPK' -Take 5      # primi 32 byte dei file che matchano
#>
param(
  [Parameter(Position=0)][ValidateSet('index','extract','magic')][string]$Cmd = 'index',
  [string]$Iso   = "d:\Homebrew6\PC-3Ddot\3D Dot Game Heroes (Europe).iso",
  [string]$Index = "$PSScriptRoot\iso_index.tsv",
  [string]$Match = '*',
  [string]$Out   = "d:\Homebrew6\PC-3Ddot\extract",
  [int]$Take     = 0,
  [int]$Bytes    = 32
)

$ErrorActionPreference = 'Stop'

function Open-Iso { [System.IO.File]::OpenRead($Iso) }

function Get-DirEntries($fs, [int64]$lba, [int]$size) {
  $b = New-Object byte[] ([Math]::Max($size,2048))
  $fs.Seek($lba * 2048, 'Begin') | Out-Null
  $fs.Read($b, 0, $b.Length) | Out-Null
  $out = @(); $off = 0
  while ($off -lt $size) {
    $rl = $b[$off]
    if ($rl -eq 0) {
      $next = [int]([Math]::Floor($off / 2048) * 2048 + 2048)
      if ($next -ge $size) { break }
      $off = $next; continue
    }
    $nl = $b[$off + 32]
    if (-not ($nl -eq 1 -and ($b[$off+33] -eq 0 -or $b[$off+33] -eq 1))) {
      $out += [PSCustomObject]@{
        Name  = ([System.Text.Encoding]::ASCII.GetString($b, $off+33, $nl)) -replace ';1$',''
        Lba   = [int64][BitConverter]::ToUInt32($b, $off + 2)
        Size  = [int64][BitConverter]::ToUInt32($b, $off + 10)
        IsDir = [bool]($b[$off + 25] -band 2)
      }
    }
    $off += $rl
  }
  return $out
}

function Build-Index($fs) {
  $pvd = New-Object byte[] 2048
  $fs.Seek(16*2048,'Begin') | Out-Null; $fs.Read($pvd,0,2048) | Out-Null
  $rootLba  = [BitConverter]::ToUInt32($pvd, 158)
  $rootSize = [BitConverter]::ToUInt32($pvd, 166)

  $rows  = New-Object System.Collections.Generic.List[object]
  $stack = New-Object System.Collections.Generic.Stack[object]
  $stack.Push([PSCustomObject]@{ Lba=[int64]$rootLba; Size=[int]$rootSize; Path='' })
  while ($stack.Count) {
    $d = $stack.Pop()
    foreach ($e in (Get-DirEntries $fs $d.Lba $d.Size)) {
      $full = if ($d.Path) { "$($d.Path)/$($e.Name)" } else { $e.Name }
      if ($e.IsDir) { $stack.Push([PSCustomObject]@{ Lba=$e.Lba; Size=[int]$e.Size; Path=$full }) }
      else { $rows.Add([PSCustomObject]@{ Path=$full; Lba=$e.Lba; Size=$e.Size }) }
    }
  }
  return $rows | Sort-Object Path
}

function Load-Index {
  if (-not (Test-Path $Index)) { throw "Indice mancante: $Index - esegui prima: .\iso.ps1 index" }
  Import-Csv $Index -Delimiter "`t" | ForEach-Object {
    [PSCustomObject]@{ Path=$_.Path; Lba=[int64]$_.Lba; Size=[int64]$_.Size }
  }
}

function Read-File($fs, $row, [int]$limit = 0) {
  $n = if ($limit -gt 0) { [Math]::Min($limit, $row.Size) } else { $row.Size }
  $b = New-Object byte[] $n
  $fs.Seek($row.Lba * 2048, 'Begin') | Out-Null
  $read = 0
  while ($read -lt $n) {
    $r = $fs.Read($b, $read, $n - $read)
    if ($r -le 0) { break }
    $read += $r
  }
  return $b
}

switch ($Cmd) {

  'index' {
    $fs = Open-Iso
    try { $rows = Build-Index $fs } finally { $fs.Close() }
    $rows | Export-Csv $Index -Delimiter "`t" -NoTypeInformation -Encoding utf8
    "Indicizzati $($rows.Count) file -> $Index"
  }

  'magic' {
    $rows = @(Load-Index | Where-Object { $_.Path -like $Match })
    if ($Take -gt 0) { $rows = $rows[0..([Math]::Min($Take,$rows.Count)-1)] }
    $fs = Open-Iso
    try {
      foreach ($r in $rows) {
        $b = Read-File $fs $r $Bytes
        $hex = ($b | ForEach-Object { $_.ToString('x2') }) -join ' '
        $asc = -join ($b | ForEach-Object { if ($_ -ge 32 -and $_ -lt 127) { [char]$_ } else { '.' } })
        "{0}  ({1:N0} B)" -f $r.Path, $r.Size
        "    $hex"
        "    |$asc|"
      }
    } finally { $fs.Close() }
  }

  'extract' {
    $rows = @(Load-Index | Where-Object { $_.Path -like $Match })
    if ($Take -gt 0) { $rows = $rows[0..([Math]::Min($Take,$rows.Count)-1)] }
    $fs = Open-Iso
    $tot = 0
    try {
      foreach ($r in $rows) {
        $dst = Join-Path $Out $r.Path
        $dir = Split-Path $dst -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
        [System.IO.File]::WriteAllBytes($dst, (Read-File $fs $r))
        $tot += $r.Size
      }
    } finally { $fs.Close() }
    "Estratti $($rows.Count) file, $('{0:N0}' -f $tot) byte -> $Out"
  }
}
