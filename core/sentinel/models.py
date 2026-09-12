"""Versioned domain vocabulary. No Streamlit dependencies."""
from dataclasses import dataclass
import hashlib,json,uuid
from datetime import datetime,timezone

SCHEMA_VERSION = 1
ENGINE_VERSION = '1.0.0'
TZ = 'America/Mazatlan'
CONFIDENCE = ('CONFIRMADO','PROBABLE','INFERIDO','PENDIENTE','DESCARTADO')
ENTITY_TYPES = ('PERSONA','TELEFONO','DISPOSITIVO','SIM','PERFIL_DIGITAL','VEHICULO','DOMICILIO','ANTENA','EMPRESA','EVIDENCIA','EVENTO','UBICACION','SERVICIO','OTRO')
RELATION_TYPES = ('UTILIZA','PERTENECE_A','COMUNICA_CON','OBSERVADO_CON','UBICADO_EN','TRABAJA_EN','RESIDE_EN','FAMILIAR_DE','PROPIETARIO_DE','PUBLICO_DESDE','COMPARTIO_IMEI','COMPARTIO_UBICACION','COINCIDENCIA_TEMPORAL','RELACIONADO_CON','OTRO')
VALID_TYPES = frozenset(('DATOS','DATOS WIFI','VOZ ENTRANTE','VOZ SALIENTE','VOZ TRANSITO','VOZ TRANSFER','MENSAJE ENTRANTE','MENSAJE SALIENTE','MENSAJES 2 VIAS','TRANSFER'))

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
def dump(value): return json.dumps(value,ensure_ascii=False,allow_nan=False,default=str,sort_keys=True)
def stable(*parts): return hashlib.sha256(dump(parts).encode()).hexdigest()
def entity_id(kind,key): return kind+':'+stable(key)[:24]

@dataclass(frozen=True)
class ImportOptions:
    timezone: str = TZ
    ab_semantics: str = 'A_ORIGEN_B_DESTINO'
    dedup_seconds: float = 0
    duration_tolerance: float = 0
    def validate(self):
        if self.timezone != TZ or self.ab_semantics != 'A_ORIGEN_B_DESTINO':
            raise ValueError('Esta versión requiere America/Mazatlan y A=origen, B=destino.')
        if not 0 <= self.dedup_seconds <= 30 or not 0 <= self.duration_tolerance <= 5:
            raise ValueError('Tolerancias fuera del rango permitido.')
