"""Read models shared by graph, geography and timeline. Bounded responses only."""
import json
from .models import entity_id

ACTIVE="COALESCE(a.confidence,r.confidence)!='DESCARTADO' AND NOT EXISTS(SELECT 1 FROM annotations excluded WHERE excluded.subject_id IN (r.source,r.destination) AND excluded.confidence='DESCARTADO')"

def metrics(s):
    return {label:s.con.execute(sql).fetchone()[0] for label,sql in {
    'Objetivos':'SELECT COUNT(*) FROM entities WHERE target=1',
    'Registros':'SELECT COUNT(*) FROM raw_records',
    'Eventos lógicos':'SELECT COUNT(*) FROM events',
    'No clasificados':"SELECT COUNT(*) FROM observations WHERE status='NO_CLASIFICADO'",
    'Por revisar':"SELECT COUNT(*) FROM observations WHERE status='REVISAR'"}.items()}

def entities(s,search='',kind='',limit=250):
    return s.rows('''SELECT e.*,a.label AS edited_label,a.attrs AS edited_attrs,a.note,a.confidence FROM entities e LEFT JOIN annotations a ON a.subject_id=e.id
      WHERE (?='' OR e.kind=?) AND (e.label LIKE ? OR e.canonical LIKE ? OR a.label LIKE ?) ORDER BY e.target DESC,e.kind,e.label LIMIT ?''',(kind,kind,'%'+search+'%','%'+search+'%','%'+search+'%',min(limit,1000)))

def entity(s,eid):
    r=s.rows('SELECT e.*,a.label edited_label,a.attrs edited_attrs,a.note,a.confidence,a.source FROM entities e LEFT JOIN annotations a ON a.subject_id=e.id WHERE e.id=?',(eid,))
    if not r:return None
    r=r[0];r['display_label']=r['edited_label'] or r['label'];r['effective_attrs']={**json.loads(r['attrs']),**json.loads(r['edited_attrs'] or '{}')};return r

def relations(s,selected=None,kind='',limit=200):
    return s.rows(f'''SELECT r.*,COALESCE(a.confidence,r.confidence) effective_confidence,
    (SELECT COUNT(DISTINCT event_id) FROM relation_support z WHERE z.relation_id=r.id) event_count,
    (SELECT COUNT(*) FROM relation_support z WHERE z.relation_id=r.id) record_count
    FROM relations r LEFT JOIN annotations a ON a.subject_id=r.id WHERE {ACTIVE}
    AND (? IS NULL OR r.source=? OR r.destination=?) AND (?='' OR r.kind=?) ORDER BY event_count DESC,r.id LIMIT ?''',(selected,selected,selected,kind,kind,limit))

def contacts(s):
    # Requires an actual relation to each DISTINCT target, not merely presence in a file.
    return s.rows(f'''WITH links AS (
      SELECT r.source target,r.destination contact,r.id rid FROM relations r LEFT JOIN annotations a ON a.subject_id=r.id WHERE r.kind IN ('COMUNICA_CON','TRAFICO_ESPECIAL_CON') AND {ACTIVE}
      UNION ALL SELECT r.destination,r.source,r.id FROM relations r LEFT JOIN annotations a ON a.subject_id=r.id WHERE r.kind IN ('COMUNICA_CON','TRAFICO_ESPECIAL_CON') AND {ACTIVE}
    ) SELECT c.id,c.label,c.canonical,COUNT(DISTINCT t.id) objectives,COUNT(DISTINCT rs.event_id) events,
    GROUP_CONCAT(DISTINCT t.canonical) target_numbers
    FROM links l JOIN entities t ON t.id=l.target AND t.target=1 JOIN entities c ON c.id=l.contact AND c.target=0 AND c.kind='TELEFONO'
    JOIN relation_support rs ON rs.relation_id=l.rid GROUP BY c.id ORDER BY objectives DESC,events DESC,c.canonical''')

def shared_devices(s):
    return s.rows(f'''SELECT d.id,d.canonical imei,COUNT(DISTINCT r.source) objectives,GROUP_CONCAT(DISTINCT t.canonical) lines,COUNT(DISTINCT rs.event_id) events
    FROM relations r JOIN entities d ON d.id=r.destination JOIN entities t ON t.id=r.source JOIN relation_support rs ON rs.relation_id=r.id LEFT JOIN annotations a ON a.subject_id=r.id
    WHERE r.kind='IMEI_OBSERVADO' AND {ACTIVE} GROUP BY d.id HAVING COUNT(DISTINCT r.source)>1 ORDER BY objectives DESC''')

def geography(s,target='',limit=250):
    return s.rows('''SELECT l.site_key,l.lat,l.lon,MIN(l.entity_id) id,MIN(l.address) address,COUNT(DISTINCT o.target) objectives,COUNT(DISTINCT es.event_id) events,GROUP_CONCAT(DISTINCT o.target) lines,COUNT(DISTINCT l.entity_id) sectors
    FROM locations l JOIN observations o ON o.location_id=l.entity_id JOIN event_support es ON es.record_id=o.id
    WHERE (?='' OR o.target=?) GROUP BY l.site_key ORDER BY events DESC,l.site_key LIMIT ?''',(target,target,limit))

def timeline(s,target='',start=None,end=None,limit=100,offset=0,subject=None):
    return s.rows('''SELECT e.*,COUNT(DISTINCT es.record_id) records FROM events e JOIN event_support es ON es.event_id=e.id JOIN observations o ON o.id=es.record_id
      WHERE (?='' OR o.target=?) AND (? IS NULL OR e.epoch>=?) AND (? IS NULL OR e.epoch<=?)
      AND (? IS NULL OR EXISTS(SELECT 1 FROM relation_support rs JOIN relations r ON r.id=rs.relation_id WHERE rs.event_id=e.id AND (r.source=? OR r.destination=?)))
      GROUP BY e.id ORDER BY e.epoch,e.id LIMIT ? OFFSET ?''',(target,target,start,start,end,end,subject,subject,subject,limit,offset))

def support(s,subject,limit=100,offset=0):
    return s.rows('''SELECT DISTINCT rr.id,im.name archivo_origen,rr.sheet hoja_origen,rr.row_number fila_origen,im.imported_at fecha_importacion,im.sha256 hash_archivo,o.kind tipo,o.target linea_observada,o.local_time fecha_hora,o.a,o.b,o.duration,o.imei,o.imsi,o.quality,o.reason,rr.cells,e.id evento_id,e.method metodo_evento
    FROM raw_records rr JOIN imports im ON im.id=rr.import_id JOIN observations o ON o.id=rr.id LEFT JOIN event_support es ON es.record_id=o.id LEFT JOIN events e ON e.id=es.event_id
    WHERE rr.id=? OR es.event_id=? OR rr.id IN (
      SELECT rs.record_id FROM relation_support rs JOIN relations r ON r.id=rs.relation_id WHERE r.id=? OR r.source=? OR r.destination=?
      UNION SELECT fs.record_id FROM finding_support fs WHERE fs.finding_id=?
    ) ORDER BY im.name,rr.row_number LIMIT ? OFFSET ?''',(subject,subject,subject,subject,subject,subject,limit,offset))

def graph(s,selected=None,limit=80,mode='COMUNES',kind=''):
    rels=relations(s,selected,kind,limit=500)
    targets=s.rows("SELECT * FROM entities WHERE target=1 AND id NOT IN (SELECT subject_id FROM annotations WHERE confidence='DESCARTADO') ORDER BY canonical")
    preferred={r['id'] for r in targets}
    if selected:preferred.add(selected)
    if mode=='COMUNES':
        preferred.update(r['id'] for r in contacts(s) if r['objectives']>1)
        preferred.update(r['id'] for r in shared_devices(s))
        if not selected:rels=[r for r in rels if r['source'] in preferred and r['destination'] in preferred]
    # Budget nodes as edges added, rather than picking arbitrary first nodes.
    ids={r['id'] for r in targets}
    if selected:ids.add(selected)
    edges=[]
    for r in rels:
        extra={r['source'],r['destination']}-ids
        if len(ids)+len(extra)>limit:continue
        ids.update(extra);edges.append(r)
    nodes=[entity(s,i) for i in sorted(ids)];nodes=[n for n in nodes if n and n.get('confidence')!='DESCARTADO']
    return nodes,edges
