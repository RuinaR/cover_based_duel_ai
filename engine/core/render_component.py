from engine.core.component import Component
from engine.managers.render_manager import RenderManager

class RenderComponent(Component):
    def __init__(self) -> None:
        super().__init__()
        self._sortingLayer = 0
    
    def getOrderInLayer(self) -> int:
        return self._sortingLayer
    
    def setOrderInLayer(self, value : int) -> None:
        if self._sortingLayer != value :
            self._sortingLayer = value
            RenderManager.getInstance().sortRenderList()

    def render(self, screen) -> None:
        pass

    def onInitialize(self) -> None:
        RenderManager.getInstance().addRender(self)


    def onRelease(self) -> None:
        RenderManager.getInstance().removeRender(self)
