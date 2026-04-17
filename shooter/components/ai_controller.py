import pygame
from pygame.math import Vector2

from shooter.components.circle_collider import CircleCollider
from shooter.components.circle_render import CircleRender
from shooter.components.slider import Slider
from shooter.gameplay.actor_controller import ActorController


class AIAction:
    def __init__(
        self,
        moveDirection: Vector2 = Vector2(0.0, 0.0),
        attackPosition=None,
        dash: bool = False,
    ) -> None:
        self.moveDirection = Vector2(moveDirection)
        self.attackPosition = None if attackPosition is None else Vector2(attackPosition)
        self.dash = bool(dash)


class AIController(ActorController):
    def __init__(
        self,
        moveSpeed: float = 100.0,
        mapLimit: Vector2 = Vector2(800, 600),
        dashSpeed: float = 600.0,
        dashDuration: float = 0.12,
        dashCooldown: float = 0.6,
        attackDuration: float = 0.15,
        attackCooldown: float = 0.2,
        bulletSpeed: float = 500.0,
        radius: float = 20.0,
        color: pygame.Color = pygame.Color(255, 80, 80, 255),
        maxHp: int = 5,
    ) -> None:
        super().__init__(
            moveSpeed,
            mapLimit,
            dashSpeed,
            dashDuration,
            dashCooldown,
            attackDuration,
            attackCooldown,
            bulletSpeed,
            radius,
        )
        self._color = color
        self._maxHp = maxHp
        self._currentHp = maxHp
        self._hpbar = None
        self._moveIntent = Vector2(0.0, 0.0)
        self._pendingAttackIntent = None
        self._queuedDash = False

    def onInitialize(self) -> None:
        cpRender = CircleRender(self._size, self._color)
        cpRender.setOrderInLayer(20)
        cpColl = CircleCollider(self._size)
        self._hpbar = Slider(
            Vector2(30, 7),
            self._maxHp,
            self._currentHp,
            pygame.Color(255, 80, 80, 255),
        )
        self._hpbar.setOffset(Vector2(0, 25))
        self._hpbar.setOrderInLayer(30)
        self.getGameObject().addComponent(cpRender)
        self.getGameObject().addComponent(cpColl)
        self.getGameObject().addComponent(self._hpbar)

    def onUpdate(self, deltaTime: float) -> None:
        super().onUpdate(deltaTime)

    def setAction(self, action: AIAction) -> None:
        self._moveIntent = Vector2(action.moveDirection)
        self._pendingAttackIntent = None if action.attackPosition is None else Vector2(action.attackPosition)
        self._queuedDash = bool(action.dash)

    def getCurrentHp(self) -> int:
        return self._currentHp

    def getMaxHp(self) -> int:
        return self._maxHp

    def heal(self, value: int) -> None:
        self._currentHp = min(self._maxHp, self._currentHp + max(0, int(value)))
        if self._hpbar is not None:
            self._hpbar.setValue(self._currentHp)

    def damage(self, value: int) -> None:
        from ai.environment.battle_event_bus import BattleEventBus

        self._currentHp = max(0, self._currentHp - int(value))
        if self._hpbar is not None:
            self._hpbar.setValue(self._currentHp)

        if self._currentHp <= 0:
            self.getGameObject().destroy()
            BattleEventBus.getInstance().emit(
                "death",
                target=self.getGameObject().getTag(),
            )

    def getMoveIntent(self) -> Vector2:
        moveDirection = Vector2(self._moveIntent)
        if moveDirection.length_squared() > 0.0:
            return moveDirection.normalize()
        return moveDirection

    def getAttackIntent(self):
        if self._pendingAttackIntent is None:
            return None

        attackPosition = Vector2(self._pendingAttackIntent)
        self._pendingAttackIntent = None
        return attackPosition

    def getDashIntent(self) -> bool:
        dashIntent = self._queuedDash
        self._queuedDash = False
        return dashIntent
