import pygame
from pygame import Vector2
from engine.core.render_component import RenderComponent


class RectRender(RenderComponent):

    def __init__(self, wh:Vector2, color) -> None:
        super().__init__()
        self._wh = Vector2(wh)
        self._color = color

    def getWH(self) -> Vector2:
        return self._wh

    def setWH(self, value: Vector2) -> None:
        self._wh = value

    def getColor(self):
        return self._color

    def setColor(self, value) -> None:
        self._color = value

    def render(self, screen) -> None:
        if self._gameObject is None:
            return

        position = self._gameObject.getPosition()
        left = position.x - (self._wh.x / 2)
        top = position.y - (self._wh.y / 2)

        pygame.draw.rect(
            screen,
            self._color,
            pygame.Rect(
                int(left),
                int(top),
                int(self._wh.x),
                int(self._wh.y),
            ),
        )
