from dataclasses import dataclass

from ai.environment.battle_session import BattleSession
from shooter.scenes.game_scene import GameScene


@dataclass(slots=True)
class BattleBundle:
    """전투 씬과 전투 세션을 함께 묶어 보관합니다."""

    scene: GameScene
    session: BattleSession


def createBattleBundle(
    externalControl: bool = False,
    policyA=None,
    policyB=None,
    autoLearn: bool = False,
    checkpointPathA=None,
    checkpointPathB=None,
    explore: bool = True,
    saveOnEpisodeEnd: bool = True,
) -> BattleBundle:
    """전투 씬과 세션을 생성해 한 번에 반환합니다."""

    scene = GameScene()
    session = BattleSession(
        scene=scene,
        externalControl=externalControl,
        policyA=policyA,
        policyB=policyB,
        autoLearn=autoLearn,
        checkpointPathA=checkpointPathA,
        checkpointPathB=checkpointPathB,
        explore=explore,
        saveOnEpisodeEnd=saveOnEpisodeEnd,
    )
    return BattleBundle(scene=scene, session=session)
