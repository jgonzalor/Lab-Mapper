"""Offline address policy. Uses only values already present in the imported row."""
import math

def offline_address(row):
    for field in ('Direccion_final','PLUS_CODE_NOMBRE'):
        value=row.get(field)
        if value is None or (isinstance(value,float) and math.isnan(value)):continue
        value=str(value).strip()
        if value.upper() in ('','NAN','NONE','<NA>','SIN_DIRECCIÓN','SIN_DIRECCION'):continue
        return value
    return 'SIN_DIRECCIÓN (MODO OFFLINE)'
