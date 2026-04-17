import pygame

from engine.core.component import Component
from shooter.components.circle_collider import CircleCollider
from shooter.components.circle_render import CircleRender
from shooter.gameplay.combat_tuning import (
    ATTACK_BUFF_DURATION_SECONDS,
    ITEM_COLOR,
    ITEM_HEAL_AMOUNT,
    ITEM_RADIUS,
    ITEM_RENDER_ORDER,
)


class Item(Component):
    def __init__(self, scene, radius: float = ITEM_RADIUS) -> None:
        super().__init__()
        self._scene = scene
        self._radius = float(radius)
        self._collected = False

    def onInitialize(self) -> None:
        collider = CircleCollider(self._radius)
        render = CircleRender(self._radius, ITEM_COLOR)
        render.setOrderInLayer(ITEM_RENDER_ORDER)
        self.getGameObject().addComponent(collider)
        self.getGameObject().addComponent(render)

    def onStart(self) -> None:
        pass

    def onUpdate(self, deltaTime: float) -> None:
        pass

    def onRelease(self) -> None:
        self._scene.clearActiveItemObject(self.getGameObject())

    def onCollisionEnter(self, other) -> None:
        self._tryCollect(other)

    def onCollisionStay(self, other) -> None:
        self._tryCollect(other)

    def onCollisionExit(self, other) -> None:
        pass

    def _tryCollect(self, other) -> None:
        if self._collected:
            return

        otherObj = other.getGameObject()
        if otherObj is None:
            return

        collectorTag = otherObj.getTag()
        if collectorTag.startswith("bullet_") or collectorTag in ("cover", "item_creator", "item"):
            return

        controller = self._resolveCollectorController(otherObj)
        if controller is None:
            return

        from ai.environment.battle_event_bus import BattleEventBus

        self._collected = True
        hpBefore = controller.getCurrentHp()
        maxHp = controller.getMaxHp()
        controller.heal(ITEM_HEAL_AMOUNT)
        healedHp = controller.getCurrentHp() > hpBefore and hpBefore < maxHp
        controller.grantAttackBuff(ATTACK_BUFF_DURATION_SECONDS)
        BattleEventBus.getInstance().emit(
            "item_pickup",
            target=collectorTag,
            healed_hp=healedHp,
            item_position=(
                self.getGameObject().getPosition().x,
                self.getGameObject().getPosition().y,
            ),
        )
        self.getGameObject().destroy()

    def _resolveCollectorController(self, gameObject):
        from shooter.components.ai_controller import AIController
        from shooter.components.player_controller import PlayerController

        controller = gameObject.getComponent(AIController)
        if controller is not None:
            return controller

        return gameObject.getComponent(PlayerController)
