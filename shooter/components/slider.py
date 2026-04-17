import pygame
from pygame.math import Vector2

from engine.core.render_component import RenderComponent


class Slider(RenderComponent):
    def __init__(
        self,
        size: Vector2,
        maxValue: float,
        value: float,
        fillColor,
        backgroundColor = pygame.Color(255,255,255,255),
        offset: Vector2 = Vector2(0.0, 0.0),
        sortingLayer: int = 0,
        borderWidth: int = 0,
        borderColor=None,
    ) -> None:
        super().__init__()
        self._size = Vector2(size)
        self._maxValue = max(0.0, float(maxValue))
        self._value = 0.0
        self._fillColor = fillColor
        self._backgroundColor = backgroundColor
        self._offset = Vector2(offset)
        self._borderWidth = max(0, int(borderWidth))
        self._borderColor = borderColor
        self.setOrderInLayer(sortingLayer)
        self.setValue(value)

    def getSize(self) -> Vector2:
        return Vector2(self._size)

    def setSize(self, value: Vector2) -> None:
        self._size = Vector2(value)

    def getOffset(self) -> Vector2:
        return Vector2(self._offset)

    def setOffset(self, value: Vector2) -> None:
        self._offset = Vector2(value)

    def getMaxValue(self) -> float:
        return self._maxValue

    def setMaxValue(self, value: float) -> None:
        self._maxValue = max(0.0, float(value))
        self.setValue(self._value)

    def getValue(self) -> float:
        return self._value

    def setValue(self, value: float) -> None:
        if self._maxValue <= 0.0:
            self._value = 0.0
            return

        self._value = max(0.0, min(float(value), self._maxValue))

    def getRatio(self) -> float:
        if self._maxValue <= 0.0:
            return 0.0
        return self._value / self._maxValue

    def setRatio(self, ratio: float) -> None:
        clampedRatio = max(0.0, min(float(ratio), 1.0))
        self.setValue(self._maxValue * clampedRatio)

    def getFillColor(self):
        return self._fillColor

    def setFillColor(self, value) -> None:
        self._fillColor = value

    def getBackgroundColor(self):
        return self._backgroundColor

    def setBackgroundColor(self, value) -> None:
        self._backgroundColor = value

    def getBorderWidth(self) -> int:
        return self._borderWidth

    def setBorderWidth(self, value: int) -> None:
        self._borderWidth = max(0, int(value))

    def getBorderColor(self):
        return self._borderColor

    def setBorderColor(self, value) -> None:
        self._borderColor = value

    def render(self, screen) -> None:
        if self.getGameObject() is None:
            return

        center = self.getGameObject().getPosition() + self._offset
        left = center.x - (self._size.x / 2.0)
        top = center.y - (self._size.y / 2.0)

        backgroundRect = pygame.Rect(
            int(left),
            int(top),
            int(self._size.x),
            int(self._size.y),
        )

        pygame.draw.rect(screen, self._backgroundColor, backgroundRect)

        fillWidth = int(self._size.x * self.getRatio())
        if fillWidth > 0:
            fillRect = pygame.Rect(
                int(left),
                int(top),
                fillWidth,
                int(self._size.y),
            )
            pygame.draw.rect(screen, self._fillColor, fillRect)

        if self._borderWidth > 0 and self._borderColor is not None:
            pygame.draw.rect(
                screen,
                self._borderColor,
                backgroundRect,
                self._borderWidth,
            )
