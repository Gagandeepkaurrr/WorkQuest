from functools import lru_cache
from pathlib import Path
from app.core.errors import AppError
from app.engine.types import Scenario
from app.engine.mechanics import checkout_v1,inventory_v1,analytics_v1

REGISTRY={'checkout_v1':checkout_v1,'inventory_v1':inventory_v1,'analytics_v1':analytics_v1}
CONTENT=Path(__file__).resolve().parents[2]/'content'/'scenarios'


def mechanics(scenario: Scenario):
    module=REGISTRY.get(scenario.mechanics_id)
    if not module:raise AppError('SCENARIO_VERSION_UNSUPPORTED','This mechanics version is unavailable.',409)
    return module


@lru_cache
def load_scenario(slug: str) -> Scenario:
    allowed={p.parent.name:p for p in CONTENT.glob('*/scenario.json')}
    if slug not in allowed:raise AppError('NOT_FOUND','Scenario unavailable.',404)
    return Scenario.model_validate_json(allowed[slug].read_text())
