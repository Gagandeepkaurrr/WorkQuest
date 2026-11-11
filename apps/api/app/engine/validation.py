import json
import re
from pydantic import ValidationError
from app.engine.commands import validate_command
from app.engine.projections import project_visible_state
from app.engine.registry import load_scenario,mechanics
from app.engine.scoring import communication_status,evaluate_score
from app.engine.transitions import apply_command,initial_state
from app.engine.types import Command,Scenario,Strict,canonical_hash


class ValidationReport(Strict):
    passed: bool
    content_hash: str
    errors: list[str]
    golden_score: int | None = None
    golden_time: int | None = None


def validate_scenario(definition: dict) -> ValidationReport:
    hashed=canonical_hash(definition);errors=[]
    if len(json.dumps(definition).encode())>2*1024*1024:return ValidationReport(passed=False,content_hash=hashed,errors=['Definition exceeds 2 MiB.'])
    try:s=Scenario.model_validate(definition)
    except ValidationError as exc:return ValidationReport(passed=False,content_hash=hashed,errors=[str(e['loc'])+': '+e['msg'] for e in exc.errors()])
    m=mechanics(s);artifact_ids={a.id for a in s.artifacts};fact_ids={f.id for f in s.facts};action_ids={a.id for a in s.action_catalog}
    for collection,name in [(s.artifacts,'artifact'),(s.facts,'fact'),(s.action_catalog,'action'),(s.diagnosis_choices,'diagnosis'),(s.hints,'hint')]:
        if len({x.id for x in collection})!=len(collection):errors.append(f'Duplicate {name} IDs.')
    if {t.id for t in s.teammates}!={'maya','leo'}:errors.append('Exactly Maya and Leo are required.')
    if action_ids!=set(m.COSTS):errors.append('Actions must match the registered mechanics exactly.')
    if s.rubric.weights!={'diagnosis':20,'outcome':40,'verification':20,'communication':10,'judgment':10}:errors.append('Rubric weights must be 20/40/20/10/10.')
    if s.rubric.cause_id not in {c.id for c in s.diagnosis_choices}:errors.append('Diagnosis references an unknown choice.')
    if set(s.rubric.diagnosis_artifacts)-artifact_ids:errors.append('Diagnosis references an unknown artifact.')
    if len(s.metadata.objectives)!=4:errors.append('Exactly four deterministic outcome objectives are required.')
    templates={'checkout_v1':'checkout-outage','inventory_v1':'inventory-race','analytics_v1':'analytics-timezone'}
    if s.initial_state!=load_scenario(templates[s.mechanics_id]).initial_state:errors.append('Initial state must match the reviewed registered mechanics fixture.')
    for a in s.artifacts:
        if set(a.requires)-artifact_ids or a.id in a.requires:errors.append(f'Invalid artifact prerequisite: {a.id}.')
    for f in s.facts:
        if f.artifact_id and f.artifact_id not in artifact_ids:errors.append(f'Invalid fact source: {f.id}.')
    for h in s.hints:
        if set(h.requires)-artifact_ids:errors.append(f'Invalid hint prerequisite: {h.id}.')
    for a in s.action_catalog:
        if a.id not in m.COSTS:continue
        if a.cost!=m.COSTS[a.id] or a.requires!=m.REQUIRES.get(a.id,[]):errors.append(f'Unregistered action cost or prerequisites: {a.id}.')
        expected=m.PARAMETERS.get(a.id,{})
        if {p.name for p in a.parameters}!=set(expected):errors.append(f'Invalid action parameter names: {a.id}.')
        for p in a.parameters:
            rule=expected.get(p.name)
            if (rule is bool and (p.type!='boolean' or p.choices)) or (isinstance(rule,tuple) and (p.type!='enum' or tuple(p.choices)!=rule)):errors.append(f'Invalid parameter schema: {a.id}/{p.name}.')
        if a.mutation!=(a.id not in m.TESTS):errors.append(f'Incorrect operation classification: {a.id}.')
    def strings(value):
        if isinstance(value,str):yield value
        elif isinstance(value,list):
            for v in value:yield from strings(v)
        elif isinstance(value,dict):
            for v in value.values():yield from strings(v)
    if any(re.search(r'<\s*/?\s*[a-z][^>]*>|https?://|javascript:|data:',value,re.I) for value in strings(definition)):errors.append('HTML and remote embedding directives are not allowed.')
    if errors:return ValidationReport(passed=False,content_hash=hashed,errors=errors)
    try:
        state=initial_state(s)
        update={'impact':m.impact(state.domain),'status':communication_status(state,s),'next_action_id':'evidence.open'}
        sequence=[{'type':'mission.update','payload':update},*s.golden_commands,{'type':'mission.diagnose','payload':{'cause_id':s.rubric.cause_id}},{'type':'mission.recap','payload':{'cause_id':s.rubric.cause_id,'outcome':'successful'}},{'type':'mission.finish','payload':{}}]
        for i,c in enumerate(sequence):state=apply_command(state,Command(**c,origin_id=f'golden-{i}'),s).next_state
        score=evaluate_score(state,s)
        if score.total_score!=100 or score.outcome!='successful':errors.append('Golden path must reach a successful 100-point result.')
        for k,v in s.golden_expected.items():
            actual=state.simulation_time if k=='simulation_time' else state.domain.get(k)
            if actual!=v:errors.append(f'Golden result mismatch: {k}.')
        for index,path in enumerate(s.negative_paths):
            negative=initial_state(s)
            for i,c in enumerate(path):negative=apply_command(negative,Command(**c,origin_id=f'negative-{index}-{i}'),s).next_state
            negative=apply_command(negative,Command(type='mission.diagnose',payload={'cause_id':s.rubric.cause_id},origin_id=f'negative-diagnosis-{index}'),s).next_state
            if evaluate_score(negative,s).outcome=='successful':errors.append(f'Negative path {index} unexpectedly succeeded.')
        if not s.negative_paths:errors.append('At least one negative path is required.')
        if 'rubric' in project_visible_state(initial_state(s),s).model_dump() and project_visible_state(initial_state(s),s).rubric!=s.rubric.weights:errors.append('Unsafe public rubric projection.')
        return ValidationReport(passed=not errors,content_hash=hashed,errors=errors,golden_score=score.total_score,golden_time=state.simulation_time)
    except Exception:
        return ValidationReport(passed=False,content_hash=hashed,errors=['A deterministic golden or negative path failed. Check command types, prerequisites and the logical cap.'])
