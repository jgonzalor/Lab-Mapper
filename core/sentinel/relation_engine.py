"""Automatically derived assertions; support links count DISTINCT logical events."""
from .models import stable,entity_id
from .validators import phone

def rebuild_relations(store):
    con=store.con;con.execute("DELETE FROM relations WHERE origin='CDR'")
    rows=store.rows('SELECT o.*,s.event_id FROM observations o JOIN event_support s ON s.record_id=o.id')
    relations={};support=[]
    def link(a,b,kind,r):
        if not a or not b or a==b:return
        rid=stable('relation',a,b,kind)
        if rid not in relations:relations[rid]=[rid,a,b,kind,r['local_time'],r['local_time'],'CONFIRMADO','CDR','Observado en registros; no implica identidad personal.','Datos_Limpios']
        else:
            relations[rid][4]=min(relations[rid][4],r['local_time']);relations[rid][5]=max(relations[rid][5],r['local_time'])
        support.append((rid,r['event_id'],r['id']))
    for r in rows:
        target=entity_id('TELEFONO',r['target'])
        if r['imei']:link(target,entity_id('DISPOSITIVO',r['imei']),'IMEI_OBSERVADO',r)
        if r['imsi']:link(target,entity_id('SIM',r['imsi']),'IMSI_OBSERVADO',r)
        if r['location_id']:link(target,r['location_id'],'ANTENA_REGISTRADA',r)
        if r['kind'].startswith(('VOZ','MENSAJE')) or r['kind']=='TRANSFER':
            a=entity_id('TELEFONO' if phone(r['a']) else 'SERVICIO',r['a'])
            b=entity_id('TELEFONO' if phone(r['b']) else 'SERVICIO',r['b'])
            kind='TRAFICO_ESPECIAL_CON' if r['kind'] in ('VOZ TRANSITO','VOZ TRANSFER','TRANSFER') else 'COMUNICA_CON'
            link(a,b,kind,r)
    con.executemany('INSERT INTO relations VALUES(?,?,?,?,?,?,?,?,?,?)',relations.values())
    con.executemany('INSERT OR IGNORE INTO relation_support VALUES(?,?,?)',support)
