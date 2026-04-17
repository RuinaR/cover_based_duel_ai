import pygame
from pygame.math import Vector2

import engine.platform.screen_info as screen_info
from shooter.components.ai_controller import AIController
from shooter.components.cover import Cover
from shooter.components.item_creator import ItemCreator
from engine.core.game_object import GameObject
from engine.core.scene import Scene


class GameScene(Scene):
    """전투 씬의 시작 오브젝트를 생성하고 참조를 제공합니다."""

    TAG_A = "ai_a"
    TAG_B = "ai_b"

    def __init__(self) -> None:
        self._map = Vector2(screen_info.SCREEN_WIDTH, screen_info.SCREEN_HEIGHT)
        self._aiAObject = None
        self._aiBObject = None
        self._aiAController = None
        self._aiBController = None
        self._coverObjects = []
        self._itemCreatorObject = None
        self._activeItemObject = None

    def initialize(self) -> None:
        self._createAgents()
        self._createCoverObjects()
        self._createItemCreator()
        self._registerWorldObjects()

    def release(self) -> None:
        pass

    def getMapSize(self) -> Vector2:
        return Vector2(self._map)

    def getController(self, tag: str):
        if tag == GameScene.TAG_A:
            return self._aiAController
        if tag == GameScene.TAG_B:
            return self._aiBController
        return None

    def getCoverObjects(self) -> list:
        return self._coverObjects[:]

    def getActiveItemObject(self):
        if self._activeItemObject is not None and self._activeItemObject.isDestroyed():
            self._activeItemObject = None
        return self._activeItemObject

    def setActiveItemObject(self, itemObject) -> None:
        self._activeItemObject = itemObject

    def clearActiveItemObject(self, itemObject=None) -> None:
        if itemObject is None or self._activeItemObject is itemObject:
            self._activeItemObject = None

    def _createAgents(self) -> None:
        self._aiAObject = GameObject(GameScene.TAG_A)
        self._aiAObject.setPosition(Vector2(self._map.x * 0.1, self._map.y / 2))
        self._aiAController = AIController()
        self._aiAObject.addComponent(self._aiAController)

        self._aiBObject = GameObject(GameScene.TAG_B)
        self._aiBObject.setPosition(Vector2(self._map.x - (self._map.x * 0.1), self._map.y / 2))
        self._aiBController = AIController(color=pygame.Color(80, 160, 255, 255))
        self._aiBObject.addComponent(self._aiBController)

    def _createCoverObjects(self) -> None:
        coverTop = GameObject("cover")
        coverTop.setPosition(Vector2(self._map.x / 2, self._map.y * 0.25))
        coverTop.addComponent(Cover(80))

        coverBottom = GameObject("cover")
        coverBottom.setPosition(Vector2(self._map.x / 2, self._map.y - (self._map.y * 0.25)))
        coverBottom.addComponent(Cover(80))

        coverCenter = GameObject("cover")
        coverCenter.setPosition(Vector2(self._map.x / 2, self._map.y / 2))
        coverCenter.addComponent(Cover(80))

        self._coverObjects = [coverTop, coverBottom, coverCenter]

    def _createItemCreator(self) -> None:
        self._itemCreatorObject = GameObject("item_creator")
        self._itemCreatorObject.addComponent(ItemCreator(self))

    def _registerWorldObjects(self) -> None:
        self._aiAObject.registerObjectManager()
        self._aiBObject.registerObjectManager()
        for coverObject in self._coverObjects:
            coverObject.registerObjectManager()
        if self._itemCreatorObject is not None:
            self._itemCreatorObject.registerObjectManager()
