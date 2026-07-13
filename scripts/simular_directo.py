"""
Simula el mes completo de JUNIO 2026 llamando el runner directamente
(sin HTTP, sin timeout). Una gestion a la vez.

Corte  5: G1=03-jun  G2=04-jun  G3=05-jun
Corte 10: G1=08-jun  G2=09-jun  G3=10-jun
Corte 15: G1=11-jun  G2=12-jun  G3=15-jun
Corte 17: G1=15-jun  G2=16-jun  G3=17-jun
Corte 20: G1=18-jun  G2=19-jun  G3=22-jun (sab->lun)
Corte 24: G1=22-jun  G2=23-jun  G3=24-jun
"""
import sys
import time
from datetime import datetime

sys.path.insert(0, "src")

from preventiva.jobs.preventiva_runner import ejecutar_preventiva
from preventiva.infrastructure.config.settings import PreventivaSettings

cfg = PreventivaSettings()

EJECUCIONES = [
    ("03062026",  5, "Corte  5 - G1"),
    ("04062026",  5, "Corte  5 - G2"),
    ("05062026",  5, "Corte  5 - G3 -> Excel corte 5"),
    ("08062026", 10, "Corte 10 - G1"),
    ("09062026", 10, "Corte 10 - G2"),
    ("10062026", 10, "Corte 10 - G3 -> Excel corte 10"),
    ("11062026", 15, "Corte 15 - G1"),
    ("12062026", 15, "Corte 15 - G2"),
    ("15062026", 15, "Corte 15 - G3 -> Excel corte 15"),
    ("15062026", 17, "Corte 17 - G1"),
    ("16062026", 17, "Corte 17 - G2"),
    ("17062026", 17, "Corte 17 - G3 -> Excel corte 17"),
    ("18062026", 20, "Corte 20 - G1"),
    ("19062026", 20, "Corte 20 - G2"),
    ("22062026", 20, "Corte 20 - G3 -> Excel corte 20"),
    ("22062026", 24, "Corte 24 - G1"),
    ("23062026", 24, "Corte 24 - G2"),
    ("24062026", 24, "Corte 24 - G3 -> Excel corte 24 + MENSUAL"),
]

print(f"\n{'Descripcion':<40} {'Estado':<6} {'Sel':>7}  {'TXT'}")
print("-" * 110)

archivos_txt = []
archivos_xls = []
errores = []

for fecha_str, corte, desc in EJECUCIONES:
    fecha_dt = datetime.strptime(fecha_str, "%d%m%Y").date()
    t0 = time.time()

    try:
        ctx = ejecutar_preventiva(
            fecha_ejecucion=fecha_dt,
            dia_corte=corte,
            modo="manual",
            settings=cfg,
        )
        estado  = ctx.estado if hasattr(ctx, "estado") else ("OK" if ctx.ok else "ERR")
        sel     = len(ctx.seleccionados) if ctx.seleccionados else 0
        txt     = str(ctx.ruta_isabel).split("\\")[-1] if ctx.ruta_isabel else "---"
        xls     = str(ctx.ruta_reporte).split("\\")[-1] if ctx.ruta_reporte else ""
        err     = ctx.mensaje_error or ""
    except Exception as e:
        estado, sel, txt, xls, err = "EXC", 0, "---", "", str(e)[:200]

    elapsed = round(time.time() - t0, 1)
    print(f"{desc:<40} {estado:<6} {sel:>7}  {txt}  {xls}  ({elapsed}s)")

    if err:
        print(f"  >> {err[:200]}")

    if txt != "---":
        archivos_txt.append(txt)
    if xls:
        archivos_xls.append(xls)
    if estado not in ("OK",):
        errores.append(f"{desc}: {err[:80]}")

# Verificar mensual
from pathlib import Path
directorio = Path(r"C:\Users\edison.cuichan\Desktop\New folder")
mensual = list(directorio.glob("REPORTE_PREVENTIVA_MENSUAL_062026.xlsx"))

print(f"\n{'='*110}")
print(f"RESUMEN JUNIO 2026")
print(f"  TXT para Isabel : {len(archivos_txt)}/18")
print(f"  Excel por corte : {len(archivos_xls)}/6")
print(f"  Excel mensual   : {len(mensual)}/1")
print(f"  Errores         : {len(errores)}")
if errores:
    print("\nERRORES:")
    for e in errores:
        print(f"  {e}")

print(f"\nArchivos generados en {directorio}:")
for f in sorted(directorio.glob("*062026*")):
    print(f"  {f.name}")
