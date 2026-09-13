"""Run a local integration cut; carrier data and report never need to enter Git."""
from pathlib import Path
import argparse,sys,json,time,collections
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.sentinel.case_store import CaseStore
from core.sentinel.importer_cdr import import_files
from core.sentinel.correlation_engine import correlate
from core.sentinel.exporters import export_case,restore_case
from core.sentinel import queries

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--cases',required=True);p.add_argument('--report',required=True);args=p.parse_args()
    start=time.perf_counter()
    files=sorted(Path(args.inputs).glob('*.xlsx'))
    with CaseStore.create('Validación multi-CDR','validation',root=args.cases) as s:
        result=import_files(s,[(p.name,p.read_bytes()) for p in files]);import_seconds=time.perf_counter()-start
        correlation=correlate(s)
        integrity=s.con.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity!='ok':raise RuntimeError('Integridad SQLite falló')
        backup=export_case(s);restored=restore_case(backup,'validation',args.cases)
        with CaseStore(restored,'validation') as reopened:assert queries.metrics(reopened)==queries.metrics(s)
        contacts=queries.contacts(s)
        report={'case_path':str(s.path),'metrics':queries.metrics(s),'import':result,'import_seconds':round(import_seconds,3),'contacts_distribution':dict(collections.Counter(r['objectives'] for r in contacts)),'shared_devices_count':len(queries.shared_devices(s)),'sites_shared':len([r for r in queries.geography(s,limit=1000) if r['objectives']>1]),'correlation':correlation,'event_methods':s.rows('SELECT method,COUNT(*) count FROM events GROUP BY method'),'integrity':integrity,'backup_restore':'passed','bundle_bytes':len(backup)}
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
