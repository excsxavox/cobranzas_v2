"""
Simula el flujo completo según la HU:
  1. Backfill histórico CAMOROSICO (2 meses)
  2. Ejecución del pipeline para cada fecha/corte disponible
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8001"


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
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


# ── Paso 0: verificar que la API esté en pie ──────────────────────────────
print("\n[0] Verificando API...")
h = get(f"{BASE}/health")
if "error" in h:
    print(f"   ERROR: API no disponible → {h}")
    sys.exit(1)
print(f"   API OK — {h}")

# ── Paso 1: Backfill histórico ────────────────────────────────────────────
print("\n[1] Cargando historial CAMOROSICO (2 meses)...")
resp = post(f"{BASE}/historico/cargar?meses=2&forzar=false")
print(f"   Ventana  : {resp.get('ventana_desde')} a {resp.get('ventana_hasta')}")
print(f"   Cargados : {resp.get('registros_cargados')} registros")
print(f"   Omitidos : {resp.get('dias_omitidos')} días (ya tenían datos)")
print(f"   Sin arch : {resp.get('dias_sin_archivo')} días sin archivo")
if resp.get("detalle"):
    print("   Detalle:")
    for d in resp["detalle"]:
        print(f"     {d['fecha']}  {d['archivo']:<45}  {d['registros']:>6} reg")

# ── Paso 2: Ejecuciones del pipeline según fechas disponibles ─────────────
# Cortes configurados en dbo.catalogo: [5, 10, 15, 17, 20, 24]
# Ejecutamos la última gestión del mes de junio (corte 5 del mes siguiente = 30-jun)
ejecuciones = [
    # (fecha_DDMMAAAA, corte, descripcion)
    ("04052026", 5,  "G1 mayo — 2 días antes del corte 5-may"),
    ("05052026", 5,  "G1 mayo — día del corte 5-may"),
    ("30062026", 5,  "G3 junio — última gestión disponible (30-jun, corte 5-jul)"),
]

for fecha, corte, desc in ejecuciones:
    print(f"\n[2] Ejecutando: {desc}")
    print(f"   fecha={fecha}  corte={corte}")
    body = {"fecha": fecha, "corte": corte, "modo": "manual"}
    r = post(f"{BASE}/ejecutar-preventiva", body)
    estado = r.get("estado", "?")
    sel    = r.get("seleccionados", 0)
    txt    = r.get("archivo_isabel") or "—"
    xls    = r.get("archivo_reporte") or "—"
    err    = r.get("mensaje_error") or ""
    print(f"   Estado       : {estado}")
    print(f"   Seleccionados: {sel}")
    print(f"   TXT Isabel   : {txt}")
    print(f"   Reporte XLS  : {xls}")
    if err:
        print(f"   ERROR        : {err[:200]}")

print("\n[FIN] Flujo completo ejecutado.")
