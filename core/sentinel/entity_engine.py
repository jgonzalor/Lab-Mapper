"""Typed entities, separate researcher revisions and first-class manual relations."""
from .models import entity_id,uid,dump,CONFIDENCE,now

def ensure_entity(con,kind,key,label=None,attrs=None,target=False,origin='CDR'):
    eid=entity_id(kind,key)
    con.execute('INSERT OR IGNORE INTO entities VALUES(?,?,?,?,?,?,?)',(eid,kind,key,label or key,dump(attrs or {}),origin,int(target)))
    if target:con.execute('UPDATE entities SET target=1 WHERE id=?',(eid,))
    return eid

def add_entity(store,kind,label,attrs,source,confidence='PENDIENTE'):
    if not label.strip() or not kind.strip() or not source.strip():raise ValueError('Tipo, nombre y fuente obligatorios')
    if confidence not in CONFIDENCE:raise ValueError('Confianza inválida')
    with store.transaction('CREAR_ENTIDAD',detail={'kind':kind,'label':label,'source':source,'attrs':attrs}):
        eid=ensure_entity(store.con,kind,uid(),label,attrs,origin='MANUAL')
        store.con.execute('INSERT INTO annotations VALUES(?,?,?,?,?,?,?,?)',(eid,label,dump(attrs),confidence,'',source,now(),store.actor))
    return eid

def add_relation(store,source,destination,kind,confidence,note,source_name,start=None,end=None):
    if source==destination:raise ValueError('Selecciona dos entidades distintas')
    if not source_name.strip() or not kind.strip():raise ValueError('Fuente y tipo obligatorios')
    if confidence not in CONFIDENCE:raise ValueError('Confianza inválida')
    if start and end and start>end:raise ValueError('Intervalo invertido')
    rid='manual:'+uid()
    with store.transaction('CREAR_RELACION',rid,{'source':source,'destination':destination,'kind':kind,'confidence':confidence,'source_name':source_name,'note':note}):
        store.con.execute('INSERT INTO relations VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,source,destination,kind,start,end,confidence,'MANUAL',note,source_name))
    return rid
