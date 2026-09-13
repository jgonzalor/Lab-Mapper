"""Portable recoverable case bundles. Local processing; no remote APIs."""
from io import BytesIO,StringIO
from pathlib import Path,PurePosixPath
import csv,hashlib,json,sqlite3,tempfile,zipfile,shutil
from .models import dump,uid,now,SCHEMA_VERSION
from .case_store import CaseStore,user_root,DDL

def csv_bytes(rows):
    out=StringIO();keys=list(rows[0]) if rows else []
    writer=csv.DictWriter(out,keys);writer.writeheader()
    for row in rows:
        # Spreadsheet formula injection protection; JSON and original bytes remain unaltered.
        writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()})
    return out.getvalue().encode('utf-8-sig')

def add_evidence(s,subject,name,data,description,source):
    if not source.strip():raise ValueError('Fuente obligatoria')
    if len(data)>100*1024*1024:raise ValueError('Evidencia excede 100 MiB')
    if not any(s.con.execute(f'SELECT 1 FROM {t} WHERE id=?',(subject,)).fetchone() for t in ('entities','relations','findings')):raise ValueError('Elemento inexistente')
    sha=hashlib.sha256(data).hexdigest();eid=uid();rel='evidence/'+eid+'.bin';path=s.path/rel
    try:
        path.write_bytes(data)
        with s.transaction('AGREGAR_EVIDENCIA',subject,{'name':name,'hash':sha,'source':source}):
            s.con.execute('INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?)',(eid,subject,Path(name).name,sha,rel,description,source,now()))
    except BaseException:path.unlink(missing_ok=True);raise
    return eid

def export_case(s):
    if s.con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
        raise ValueError('La base no pasa verificación de integridad; no exportar como respaldo válido')
    out=BytesIO()
    with tempfile.TemporaryDirectory() as temp:
        db=Path(temp)/'case.db';con=sqlite3.connect(db);s.con.backup(con);con.close()
        blobs={'case.db':db.read_bytes()}
        for table in ('imports','evidence'):
            for r in s.rows(f'SELECT path,sha256 FROM {table}'):
                p=(s.path/r['path']).resolve()
                if not p.is_relative_to(s.path):raise ValueError('Ruta fuera del caso')
                data=p.read_bytes()
                if hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError('Hash no coincide: '+r['path'])
                blobs[r['path']]=data
        manifest={'schema':SCHEMA_VERSION,'case_id':s.meta('id'),'name':s.meta('name'),'files':{p:hashlib.sha256(v).hexdigest() for p,v in blobs.items()}}
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for p,data in blobs.items():z.writestr(p,data)
            z.writestr('manifest.json',dump(manifest))
    with s.transaction('EXPORTAR_CASO',detail={'files':len(blobs)}):pass
    return out.getvalue()

def restore_case(data,actor,root=None):
    """Validate all members and database schema before making a recovered case visible."""
    with tempfile.TemporaryDirectory() as tmp:
        temp=Path(tmp)
        with zipfile.ZipFile(BytesIO(data)) as z:
            infos=z.infolist()
            if len(infos)>10000 or sum(i.file_size for i in infos)>1024**3:raise ValueError('Paquete excede límites de recuperación')
            names=z.namelist()
            if len(set(names))!=len(names):raise ValueError('Miembros duplicados')
            manifest=json.loads(z.read('manifest.json'))
            if manifest.get('schema')!=SCHEMA_VERSION:raise ValueError('Versión incompatible')
            if set(names)!=set(manifest['files'])|{'manifest.json'} or 'case.db' not in names:raise ValueError('Manifiesto incompleto')
            for name,sha in manifest['files'].items():
                p=PurePosixPath(name)
                if p.is_absolute() or '..' in p.parts or '\\' in name or (name!='case.db' and p.parts[0] not in ('imports','evidence')):raise ValueError('Ruta inválida en paquete')
                content=z.read(name)
                if hashlib.sha256(content).hexdigest()!=sha:raise ValueError('Hash de paquete inválido')
                dest=temp/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content)
        con=sqlite3.connect(temp/'case.db');ref=sqlite3.connect(':memory:');ref.executescript(DDL)
        try:
            schema=lambda c:c.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
            if schema(con)!=schema(ref):raise ValueError('Esquema SQLite no autorizado')
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or con.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Base de datos inconsistente')
            for table in ('imports','evidence'):
                for rel,sha in con.execute(f'SELECT path,sha256 FROM {table}'):
                    if rel not in manifest['files'] or manifest['files'][rel]!=sha:raise ValueError('Evidencia o importación no respaldada')
            old_owner=con.execute("SELECT value FROM meta WHERE key='owner'").fetchone()[0]
            new_id=uid()
            con.executemany('UPDATE meta SET value=? WHERE key=?',[(actor,'owner'),(new_id,'id')]);con.commit()
        finally:con.close();ref.close()
        path=user_root(actor,root)/new_id;shutil.copytree(temp,path)
        (path/'exports').mkdir(exist_ok=True)
    with CaseStore(path,actor) as s:
        with s.transaction('RESTAURAR_CASO',detail={'source_case':manifest['case_id'],'source_owner':old_owner}):pass
    return str(path)
