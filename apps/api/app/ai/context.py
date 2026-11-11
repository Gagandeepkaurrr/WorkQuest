from app.ai.contracts import CharacterContext,ContextFact
from app.core.errors import AppError
from app.engine.transitions import allowed_next_actions
from app.engine.types import Scenario,WorldState
from app.engine.visibility import eligible_character_facts


def build_character_context(state: WorldState,scenario: Scenario,teammate_id: str,transcript: list[dict],message: str) -> CharacterContext:
    teammate=next((t for t in scenario.teammates if t.id==teammate_id),None)
    if not teammate:raise AppError('NOT_FOUND','Teammate unavailable.',404)
    context=CharacterContext(teammate_id=teammate.id,name=teammate.name,role=teammate.role,persona=teammate.persona,briefing=scenario.metadata.description,fallback=teammate.fallback,facts=[ContextFact(id=f.id,text=f.text,artifact_id=f.artifact_id) for f in eligible_character_facts(state,scenario,teammate_id)],allowed_action_ids=allowed_next_actions(state,scenario),transcript=[{'role':str(t['role']),'text':str(t['text'])[:500]} for t in transcript[-6:]],message=message)
    # Conservative byte bound: no paid token-count call and no hidden over-budget context.
    while len(context.model_dump_json().encode())>6000 and context.transcript:context.transcript.pop(0)
    if len(context.model_dump_json().encode())>6000:raise AppError('VALIDATION_ERROR','This message is too large with the current evidence. Ask a shorter question.',422)
    return context
