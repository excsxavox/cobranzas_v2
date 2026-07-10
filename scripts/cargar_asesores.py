# Carga el archivo CSV de asesores en la tabla asesores.
# Formato CSV esperado (coma separador, primera fila cabecera):
#   usuario,perfil_usuario
#
# Mapeo: usuario -> nombre,  perfil_usuario -> perfil
#
# Uso:
#   .venv\Scripts\python scripts/cargar_asesores.py "ruta/al/archivo.csv"

import sys
import csv
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_PATH = Path(__file__).parent.parent / "data" / "BD_Cobranza.sqlite"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/cargar_asesores.py <ruta_archivo.csv>")
        sys.exit(1)

    archivo = Path(sys.argv[1])
    if not archivo.exists():
        print(f"Archivo no encontrado: {archivo}")
        sys.exit(1)

    ahora = str(datetime.now())
    insertados = 0
    omitidos = 0

    with Session() as session:
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                with archivo.open(encoding=encoding, newline="") as f:
                    reader = csv.DictReader(f)
                    reader.fieldnames = [c.strip().strip('"').lower() for c in reader.fieldnames]

                    for fila in reader:
                        usuario = (fila.get("usuario") or "").strip()
                        perfil  = (fila.get("perfil_usuario") or "").strip()
                        if not usuario:
                            omitidos += 1
                            continue

                        existe = session.execute(
                            text("SELECT COUNT(*) FROM asesores WHERE nombre = :n"),
                            {"n": usuario}
                        ).scalar()

                        if not existe:
                            session.execute(
                                text("INSERT INTO asesores (nombre, perfil, activo, creado_en) VALUES (:n, :p, 1, :f)"),
                                {"n": usuario, "p": perfil, "f": ahora}
                            )
                            insertados += 1
                        else:
                            session.execute(
                                text("UPDATE asesores SET perfil=:p WHERE nombre=:n"),
                                {"p": perfil, "n": usuario}
                            )

                session.commit()
                break
            except UnicodeDecodeError:
                continue

    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM asesores")).scalar()

    print(f"\nCarga completada:")
    print(f"  Insertados: {insertados}")
    print(f"  Omitidos:   {omitidos}")
    print(f"  Total en tabla asesores: {total}")


if __name__ == "__main__":
    main()
