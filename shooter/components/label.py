import pygame
from pygame.math import Vector2

from engine.core.render_component import RenderComponent


class Label(RenderComponent):
    def __init__(
        self,
        text: str,
        color=pygame.Color(255, 255, 255, 255),
        fontSize: int = 24,
        offset: Vector2 = Vector2(0.0, 0.0),
        sortingLayer: int = 110,
    ) -> None:
        super().__init__()
        self._text = text
        self._color = color
        self._fontSize = fontSize
        self._offset = Vector2(offset)
        self._font = None
        self.setOrderInLayer(sortingLayer)

    def getText(self) -> str:
        return self._text

    def setText(self, value: str) -> None:
        self._text = value

    def getColor(self):
        return self._color

    def setColor(self, value) -> None:
        self._color = value

    def getFontSize(self) -> int:
        return self._fontSize

    def setFontSize(self, value: int) -> None:
        self._fontSize = max(1, int(value))
        self._font = None

    def getOffset(self) -> Vector2:
        return Vector2(self._offset)

    def setOffset(self, value: Vector2) -> None:
        self._offset = Vector2(value)

    def render(self, screen) -> None:
        if self.getGameObject() is None:
            return

        self._ensureFont()
        if self._font is None:
            return

        center = self.getGameObject().getPosition() + self._offset
        textSurface = self._font.render(self._text, True, self._color)
        textRect = textSurface.get_rect(center=(int(center.x), int(center.y)))
        screen.blit(textSurface, textRect)

    def _ensureFont(self) -> None:
        if self._font is not None:
            return
        if not pygame.font.get_init():
            pygame.font.init()
        self._font = pygame.font.Font(None, self._fontSize)
