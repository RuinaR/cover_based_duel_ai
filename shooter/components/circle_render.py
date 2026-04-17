import pygame

from engine.core.render_component import RenderComponent

class CircleRender(RenderComponent):

    def __init__(self, radius : float, color) -> None:
        super().__init__()
        self._radius = radius
        self._color = color

    def getRadius(self) -> float:
        return self._radius
    
    def setRadius(self, value : float) -> None:
        self._radius = value

    def getColor(self):
        return self._color

    def setColor(self, value) -> None:
        self._color = value

    def render(self, screen) -> None:
        if self._gameObject is None:
            return

        position = self._gameObject.getPosition()
        pygame.draw.circle(
            screen,
            self._color,
            (int(position.x), int(position.y)),
            int(self._radius),
        )
