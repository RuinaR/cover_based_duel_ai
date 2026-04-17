from engine.core.state import State


class ActorState(State):
    def __init__(self, controller, name: str) -> None:
        super().__init__(controller, name)

    def getController(self):
        return self._owner


class ActorIdleState(ActorState):
    def __init__(self, controller) -> None:
        super().__init__(controller, "idle")

    def update(self, deltaTime: float) -> None:
        controller = self.getController()
        attackPosition = controller.getAttackIntent()
        if attackPosition is not None and controller.canAttack():
            controller.enterAttack(attackPosition)
            return

        moveDirection = controller.getMoveIntent()
        if moveDirection.length_squared() > 0.0:
            controller.setLastMoveDirection(moveDirection)
            if controller.canDash() and controller.getDashIntent():
                controller.enterDash()
                return

        if moveDirection.length_squared() > 0.0:
            controller.enterMove(moveDirection)


class ActorMoveState(ActorState):
    def __init__(self, controller) -> None:
        super().__init__(controller, "move")

    def update(self, deltaTime: float) -> None:
        controller = self.getController()
        attackPosition = controller.getAttackIntent()
        if attackPosition is not None and controller.canAttack():
            controller.enterAttack(attackPosition)
            return

        moveDirection = controller.getMoveIntent()
        if moveDirection.length_squared() > 0.0:
            controller.setLastMoveDirection(moveDirection)

        if controller.canDash() and controller.getDashIntent():
            controller.enterDash()
            return

        if moveDirection.length_squared() == 0.0:
            controller.enterIdle()
            return

        controller.move(moveDirection, controller.getMoveSpeed(), deltaTime)


class ActorDashState(ActorState):
    def __init__(self, controller) -> None:
        super().__init__(controller, "dash")

    def enter(self) -> None:
        self.getController().consumeDash()

    def update(self, deltaTime: float) -> None:
        controller = self.getController()
        controller.move(controller.getDashDirection(), controller.getDashSpeed(), deltaTime)

        if self.getElapsed() >= controller.getDashDuration():
            moveDirection = controller.getMoveIntent()
            if moveDirection.length_squared() > 0.0:
                controller.enterMove(moveDirection)
            else:
                controller.enterIdle()


class ActorAttackState(ActorState):
    def __init__(self, controller) -> None:
        super().__init__(controller, "attack")

    def enter(self) -> None:
        controller = self.getController()
        attackPosition = controller.getPendingAttackPosition()
        if attackPosition is None:
            controller.enterIdle()
            return

        direction = attackPosition - controller.getGameObject().getPosition()
        if direction.length_squared() == 0.0:
            controller.enterIdle()
            return

        controller.fire(direction.normalize())
        controller.consumeAttack()

    def update(self, deltaTime: float) -> None:
        controller = self.getController()
        if self.getElapsed() >= controller.getAttackDuration():
            moveDirection = controller.getMoveIntent()
            if moveDirection.length_squared() > 0.0:
                controller.enterMove(moveDirection)
            else:
                controller.enterIdle()
