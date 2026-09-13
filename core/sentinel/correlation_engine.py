"""Bounded same-site temporal evidence, not co-presence or triangulation."""
from collections import defaultdict,deque
from .models import stable,dump,ENGINE_VERSION

def correlate(store,window_seconds=300,min_distinct_events=2,max_pairs=50000):
    if not 0<=window_seconds<=3600:raise ValueError('Ventana permitida: 0 a 3,600 segundos')
    if not 2<=min_distinct_events<=100:raise ValueError('Mínimo permitido: 2 a 100 eventos distintos por par/sitio')
    with store.transaction('CORRELACIONAR',detail={'window_seconds':window_seconds,'min_distinct_events':min_distinct_events,'engine':ENGINE_VERSION}):
        con=store.con;con.execute('DELETE FROM findings')
        rows=store.rows('''SELECT o.target,o.epoch,o.id,s.event_id,l.site_key FROM observations o
        JOIN locations l ON l.entity_id=o.location_id JOIN event_support s ON s.record_id=o.id
        WHERE o.status='VALIDO' GROUP BY s.event_id,o.target,l.site_key ORDER BY l.site_key,o.epoch,o.id''')
        active=deque();site=None;count=0;truncated=False;hits=defaultdict(list)
        for r in rows:
            if r['site_key']!=site:active.clear();site=r['site_key']
            while active and r['epoch']-active[0]['epoch']>window_seconds:active.popleft()
            for other in active:
                if other['target']==r['target'] or other['event_id']==r['event_id']:continue
                if count>=max_pairs:truncated=True;break
                a,b=sorted([r['target'],other['target']]);fid=stable('temporal',site,a,b,r['event_id'],other['event_id'])
                delta=abs(r['epoch']-other['epoch'])
                rule={'window_seconds':window_seconds,'site_precision':7,'meaning':'Registros de sitio celular dentro de ventana; no presencia conjunta','engine':ENGINE_VERSION}
                con.execute('INSERT OR IGNORE INTO findings VALUES(?,?,?,?,?,?,?,?)',(fid,'COINCIDENCIA_TEMPORAL',a,b,site,delta,'INFERIDO',dump(rule)))
                con.executemany('INSERT OR IGNORE INTO finding_support VALUES(?,?,?)',[(fid,x['event_id'],x['id']) for x in (r,other)])
                hits[(a,b,site)].append((fid,r,other));count+=1
            if truncated:break
            active.append(r)
        relevant=0
        for (a,b,site),pairs in hits.items():
            # Separate matches must support each line, not just many rows from one long data session.
            by_target=defaultdict(set)
            for _,r,o in pairs:
                for x in (r,o):by_target[x['target']].add(x['event_id'])
            if min(len(v) for v in by_target.values())<min_distinct_events:continue
            fid=stable('relevant',a,b,site,window_seconds,min_distinct_events)
            con.execute('INSERT INTO findings VALUES(?,?,?,?,?,?,?,?)',(fid,'COINCIDENCIA_RELEVANTE',a,b,site,None,'INFERIDO',dump({'window_seconds':window_seconds,'minimum_distinct_events_per_line':min_distinct_events,'engine':ENGINE_VERSION,'meaning':'Repetición que cumple umbral operativo, no reunión demostrada'})))
            con.executemany('INSERT OR IGNORE INTO finding_support VALUES(?,?,?)',[(fid,x['event_id'],x['id']) for _,r,o in pairs for x in (r,o)]);relevant+=1
        status='LIMITADO_A_50000_PARES' if truncated else 'COMPLETO'
        con.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('correlation_status',status))
        con.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('correlation_options',dump({'window_seconds':window_seconds,'min_distinct_events':min_distinct_events})))
    return {'pairs':count,'relevant':relevant,'status':status}
