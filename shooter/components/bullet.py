import pygame
from pygame import Vector2

from engine.core.component import Component


class Bullet(Component):
    DODGE_REWARD_DISTANCE = 80.0

    def __init__(self, normalDir: Vector2, velocity: float) -> None:
        super().__init__()
        self._dir = Vector2(normalDir)
        self._velocity = velocity
        self._elapse = 5.0
        self._ownerTag = ""
        self._targetTag = None
        self._closestTargetDistance = float("inf")
        self._resolvedOutcome = False

    def onInitialize(self) -> None:
        from shooter.components.point_collider import PointCollider
        from shooter.components.point_render import PointRender

        self._ownerTag = self._resolveOwnerTag()
        self._targetTag = self._resolveTargetTag(self._ownerTag)
        self.getGameObject().addComponent(PointCollider())
        self.getGameObject().addComponent(PointRender(pygame.Color(255, 0, 0, 255)))

    def onStart(self) -> None:
        pass

    def onUpdate(self, deltaTime: float) -> None:
        self._trackTargetDistance()

        addVec = self._dir * self._velocity * deltaTime
        self.getGameObject().setPosition(self.getGameObject().getPosition() + addVec)
        self._trackTargetDistance()

        self._elapse -= deltaTime
        if self._elapse <= 0:
            self._emitDodgeRewardIfNeeded()
            self.getGameObject().destroy()

    def onRelease(self) -> None:
        pass

    def onCollisionEnter(self, other) -> None:
        from ai.environment.battle_event_bus import BattleEventBus
        from shooter.components.ai_controller import AIController
        from shooter.components.player_controller import PlayerController

        otherObj = other.getGameObject()
        if otherObj is None:
            return

        otherTag = otherObj.getTag()
        if otherTag.startswith("bullet_"):
            return
        if otherTag == self._ownerTag:
            return
        if not self._canDamageTarget(otherTag):
            return

        if otherTag == "player":
            self.getGameObject().destroy()
            targetController = otherObj.getComponent(PlayerController)
            if targetController is not None:
                self._resolvedOutcome = True
                targetController.damage(1)
                BattleEventBus.getInstance().emit(
                    "hit",
                    source=self._ownerTag,
                    target=otherTag,
                    damage=1,
                    bullet_tag=self.getGameObject().getTag(),
                )
            return

        if otherTag in ("ai_a", "ai_b"):
            self.getGameObject().destroy()
            aiController = otherObj.getComponent(AIController)
            if aiController is not None:
                self._resolvedOutcome = True
                aiController.damage(1)
                BattleEventBus.getInstance().emit(
                    "hit",
                    source=self._ownerTag,
                    target=otherTag,
                    damage=1,
                    bullet_tag=self.getGameObject().getTag(),
                )
            return

        if otherTag == "cover":
            self._resolvedOutcome = True
            self._emitCoverBlockReward()
            self.getGameObject().destroy()

    def onCollisionStay(self, other) -> None:
        otherObj = other.getGameObject()
        if otherObj is None:
            return

        otherTag = otherObj.getTag()
        if otherTag.startswith("bullet_"):
            return
        if otherTag == self._ownerTag:
            return
        if otherTag == "cover" and not self._resolvedOutcome:
            self._resolvedOutcome = True
            self._emitCoverBlockReward()
        self.getGameObject().destroy()

    def onCollisionExit(self, other) -> None:
        pass

    def _resolveOwnerTag(self) -> str:
        bulletTag = self.getGameObject().getTag()
        prefix = "bullet_"
        if bulletTag.startswith(prefix):
            return bulletTag[len(prefix):]
        return ""

    def _resolveTargetTag(self, ownerTag: str) -> str | None:
        if ownerTag == "ai_a":
            return "ai_b"
        if ownerTag == "ai_b":
            return "ai_a"
        return None

    def _canDamageTarget(self, otherTag: str) -> bool:
        if self._targetTag is not None:
            return otherTag == self._targetTag
        return otherTag not in ("", self._ownerTag) and not otherTag.startswith("bullet_")

    def _trackTargetDistance(self) -> None:
        targetObj = self._getTargetObject()
        if targetObj is None:
            return

        bulletPos = self.getGameObject().getPosition()
        targetPos = targetObj.getPosition()
        self._closestTargetDistance = min(
            self._closestTargetDistance,
            (targetPos - bulletPos).length(),
        )

    def _getTargetObject(self):
        if self._targetTag is None:
            return None

        from engine.managers.object_manager import ObjectManager

        for gameObject in ObjectManager.getInstance().getObjectList():
            if gameObject.isDestroyed():
                continue
            if gameObject.getTag() == self._targetTag:
                return gameObject
        return None

    def _emitDodgeRewardIfNeeded(self) -> None:
        if self._resolvedOutcome:
            return
        if self._targetTag is None:
            return
        if self._closestTargetDistance > self.DODGE_REWARD_DISTANCE:
            return

        from ai.environment.battle_event_bus import BattleEventBus

        self._resolvedOutcome = True
        BattleEventBus.getInstance().emit(
            "dodge",
            source=self._ownerTag,
            target=self._targetTag,
            bullet_tag=self.getGameObject().getTag(),
        )

    def _emitCoverBlockReward(self) -> None:
        if self._targetTag is None:
            return

        from ai.environment.battle_event_bus import BattleEventBus

        BattleEventBus.getInstance().emit(
            "cover_block",
            source=self._ownerTag,
            target=self._targetTag,
            bullet_tag=self.getGameObject().getTag(),
        )
