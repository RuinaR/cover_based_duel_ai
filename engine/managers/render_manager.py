
class RenderManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if RenderManager._initialized:
            return

        self._renderList = []

        RenderManager._initialized = True

    @classmethod
    def getInstance(cls):
        return cls()
     
    def reset(self) -> None:
        self._renderList.clear()

    
    def addRender(self, render) -> None:
        if render is None:
            return

        if render in self._renderList:
            self.sortRenderList()
            return

        self._renderList.append(render)
        self.sortRenderList()

    def removeRender(self, render) -> None:
        if render in self._renderList:
            self._renderList.remove(render)

    def render(self, screen) -> None:
        for render in self._renderList[:]:
            if render.isDestroyed():
                self._renderList.remove(render)
                continue

            render.render(screen)

    def sortRenderList(self) -> None:
        self._renderList.sort(key=lambda render: render.getOrderInLayer())


