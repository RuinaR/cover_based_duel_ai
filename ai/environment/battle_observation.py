from pygame.math import Vector2

from engine.managers.object_manager import ObjectManager
from shooter.components.ai_controller import AIController
from shooter.scenes.game_scene import GameScene


class BattleObservationBuilder:
    """전투 씬에서 정책이 사용할 관측 정보를 구성합니다."""
    MAX_TRACKED_ENEMY_BULLETS = 2

    def __init__(self, scene: GameScene) -> None:
        self._scene = scene

    def buildForBattle(self) -> dict:
        """양쪽 AI용 관측 딕셔너리를 한 번에 생성합니다."""
        controllerA = self._scene.getController(GameScene.TAG_A)
        controllerB = self._scene.getController(GameScene.TAG_B)
        if controllerA is None or controllerB is None:
            return {}

        return {
            GameScene.TAG_A: self._buildForController(controllerA, controllerB),
            GameScene.TAG_B: self._buildForController(controllerB, controllerA),
        }

    def _buildForController(self, controller: AIController, enemyController: AIController) -> dict:
        selfPos = controller.getGameObject().getPosition()
        enemyPos = enemyController.getGameObject().getPosition()
        toEnemy = enemyPos - selfPos
        coverInfo = self._buildCoverObservation(selfPos, enemyPos)
        itemInfo = self._buildItemObservation(selfPos, enemyPos)
        bulletInfo = self._buildEnemyBulletObservation(
            selfPos,
            enemyController.getGameObject().getTag(),
        )

        directionToEnemy = Vector2(0.0, 0.0)
        if toEnemy.length_squared() > 0.0:
            directionToEnemy = toEnemy.normalize()

        return {
            "self_tag": controller.getGameObject().getTag(),
            "self_position": (selfPos.x, selfPos.y),
            "enemy_position": (enemyPos.x, enemyPos.y),
            "enemy_direction": (directionToEnemy.x, directionToEnemy.y),
            "distance_to_enemy": toEnemy.length(),
            "self_hp": controller.getCurrentHp(),
            "self_hp_max": controller.getMaxHp(),
            "enemy_hp": enemyController.getCurrentHp(),
            "enemy_hp_max": enemyController.getMaxHp(),
            "state": controller.getStateName(),
            "enemy_state": enemyController.getStateName(),
            "can_dash": controller.canDash(),
            "can_attack": controller.canAttack(),
            "enemy_can_dash": enemyController.canDash(),
            "enemy_can_attack": enemyController.canAttack(),
            "self_dash_cooldown_ratio": controller.getDashCooldownRatio(),
            "self_attack_cooldown_ratio": controller.getAttackCooldownRatio(),
            "enemy_dash_cooldown_ratio": enemyController.getDashCooldownRatio(),
            "enemy_attack_cooldown_ratio": enemyController.getAttackCooldownRatio(),
            "self_dash_cooldown_remaining": controller.getDashCooldownRemaining(),
            "self_attack_cooldown_remaining": controller.getAttackCooldownRemaining(),
            "enemy_dash_cooldown_remaining": enemyController.getDashCooldownRemaining(),
            "enemy_attack_cooldown_remaining": enemyController.getAttackCooldownRemaining(),
            "self_has_attack_buff": controller.hasAttackBuff(),
            "enemy_has_attack_buff": enemyController.hasAttackBuff(),
            "self_attack_buff_ratio": controller.getAttackBuffRatio(),
            "enemy_attack_buff_ratio": enemyController.getAttackBuffRatio(),
            "cover_positions": coverInfo["cover_positions"],
            "nearest_cover_position": coverInfo["nearest_cover_position"],
            "nearest_cover_direction": coverInfo["nearest_cover_direction"],
            "nearest_cover_distance": coverInfo["nearest_cover_distance"],
            "enemy_nearest_cover_distance": coverInfo["enemy_nearest_cover_distance"],
            "item_active": itemInfo["item_active"],
            "item_position": itemInfo["item_position"],
            "self_item_direction": itemInfo["self_item_direction"],
            "self_item_distance": itemInfo["self_item_distance"],
            "enemy_item_direction": itemInfo["enemy_item_direction"],
            "enemy_item_distance": itemInfo["enemy_item_distance"],
            "enemy_bullet_count": bulletInfo["enemy_bullet_count"],
            "enemy_bullet_positions": bulletInfo["enemy_bullet_positions"],
            "nearest_enemy_bullet_position": bulletInfo["nearest_enemy_bullet_position"],
            "nearest_enemy_bullet_direction": bulletInfo["nearest_enemy_bullet_direction"],
            "nearest_enemy_bullet_distance": bulletInfo["nearest_enemy_bullet_distance"],
            "second_enemy_bullet_distance": bulletInfo["second_enemy_bullet_distance"],
        }

    def _buildCoverObservation(self, selfPos: Vector2, enemyPos: Vector2) -> dict:
        coverPositions = []
        nearestCoverPos = (0.0, 0.0)
        nearestCoverDirection = (0.0, 0.0)
        nearestCoverDistance = 9999.0
        enemyNearestCoverDistance = 9999.0

        for coverObj in self._scene.getCoverObjects():
            if coverObj is None or coverObj.isDestroyed():
                continue

            coverPos = coverObj.getPosition()
            coverPositions.append((coverPos.x, coverPos.y))

            toCoverSelf = coverPos - selfPos
            distanceSelf = toCoverSelf.length()
            if distanceSelf < nearestCoverDistance:
                nearestCoverDistance = distanceSelf
                nearestCoverPos = (coverPos.x, coverPos.y)
                nearestCoverDirection = self._normalizeTuple(toCoverSelf)

            toCoverEnemy = coverPos - enemyPos
            distanceEnemy = toCoverEnemy.length()
            if distanceEnemy < enemyNearestCoverDistance:
                enemyNearestCoverDistance = distanceEnemy

        if not coverPositions:
            nearestCoverDistance = 9999.0
            enemyNearestCoverDistance = 9999.0

        return {
            "cover_positions": tuple(coverPositions),
            "nearest_cover_position": nearestCoverPos,
            "nearest_cover_direction": nearestCoverDirection,
            "nearest_cover_distance": nearestCoverDistance,
            "enemy_nearest_cover_distance": enemyNearestCoverDistance,
        }

    def _buildItemObservation(self, selfPos: Vector2, enemyPos: Vector2) -> dict:
        itemObject = self._scene.getActiveItemObject()
        if itemObject is None:
            return {
                "item_active": False,
                "item_position": (0.0, 0.0),
                "self_item_direction": (0.0, 0.0),
                "self_item_distance": 9999.0,
                "enemy_item_direction": (0.0, 0.0),
                "enemy_item_distance": 9999.0,
            }

        itemPos = itemObject.getPosition()
        selfToItem = itemPos - selfPos
        enemyToItem = itemPos - enemyPos

        return {
            "item_active": True,
            "item_position": (itemPos.x, itemPos.y),
            "self_item_direction": self._normalizeTuple(selfToItem),
            "self_item_distance": selfToItem.length(),
            "enemy_item_direction": self._normalizeTuple(enemyToItem),
            "enemy_item_distance": enemyToItem.length(),
        }

    def _buildEnemyBulletObservation(self, selfPos: Vector2, enemyTag: str) -> dict:
        enemyBulletTag = f"bullet_{enemyTag}"
        bulletEntries: list[tuple[float, Vector2]] = []

        for gameObject in ObjectManager.getInstance().getObjectList():
            if gameObject is None or gameObject.isDestroyed():
                continue
            if gameObject.getTag() != enemyBulletTag:
                continue

            bulletPos = gameObject.getPosition()
            bulletEntries.append(((bulletPos - selfPos).length(), bulletPos))

        bulletEntries.sort(key=lambda entry: entry[0])
        trackedBullets = bulletEntries[: self.MAX_TRACKED_ENEMY_BULLETS]

        nearestDistance = 9999.0
        secondDistance = 9999.0
        nearestPosition = (0.0, 0.0)
        nearestDirection = (0.0, 0.0)
        bulletPositions = []

        for index, (distance, bulletPos) in enumerate(trackedBullets):
            bulletPositions.append((bulletPos.x, bulletPos.y))
            if index == 0:
                nearestDistance = distance
                nearestPosition = (bulletPos.x, bulletPos.y)
                nearestDirection = self._normalizeTuple(bulletPos - selfPos)
            elif index == 1:
                secondDistance = distance

        return {
            "enemy_bullet_count": len(bulletEntries),
            "enemy_bullet_positions": tuple(bulletPositions),
            "nearest_enemy_bullet_position": nearestPosition,
            "nearest_enemy_bullet_direction": nearestDirection,
            "nearest_enemy_bullet_distance": nearestDistance,
            "second_enemy_bullet_distance": secondDistance,
        }

    def _normalizeTuple(self, value: Vector2) -> tuple[float, float]:
        if value.length_squared() == 0.0:
            return (0.0, 0.0)

        normalized = value.normalize()
        return (normalized.x, normalized.y)
