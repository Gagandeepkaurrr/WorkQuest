from app.modules.reports.models import ScorecardRecord


def build_public_report_snapshot(scorecard: ScorecardRecord,share_options: dict) -> dict:
    # Deliberately allowlisted. Never copy whole deterministic results or learner records.
    data=scorecard.criteria_json
    return {'title':share_options['title'],'version':share_options['version'],'completed_at':scorecard.created_at.isoformat(),'outcome':scorecard.outcome,'total_score':scorecard.total_score,'criteria':[{'title':c['title'],'awarded_points':c['awarded_points'],'maximum_points':c['maximum_points']} for c in data['criteria']],'practice_mode':share_options['practice_mode'],'hints_used':len(data['hints_used']),'alias':share_options.get('alias',''),'label':'Practice assessment'}
