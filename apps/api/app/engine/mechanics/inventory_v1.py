from app.core.errors import AppError

COSTS={'inventory.set_queue':1,'inventory.set_sales':1,'inventory.deploy_patch':2,'inventory.reconcile':2,'inventory.test_race':1,'inventory.test_ledger':1}
PARAMETERS={'inventory.set_queue':{'enabled':bool},'inventory.set_sales':{'status':('running','suspended')},'inventory.deploy_patch':{'kind':('atomic','idempotency_only','legacy')}}
REQUIRES={'inventory.deploy_patch':['inventory.patch_review'],'inventory.reconcile':['inventory.ledger']}
TESTS=['inventory.test_race','inventory.test_ledger']


def broken(d):return d['sales']=='running' and not d['queue'] and d['patch']!='atomic'


def metrics(d):
    stopped=d['sales']=='suspended';bad=broken(d)
    return {'label':'Simulation state','sales':d['sales'],'queue':d['queue'],'patch':d['patch'],'accepted_per_tick':0 if stopped else 25 if bad else 20,'sold_out_per_tick':0 if stopped or bad else 5,'oversell_percentage':20 if bad else 0,'oversell_rate':'sales suspended' if stopped else '5/25 (20%)' if bad else '0/20 (0%)','p95_ms':0 if stopped else 900 if d['queue'] else 100,'invalid_reservations':d['invalid_reservations'],'new_oversells':d['new_oversells'],'lost_sales':d['lost_sales'],'legitimate_reservations':len(d['legitimate_ids'])}


def tick(d,tick_number):
    if d['sales']=='suspended':d['lost_sales']+=20;return
    d['legitimate_ids'] += [f'T{tick_number}-R{i:02d}' for i in range(1,21)]
    if broken(d):
        d['invalid_ids'] += [f'T{tick_number}-R{i:02d}' for i in range(21,26)]
        d['new_oversells']+=5
    d['invalid_reservations']=len(d['invalid_ids'])


def precondition(d,kind):
    if kind=='inventory.reconcile' and broken(d):raise AppError('PRECONDITION_FAILED','Stop new oversells before reconciling invalid reservations.',409)


def mutate(d,kind,p):
    result={'message':'Simulated operation applied.'}
    if kind=='inventory.set_queue':d['queue']=p['enabled']
    elif kind=='inventory.set_sales':d['sales']=p['status']
    elif kind=='inventory.deploy_patch':d['patch']=p['kind']
    elif kind=='inventory.reconcile':
        result={'message':f"Cancelled exactly {len(d['invalid_ids'])} invalid simulated reservations. Legitimate reservations remain intact.",'cancelled_ids':list(d['invalid_ids'])}
        d['cancelled_invalid_ids']+=d['invalid_ids'];d['invalid_ids']=[];d['invalid_reservations']=0
    return result


def fingerprint(d,test):
    if test=='inventory.test_race':return {'patch':d['patch']}
    return {k:d[k] for k in ('sales','queue','patch','invalid_reservations')}


def test_result(d,kind,ticks):
    if kind=='inventory.test_race':
        passed=d['patch']=='atomic'
        return passed,'Isolated fixture bypassed the queue: 20 accepted, 5 sold out.' if passed else 'Isolated fixture bypassed the queue: 25 accepted for 20 units; distinct keys still race.'
    m=metrics(d);intact=not(set(d['legitimate_ids'])&set(d['cancelled_invalid_ids']))
    passed=d['invalid_reservations']==0 and intact and m['accepted_per_tick']==20 and not broken(d)
    return passed,'Incident ledger is reconciled; legitimate reservations remain, current workload accepts 20/25.' if passed else 'Ledger or live throughput still violates the stock invariant.'


def checks(d):
    return [d['patch']=='atomic' and not d['queue'],not broken(d),d['invalid_reservations']==0,d['sales']=='running' and metrics(d)['accepted_per_tick']==20]

def contained(d):return not broken(d)
def harm_ok(d):return d['new_oversells']<=25 and d['lost_sales']<=40
def impact(d):return d['invalid_reservations']
