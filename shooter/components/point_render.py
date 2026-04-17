import pygame

from engine.core.render_component import RenderComponent


class PointRender(RenderComponent):

    def __init__(self, color, size: float = 3.0) -> None:
        super().__init__()
        self._color = color
        self._size = size

    def getColor(self):
        return self._color

    def setColor(self, value) -> None:
        self._color = value

    def getSize(self) -> float:
        return self._size

    def setSize(self, value: float) -> None:
        self._size = value

    def render(self, screen) -> None:
        if self._gameObject is None:
            return

        position = self._gameObject.getPosition()
        pygame.draw.circle(
            screen,
            self._color,
            (int(position.x), int(position.y)),
            int(self._size),
        )
