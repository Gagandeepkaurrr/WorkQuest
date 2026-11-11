from app.engine.registry import mechanics
from app.engine.types import Criterion, Scenario, Scorecard, WorldState, canonical_hash


def verification_status(state: WorldState,scenario: Scenario) -> dict:
    module=mechanics(scenario)
    return {key:{**value,'current':value['fingerprint']==canonical_hash(module.fingerprint(state.domain,key))} for key,value in state.verifications.items()}


def tests_pass(state: WorldState,scenario: Scenario) -> list[bool]:
    status=verification_status(state,scenario)
    return [bool(status.get(t,{}).get('passed') and status.get(t,{}).get('current')) for t in mechanics(scenario).TESTS]


def outcome(state: WorldState,scenario: Scenario) -> str:
    m=mechanics(scenario)
    if all(m.checks(state.domain)) and all(tests_pass(state,scenario)) and state.diagnosis==scenario.rubric.cause_id:return 'successful'
    return 'contained' if m.contained(state.domain) else 'unresolved'


def communication_status(state: WorldState,scenario: Scenario) -> str:
    m=mechanics(scenario)
    if scenario.mechanics_id=='analytics_v1':
        status='corrected' if m.contained(state.domain) else 'incorrect'
        if m.contained(state.domain) and all(tests_pass(state,scenario)):status='verified'
        return status
    status='contained' if m.contained(state.domain) else 'impacted'
    if all(m.checks(state.domain)):
        status='verified' if all(tests_pass(state,scenario)) else 'repaired'
    return status


def evaluate_score(state: WorldState,scenario: Scenario) -> Scorecard:
    m=mechanics(scenario)
    diagnosis=5*sum(a in state.opened for a in scenario.rubric.diagnosis_artifacts)+10*(state.diagnosis==scenario.rubric.cause_id)
    checks=m.checks(state.domain);tests=tests_pass(state,scenario);result=outcome(state,scenario)
    recap=bool(state.recap and state.recap['cause_id']==state.diagnosis==scenario.rubric.cause_id and state.recap['outcome']==result)
    values={'diagnosis':diagnosis,'outcome':10*sum(checks),'verification':10*sum(tests),'communication':5*bool(state.updates)+5*recap,'judgment':5*m.harm_ok(state.domain)+5*(state.simulation_time<=14)}
    explanations={'diagnosis':f'{sum(a in state.opened for a in scenario.rubric.diagnosis_artifacts)}/2 required evidence artifacts inspected; diagnosis {"matches" if state.diagnosis==scenario.rubric.cause_id else "does not match"} the incident.','outcome':f'{sum(checks)}/4 outcome checks met.','verification':f'{sum(tests)}/2 tests passing and current.','communication':f'Valid interim update: {bool(state.updates)}. Accurate final recap: {recap}.','judgment':f'Harm threshold met: {m.harm_ok(state.domain)}. Finished by minute 14: {state.simulation_time<=14}.'}
    def references(k):
        types={'diagnosis':{'evidence.open','mission.diagnose'},'communication':{'mission.update','mission.recap'},'verification':set(m.TESTS)}.get(k,set(m.COSTS)|{'mission.finish'})
        return list(dict.fromkeys(e['origin_id'] for e in state.ledger if e['type'] in types))
    criteria=[Criterion(criterion_id=k,title=k.title(),maximum_points=v,awarded_points=values[k],explanation=explanations[k],supporting_origin_ids=references(k)) for k,v in scenario.rubric.weights.items()]
    missed=[scenario.metadata.objectives[i] for i,ok in enumerate(checks) if not ok]+[t for t,ok in zip(m.TESTS,tests,strict=True) if not ok]
    score=Scorecard(total_score=sum(values.values()),outcome=result,criteria=criteria,simulation_time=state.simulation_time,hints_used=state.hints,metrics=m.metrics(state.domain),action_sequence=[{'origin_id':e['origin_id'],'type':e['type'],'payload':e['payload'],'logical_tick':e['logical_tick']} for e in state.ledger],explanation=scenario.rubric.explanation,missed_checks=missed)
    score.deterministic_hash=canonical_hash(score.model_dump(exclude={'deterministic_hash'}))
    return score


def calculate_scorecard(final_state: WorldState,inherited_ledger: list,new_events: list,scenario: Scenario) -> Scorecard:
    state=final_state.model_copy(deep=True)
    merged={e['origin_id']:e for e in inherited_ledger+new_events}
    state.ledger=list(merged.values())
    return evaluate_score(state,scenario)
