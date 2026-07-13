"""
Simula el mes completo de JUNIO 2026 segun la HU:
  6 cortes x 3 gestiones = 18 TXT + 6 Excel por corte + 1 Excel mensual = 25 archivos

Cortes: 5, 10, 15, 17, 20, 24

Fechas de gestion (junio 2026, sin feriados):
  Corte  5: G1=03-jun  G2=04-jun  G3=05-jun
  Corte 10: G1=08-jun  G2=09-jun  G3=10-jun
  Corte 15: G1=11-jun  G2=12-jun  G3=15-jun (lunes, 2 dias habiles antes)
  Corte 17: G1=15-jun  G2=16-jun  G3=17-jun
  Corte 20: G1=18-jun  G2=19-jun  G3=22-jun (sabado->lunes)
  Corte 24: G1=22-jun  G2=23-jun  G3=24-jun
"""
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8002"

EJECUCIONES = [
    # (fecha_DDMMAAAA, corte, gestion, descripcion)
    ("03062026",  5, 1, "Corte  5 - G1"),
    ("04062026",  5, 2, "Corte  5 - G2"),
    ("05062026",  5, 3, "Corte  5 - G3 -> Excel corte 5"),
    ("08062026", 10, 1, "Corte 10 - G1"),
    ("09062026", 10, 2, "Corte 10 - G2"),
    ("10062026", 10, 3, "Corte 10 - G3 -> Excel corte 10"),
    ("11062026", 15, 1, "Corte 15 - G1"),
    ("12062026", 15, 2, "Corte 15 - G2"),
    ("15062026", 15, 3, "Corte 15 - G3 -> Excel corte 15"),
    ("15062026", 17, 1, "Corte 17 - G1"),
    ("16062026", 17, 2, "Corte 17 - G2"),
    ("17062026", 17, 3, "Corte 17 - G3 -> Excel corte 17"),
    ("18062026", 20, 1, "Corte 20 - G1"),
    ("19062026", 20, 2, "Corte 20 - G2"),
    ("22062026", 20, 3, "Corte 20 - G3 -> Excel corte 20 (sab->lun)"),
    ("22062026", 24, 1, "Corte 24 - G1"),
    ("23062026", 24, 2, "Corte 24 - G2"),
    ("24062026", 24, 3, "Corte 24 - G3 -> Excel corte 24 + Excel MENSUAL"),
]


def post(url, body=None):
    data = json.dumps(body).encode() if body else b""
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detalle": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


# Verificar API
h = get(f"{BASE}/health")
if "error" in h:
    print(f"ERROR: API no disponible -> {h}")
    sys.exit(1)
print(f"API OK\n")

archivos_generados = []
errores = []

print(f"{'Descripcion':<35} {'Estado':<8} {'Sel':>7}  {'TXT':<45}  {'Excel'}")
print("-" * 130)

for fecha, corte, gestion, desc in EJECUCIONES:
    body = {"fecha": fecha, "corte": corte, "modo": "manual"}
    r = post(f"{BASE}/ejecutar-preventiva", body)
    time.sleep(2)  # pausa entre ejecuciones para liberar BD

    estado = r.get("estado", "?")
    sel    = r.get("seleccionados", 0)
    txt    = r.get("archivo_isabel") or ""
    xls    = r.get("archivo_reporte") or ""
    err    = r.get("mensaje_error") or ""

    txt_nombre = txt.split("\\")[-1] if txt else "---"
    xls_nombre = xls.split("\\")[-1] if xls else ""

    simbolo = "OK" if estado == "OK" else "ERR"
    print(f"{desc:<35} {simbolo:<8} {sel:>7}  {txt_nombre:<45}  {xls_nombre}")

    # Mostrar SIEMPRE el detalle si hay error o estado != OK
    if estado != "OK" or err:
        print(f"  >> DETALLE RESPUESTA: {json.dumps(r, ensure_ascii=False)[:400]}")

    if txt:
        archivos_generados.append(txt_nombre)
    if xls:
        archivos_generados.append(xls_nombre)
    if err and estado != "OK":
        errores.append(f"{desc}: {err[:120]}")

# Verificar reporte mensual
import os
from pathlib import Path
directorio = Path(r"C:\Users\edison.cuichan\Desktop\New folder")
mensual = list(directorio.glob("REPORTE_PREVENTIVA_MENSUAL_062026.xlsx"))
if mensual:
    archivos_generados.append(mensual[0].name)

print(f"\n{'='*130}")
print(f"\nRESUMEN JUNIO 2026")
print(f"  TXT para Isabel    : {sum(1 for a in archivos_generados if a.startswith('PREVENTIVA'))}")
print(f"  Excel por corte    : {sum(1 for a in archivos_generados if 'CORTE' in a and a.endswith('.xlsx'))}")
print(f"  Excel mensual      : {sum(1 for a in archivos_generados if 'MENSUAL' in a)}")
print(f"  TOTAL archivos     : {len(archivos_generados)}")
print(f"  Errores            : {len(errores)}")

if errores:
    print("\nERRORES:")
    for e in errores:
        print(f"  {e}")

print(f"\nArchivos en {directorio}:")
todos = sorted(directorio.glob("*062026*"))
for f in todos:
    print(f"  {f.name}")
