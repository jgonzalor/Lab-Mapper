"""Strict classification; identifiers are never inferred by stripping arbitrary text."""
import math,re,unicodedata
from datetime import datetime,date,time
from decimal import Decimal,InvalidOperation
from zoneinfo import ZoneInfo
from .models import VALID_TYPES,TZ

def text(v):
    if v is None: return ''
    if isinstance(v,float) and not math.isfinite(v): return ''
    s=str(v).strip()
    return '' if s.upper() in {'NAN','NAT','NONE','NULL','<NA>'} else s

def norm(v):
    s=unicodedata.normalize('NFKD',text(v))
    return ' '.join(''.join(c for c in s if not unicodedata.combining(c)).upper().split())

def identifier(v):
    if isinstance(v,bool): return ''
    s=text(v)
    if isinstance(v,float) and (not v.is_integer() or abs(v)>=10**15): return ''
    if re.fullmatch(r'\d+\.0+',s): s=s.split('.')[0]
    return s if re.fullmatch(r'\d+',s) else ''

def phone(v):
    s=text(v)
    if s.startswith('+'): s=s[1:]
    s=identifier(s)
    if len(s)==12 and s.startswith('52'): s=s[2:]
    elif len(s)==13 and s.startswith('521'): s=s[3:]
    return s if 10<=len(s)<=15 else ''

def device(v,sim=False):
    s=identifier(v)
    return s if ((14<=len(s)<=15) if sim else len(s) in (14,15,16)) and len(set(s))>1 else ''

def number(v):
    try:
        f=float(v)
        return f if math.isfinite(f) else None
    except (ValueError,TypeError): return None

def duration(v):
    if isinstance(v,time): return v.hour*3600+v.minute*60+v.second
    s=text(v)
    if re.fullmatch(r'\d+:\d{2}:\d{2}(?:\.\d+)?',s):
        h,m,sec=map(float,s.split(':'))
        if m>=60 or sec>=60:return None
        return h*3600+m*60+sec
    n=number(v)
    return n if n is not None and n>=0 else None

def temporal(v):
    """Naive times labelled, not shifted. Ambiguous/nonexistent local times rejected."""
    policy='EXPLICITA_CONVERTIDA'
    if isinstance(v,datetime): dt=v
    else:
        s=text(v)
        if not s:return None,None,'FECHA_AUSENTE'
        if not re.search(r'[ T]\d{1,2}:\d{2}',s):return None,None,'HORA_AUSENTE; no inventar medianoche'
        try:dt=datetime.fromisoformat(s.replace('Z','+00:00'))
        except ValueError:
            dt=None
            for fmt in ('%d/%m/%Y %H:%M:%S','%d/%m/%Y %H:%M','%d-%m-%Y %H:%M:%S','%d-%m-%Y %H:%M','%d/%m/%Y %I:%M:%S %p','%d/%m/%Y %I:%M %p'):
                try:dt=datetime.strptime(s,fmt);break
                except ValueError:pass
            if dt is None:return None,None,'FECHA_NO_INTERPRETABLE'
    zone=ZoneInfo(TZ)
    if dt.tzinfo is None:
        a=dt.replace(tzinfo=zone,fold=0);b=dt.replace(tzinfo=zone,fold=1)
        if a.utcoffset()!=b.utcoffset():return None,None,'HORA_LOCAL_AMBIGUA_O_INEXISTENTE'
        dt=a;policy='LOCAL_ASUMIDA_POR_CONVENCION_SIN_DESPLAZAR'
    dt=dt.astimezone(zone)
    return dt.isoformat(),dt.timestamp(),policy

def classify(v):
    t=norm(v)
    return t if t in VALID_TYPES else 'NO_CLASIFICADO'

def endpoint(v):
    p=phone(v)
    if p:return 'TELEFONO',p
    s=text(v)
    if s and len(s)<=80 and (re.fullmatch(r'[\w.@+\- ]+',s)):
        return 'SERVICIO',norm(s)
    return None,None

def safe_cell(v):
    if isinstance(v,(datetime,date,time)):return v.isoformat()
    if v is None or (isinstance(v,float) and not math.isfinite(v)):return None
    if isinstance(v,(str,int,float,bool)):return v
    return str(v)
