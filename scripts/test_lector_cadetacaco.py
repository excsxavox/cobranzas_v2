# Prueba rapida del lector cadetacaco contra el archivo real
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preventiva.infrastructure.adapters.lis_cadetacaco_reader import leer_cadetacaco

ruta = Path(r"C:\Users\edison.cuichan\Desktop\New folder\cadetacaco_cie05312026_1142_of_0.lis")
registros = leer_cadetacaco(ruta, fecha_corte=date(2026, 5, 31))

print(f"Total registros leidos: {len(registros)}")
if registros:
    r = registros[0]
    print(f"  operacion:       {r.operacion}")
    print(f"  identificacion:  {r.identificacion}")
    print(f"  nombre:          {r.nombre}")
    print(f"  tipo_operacion:  {r.tipo_operacion}")
    print(f"  dia_pago:        {r.dia_pago}")
    print(f"  valor_cuota:     {r.valor_cuota}")
    print(f"  dias_mora:       {r.dias_mora}")
    print(f"  fecha_concesion: {r.fecha_concesion}")
