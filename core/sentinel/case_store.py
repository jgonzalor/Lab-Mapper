"""SQLite repository boundary, per-user ownership and transactional audit trail."""
from pathlib import Path
from contextlib import contextmanager
import sqlite3,json,os
from .models import uid,now,dump,SCHEMA_VERSION,CONFIDENCE,stable

DDL='''
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS imports(id TEXT PRIMARY KEY,name TEXT NOT NULL,sha256 TEXT UNIQUE NOT NULL,target TEXT NOT NULL,imported_at TEXT NOT NULL,path TEXT NOT NULL,options TEXT NOT NULL,sheets TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY,kind TEXT NOT NULL,canonical TEXT NOT NULL,label TEXT NOT NULL,attrs TEXT NOT NULL DEFAULT '{}',origin TEXT NOT NULL,target INTEGER NOT NULL DEFAULT 0, UNIQUE(kind,canonical));
CREATE TABLE IF NOT EXISTS raw_records(id TEXT PRIMARY KEY,import_id TEXT NOT NULL REFERENCES imports(id),sheet TEXT NOT NULL,row_number INTEGER NOT NULL,cells TEXT NOT NULL,UNIQUE(import_id,sheet,row_number));
CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY REFERENCES raw_records(id),target TEXT NOT NULL,kind TEXT NOT NULL,a TEXT,b TEXT,local_time TEXT,epoch REAL,duration REAL,imei TEXT,imsi TEXT,location_id TEXT REFERENCES entities(id),status TEXT NOT NULL,reason TEXT NOT NULL,quality TEXT NOT NULL,signature TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS locations(entity_id TEXT PRIMARY KEY REFERENCES entities(id),site_key TEXT NOT NULL,lat REAL NOT NULL,lon REAL NOT NULL,azimuth REAL,plus_code TEXT,address TEXT);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,kind TEXT NOT NULL,source TEXT,destination TEXT,local_time TEXT NOT NULL,epoch REAL NOT NULL,duration REAL,method TEXT NOT NULL,confidence TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS event_support(event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,record_id TEXT NOT NULL REFERENCES observations(id),PRIMARY KEY(event_id,record_id));
CREATE TABLE IF NOT EXISTS relations(id TEXT PRIMARY KEY,source TEXT NOT NULL REFERENCES entities(id),destination TEXT NOT NULL REFERENCES entities(id),kind TEXT NOT NULL,start_time TEXT,end_time TEXT,confidence TEXT NOT NULL,origin TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',source_name TEXT NOT NULL DEFAULT '',CHECK(source != destination));
CREATE TABLE IF NOT EXISTS relation_support(relation_id TEXT NOT NULL REFERENCES relations(id) ON DELETE CASCADE,event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,record_id TEXT NOT NULL REFERENCES observations(id),PRIMARY KEY(relation_id,event_id,record_id));
CREATE TABLE IF NOT EXISTS findings(id TEXT PRIMARY KEY,kind TEXT NOT NULL,source TEXT NOT NULL,destination TEXT NOT NULL,location TEXT,delta_seconds REAL,confidence TEXT NOT NULL,rule TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS finding_support(finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,record_id TEXT NOT NULL REFERENCES observations(id),PRIMARY KEY(finding_id,event_id,record_id));
CREATE TABLE IF NOT EXISTS annotations(subject_id TEXT PRIMARY KEY,label TEXT,attrs TEXT NOT NULL DEFAULT '{}',confidence TEXT,note TEXT NOT NULL DEFAULT '',source TEXT NOT NULL,updated_at TEXT NOT NULL,actor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,subject_id TEXT NOT NULL,name TEXT NOT NULL,sha256 TEXT NOT NULL,path TEXT NOT NULL,description TEXT NOT NULL,source TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log(seq INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,subject TEXT NOT NULL,before_json TEXT,after_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS obs_time ON observations(epoch);
CREATE INDEX IF NOT EXISTS obs_target_time ON observations(target,epoch);
CREATE INDEX IF NOT EXISTS obs_location ON observations(location_id,epoch);
CREATE INDEX IF NOT EXISTS obs_signature ON observations(signature);
CREATE INDEX IF NOT EXISTS event_time ON events(epoch);
CREATE INDEX IF NOT EXISTS support_record ON event_support(record_id);
CREATE INDEX IF NOT EXISTS rel_source ON relations(source);
CREATE INDEX IF NOT EXISTS rel_dest ON relations(destination);
CREATE INDEX IF NOT EXISTS rel_support_event ON relation_support(event_id);
CREATE INDEX IF NOT EXISTS entity_kind ON entities(kind,target);
'''

def cases_root():
    return Path(os.environ.get('SENTINEL_CASES_DIR',str(Path.home()/'GoMapperCases'))).expanduser().resolve()

def user_root(actor,root=None):
    if not actor:raise ValueError('Usuario autenticado requerido')
    p=Path(root or cases_root())/stable(actor)[:24];p.mkdir(parents=True,exist_ok=True,mode=0o700)
    return p

class CaseStore:
    def __init__(self,path,actor):
        self.path=Path(path).resolve();self.actor=actor
        if not (self.path/'case.db').is_file():raise ValueError('Caso inexistente')
        self.con=sqlite3.connect(self.path/'case.db',timeout=30)
        self.con.row_factory=sqlite3.Row
        self.con.execute('PRAGMA foreign_keys=ON')
        if self.meta('owner')!=actor:
            self.con.close();raise PermissionError('Caso no autorizado para este usuario')
        if int(self.meta('schema_version'))!=SCHEMA_VERSION:
            self.con.close();raise ValueError('Versión de caso no compatible')
    @classmethod
    def create(cls,name,actor,description='',investigator='',root=None):
        if not name.strip():raise ValueError('Nombre de caso obligatorio')
        path=user_root(actor,root)/uid();path.mkdir(mode=0o700)
        for d in ('imports','evidence','exports'):(path/d).mkdir(mode=0o700)
        con=sqlite3.connect(path/'case.db');con.executescript(DDL)
        values={'id':path.name,'name':name.strip(),'owner':actor,'description':description,'investigator':investigator,'created_at':now(),'schema_version':str(SCHEMA_VERSION),'revision':'0'}
        con.executemany('INSERT INTO meta VALUES(?,?)',values.items());con.commit();con.close()
        return cls(path,actor)
    @classmethod
    def list_cases(cls,actor,root=None):
        result=[]
        for p in sorted(user_root(actor,root).glob('*/case.db')):
            try:
                with cls(p.parent,actor) as s:result.append({'path':str(s.path),'name':s.meta('name'),'id':s.meta('id')})
            except (ValueError,PermissionError,sqlite3.Error):continue
        return result
    def __enter__(self):return self
    def __exit__(self,*exc):self.close()
    def close(self):self.con.close()
    def meta(self,key):
        r=self.con.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone();return r[0] if r else None
    def rows(self,sql,args=()):return [dict(r) for r in self.con.execute(sql,args)]
    @contextmanager
    def transaction(self,action,subject='case',detail=None):
        self.con.execute('BEGIN IMMEDIATE')
        try:
            yield self.con
            self.log(action,subject,detail or {})
            self.con.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
            self.con.commit()
        except BaseException:self.con.rollback();raise
    def log(self,action,subject,after,before=None):
        self.con.execute('INSERT INTO audit_log(created_at,actor,action,subject,before_json,after_json) VALUES(?,?,?,?,?,?)',(now(),self.actor,action,subject,dump(before) if before is not None else None,dump(after)))
    def annotate(self,subject,label=None,attrs=None,confidence=None,note='',source=''):
        if not source.strip():raise ValueError('Fuente obligatoria')
        if confidence and confidence not in CONFIDENCE:raise ValueError('Confianza inválida')
        exists=any(self.con.execute(f'SELECT 1 FROM {t} WHERE id=?',(subject,)).fetchone() for t in ('entities','relations','findings'))
        if not exists:raise ValueError('Elemento inexistente')
        before=self.rows('SELECT * FROM annotations WHERE subject_id=?',(subject,))
        with self.transaction('ANOTAR',subject,{'source':source}):
            self.con.execute('INSERT OR REPLACE INTO annotations VALUES(?,?,?,?,?,?,?,?)',(subject,label,dump(attrs or {}),confidence,note,source,now(),self.actor))
            self.log('REVISION',subject,{'label':label,'attrs':attrs,'confidence':confidence,'note':note,'source':source},before)
    def update_case(self,name,description,investigator):
        if not name.strip():raise ValueError('Nombre obligatorio')
        with self.transaction('EDITAR_CASO',detail={'name':name,'description':description,'investigator':investigator}):
            self.con.executemany('UPDATE meta SET value=? WHERE key=?',[(name,'name'),(description,'description'),(investigator,'investigator')])
