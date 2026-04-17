import pygame
from pygame.math import Vector2

from engine.core.render_component import RenderComponent
from engine.platform.pygame_input import PyGameInput


class Button(RenderComponent):
    def __init__(
        self,
        size: Vector2, 
        text: str,
        onClick,
        color = pygame.Color(200, 200, 200, 255),
        textColor=pygame.Color(0, 0, 0, 255),
        fontSize: int = 18,
        offset: Vector2 = Vector2(0.0, 0.0),
        sortingLayer: int = 100,
    ) -> None:
        super().__init__()
        self._size = Vector2(size)
        self._baseColor = color
        self._text = text
        self._onClick = onClick
        self._textColor = textColor
        self._fontSize = fontSize
        self._offset = Vector2(offset)
        self._isHovered = False
        self._isPressed = False
        self._font = None
        self.setOrderInLayer(sortingLayer)

    def getSize(self) -> Vector2:
        return Vector2(self._size)

    def setSize(self, value: Vector2) -> None:
        self._size = Vector2(value)

    def getOffset(self) -> Vector2:
        return Vector2(self._offset)

    def setOffset(self, value: Vector2) -> None:
        self._offset = Vector2(value)

    def getText(self) -> str:
        return self._text

    def setText(self, value: str) -> None:
        self._text = value

    def setFontSize(self, value: int) -> None:
        self._fontSize = value

    def getFontSize(self) -> int:
        return self._fontSize

    def setOnClick(self, value) -> None:
        self._onClick = value

    def onUpdate(self, deltaTime: float) -> None:
        if self.getGameObject() is None:
            return

        mousePos = Vector2(pygame.mouse.get_pos())
        self._isHovered = self._containsPoint(mousePos)

        for event in PyGameInput.getInstance().getEventInfo():
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._isHovered:
                    self._isPressed = True

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                wasPressed = self._isPressed
                self._isPressed = False
                if wasPressed and self._isHovered and callable(self._onClick):
                    self._onClick()

    def render(self, screen) -> None:
        if self.getGameObject() is None:
            return

        self._ensureFont()
        left, top = self._getTopLeft()
        rect = pygame.Rect(int(left), int(top), int(self._size.x), int(self._size.y))
        pygame.draw.rect(screen, self._getCurrentColor(), rect)

        if self._font is None:
            return

        textSurface = self._font.render(self._text, True, self._textColor)
        textRect = textSurface.get_rect(center=rect.center)
        screen.blit(textSurface, textRect)

    def _getCurrentColor(self):
        if self._isPressed:
            return self._brightenColor(self._baseColor, 40)
        if self._isHovered:
            return self._brightenColor(self._baseColor, 20)
        return self._baseColor

    def _brightenColor(self, color, amount: int):
        return pygame.Color(
            min(255, color.r + amount),
            min(255, color.g + amount),
            min(255, color.b + amount),
            color.a,
        )

    def _containsPoint(self, point: Vector2) -> bool:
        left, top = self._getTopLeft()
        right = left + self._size.x
        bottom = top + self._size.y
        return left <= point.x <= right and top <= point.y <= bottom

    def _getTopLeft(self):
        # Button uses the GameObject position as the rectangle center.
        center = self.getGameObject().getPosition() + self._offset
        left = center.x - (self._size.x / 2.0)
        top = center.y - (self._size.y / 2.0)
        return left, top

    def _ensureFont(self) -> None:
        if self._font is not None:
            return
        if not pygame.font.get_init():
            pygame.font.init()
        self._font = pygame.font.Font(None, self._fontSize)
