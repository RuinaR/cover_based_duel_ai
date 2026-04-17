from engine.core.collider import Collider

class CircleCollider(Collider):
    def __init__(self, radius:float) -> None:
        super().__init__()
        self._radius = radius

    def getRadius(self) -> float:
        return self._radius
    
    def setRadius(self, value:float) -> None:
        self._radius = value
    
