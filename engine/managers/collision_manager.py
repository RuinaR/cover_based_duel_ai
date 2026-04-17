from shooter.components.circle_collider import CircleCollider
from shooter.components.point_collider import PointCollider
from shooter.components.rect_collider import RectCollider


class CollisionManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if CollisionManager._initialized:
            return

        self._colliderList = []
        self._pendingAddList = []
        self._collisionPairs = set()

        CollisionManager._initialized = True

    @classmethod
    def getInstance(cls):
        return cls()

    def initialize(self) -> None:
        self._colliderList.clear()
        self._pendingAddList.clear()
        self._collisionPairs.clear()

    def release(self) -> None:
        self._colliderList.clear()
        self._pendingAddList.clear()
        self._collisionPairs.clear()

    def addCollider(self, collider):
        if collider is None:
            raise ValueError("Collider is None.")

        if collider in self._colliderList or collider in self._pendingAddList:
            return collider

        self._pendingAddList.append(collider)
        return collider

    def removeCollider(self, collider) -> None:
        if collider is None:
            return

        if collider in self._pendingAddList:
            self._pendingAddList.remove(collider)

        if collider in self._colliderList:
            self._colliderList.remove(collider)

        self._removeColliderPairs(collider)

    def update(self) -> None:
        self._processPendingAdd()
        self._cleanupDestroyedColliders()

        currentPairs = set()
        colliderCount = len(self._colliderList)

        for i in range(colliderCount):
            colliderA = self._colliderList[i]
            if self._isInvalidCollider(colliderA):
                continue

            for j in range(i + 1, colliderCount):
                colliderB = self._colliderList[j]
                if self._isInvalidCollider(colliderB):
                    continue

                if colliderA.getGameObject() is colliderB.getGameObject():
                    continue

                if not self._checkCollision(colliderA, colliderB):
                    continue

                currentPairs.add(self._makePair(colliderA, colliderB))

        enteredPairs = currentPairs - self._collisionPairs
        stayedPairs = currentPairs & self._collisionPairs
        exitedPairs = self._collisionPairs - currentPairs

        for colliderA, colliderB in enteredPairs:
            self._notifyEnter(colliderA, colliderB)

        for colliderA, colliderB in stayedPairs:
            self._notifyStay(colliderA, colliderB)

        for colliderA, colliderB in exitedPairs:
            self._notifyExit(colliderA, colliderB)

        self._collisionPairs = currentPairs

    def _processPendingAdd(self) -> None:
        if len(self._pendingAddList) == 0:
            return

        for collider in self._pendingAddList[:]:
            if self._isInvalidCollider(collider):
                continue

            self._colliderList.append(collider)

        self._pendingAddList.clear()

    def _cleanupDestroyedColliders(self) -> None:
        for collider in self._colliderList[:]:
            if self._isInvalidCollider(collider):
                self._colliderList.remove(collider)
                self._removeColliderPairs(collider)

        for collider in self._pendingAddList[:]:
            if self._isInvalidCollider(collider):
                self._pendingAddList.remove(collider)
                self._removeColliderPairs(collider)

    def _removeColliderPairs(self, collider) -> None:
        removedPairs = {
            pair for pair in self._collisionPairs
            if collider in pair
        }

        for colliderA, colliderB in removedPairs:
            other = colliderB if colliderA is collider else colliderA
            if not self._isInvalidCollider(other):
                self._notifyExitByDestroy(other)

        self._collisionPairs -= removedPairs

    def _makePair(self, colliderA, colliderB):
        if id(colliderA) < id(colliderB):
            return (colliderA, colliderB)
        return (colliderB, colliderA)

    def _isInvalidCollider(self, collider) -> bool:
        if collider is None:
            return True
        if collider.isDestroyed():
            return True

        gameObject = collider.getGameObject()
        if gameObject is None:
            return True

        return gameObject.isDestroyed()

    def _checkCollision(self, colliderA, colliderB) -> bool:
        if isinstance(colliderA, PointCollider):
            if isinstance(colliderB, PointCollider):
                return self._checkPointPoint(colliderA, colliderB)
            if isinstance(colliderB, CircleCollider):
                return self._checkPointCircle(colliderA, colliderB)
            if isinstance(colliderB, RectCollider):
                return self._checkPointRect(colliderA, colliderB)

        if isinstance(colliderA, CircleCollider):
            if isinstance(colliderB, PointCollider):
                return self._checkPointCircle(colliderB, colliderA)
            if isinstance(colliderB, CircleCollider):
                return self._checkCircleCircle(colliderA, colliderB)
            if isinstance(colliderB, RectCollider):
                return self._checkCircleRect(colliderA, colliderB)

        if isinstance(colliderA, RectCollider):
            if isinstance(colliderB, PointCollider):
                return self._checkPointRect(colliderB, colliderA)
            if isinstance(colliderB, CircleCollider):
                return self._checkCircleRect(colliderB, colliderA)
            if isinstance(colliderB, RectCollider):
                return self._checkRectRect(colliderA, colliderB)

        return False

    def _checkPointPoint(self, pointA, pointB) -> bool:
        positionA = pointA.getGameObject().getPosition()
        positionB = pointB.getGameObject().getPosition()
        return positionA == positionB

    def _checkPointCircle(self, pointCollider, circleCollider) -> bool:
        point = pointCollider.getGameObject().getPosition()
        center = circleCollider.getGameObject().getPosition()
        radius = circleCollider.getRadius()

        delta = point - center
        return delta.length_squared() <= radius * radius

    def _checkPointRect(self, pointCollider, rectCollider) -> bool:
        point = pointCollider.getGameObject().getPosition()
        left, top, right, bottom = self._getRectBounds(rectCollider)

        return left <= point.x <= right and top <= point.y <= bottom

    def _checkCircleCircle(self, circleA, circleB) -> bool:
        centerA = circleA.getGameObject().getPosition()
        centerB = circleB.getGameObject().getPosition()
        totalRadius = circleA.getRadius() + circleB.getRadius()

        delta = centerA - centerB
        return delta.length_squared() <= totalRadius * totalRadius

    def _checkCircleRect(self, circleCollider, rectCollider) -> bool:
        center = circleCollider.getGameObject().getPosition()
        radius = circleCollider.getRadius()
        left, top, right, bottom = self._getRectBounds(rectCollider)

        closestX = self._clamp(center.x, left, right)
        closestY = self._clamp(center.y, top, bottom)

        dx = center.x - closestX
        dy = center.y - closestY
        return (dx * dx) + (dy * dy) <= radius * radius

    def _checkRectRect(self, rectA, rectB) -> bool:
        leftA, topA, rightA, bottomA = self._getRectBounds(rectA)
        leftB, topB, rightB, bottomB = self._getRectBounds(rectB)

        return (
            leftA <= rightB and
            rightA >= leftB and
            topA <= bottomB and
            bottomA >= topB
        )

    def _getRectBounds(self, rectCollider):
        center = rectCollider.getGameObject().getPosition()
        wh = rectCollider.getWH()
        halfW = wh.x / 2.0
        halfH = wh.y / 2.0

        left = center.x - halfW
        top = center.y - halfH
        right = center.x + halfW
        bottom = center.y + halfH
        return left, top, right, bottom

    def _clamp(self, value: float, minValue: float, maxValue: float) -> float:
        return max(minValue, min(value, maxValue))

    def _notifyEnter(self, colliderA, colliderB) -> None:
        gameObjectA = colliderA.getGameObject()
        gameObjectB = colliderB.getGameObject()
        if gameObjectA is None or gameObjectB is None:
            return

        gameObjectA.onCollisionEnter(colliderB)
        gameObjectB.onCollisionEnter(colliderA)

    def _notifyStay(self, colliderA, colliderB) -> None:
        gameObjectA = colliderA.getGameObject()
        gameObjectB = colliderB.getGameObject()
        if gameObjectA is None or gameObjectB is None:
            return

        gameObjectA.onCollisionStay(colliderB)
        gameObjectB.onCollisionStay(colliderA)

    def _notifyExit(self, colliderA, colliderB) -> None:
        gameObjectA = colliderA.getGameObject()
        gameObjectB = colliderB.getGameObject()
        if gameObjectA is None or gameObjectB is None:
            return

        gameObjectA.onCollisionExit(colliderB)
        gameObjectB.onCollisionExit(colliderA)

    def _notifyExitByDestroy(self, collider) -> None:
        gameObject = collider.getGameObject()
        if gameObject is None:
            return

        gameObject.onCollisionExit(None)
