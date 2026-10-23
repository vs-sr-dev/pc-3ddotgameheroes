// Generato da tools/lua_signatures.py - NON modificare a mano.
// Interfaccia di scripting inferita dai call site del corpus Lua
// originale (29,626 call site, 497 metodi).
//
// I tipi sono dedotti staticamente: verificare i casi ScriptValue
// contro l'EBOOT prima di considerarli definitivi.

#pragma once
#include "script_value.h"

// 14,999 call site
class IObject {
public:
    virtual ~IObject() = default;

    // 1,291x
    virtual void SetPhase(int a0) = 0;
    // 1,281x
    virtual void AddNode(PackageId a0, ScriptValue a1 /*opt*/) = 0;
    // 916x
    virtual void AddAnimation(int a0, float a1) = 0;
    // 842x
    virtual ScriptValue GetPhase() = 0;
    // 650x
    virtual void SetType(ActorType a0) = 0;
    // 554x
    virtual void SetTime(ScriptValue a0, float a1 /*opt*/) = 0;
    // 458x
    virtual ScriptValue IsTimeZero(int a0 /*opt*/) = 0;
    // 401x
    virtual void SetDirectionToPlayer() = 0;
    // 389x
    virtual void StartEvent(const char* a0) = 0;
    // 368x
    virtual void setNum(int a0) = 0;
    // 352x
    virtual ScriptValue IsEvent() = 0;
    // 352x
    virtual void CreateBalloon(ActorType a0) = 0;
    // 352x
    virtual void CreatePlayerBalloon(ActorType a0) = 0;
    // 318x
    virtual void SetSpeed(float a0) = 0;
    // 305x
    virtual void SetDistance(float a0) = 0;
    // 281x
    virtual ScriptValue IsDistanceZero() = 0;
    // 280x
    virtual ScriptValue IsHitWall() = 0;
    // 247x
    virtual void AddColor(float a0, float a1, float a2) = 0;
    // 217x
    virtual ScriptValue IsHitObject() = 0;
    // 213x
    virtual void PlaySE(SoundID a0) = 0;
    // 192x
    virtual ScriptValue getNum() = 0;
    // 180x
    virtual void AddAnimationWalk(int a0, float a1, float a2) = 0;
    // 168x
    virtual ScriptValue getLimitsHave() = 0;
    // 150x
    virtual void Move(bool a0 /*opt*/) = 0;
    // 150x
    virtual void SetNode(int a0) = 0;
    // 143x
    virtual void InitializeAnimation() = 0;
    // 127x
    virtual ScriptValue GetItem(ItemId a0 /*opt*/) = 0;
    // 114x
    virtual void addString(const char* a0) = 0;
    // 113x
    virtual void SetAnimationId(float a0, int a1 /*opt*/) = 0;
    // 113x
    virtual void pause() = 0;
    // 112x
    virtual void setLimitsHave(int a0) = 0;
    // 112x
    virtual void createObject(const char* a0) = 0;
    // 100x
    virtual void SetItemId(ItemId a0) = 0;
    // 100x
    virtual void setBumpFlag(bool a0) = 0;
    // 91x
    virtual void SetDirection(int a0) = 0;
    // 83x
    virtual void AddItemNum(int a0) = 0;
    // 83x
    virtual void SetAmount(int a0) = 0;
    // 80x
    virtual void SetUserInt(int a0, int a1 /*opt*/) = 0;
    // 78x
    virtual void DeletePlayerBalloon() = 0;
    // 78x
    virtual void DeleteBalloon() = 0;
    // 78x
    virtual void setPrice(int a0, int a1) = 0;
    // 73x
    virtual void SetHp(int a0) = 0;
    // 71x
    virtual ScriptValue GetAnimationId() = 0;
    // 64x
    virtual ScriptValue GetPosition() = 0;
    // 55x
    virtual ScriptValue IsLesserDistance(ScriptValue a0, ScriptValue a1 /*opt*/) = 0;
    // 52x
    virtual ScriptValue IsHitGuardPlayer(ObjectClassId a0) = 0;
    // 48x
    virtual void setBookRegistInfo(GameDataFlag a0, int a1) = 0;
    // 48x
    virtual void setSword(SwordId a0) = 0;
    // 44x
    virtual void SetFlySpeed(float a0, float a1 /*opt*/) = 0;
    // 44x
    virtual void CreateEffect() = 0;
    // 42x
    virtual void SetRandomDirection() = 0;
    // 40x
    virtual void SetFallFlag(bool a0) = 0;
    // 37x
    virtual ScriptValue IsEqualPlayerFloor() = 0;
    // 35x
    virtual void Destroy() = 0;
    // 35x
    virtual void DisableAutoDead() = 0;
    // 35x
    virtual void setUseCount(int a0) = 0;
    // 34x
    virtual ScriptValue IsDead() = 0;
    // 33x
    virtual void Fly(float a0 /*opt*/) = 0;
    // 28x
    virtual void CreateStrongSign() = 0;
    // 26x
    virtual void setPosition(ScriptValue a0) = 0;
    // 25x
    virtual void usePlayerParameter() = 0;
    // 24x
    virtual void setSwordInit(SwordId a0) = 0;
    // 24x
    virtual ScriptValue GetGridHeight() = 0;
    // 24x
    virtual void Jump(float a0 /*opt*/) = 0;
    // 24x
    virtual ScriptValue IsEqualPlayerXZ(float a0 /*opt*/) = 0;
    // 24x
    virtual void setMaxCost(int a0) = 0;
    // 24x
    virtual void setRestCost(int a0) = 0;
    // 24x
    virtual void setLengthCost(int a0) = 0;
    // 24x
    virtual void setBaseLengthLevel(int a0) = 0;
    // 24x
    virtual void setMaxLengthLevel(int a0) = 0;
    // 24x
    virtual void setThickCost(int a0) = 0;
    // 24x
    virtual void setBaseThickLevel(int a0) = 0;
    // 24x
    virtual void setMaxThickLevel(int a0) = 0;
    // 24x
    virtual void setAngleCost(int a0) = 0;
    // 24x
    virtual void setBaseAngleLevel(int a0) = 0;
    // 24x
    virtual void setMaxAngleLevel(int a0) = 0;
    // 24x
    virtual void setBulletCost(int a0) = 0;
    // 24x
    virtual void setBaseBulletLevel(int a0) = 0;
    // 24x
    virtual void setMaxBulletLevel(int a0) = 0;
    // 24x
    virtual void setPowerCost(int a0) = 0;
    // 24x
    virtual void setBasePowerLevel(int a0) = 0;
    // 24x
    virtual void setMaxPowerLevel(int a0) = 0;
    // 24x
    virtual void setPenetrateCost(int a0) = 0;
    // 24x
    virtual void setBasePenetrateLevel(int a0) = 0;
    // 24x
    virtual void setMaxPenetrateLevel(int a0) = 0;
    // 24x
    virtual void setSpecialCost(int a0) = 0;
    // 24x
    virtual void setBaseSpecialLevel(int a0) = 0;
    // 24x
    virtual void setMaxSpecialLevel(int a0) = 0;
    // 22x
    virtual void setAddParameter(int a0) = 0;
    // 21x
    virtual void SetJumpSpeed(float a0) = 0;
    // 20x
    virtual void CountUpBeatEnemyNum() = 0;
    // 20x
    virtual void BlockDefenceMove() = 0;
    // 20x
    virtual ScriptValue BlockDefenceCollision(ScriptValue a0) = 0;
    // 19x
    virtual void CreateExclamationMark() = 0;
    // 19x
    virtual ScriptValue GetVector() = 0;
    // 19x
    virtual void DropBDMoney() = 0;
    // 18x
    virtual ScriptValue GetUserInt() = 0;
    // 18x
    virtual void createFairyEffect() = 0;
    // 18x
    virtual void Blink(float a0 /*opt*/, float a1 /*opt*/) = 0;
    // 18x
    virtual void SetNodeVisible(int a0, bool a1) = 0;
    // 17x
    virtual ScriptValue IsBlink() = 0;
    // 17x
    virtual void KnockBackPlayer(float a0 /*opt*/) = 0;
    // 16x
    virtual void SetCollisionRectangle(float a0, float a1, float a2) = 0;
    // 16x
    virtual ScriptValue Throw(const char* a0, bool a1 /*opt*/) = 0;
    // 16x
    virtual ScriptValue GetHP() = 0;
    // 13x
    virtual void SetCollision(float a0) = 0;
    // 13x
    virtual ScriptValue IsBlinkPlayer() = 0;
    // 13x
    virtual ScriptValue IsJumpFinish() = 0;
    // 13x
    virtual void PlaySEAlways(SoundID a0) = 0;
    // 12x
    virtual void SetUserFloat(float a0) = 0;
    // 12x
    virtual void setShield(ItemId a0) = 0;
    // 11x
    virtual ScriptValue GetFloor() = 0;
    // 11x
    virtual void SetupGeneralStore(int a0, int a1) = 0;
    // 10x
    virtual ScriptValue GetPlayerHP() = 0;
    // 10x
    virtual ScriptValue GetMapState() = 0;
    // 10x
    virtual void useArrowParameter() = 0;
    // 9x
    virtual void KnockBack(float a0) = 0;
    // 9x
    virtual ScriptValue IsLesserDistanceX(ScriptValue a0) = 0;
    // 9x
    virtual ScriptValue IsLesserDistanceZ(ScriptValue a0) = 0;
    // 9x
    virtual ScriptValue IsPlayerToDirection2(ScriptValue a0 /*opt*/) = 0;
    // 8x
    virtual ScriptValue IsGuardPlayer() = 0;
    // 8x
    virtual ScriptValue isHitMapObject() = 0;
    // 8x
    virtual void RollingWeapon() = 0;
    // 8x
    virtual ScriptValue getPosition() = 0;
    // 8x
    virtual ScriptValue GetPlayerAngle() = 0;
    // 8x
    virtual void useBombParameter() = 0;
    // 8x
    virtual void setUseDelay(float a0) = 0;
    // 7x
    virtual void setAngle(const char* a0, int a1 /*opt*/) = 0;
    // 7x
    virtual void ChangeMap(MapId a0 /*opt*/, int a1 /*opt*/) = 0;
    // 7x
    virtual ScriptValue IsPlayerWeapon(ScriptValue a0) = 0;
    // 7x
    virtual void subBookRegistCount() = 0;
    // 7x
    virtual void Damage(ActorType a0) = 0;
    // 7x
    virtual void DamagePlayer(int a0) = 0;
    // 7x
    virtual void BlinkPlayer() = 0;
    // 7x
    virtual ScriptValue IsWall(ScriptValue a0) = 0;
    // 7x
    virtual ScriptValue IsFly() = 0;
    // 7x
    virtual void DecrementBlock() = 0;
    // 7x
    virtual void setPerHealHp(int a0) = 0;
    // 6x
    virtual void equipShield(ItemId a0) = 0;
    // 6x
    virtual ScriptValue GetUserFloat() = 0;
    // 6x
    virtual ScriptValue IsGuardShield(ScriptValue a0) = 0;
    // 6x
    virtual void createBomb() = 0;
    // 6x
    virtual void SetVector(float a0, float a1) = 0;
    // 6x
    virtual void setPerHealMp(int a0) = 0;
    // 6x
    virtual void decreaseEmptyBottle() = 0;
    // 6x
    virtual void playSE(SoundID a0) = 0;
    // 6x
    virtual void setMagicCost(int a0) = 0;
    // 6x
    virtual void useWindWingParameter() = 0;
    // 5x
    virtual void dead() = 0;
    // 5x
    virtual void SetRandomPositionXZ(float a0, float a1) = 0;
    // 5x
    virtual void SetThroughWall(bool a0) = 0;
    // 5x
    virtual ScriptValue IsFrozenShader() = 0;
    // 5x
    virtual ScriptValue IsEqualPlayerX() = 0;
    // 5x
    virtual ScriptValue IsEqualPlayerZ() = 0;
    // 5x
    virtual void setResurrectionPoint() = 0;
    // 4x
    virtual void CreateObject(const char* a0) = 0;
    // 4x
    virtual void SetReverseDirection() = 0;
    // 4x
    virtual void SetAngleFromDirection() = 0;
    // 4x
    virtual void SetDirectionToPlayer2() = 0;
    // 4x
    virtual ScriptValue IsJumpTop() = 0;
    // 4x
    virtual ScriptValue getAngle(int a0) = 0;
    // 4x
    virtual void createWarpEffect() = 0;
    // 4x
    virtual void CreateSpark() = 0;
    // 4x
    virtual ScriptValue GetDropMiniGameItem() = 0;
    // 4x
    virtual void equipSword(SwordId a0) = 0;
    // 4x
    virtual void setPower(int a0) = 0;
    // 4x
    virtual void useCandlesParameter() = 0;
    // 4x
    virtual void setHealHp(int a0) = 0;
    // 4x
    virtual void useHighSleepingBagParameter() = 0;
    // 4x
    virtual void useLampParameter() = 0;
    // 4x
    virtual void useSleepingBagParameter() = 0;
    // 4x
    virtual void useSunStoneParameter() = 0;
    // 3x
    virtual void AddArrowNum(int a0) = 0;
    // 3x
    virtual void AddBombNum(int a0) = 0;
    // 3x
    virtual ScriptValue GetElapsedTime() = 0;
    // 3x
    virtual void Rotate() = 0;
    // 3x
    virtual void AddMoney(int a0) = 0;
    // 3x
    virtual void SetDirectionToPlayer360() = 0;
    // 3x
    virtual ScriptValue IsDirectionFromPlayer() = 0;
    // 3x
    virtual void SetInitVector() = 0;
    // 3x
    virtual ScriptValue IsActorMoveArea(ScriptValue a0) = 0;
    // 3x
    virtual void SetDirectionToInit() = 0;
    // 3x
    virtual void SetFloor(ScriptValue a0) = 0;
    // 3x
    virtual void SetRandomDirectionFromAngle(ScriptValue a0, ScriptValue a1) = 0;
    // 3x
    virtual ScriptValue IsRockBound() = 0;
    // 3x
    virtual void Throw3Way(const char* a0) = 0;
    // 3x
    virtual ScriptValue GetSpeed() = 0;
    // 3x
    virtual ScriptValue GetBallNumInField() = 0;
    // 3x
    virtual void CreateEffectBDBoss() = 0;
    // 3x
    virtual ScriptValue IsGoalPhase() = 0;
    // 3x
    virtual void setInvisibleCloak(float a0) = 0;
    // 3x
    virtual void setAddMoney(int a0) = 0;
    // 3x
    virtual void setPowerDrinks(float a0) = 0;
    // 3x
    virtual void setWarriorsAware(float a0) = 0;
    // 2x
    virtual void SetupBlacksmith() = 0;
    // 2x
    virtual void DropItem(ScriptValue a0) = 0;
    // 2x
    virtual ScriptValue IsPlayerReflection() = 0;
    // 2x
    virtual ScriptValue GetType() = 0;
    // 2x
    virtual void SetHitShield() = 0;
    // 2x
    virtual void SetRandomDirection8() = 0;
    // 2x
    virtual ScriptValue IsPlayerToDirection() = 0;
    // 2x
    virtual void SetFlyUpLimit(float a0) = 0;
    // 2x
    virtual void createLightningDamage() = 0;
    // 2x
    virtual ScriptValue IsSquidPlunge(bool a0) = 0;
    // 2x
    virtual void createNormalInk() = 0;
    // 2x
    virtual void SetScorpionMove() = 0;
    // 2x
    virtual void SetMagicWeaponFlag(bool a0) = 0;
    // 2x
    virtual ScriptValue IsFromMode() = 0;
    // 2x
    virtual ScriptValue IsPlayerArea() = 0;
    // 2x
    virtual void SetScaling(float a0) = 0;
    // 2x
    virtual void createDevilBomb() = 0;
    // 2x
    virtual void DecrementBall(int a0) = 0;
    // 2x
    virtual void AffectItem() = 0;
    // 2x
    virtual void BDBulletMove() = 0;
    // 2x
    virtual void SetBDBossParam(ScriptValue a0, ScriptValue a1) = 0;
    // 2x
    virtual void SetupTowerStore(int a0 /*opt*/) = 0;
    // 2x
    virtual void useCandles() = 0;
    // 2x
    virtual void setAddMaxHp(int a0) = 0;
    // 2x
    virtual void useLamp() = 0;
    // 2x
    virtual void setMapGirdObjIndex(int a0) = 0;
    // 2x
    virtual void collisionVisible(bool a0) = 0;
    // 1x
    virtual void CheckSwordAdvantage() = 0;
    // 1x
    virtual void HealPlayer(int a0) = 0;
    // 1x
    virtual void redAppleEffect() = 0;
    // 1x
    virtual void HealMpPlayer(int a0) = 0;
    // 1x
    virtual void blueAppleEffect() = 0;
    // 1x
    virtual void FragmentHeartCheck() = 0;
    // 1x
    virtual void useInvisibleCloak(float a0) = 0;
    // 1x
    virtual void usePowerDrinks(float a0) = 0;
    // 1x
    virtual void FullHealPlayer() = 0;
    // 1x
    virtual void FullMpHealPlayer() = 0;
    // 1x
    virtual void useWarriorsAware(float a0) = 0;
    // 1x
    virtual void SetDropItemSpeed(float a0, float a1, float a2, int a3) = 0;
    // 1x
    virtual void SetDropItemTime(float a0, float a1) = 0;
    // 1x
    virtual void SetFrozenShake(float a0, float a1) = 0;
    // 1x
    virtual ScriptValue isPlayerKnockBack() = 0;
    // 1x
    virtual void SetPositionOnPlayer() = 0;
    // 1x
    virtual void PlayMotion(float a0, float a1, float a2) = 0;
    // 1x
    virtual void ThrowCockGreatArmy() = 0;
    // 1x
    virtual void SetupMedalKing(int a0, int a1) = 0;
    // 1x
    virtual void reflectionEffect() = 0;
    // 1x
    virtual void createLightning() = 0;
    // 1x
    virtual ScriptValue IsHitOnFloor() = 0;
    // 1x
    virtual void createRockBound() = 0;
    // 1x
    virtual void RollingRock() = 0;
    // 1x
    virtual void SquidMove() = 0;
    // 1x
    virtual void Shot(const char* a0) = 0;
    // 1x
    virtual ScriptValue IsWallAmongPlayer() = 0;
    // 1x
    virtual void AddCollisionHeightBelow(float a0) = 0;
    // 1x
    virtual void DamagePoint(ScriptValue a0) = 0;
    // 1x
    virtual void createDarkEyeEffect() = 0;
    // 1x
    virtual void PlayerLock(ScriptValue a0, int a1) = 0;
    // 1x
    virtual void RoperRedDamage() = 0;
    // 1x
    virtual void RoperBlueDamage() = 0;
    // 1x
    virtual ScriptValue SetChildObject(const char* a0, float a1, float a2, float a3) = 0;
    // 1x
    virtual ScriptValue GetChildObject() = 0;
    // 1x
    virtual void ClearColor() = 0;
    // 1x
    virtual void succubusEffect() = 0;
    // 1x
    virtual void SetEscapeDirection() = 0;
    // 1x
    virtual void DragonThrow(const char* a0) = 0;
    // 1x
    virtual ScriptValue IsDragonKiller() = 0;
    // 1x
    virtual void bossDragonBall() = 0;
    // 1x
    virtual void SetTargetPositionFromPlayerPosition() = 0;
    // 1x
    virtual ScriptValue ReverseMove() = 0;
    // 1x
    virtual ScriptValue IsPlayerSafetyZone() = 0;
    // 1x
    virtual ScriptValue IsStartPosition() = 0;
    // 1x
    virtual void createMagicEffect() = 0;
    // 1x
    virtual void setEffectScaling(float a0, ScriptValue a1) = 0;
    // 1x
    virtual void updateEffect() = 0;
    // 1x
    virtual void BlockMove() = 0;
    // 1x
    virtual void CheckItemEffect() = 0;
    // 1x
    virtual ScriptValue GetHitDirection() = 0;
    // 1x
    virtual ScriptValue GetPlayerX() = 0;
    // 1x
    virtual ScriptValue GetPlayerZ() = 0;
    // 1x
    virtual ScriptValue GetReflectAngle() = 0;
    // 1x
    virtual ScriptValue SwordReflect(ScriptValue a0) = 0;
    // 1x
    virtual void CheckGoalHit() = 0;
    // 1x
    virtual ScriptValue IsGoalHit() = 0;
    // 1x
    virtual void CheckLap() = 0;
    // 1x
    virtual void SetHitPlayer(bool a0) = 0;
    // 1x
    virtual void DropBDTowerItem() = 0;
    // 1x
    virtual ScriptValue CheckObstacleBlock() = 0;
    // 1x
    virtual void SetBDAttackRange(ScriptValue a0) = 0;
    // 1x
    virtual void ResetMapGridData() = 0;
    // 1x
    virtual void SetupBDSelecter() = 0;
    // 1x
    virtual ScriptValue getType() = 0;
    // 1x
    virtual void enable() = 0;
    // 1x
    virtual void disable() = 0;
    // 1x
    virtual void setHealMp(int a0) = 0;
    // 1x
    virtual void bluePortionEffect() = 0;
    // 1x
    virtual void setAddMaxMp(int a0) = 0;
    // 1x
    virtual void redPortionEffect() = 0;
    // 1x
    virtual void elixirEffect() = 0;
    // 1x
    virtual void pointLight() = 0;
    // 1x
    virtual void SetFrozenBroken(bool a0) = 0;
    // 1x
    virtual void SetFrozenBlock(bool a0) = 0;
    // 1x
    virtual void createMowEffect() = 0;
};

// 13,136 call site
class IEvent {
public:
    virtual ~IEvent() = default;

    // 2,805x
    virtual void Print(const char* a0) = 0;
    // 1,156x
    virtual void WaitContinue() = 0;
    // 1,093x
    virtual ScriptValue GetEventFlag(EventFlag a0) = 0;
    // 1,052x
    virtual void CloseMessage() = 0;
    // 502x
    virtual void Wait(float a0) = 0;
    // 443x
    virtual void RestoreCamera() = 0;
    // 414x
    virtual void SetEventFlag(EventFlag a0, int a1) = 0;
    // 373x
    virtual void BackupCamera() = 0;
    // 335x
    virtual void UnlockPlayer() = 0;
    // 306x
    virtual void RestoreDof() = 0;
    // 304x
    virtual void Play() = 0;
    // 303x
    virtual void Pause() = 0;
    // 265x
    virtual void PlaySe(SoundID a0) = 0;
    // 262x
    virtual void BackupDof() = 0;
    // 260x
    virtual void LockPlayer() = 0;
    // 225x
    virtual void SetNpcDirection(const char* a0, int a1) = 0;
    // 173x
    virtual void SetPlayerDirection(int a0) = 0;
    // 152x
    virtual void Select() = 0;
    // 150x
    virtual ScriptValue GetSelect() = 0;
    // 137x
    virtual void PlayEnemy() = 0;
    // 130x
    virtual void PlayNpc() = 0;
    // 118x
    virtual void SetNpcVisible(const char* a0, int a1) = 0;
    // 114x
    virtual void CreateNpc(float a0, float a1, float a2, const char* a3) = 0;
    // 113x
    virtual void SetStatusVisible(int a0) = 0;
    // 112x
    virtual void PauseEnemy() = 0;
    // 87x
    virtual void PauseNpc() = 0;
    // 84x
    virtual void FadeOut() = 0;
    // 83x
    virtual void SetParamDepthofField(float a0, float a1, float a2) = 0;
    // 78x
    virtual void FadeIn() = 0;
    // 78x
    virtual void SetCamera(float a0, float a1 /*opt*/, float a2 /*opt*/, float a3 /*opt*/, float a4 /*opt*/, float a5 /*opt*/) = 0;
    // 77x
    virtual void setItemMenuOpenFlag(int a0) = 0;
    // 69x
    virtual void SetPlayerPosition(int a0, int a1, int a2) = 0;
    // 58x
    virtual void SetMoney(int a0) = 0;
    // 57x
    virtual ScriptValue GetJobType() = 0;
    // 56x
    virtual void ResetDash() = 0;
    // 52x
    virtual void MoveNpc(const char* a0, float a1, float a2, float a3, int a4 /*opt*/) = 0;
    // 47x
    virtual ScriptValue IsSpelunker() = 0;
    // 47x
    virtual void SetMap(const char* a0, const char* a1) = 0;
    // 46x
    virtual void AddItem2(ItemId a0) = 0;
    // 42x
    virtual void MovePlayer(float a0, float a1, float a2) = 0;
    // 41x
    virtual ScriptValue GetPlayerSex() = 0;
    // 41x
    virtual ScriptValue GetMoney() = 0;
    // 37x
    virtual void PlayBgm(SoundID a0) = 0;
    // 37x
    virtual void StopBgm() = 0;
    // 28x
    virtual void SetNpcNode(const char* a0, int a1) = 0;
    // 24x
    virtual void PlayFlash(int a0, float a1) = 0;
    // 23x
    virtual void SetupBGMInProportion(float a0, float a1) = 0;
    // 22x
    virtual void SetupBGMOutProportion(float a0) = 0;
    // 21x
    virtual void SavePlayerAngle() = 0;
    // 20x
    virtual void StartHailItem(int a0, int a1) = 0;
    // 19x
    virtual void RestartMiniGame() = 0;
    // 18x
    virtual void PlayCamera(float a0, float a1, int a2) = 0;
    // 15x
    virtual void EndHailItem() = 0;
    // 15x
    virtual void RestorPlayerAngle() = 0;
    // 15x
    virtual void PlayEnvironmental(SoundID a0, float a1) = 0;
    // 15x
    virtual void createTimerEffect(int a0, float a1, float a2, float a3, float a4) = 0;
    // 14x
    virtual void WaitScene() = 0;
    // 14x
    virtual void AddItem(ScriptValue a0) = 0;
    // 14x
    virtual ScriptValue GetFromMode() = 0;
    // 13x
    virtual void PlayScene(int a0 /*opt*/, float a1 /*opt*/, int a2 /*opt*/) = 0;
    // 12x
    virtual void SetCameraAtBody(float a0, float a1, float a2, const char* a3) = 0;
    // 12x
    virtual void SetMiniGameStage(int a0) = 0;
    // 11x
    virtual void playerDefaultState() = 0;
    // 11x
    virtual void SetDungeonResurrectionPoint(MapId a0) = 0;
    // 11x
    virtual void StopEnvironmental(SoundID a0, float a1) = 0;
    // 10x
    virtual void switchDofPointGaze() = 0;
    // 10x
    virtual void SetDofApaerture(float a0, int a1) = 0;
    // 10x
    virtual void resetDofPointGaze() = 0;
    // 10x
    virtual void UnlockTrophy(int a0) = 0;
    // 10x
    virtual void SetStage(int a0) = 0;
    // 10x
    virtual void DestroyMiniGame() = 0;
    // 9x
    virtual void SetSunLightAngle(float a0, float a1) = 0;
    // 9x
    virtual void RestoreSunLightAngle() = 0;
    // 9x
    virtual void createBossWarpEffect(const char* a0) = 0;
    // 9x
    virtual void SetFieldResurrectionPoint(MapId a0) = 0;
    // 9x
    virtual void SetProgressFlag(int a0, int a1) = 0;
    // 9x
    virtual void StartMiniGame(int a0, ScriptValue a1 /*opt*/) = 0;
    // 8x
    virtual void WaitMain() = 0;
    // 8x
    virtual void FadeBlack() = 0;
    // 8x
    virtual void WhiteOut() = 0;
    // 8x
    virtual void setHeroGetBackFlag(int a0) = 0;
    // 8x
    virtual void SetPlayerSpeed(ScriptValue a0) = 0;
    // 8x
    virtual ScriptValue GetMiniGameStage() = 0;
    // 7x
    virtual void ContinueMiniGame() = 0;
    // 6x
    virtual void HealPlayerMp(int a0) = 0;
    // 6x
    virtual void SetDataSave(int a0) = 0;
    // 6x
    virtual void CreateGuard(int a0 /*opt*/, int a1 /*opt*/, int a2 /*opt*/, int a3 /*opt*/) = 0;
    // 6x
    virtual void StartBDTutorial() = 0;
    // 6x
    virtual ScriptValue IsBDPerfectClear() = 0;
    // 5x
    virtual void StartPlayerMotion(int a0) = 0;
    // 5x
    virtual void HealPlayerHp(int a0) = 0;
    // 5x
    virtual void MoveNpcAndY(const char* a0, float a1, float a2, float a3, float a4) = 0;
    // 5x
    virtual void PlayPanCamera2(float a0, float a1, float a2, float a3, float a4, float a5, float a6, float a7, float a8, float a9, float a10, float a11, float a12, float a13) = 0;
    // 5x
    virtual void WhiteIn() = 0;
    // 5x
    virtual void GetSetRace() = 0;
    // 4x
    virtual void resetFieldCamera() = 0;
    // 4x
    virtual void setPlayerAngle(int a0) = 0;
    // 4x
    virtual void pointLightOff() = 0;
    // 4x
    virtual ScriptValue GetDRTime() = 0;
    // 4x
    virtual void ResetBDPlayerSword() = 0;
    // 3x
    virtual void visibleEnemy(int a0) = 0;
    // 3x
    virtual void CreateSnake(int a0, int a1, int a2) = 0;
    // 3x
    virtual void CreateBee(int a0, int a1, int a2) = 0;
    // 3x
    virtual void CreateGolem(int a0, int a1, int a2) = 0;
    // 3x
    virtual void CreateKraken(int a0, int a1, int a2) = 0;
    // 3x
    virtual void CreateDragon(int a0, int a1, int a2) = 0;
    // 3x
    virtual void CreateDarkKnight(int a0, int a1, int a2) = 0;
    // 3x
    virtual void StartParallelLightAnime(int a0, float a1, float a2, float a3, float a4, float a5, float a6) = 0;
    // 3x
    virtual void SetParallelLight(float a0, float a1, float a2, float a3, float a4, float a5) = 0;
    // 3x
    virtual void SetBall(ScriptValue a0) = 0;
    // 3x
    virtual void SetItemEffectValue(int a0, ScriptValue a1) = 0;
    // 3x
    virtual ScriptValue GetMiniGameMaxStage() = 0;
    // 3x
    virtual ScriptValue GetBestStage() = 0;
    // 3x
    virtual ScriptValue IsFirstRace(int a0) = 0;
    // 3x
    virtual ScriptValue GetRaceBestRecord(int a0) = 0;
    // 3x
    virtual void EquipSword() = 0;
    // 2x
    virtual void SetPlayerVisible(int a0) = 0;
    // 2x
    virtual void StartFeedBack() = 0;
    // 2x
    virtual void EndFeedBack() = 0;
    // 2x
    virtual void AddMaxMP(int a0) = 0;
    // 2x
    virtual void setDarkPriestFlag(int a0) = 0;
    // 2x
    virtual void CreatePriest(int a0, int a1, int a2) = 0;
    // 2x
    virtual void WaitHpOrTime(int a0, int a1) = 0;
    // 2x
    virtual void PlaySceneScriptCamera(int a0, int a1, int a2) = 0;
    // 2x
    virtual void PlayPanCamera(float a0, float a1, int a2, float a3, float a4, float a5, float a6, float a7, int a8, float a9, float a10, float a11, float a12, float a13) = 0;
    // 2x
    virtual void DestinationPlayer(int a0, int a1, float a2) = 0;
    // 2x
    virtual void setPointLight(int a0, float a1, float a2, float a3) = 0;
    // 2x
    virtual void OpenDarknessTowerDoor() = 0;
    // 2x
    virtual void CreateBreaker(const char* a0, int a1) = 0;
    // 2x
    virtual void ResetColor() = 0;
    // 2x
    virtual void SetGuardMiss(float a0) = 0;
    // 2x
    virtual void SetDashRaceParam(ScriptValue a0, ScriptValue a1) = 0;
    // 2x
    virtual void SetUpGoalLine() = 0;
    // 2x
    virtual ScriptValue GetRaceRecord(int a0, ScriptValue a1) = 0;
    // 1x
    virtual void SetCaptureDOF() = 0;
    // 1x
    virtual void AddMaxHP(int a0) = 0;
    // 1x
    virtual void pushBlueSwitch(int a0, int a1) = 0;
    // 1x
    virtual void popBlueSwitch(int a0, int a1) = 0;
    // 1x
    virtual ScriptValue isUseLightItem() = 0;
    // 1x
    virtual void Ending() = 0;
    // 1x
    virtual void SetInheriting() = 0;
    // 1x
    virtual void createDarkTowerEffect(int a0, int a1, int a2) = 0;
    // 1x
    virtual void setEndingPointLigh(int a0, float a1, float a2, float a3) = 0;
    // 1x
    virtual void allEffectOff() = 0;
    // 1x
    virtual void StopSe(SoundID a0) = 0;
    // 1x
    virtual void ActiveLavaFountain() = 0;
    // 1x
    virtual void KnockBackNpc(const char* a0, int a1, int a2, float a3, int a4) = 0;
    // 1x
    virtual void createFairyGlareEffect(float a0, float a1, float a2) = 0;
    // 1x
    virtual void SetAutoCamera(float a0, float a1, float a2, const char* a3) = 0;
    // 1x
    virtual void offDarkTowerDoorEffect() = 0;
    // 1x
    virtual void HailItemNpcStart(const char* a0, int a1) = 0;
    // 1x
    virtual void SetSwordData() = 0;
    // 1x
    virtual ScriptValue IsNewGamePlus() = 0;
    // 1x
    virtual void ChangeSword(SwordId a0, SwordId a1) = 0;
    // 1x
    virtual void HandOverSwordAbility(SwordId a0, SwordId a1) = 0;
    // 1x
    virtual void SetSpelunkerModeFlg() = 0;
    // 1x
    virtual void CreateDevil(int a0, int a1, int a2) = 0;
    // 1x
    virtual void RestoreParallelLight() = 0;
    // 1x
    virtual void PlayGameOver() = 0;
    // 1x
    virtual void SetBreakOutParam(ScriptValue a0, ScriptValue a1) = 0;
    // 1x
    virtual ScriptValue IsBONoMissClear() = 0;
    // 1x
    virtual ScriptValue IsGuardMiss() = 0;
    // 1x
    virtual void SetRaceNewRecord() = 0;
    // 1x
    virtual ScriptValue IsUpdateBestTime() = 0;
    // 1x
    virtual ScriptValue GetLap() = 0;
    // 1x
    virtual ScriptValue GetMaxLap() = 0;
    // 1x
    virtual void CloseLapMessage() = 0;
    // 1x
    virtual void SetDRReady() = 0;
    // 1x
    virtual ScriptValue IsMoneyOK() = 0;
    // 1x
    virtual void LevelUpBlockTower() = 0;
    // 1x
    virtual void RestoreTowerStatusTempDraw() = 0;
    // 1x
    virtual void AddBonusMoney() = 0;
    // 1x
    virtual void BDStartResult() = 0;
    // 1x
    virtual ScriptValue GetNowDungeonNo() = 0;
    // 1x
    virtual void HealFairySpring() = 0;
    // 1x
    virtual void createFairyHealEffect() = 0;
};

// 1,351 call site
class IPackageManager {
public:
    virtual ~IPackageManager() = default;

    // 1,289x
    virtual void addNodeListElement(PackageId a0, PackageId a1, PackageId a2, const char* a3 /*opt*/) = 0;
    // 49x
    virtual void addDsbPackageElement(PackageId a0, const char* a1) = 0;
    // 13x
    virtual void addTexturePackageElement(PackageId a0, const char* a1) = 0;
};

// 72 call site
class IMapManager {
public:
    virtual ~IMapManager() = default;

    // 72x
    virtual void addLoadList(PackageId a0) = 0;
};

// 51 call site
class IBoss {
public:
    virtual ~IBoss() = default;

    // 12x
    virtual void AddArmColor(int a0, float a1, float a2, float a3) = 0;
    // 8x
    virtual void SetSummonItem(const char* a0) = 0;
    // 7x
    virtual void SetLifeBowlPosition(int a0, int a1) = 0;
    // 7x
    virtual void SetDropMoney(int a0, int a1, int a2) = 0;
    // 4x
    virtual void AddHandColor(float a0, float a1, float a2) = 0;
    // 4x
    virtual void AddLegColor(float a0, float a1, float a2) = 0;
    // 3x
    virtual void AddBodyColor(float a0, float a1, float a2) = 0;
    // 3x
    virtual void AddTailColor(float a0, float a1, float a2) = 0;
    // 1x
    virtual void SetChildDrop(const char* a0, int a1) = 0;
    // 1x
    virtual void AddHeadColor(float a0, float a1, float a2) = 0;
    // 1x
    virtual void AddPressColor(float a0, float a1, float a2) = 0;
};

// 10 call site
class Iobserver {
public:
    virtual ~Iobserver() = default;

    // 3x
    virtual void PlaySound(SoundID a0) = 0;
    // 2x
    virtual ScriptValue getSameTypeObservationObjectSum(ActorType a0) = 0;
    // 2x
    virtual ScriptValue getSameTypeObservationObject(ScriptValue a0, ActorType a1) = 0;
    // 1x
    virtual ScriptValue isEmptyObservationObject(ActorType a0, ScriptValue a1) = 0;
    // 1x
    virtual ScriptValue getEventObjectSum() = 0;
    // 1x
    virtual ScriptValue getEventObject(ScriptValue a0) = 0;
};

// 5 call site
class Iclub {
public:
    virtual ~Iclub() = default;

    // 4x
    virtual void setVisible(bool a0) = 0;
    // 1x
    virtual void SetPositionFromParent(ScriptValue a0, float a1, float a2, float a3) = 0;
};

// 2 call site
class Igimmick {
public:
    virtual ~Igimmick() = default;

    // 2x
    virtual ScriptValue isEnable() = 0;
};

