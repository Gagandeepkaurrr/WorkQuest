from app.engine.registry import mechanics
from app.engine.scoring import communication_status, outcome, tests_pass, verification_status
from app.engine.transitions import allowed_next_actions
from app.engine.types import Scenario, VisibleWorldState, WorldState
from app.engine.visibility import available_artifacts


def project_visible_state(state: WorldState,scenario: Scenario) -> VisibleWorldState:
    m=mechanics(scenario);allowed=allowed_next_actions(state,scenario)
    artifacts=[{'id':a.id,'title':a.title,'type':a.type,'opened':a.id in state.opened,'first_open_cost':0 if a.id in state.opened else 1,'teammate':a.teammate} for a in available_artifacts(state,scenario)]
    actions=[{**a.model_dump(),'available':a.id in allowed and not state.finalized,'missing_evidence':[r for r in a.requires if r not in state.opened]} for a in scenario.action_catalog]
    # Do not reveal unavailable artifact identifiers through prerequisite metadata.
    visible_ids={a['id'] for a in artifacts}
    for a in actions:
        a['requires']=[r for r in a['requires'] if r in visible_ids]
        a['missing_evidence']=['Further investigation required'] if a['missing_evidence'] else []
    return VisibleWorldState(simulation_time=state.simulation_time,finalized=state.finalized,metrics=m.metrics(state.domain),metric_history=state.metric_history,artifacts=artifacts,actions=actions,tasks=[{'id':f'outcome-{i}','label':label,'completed':ok} for i,(label,ok) in enumerate(zip(scenario.metadata.objectives,m.checks(state.domain),strict=True))]+[{'id':'verification','label':'Complete both current verification checks','completed':all(tests_pass(state,scenario))}],diagnosis_choices=scenario.diagnosis_choices,diagnosis=state.diagnosis,verifications={k:{field:value[field] for field in ('passed','current','detail','logical_tick','origin_id')} for k,value in verification_status(state,scenario).items()},communication={'impact':m.impact(state.domain),'status':communication_status(state,scenario),'next_actions':allowed,'outcome':outcome(state,scenario)},hints=[{'id':h.id,'text':h.text} for h in scenario.hints if h.id in state.hints],teammates=[{'id':t.id,'name':t.name,'role':t.role,'welcome':t.welcome} for t in scenario.teammates],rubric=scenario.rubric.weights)
