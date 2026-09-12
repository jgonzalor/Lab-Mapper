# Sentinel Mapa Investigativo V1

Módulo propio integrado a Go Mapper. Conserva la ruta `pages/app_grafo_inteligente.py`, guardian, menú y tema de la Suite. No requiere actualizar las dependencias de la Suite. JavaScript de mapa Leaflet 1.9.4 distribuido localmente con su licencia BSD-2-Clause; grafo SVG circular y puente de selección originales. No incluye código de OSINT-Mapping-Tool.

## Operación local (recomendada)

Usar Python 3.11 o 3.12. Mantener la instalación de dependencias de la Suite:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SENTINEL_CASES_DIR = "C:\GoMapperCases"
streamlit run app.py
```

Configurar las credenciales mediante el mecanismo existente de guardian en `.streamlit/secrets.toml`. No publicar secretos ni copiar los casos al repositorio. No usar credenciales de desarrollo en instalaciones institucionales. Esta entrega no modifica guardian ni sus políticas globales.

El directorio de casos, por defecto `~/GoMapperCases`, debe encontrarse en un disco local persistente con respaldo y permisos del sistema operativo. SQLite no incorpora cifrado en esta implementación. Utilizar cifrado de disco y acceso restringido conforme al entorno institucional. Una instancia efímera de Streamlit Cloud no garantiza durabilidad; la misma interfaz puede ejecutarse allí, pero no debe ser la única custodia del caso. No se configura nube, acceso público ni despliegue automáticamente.

## Flujo

1. Entrar a **Sentinel Mapa Investigativo**, crear un caso e indicar investigador.
2. Expandir **Importar CDR / respaldo / datos del caso** y seleccionar varios Excel simultáneamente.
3. Mantener tolerancias cero inicialmente. Pulsar **Importar y analizar**. No se importa la hoja Duplicados como eventos.
4. **Análisis** muestra contactos n/N, IMEI compartidos, relaciones entre objetivos y coincidencias celulares con reglas explícitas.
5. **Relaciones** abre el grafo circular acotado. Clic en nodo/arista abre su ficha. **Expansión** muestra relaciones del seleccionado; filtrar por tipo reduce ruido.
6. **Mapa** agrupa sitios/sectores. Elegir una línea limita sus ubicaciones. Fondo sin red por defecto; activar OpenStreetMap es opcional. No existe geocodificación automática ni envío de CDR a APIs.
7. **Cronología** permite línea, fechas, entidad y paginación, y muestra las filas que sostienen cada evento.
8. Agregar persona, teléfono, dispositivo, SIM, perfil, vehículo, domicilio, empresa, evidencia, evento, ubicación u otra categoría. Registrar fuente/confianza y vincular con entidades existentes.
9. Editar interpretación o descartar no reescribe las celdas importadas. Para sustituir extremos o tipo de una relación, descartar la anterior y crear la correcta, conservando ambas en bitácora.
10. Preparar respaldo completo y descargar ZIP. Cerrar y reabrir conserva el caso. **Recuperar paquete de caso** permite restaurar una copia con comprobación de hashes/esquema.

Guardar ocurre al confirmar cada formulario. Descargar CSV exporta la vista/página indicada; el ZIP es el respaldo integral. Los CSV usan UTF-8 BOM y neutralizan fórmulas peligrosas; los identificadores canónicos permanecen en SQLite/JSON y los Excel originales. No abrir identificadores largos como números en Excel.

## Contrato analítico

- Teléfono identifica la línea observada; A=origen, B=destino. No invertir automáticamente por ENTRANTE.
- Prefijo mexicano se unifica solo cuando coincide con la longitud de 52+10 o 521+10; se preservan originales.
- Hora sin zona se interpreta como America/Mazatlan por convención documentada, sin desplazamiento. Hora explícitamente zonificada se convierte. Una cadena con fecha sin hora no inventa medianoche.
- Valores administrativos permanecen NO_CLASIFICADO. Registros de tráfico contradictorios permanecen REVISAR.
- APN no es contacto telefónico. Remitentes SMS alfanuméricos se conservan como SERVICIO; quedan fuera del ranking de contactos numéricos.
- VOZ TRANSITO/TRANSFER son tráfico especial y no se fusionan con llamadas normales. Una llamada registrada no implica necesariamente conversación completada.
- Repetición exacta de registro: agrupación inferida, conservando todas las filas. No se deduplica mediante Es_Duplicado ni por minuto.
- Espejo multi-CDR: misma dirección, familia compatible, duración conocida y emparejamiento recíproco único entre líneas distintas. Empates se conservan por separado. Tolerancia distinta de cero produce agrupación PROBABLE. La política queda fijada en el caso para evitar cambios silenciosos.
- IMEI observado de 14 dígitos se conserva íntegro; no se calcula otro dígito ni se atribuye automáticamente marca, modelo, persona o titular.
- Sitio compartido significa coordenadas registradas comunes. Sector conserva azimuth e identificadores celulares disponibles. Plus Code no es clave única de antena.
- Coincidencia temporal compara eventos lógicos distintos en el mismo sitio, en la ventana elegida; no compara dos soportes de la misma llamada como eventos independientes. No usa toda la duración de DATOS como prueba de permanencia. La relevancia operativa requiere el mínimo de eventos distintos por línea; no prueba reunión.
- CONFIRMADO indica observación/documentación, no identidad verdadera ni ubicación exacta de una persona.

## Arquitectura y límites

`core/sentinel` contiene modelos, validación, ingestión, entidades, ubicaciones, eventos, relaciones, correlación, repositorio SQL, consultas y exportación. `ui/sentinel` contiene presentación y componente local. La página existente se mantiene como entrada mínima.

No hay importaciones de páginas Streamlit en el motor. SQLite usa claves foráneas, transacciones, índices, propietario por caso y revisiones de interpretación. Aislamiento de aplicación por usuario de guardian; no sustituye permisos del disco ni un sistema multiinstitucional de roles. PostgreSQL requiere implementar otro repositorio y migraciones, no trasladar objetos st.session_state.

V1 carga como máximo 500,000 filas y 100 MiB por Excel, con 500,000 filas por lote. El motor aún reconstruye las derivaciones al importar: no es ingestión incremental ni está certificado para millones. La escala efectivamente probada queda en el reporte privado de validación. No recalcula importación/correlación en reruns; solo una vista ejecuta sus consultas. Las vistas son paginadas/acotadas y los límites se muestran. El cálculo de coincidencias se limita a 50,000 pares y declara LIMITADO cuando alcanza ese tope.

La coincidencia geográfica V1 es por igualdad de sitio a siete decimales, no radio configurable ni triangulación. Puede dejar sitios casi iguales separados; se prefiere ese falso negativo a fusionar infraestructura sin evidencia. Las revisiones de entidades/relaciones permanecen separadas del importado. Al importar nuevos datos se invalidan y recalculan hallazgos; no hay un archivo completo de todas las versiones históricas del motor. Exportar un corte antes de cambiar el universo si se requiere reproducir cada estado histórico.

La ficha, campos manuales y entidades extra son una V1 operativa; no un editor de investigación comparable en gestos a una aplicación dedicada React. El grafo permite selección, movimiento local de nodos y expansión acotada; no guarda posiciones arrastradas. Los tipos nuevos aceptan atributos básicos; contratos especializados pueden añadirse después. No se implementa conversor de antiguos grafos NODOS/ARISTAS: esos archivos permanecen disponibles para revisión con la versión anterior.

## Pruebas

```bash
pip install pytest
python -m pytest tests/sentinel -q
```

Para integrar el conjunto real fuera del repositorio:

```powershell
$env:SENTINEL_TEST_DATA = "C:\Evidencia\Excel"
python -m pytest tests/sentinel -q
python scripts/sentinel_validate.py --inputs "C:\Evidencia\Excel" --cases "C:\ValidacionSentinel" --report "C:\ValidacionSentinel\reporte.json"
```

La prueba real está diseñada para los cuatro Excel de referencia; si cambian, actualizar expectativas con auditoría, no ajustar el motor a resultados deseados. No agregar sus archivos ni identificadores a Git.

Se comprueba guardian sin autenticación, las cinco vistas mediante Streamlit AppTest, lógica crítica, integridad, exportación/restauración. AppTest no sustituye un smoke test del componente JavaScript en navegador real; verificar clic de nodo, arista y punto antes de desplegar en un entorno institucional.

## Cambios de alcance mínimo

Editados: página de grafo, etiqueta de menú, tarjeta de portada y reglas de exclusión de Git. Añadidos: paquetes Sentinel, pruebas, validador y esta documentación. No se modificaron guardian, KMZ, Link Analysis, Consulta Visual, Línea de tiempo, Maestro, ORÁCULO, Informes ni versiones de dependencias.

Errores ajenos observados: indentación en modules/auth.py y modules/kmz_builder.py; configuración theme.sidebar no reconocida por Streamlit 1.35; duplicidad de auxiliares KMZ y algunas dependencias; configuración de acceso en archivos públicos preexistentes. No se ocultaron corrigiendo componentes fuera del alcance. Revisar por separado configuración expuesta y rotación si los valores aún son válidos.


## Ampliación solicitada: Limpieza offline

Limpieza incorpora **Modo offline: no consultar direcciones en internet**. Por defecto permanece desactivado, conservando el modo habitual. Activo omite el geocodificador principal, búsqueda administrativa de localidad y búsqueda de nombres en caché/PlusRepo; mantiene direcciones ya aportadas y calcula Plus Code localmente. Las direcciones no disponibles se marcan SIN_DIRECCIÓN (MODO OFFLINE). Mantiene las hojas de exportación existentes y añade la política offline en LOG_Limpieza. No aplica cambios a la zona horaria ni a la deduplicación propia de Limpieza.

Causas corregidas: la ruta secundaria pluscode_label consultaba Nominatim aunque GEOCODE_ENABLED fuese falso; las claves opcionales de proveedores se leían al importar la página y podían lanzar una excepción sin secrets.toml; RateLimiter configuraba error_wait_seconds menor que min_delay_seconds, combinación rechazada por Geopy. Ahora ambas rutas respetan offline/GEOCODE_ENABLED, las claves se resuelven al usar el proveedor y los tiempos son compatibles.

Hallazgos adicionales de Limpieza: Tipo normaliza texto pero no valida que sea tráfico; el detector de encabezado no elimina bloques administrativos posteriores. La bandera Es_Duplicado se calcula antes de reducir DATOS y puede seguir verdadera en el registro retenido. No se cambió esa semántica ni se borraron filas de origen por esta ampliación. Sentinel valida nuevamente y conserva los descartes. La depuración administrativa de la salida de Limpieza merece una migración de formato y auditoría separada.
