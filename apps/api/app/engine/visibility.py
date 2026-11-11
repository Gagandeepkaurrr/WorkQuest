from app.engine.types import Scenario, WorldState


def available_artifacts(state: WorldState,scenario: Scenario):
    return [a for a in scenario.artifacts if all(r in state.opened for r in a.requires)]


def eligible_character_facts(state: WorldState,scenario: Scenario,teammate_id: str):
    available={a.id for a in available_artifacts(state,scenario)}
    return [f for f in scenario.facts if teammate_id in f.teammates and (f.artifact_id is None or (f.artifact_id in state.opened and f.artifact_id in available))]
