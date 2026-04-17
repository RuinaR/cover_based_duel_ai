from engine.core.component import Component
from shooter.components.rect_collider import RectCollider
from shooter.components.rect_render import RectRender
from pygame import Vector2
from pygame import Color

class Cover(Component):
    def __init__(self, size : float) -> None:
        super().__init__()
        self._size = size


    #Override
    def onInitialize(self) -> None:
        cpColl = RectCollider(Vector2(self._size, self._size))
        cpRender = RectRender(Vector2(self._size, self._size), Color(165,42,42,255))
        self.getGameObject().addComponent(cpColl)
        self.getGameObject().addComponent(cpRender)
        pass

    def onStart(self) -> None:
        pass

    def onUpdate(self, deltaTime: float) -> None:
        pass

    def onRelease(self) -> None:
        pass

    def onCollisionEnter(self, other) -> None:
        pass

    def onCollisionStay(self, other) -> None:
        pass

    def onCollisionExit(self, other) -> None:
        pass
