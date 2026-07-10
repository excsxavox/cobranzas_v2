# Muestra las cabeceras normalizadas de cualquier archivo .lis tab-separado.
# Uso: python scripts/inspect_headers.py ruta_archivo.lis

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cobranzas.infrastructure.adapters.parser_comun import leer_lineas_archivo
from cobranzas.domain.schemas.tab_schema import normalizar_encabezados


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/inspect_headers.py <ruta_archivo.lis>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Archivo no encontrado: {path}")
        sys.exit(1)

    lineas = leer_lineas_archivo(path)
    print(f"\nArchivo: {path.name}")
    print(f"Total líneas: {len(lineas)}")

    for i, linea in enumerate(lineas[:10]):
        tabs = linea.count("\t")
        print(f"  Línea {i}: {tabs} tabs | {linea[:120]!r}")

    header_idx = next(
        (i for i, l in enumerate(lineas) if "\t" in l and l.strip()),
        None,
    )
    if header_idx is None:
        print("\n[ERROR] No se encontró ninguna línea con tabuladores.")
        return

    print(f"\nCabecera detectada en línea {header_idx}:")
    cab_orig = lineas[header_idx].split("\t")
    cab_norm = normalizar_encabezados(cab_orig)
    print(f"  {'Original':<40} -> {'Normalizado'}")
    print(f"  {'-'*60}")
    for orig, norm in zip(cab_orig, cab_norm):
        print(f"  {orig:<40} -> {norm}")

    print(f"\nTotal columnas: {len(cab_orig)}")
    print(f"Total filas de datos (aprox): {len([l for l in lineas[header_idx+1:] if l.strip()])}")


if __name__ == "__main__":
    main()
