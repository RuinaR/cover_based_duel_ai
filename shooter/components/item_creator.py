import random

from pygame.math import Vector2

from engine.core.component import Component
from engine.core.game_object import GameObject
from shooter.components.item import Item
from shooter.gameplay.combat_tuning import (
    ITEM_RADIUS,
    ITEM_SPAWN_ATTEMPTS,
    ITEM_SPAWN_INTERVAL_SECONDS,
    ITEM_SPAWN_MARGIN,
)
from shooter.components.rect_collider import RectCollider


class ItemCreator(Component):
    def __init__(
        self,
        scene,
        spawnInterval: float = ITEM_SPAWN_INTERVAL_SECONDS,
        itemRadius: float = ITEM_RADIUS,
        seed: int | None = None,
    ) -> None:
        super().__init__()
        self._scene = scene
        self._spawnInterval = float(spawnInterval)
        self._itemRadius = float(itemRadius)
        self._elapsed = 0.0
        self._rng = random.Random(seed)

    def onStart(self) -> None:
        self._elapsed = 0.0

    def onUpdate(self, deltaTime: float) -> None:
        self._elapsed += deltaTime
        if self._elapsed < self._spawnInterval:
            return

        activeItem = self._scene.getActiveItemObject()
        if activeItem is not None and not activeItem.isDestroyed():
            return

        spawnPosition = self._findSpawnPosition()
        if spawnPosition is None:
            return

        self._elapsed = 0.0
        itemObject = GameObject("item")
        itemObject.setPosition(spawnPosition)
        itemObject.addComponent(Item(self._scene, radius=self._itemRadius))
        self._scene.setActiveItemObject(itemObject)
        itemObject.registerObjectManager()

    def _findSpawnPosition(self) -> Vector2 | None:
        mapSize = self._scene.getMapSize()
        margin = self._itemRadius + ITEM_SPAWN_MARGIN
        minX = margin
        maxX = max(margin, mapSize.x - margin)
        minY = margin
        maxY = max(margin, mapSize.y - margin)

        for _ in range(ITEM_SPAWN_ATTEMPTS):
            position = Vector2(
                self._rng.uniform(minX, maxX),
                self._rng.uniform(minY, maxY),
            )
            if not self._overlapsCover(position):
                return position

        return None

    def _overlapsCover(self, position: Vector2) -> bool:
        for coverObject in self._scene.getCoverObjects():
            if coverObject is None or coverObject.isDestroyed():
                continue

            rectCollider = coverObject.getComponent(RectCollider)
            if rectCollider is None:
                continue

            halfSize = rectCollider.getWH() / 2.0
            coverPos = coverObject.getPosition()
            left = coverPos.x - halfSize.x - self._itemRadius
            right = coverPos.x + halfSize.x + self._itemRadius
            top = coverPos.y - halfSize.y - self._itemRadius
            bottom = coverPos.y + halfSize.y + self._itemRadius

            if left <= position.x <= right and top <= position.y <= bottom:
                return True

        return False
