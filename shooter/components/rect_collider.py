from engine.core.collider import Collider
from pygame import Vector2



class RectCollider(Collider):

    def __init__(self, wh : Vector2) -> None:
        super().__init__()
        self._wh = Vector2(wh)

    def getWH(self) -> Vector2:
        return self._wh
    
    def setWH(self, value:Vector2) -> None:
        self._wh = value
