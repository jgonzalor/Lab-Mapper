"""Logical events and many source rows. Reciprocal, unique matching; no transitive fusion."""
from collections import defaultdict
from bisect import bisect_left,bisect_right
from .models import stable

def family(kind):
    if kind in ('VOZ ENTRANTE','VOZ SALIENTE'):return 'VOZ'
    if kind in ('MENSAJE ENTRANTE','MENSAJE SALIENTE'):return 'SMS'
    return kind

def rebuild_events(store,options):
    con=store.con
    con.execute('DELETE FROM events')
    rows=store.rows("SELECT * FROM observations WHERE status='VALIDO' ORDER BY epoch,id")
    exact=defaultdict(list)
    for r in rows:exact[r['signature']].append(r)
    reps=[v[0] for v in exact.values()]
    buckets=defaultdict(list)
    for r in reps:
        if family(r['kind']) in ('VOZ','SMS') and r['duration'] is not None:
            buckets[(r['a'],r['b'],family(r['kind']))].append(r)
    candidate=defaultdict(list)
    for rs in buckets.values():
        rs.sort(key=lambda r:r['epoch']);times=[r['epoch'] for r in rs]
        for r in rs:
            for other in rs[bisect_left(times,r['epoch']-options.dedup_seconds):bisect_right(times,r['epoch']+options.dedup_seconds)]:
                if other['target']==r['target'] or {r['target'],other['target']}!={r['a'],r['b']}:continue
                if abs(other['duration']-r['duration'])>options.duration_tolerance:continue
                if not ((r['kind'].endswith('ENTRANTE') and other['kind'].endswith('SALIENTE')) or (r['kind'].endswith('SALIENTE') and other['kind'].endswith('ENTRANTE'))):continue
                candidate[r['id']].append(other)
    seen=set()
    for r in reps:
        if r['id'] in seen:continue
        group=[r];method='REGISTRO_UNICO';confidence='CONFIRMADO'
        candidates=candidate[r['id']]
        if len(candidates)==1 and len(candidate[candidates[0]['id']])==1 and candidates[0]['id'] not in seen:
            other=candidates[0];group.append(other)
            method='ESPEJO_UNICO_EXACTO' if r['epoch']==other['epoch'] and r['duration']==other['duration'] else 'ESPEJO_UNICO_CON_TOLERANCIA'
            confidence='PROBABLE' if method.endswith('TOLERANCIA') else 'INFERIDO'
        elif candidates:method='CANDIDATOS_AMBIGUOS_NO_FUSIONADOS';confidence='PENDIENTE'
        support=[x for rep in group for x in exact[rep['signature']]]
        if len(support)>len(group):method+=' + REPETICION_EXACTA_DE_REGISTRO';confidence='INFERIDO'
        seen.update(x['id'] for x in group)
        eid=stable('event',*sorted(x['id'] for x in support))
        first=min(group,key=lambda x:(x['epoch'],x['id']))
        con.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)',(eid,family(r['kind']),r['a'],r['b'],first['local_time'],first['epoch'],first['duration'],method,confidence))
        con.executemany('INSERT INTO event_support VALUES(?,?)',[(eid,x['id']) for x in support])
