import math

from pygame.math import Vector2

from shooter.components.bullet import Bullet
from shooter.gameplay.combat_tuning import (
    ATTACK_BUFF_DURATION_SECONDS,
    SPREAD_SHOT_ANGLE_DEGREES,
)
from shooter.components.circle_collider import CircleCollider
from shooter.components.point_collider import PointCollider
from shooter.components.rect_collider import RectCollider
from shooter.gameplay.actor_state import (
    ActorAttackState,
    ActorDashState,
    ActorIdleState,
    ActorMoveState,
)
from engine.core.component import Component
from engine.core.game_object import GameObject
from engine.core.state import StateMachine


class ActorController(Component):
    def __init__(
        self,
        moveSpeed: float = 100.0,
        mapLimit: Vector2 = Vector2(800,600),
        dashSpeed: float = 600.0,
        dashDuration: float = 0.12,
        dashCooldown: float = 0.6,
        attackDuration: float = 0.15,
        attackCooldown: float = 0.2,
        bulletSpeed: float = 500.0,
        size: float = 20.0
    ) -> None:
        super().__init__()
        self._moveSpeed = moveSpeed
        self._mapLimit = Vector2(mapLimit)
        self._dashSpeed = dashSpeed
        self._dashDuration = dashDuration
        self._dashCooldown = dashCooldown
        self._attackDuration = attackDuration
        self._attackCooldown = attackCooldown
        self._bulletSpeed = bulletSpeed
        self._size = size

        self._dashCooldownRemain = 0.0
        self._attackCooldownRemain = 0.0
        self._dashDirection = Vector2(0.0, 0.0)
        self._lastMoveDirection = Vector2(1.0, 0.0)
        self._pendingAttackPosition = None
        self._blockingColliders = set()
        self._attackBuffRemain = 0.0

        self._stateMachine = StateMachine(self)
        self._idleState = ActorIdleState(self)
        self._moveState = ActorMoveState(self)
        self._dashState = ActorDashState(self)
        self._attackState = ActorAttackState(self)

    def onStart(self) -> None:
        self._stateMachine.changeState(self._idleState)

    def onUpdate(self, deltaTime: float) -> None:
        self._updateCooldown(deltaTime)
        self._updateBuffs(deltaTime)
        self._stateMachine.update(deltaTime)

    def _updateCooldown(self, deltaTime: float) -> None:
        self._dashCooldownRemain = max(0.0, self._dashCooldownRemain - deltaTime)
        self._attackCooldownRemain = max(0.0, self._attackCooldownRemain - deltaTime)

    def _updateBuffs(self, deltaTime: float) -> None:
        self._attackBuffRemain = max(0.0, self._attackBuffRemain - deltaTime)

    def enterIdle(self) -> None:
        self._stateMachine.changeState(self._idleState)

    def enterMove(self, moveDirection: Vector2) -> None:
        self._lastMoveDirection = Vector2(moveDirection)
        self._stateMachine.changeState(self._moveState)

    def enterDash(self) -> None:
        direction = Vector2(self._lastMoveDirection)
        if direction.length_squared() == 0.0:
            return

        self._dashDirection = direction.normalize()
        self._stateMachine.changeState(self._dashState)

    def enterAttack(self, attackPosition: Vector2) -> None:
        self._pendingAttackPosition = Vector2(attackPosition)
        self._stateMachine.changeState(self._attackState)

    def canDash(self) -> bool:
        return self._dashCooldownRemain <= 0.0

    def canAttack(self) -> bool:
        return self._attackCooldownRemain <= 0.0

    def move(self, direction: Vector2, speed: float, deltaTime: float) -> None:
        moveDelta = Vector2(direction) * speed * deltaTime
        moveDelta = self._filterMoveByCollision(moveDelta)
        newPosition = self.getGameObject().getPosition() + moveDelta
        newPosition.x = max(0.0, min(newPosition.x, self._mapLimit.x))
        newPosition.y = max(0.0, min(newPosition.y, self._mapLimit.y))
        self.getGameObject().setPosition(newPosition)

    def fire(self, directionNormal: Vector2) -> GameObject:
        shotDirections = self._buildShotDirections(directionNormal)
        primaryBullet = None
        for index, shotDirection in enumerate(shotDirections):
            bullet = self._makeBullet(shotDirection, self._bulletSpeed)
            if index == 0:
                primaryBullet = bullet
        return primaryBullet

    def consumeDash(self) -> None:
        self._dashCooldownRemain = self._dashCooldown

    def consumeAttack(self) -> None:
        self._attackCooldownRemain = self._attackCooldown

    def setLastMoveDirection(self, value: Vector2) -> None:
        self._lastMoveDirection = Vector2(value)

    def getDashDirection(self) -> Vector2:
        return Vector2(self._dashDirection)

    def getMoveSpeed(self) -> float:
        return self._moveSpeed

    def getDashSpeed(self) -> float:
        return self._dashSpeed

    def getDashDuration(self) -> float:
        return self._dashDuration

    def getDashCooldown(self) -> float:
        return self._dashCooldown

    def getDashCooldownRemaining(self) -> float:
        return self._dashCooldownRemain

    def getDashCooldownRatio(self) -> float:
        if self._dashCooldown <= 0.0:
            return 0.0
        return min(1.0, max(0.0, self._dashCooldownRemain / self._dashCooldown))

    def getAttackDuration(self) -> float:
        return self._attackDuration

    def getAttackCooldown(self) -> float:
        return self._attackCooldown

    def getAttackCooldownRemaining(self) -> float:
        return self._attackCooldownRemain

    def getAttackCooldownRatio(self) -> float:
        if self._attackCooldown <= 0.0:
            return 0.0
        return min(1.0, max(0.0, self._attackCooldownRemain / self._attackCooldown))

    def getPendingAttackPosition(self):
        return self._pendingAttackPosition

    def getStateName(self):
        return self._stateMachine.getCurrentStateName()

    def getLastMoveDirection(self) -> Vector2:
        return Vector2(self._lastMoveDirection)

    def grantAttackBuff(self, duration: float = ATTACK_BUFF_DURATION_SECONDS) -> None:
        self._attackBuffRemain = max(self._attackBuffRemain, float(duration))

    def hasAttackBuff(self) -> bool:
        return self._attackBuffRemain > 0.0

    def getAttackBuffRemaining(self) -> float:
        return self._attackBuffRemain

    def getAttackBuffRatio(self) -> float:
        if ATTACK_BUFF_DURATION_SECONDS <= 0.0:
            return 0.0
        return min(1.0, max(0.0, self._attackBuffRemain / ATTACK_BUFF_DURATION_SECONDS))

    def onCollisionEnter(self, other) -> None:
        self._addBlockingCollider(other)

    def onCollisionStay(self, other) -> None:
        self._addBlockingCollider(other)

    def onCollisionExit(self, other) -> None:
        if other is None:
            self._cleanupBlockingColliders()
            return

        self._blockingColliders.discard(other)

    def _makeBullet(self, directionNormal: Vector2, speed: float) -> GameObject:
        ownerTag = self.getGameObject().getTag()
        bulletObj = GameObject(f"bullet_{ownerTag}")
        bulletObj.addComponent(Bullet(directionNormal, speed))
        bulletObj.setPosition(self.getGameObject().getPosition() + directionNormal * (self._size + 5))
        bulletObj.registerObjectManager()
        return bulletObj

    def _buildShotDirections(self, directionNormal: Vector2) -> list[Vector2]:
        direction = Vector2(directionNormal)
        if direction.length_squared() == 0.0:
            return [Vector2(1.0, 0.0)]

        direction = direction.normalize()
        if not self.hasAttackBuff():
            return [direction]

        spreadAngle = SPREAD_SHOT_ANGLE_DEGREES
        return [
            self._rotateDirection(direction, -spreadAngle),
            direction,
            self._rotateDirection(direction, spreadAngle),
        ]

    def _rotateDirection(self, direction: Vector2, angleDegrees: float) -> Vector2:
        radians = math.radians(angleDegrees)
        cosValue = math.cos(radians)
        sinValue = math.sin(radians)
        return Vector2(
            (direction.x * cosValue) - (direction.y * sinValue),
            (direction.x * sinValue) + (direction.y * cosValue),
        ).normalize()

    def _addBlockingCollider(self, other) -> None:
        if other is None:
            return

        if not self.shouldBlockByCollider(other):
            return

        self._blockingColliders.add(other)

    def _cleanupBlockingColliders(self) -> None:
        validColliders = set()
        for collider in self._blockingColliders:
            if collider is None:
                continue
            if collider.isDestroyed():
                continue

            gameObject = collider.getGameObject()
            if gameObject is None or gameObject.isDestroyed():
                continue

            validColliders.add(collider)

        self._blockingColliders = validColliders

    def _filterMoveByCollision(self, moveDelta: Vector2) -> Vector2:
        self._cleanupBlockingColliders()
        if moveDelta.length_squared() == 0.0:
            return moveDelta

        filteredDelta = Vector2(moveDelta)
        selfBounds = self._getSelfBounds()
        selfCenter = self.getGameObject().getPosition()

        for collider in self._blockingColliders:
            otherBounds = self._getColliderBounds(collider)
            if otherBounds is None:
                continue

            otherCenter = collider.getGameObject().getPosition()

            if (
                filteredDelta.x > 0.0 and
                otherCenter.x >= selfCenter.x and
                self._hasVerticalOverlap(selfBounds, otherBounds)
            ):
                filteredDelta.x = 0.0

            if (
                filteredDelta.x < 0.0 and
                otherCenter.x <= selfCenter.x and
                self._hasVerticalOverlap(selfBounds, otherBounds)
            ):
                filteredDelta.x = 0.0

            if (
                filteredDelta.y > 0.0 and
                otherCenter.y >= selfCenter.y and
                self._hasHorizontalOverlap(selfBounds, otherBounds)
            ):
                filteredDelta.y = 0.0

            if (
                filteredDelta.y < 0.0 and
                otherCenter.y <= selfCenter.y and
                self._hasHorizontalOverlap(selfBounds, otherBounds)
            ):
                filteredDelta.y = 0.0

        return filteredDelta

    def _getSelfBounds(self):
        pointCollider = self.getGameObject().getComponent(PointCollider)
        if pointCollider is not None:
            position = self.getGameObject().getPosition()
            return (position.x, position.y, position.x, position.y)

        circleCollider = self.getGameObject().getComponent(CircleCollider)
        if circleCollider is not None:
            position = self.getGameObject().getPosition()
            radius = circleCollider.getRadius()
            return (
                position.x - radius,
                position.y - radius,
                position.x + radius,
                position.y + radius,
            )

        rectCollider = self.getGameObject().getComponent(RectCollider)
        if rectCollider is not None:
            position = self.getGameObject().getPosition()
            wh = rectCollider.getWH()
            halfW = wh.x / 2.0
            halfH = wh.y / 2.0
            return (
                position.x - halfW,
                position.y - halfH,
                position.x + halfW,
                position.y + halfH,
            )

        position = self.getGameObject().getPosition()
        half = self._size / 2.0
        return (
            position.x - half,
            position.y - half,
            position.x + half,
            position.y + half,
        )

    def _getColliderBounds(self, collider):
        if collider is None:
            return None

        gameObject = collider.getGameObject()
        if gameObject is None:
            return None

        position = gameObject.getPosition()

        if isinstance(collider, PointCollider):
            return (position.x, position.y, position.x, position.y)

        if isinstance(collider, CircleCollider):
            radius = collider.getRadius()
            return (
                position.x - radius,
                position.y - radius,
                position.x + radius,
                position.y + radius,
            )

        if isinstance(collider, RectCollider):
            wh = collider.getWH()
            halfW = wh.x / 2.0
            halfH = wh.y / 2.0
            return (
                position.x - halfW,
                position.y - halfH,
                position.x + halfW,
                position.y + halfH,
            )

        return None

    def _hasVerticalOverlap(self, boundsA, boundsB) -> bool:
        return boundsA[1] <= boundsB[3] and boundsA[3] >= boundsB[1]

    def _hasHorizontalOverlap(self, boundsA, boundsB) -> bool:
        return boundsA[0] <= boundsB[2] and boundsA[2] >= boundsB[0]
    


    #Override

    def getMoveIntent(self) -> Vector2:
        return Vector2(0.0, 0.0)

    def getAttackIntent(self):
        return None

    def getDashIntent(self) -> bool:
        return False

    def shouldBlockByCollider(self, other) -> bool:
        return True
