from dataclasses import dataclass
from pathlib import Path

from models.policies import AIPolicy, PolicyFactory, PolicySpec


TRAINING_POLICY_KIND = "qtable"


@dataclass(slots=True)
class TrainingSetup:
    specA: PolicySpec
    specB: PolicySpec
    policyA: AIPolicy
    policyB: AIPolicy
    loadedA: bool
    loadedB: bool


def loadTrainingSetup(
    policyKind: str = TRAINING_POLICY_KIND,
    epsilon: float = 0.25,
    epsilonMin: float = 0.05,
    epsilonDecay: float = 0.997,
) -> TrainingSetup:
    policyOptions = {
        "epsilon": epsilon,
        "epsilonMin": epsilonMin,
        "epsilonDecay": epsilonDecay,
    }
    specA = PolicySpec(
        kind=policyKind,
        checkpointPath=Path("models") / f"{policyKind}_policy_a.gz",
        options=policyOptions,
    )
    specB = PolicySpec(
        kind=policyKind,
        checkpointPath=Path("models") / f"{policyKind}_policy_b.gz",
        options=policyOptions,
    )
    policyA = PolicyFactory.create(specA)
    policyB = PolicyFactory.create(specB)
    loadedA = PolicyFactory.loadCheckpoint(policyA, specA.checkpointPath)
    loadedB = PolicyFactory.loadCheckpoint(policyB, specB.checkpointPath)
    return TrainingSetup(specA, specB, policyA, policyB, loadedA, loadedB)
