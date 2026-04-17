from engine.core.scene import Scene

from engine.core.game_object import GameObject
from shooter.components.button import Button
from shooter.components.label import Label

from pygame import Vector2

import engine.platform.screen_info as screen_info

class StartScene(Scene):

    def __init__(self, message : str = None, onStart = None)->None:
        self._message = message
        self._onStart = onStart

    def initialize(self) -> None:
        btnObj = GameObject("btn")
        btnObj.setPosition(Vector2(screen_info.SCREEN_WIDTH / 2, screen_info.SCREEN_HEIGHT / 2))
        cpBtn = Button(Vector2(200,100), "[Start]", self._startGame)
        cpBtn.setFontSize(50)
        btnObj.addComponent(cpBtn)
        btnObj.registerObjectManager()

        labelObj = GameObject("label")
        labelObj.setPosition(Vector2(screen_info.SCREEN_WIDTH / 2, screen_info.SCREEN_HEIGHT / 4))
        cpLabel = Label("Cover-Based Duel AI")
        labelObj.addComponent(cpLabel)
        labelObj.registerObjectManager()

        if self._message is not None:
            labelObj2 = GameObject("label")
            labelObj2.setPosition(Vector2(screen_info.SCREEN_WIDTH / 2,\
                                          screen_info.SCREEN_HEIGHT - screen_info.SCREEN_HEIGHT / 4))
            cpLabel2 = Label(self._message)
            labelObj2.addComponent(cpLabel2)
            labelObj2.registerObjectManager()
        pass

    def release(self) -> None:
        pass

    def _startGame(self) -> None:
        if callable(self._onStart):
            self._onStart()

