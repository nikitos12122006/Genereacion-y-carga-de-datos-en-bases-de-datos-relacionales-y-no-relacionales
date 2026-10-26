#Ejecutar :
#py generators.py --n-usuarios 10000 --vehicles-json ".\vehicles.json" --cp-csv ".\codigos_postales.csv" --out-dir ".\salida_1000"
#py generators.py --n-usuarios 10000 --vehicles-json ".\vehicles.json" --cp-csv ".\codigos_postales.csv" --out-dir ".\salida_10000"
#py generators.py --n-usuarios 100000 --vehicles-json ".\vehicles.json" --cp-csv ".\codigos_postales.csv" --out-dir ".\salida_100000"


import csv
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any
import argparse

import pyarrow as pa
import pyarrow.parquet as pq
from fastavro import writer as avro_writer
 
from faker import Faker
from faker.providers import BaseProvider
from providers import CATEGORIAS, PersonProvider, VehicleProvider

VEHICLES_JSON_PATH = Path(r"C:\Users\Nikita\Desktop\Bases de datos\Prácticas\P1\vehicles.json")
CODIGOS_POSTALES_CSV_PATH = Path(r"C:\Users\Nikita\Desktop\Bases de datos\Prácticas\P1\codigos_postales.csv")


#Poisson vive aqui, en el generador, y no en providers.py: no es un dato que
# se genere con Faker (no describe a una persona ni a un vehículo),
# sino un FILTRO que decide cuántas filas de vehículos de cada usuario
# acaban entrando en el dataset/CSV final.
 
def poisson(lam: float) -> int:
    """Muestra un entero de una Poisson(lam) mediante el algoritmo de
    Knuth (solo con random.random(), sin numpy)."""
    l = pow(2.718281828459045, -lam)  # e^-lam
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= l:
            return k - 1
 
 
def poisson_truncada(lam: float, low: int, high: int) -> int:
    """Poisson(lam) truncada a [low, high] por rechazo: se repite el
    sorteo hasta que el resultado cae dentro del rango permitido."""
    while True:
        k = poisson(lam)
        if low <= k <= high:
            return k
 
 

# DATASET 1.1 — usuarios

 
def generar_usuarios(n: int, fake: Faker) -> list[dict]:
    """Genera `n` usuarios con nombre, DNI, email, móvil, fijo,
    dirección, ciudad, código postal y provincia (1.1). El CP y la
    ciudad salen de una combinación real del dataset INE (coherentes
    entre sí), y la provincia sale coherente con ese CP."""
    usuarios = []
    for _ in range(n):
        nombre = fake.name()
        codigo_postal, ciudad = fake.cp_ciudad()
        usuarios.append(
            {
                "dni": fake.unique.dni(),
                "nombre": nombre,
                "email": fake.email_de(nombre),
                "telefono_movil": fake.telefono_movil(),
                "telefono_fijo": fake.telefono_fijo(),
                "direccion": fake.direccion(ciudad, codigo_postal),
                "ciudad": ciudad,
                "codigo_postal": codigo_postal,
                "provincia": fake.provincia(codigo_postal),
            }
        )
    return usuarios
 
 

# DATASET 1.2 — vehículos, generados a partir de los usuarios

 
def generar_vehiculos(
    usuarios: list[dict],
    fake: Faker,
    lam: float = 0.9,
    low: int = 0,
    high: int = 4,
) -> list[dict]:
    """Por cada usuario, filtra con poisson_truncada()  cuántos
    vehículos de ese usuario acaban entrando en el dataset/CSV final,
    y genera cada uno de ellos con datos coherentes del catálogo
    , matrícula según el año  y bastidor, enlazado por
    DNI (1.2). Faker/VehicleProvider solo se encarga de los DATOS del
    vehículo; cuántos vehículos hay por usuario lo decide este filtro."""
    vehiculos = []
    for usuario in usuarios:
        n_vehiculos = poisson_truncada(lam, low, high)
        for _ in range(n_vehiculos):
            fabricante, modelo, categoria_raw, periodos = fake.vehicle_model()
            anio = fake.vehicle_year(periodos)
            vehiculos.append(
                {
                    "dni_propietario": usuario["dni"],
                    "matricula": fake.unique.matricula(anio),
                    "bastidor": fake.unique.bastidor(),
                    "anio": anio,
                    "fabricante": fabricante,
                    "modelo": modelo,
                    "categoria": CATEGORIAS.get(categoria_raw, categoria_raw),
                }
            )
    return vehiculos
 
 

# Guardado de control (CSV / JSON, sin pandas)

 
def guardar_csv(registros: list[dict], path: Path) -> None:
    if not registros:
        path.write_text("")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(registros[0].keys()))
        writer.writeheader()
        writer.writerows(registros)

def guardar_parquet(registros: list[dict], path: Path) -> None:
    """Escribe un Parquet a partir de una lista de dicts, usando
    pyarrow directamente (Table.from_pylist), sin pasar por pandas."""
    if not registros:
        return
    tabla = pa.Table.from_pylist(registros)
    pq.write_table(tabla, path)



 
 
def guardar_json(registros: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)


USUARIO_AVRO_SCHEMA = {
    "type": "record",
    "name": "Usuario",
    "namespace": "bdia2627.p1",
    "fields": [
        {"name": "dni", "type": "string"},
        {"name": "nombre", "type": "string"},
        {"name": "email", "type": "string"},
        {"name": "telefono_movil", "type": "string"},
        {"name": "telefono_fijo", "type": "string"},
        {"name": "direccion", "type": "string"},
        {"name": "ciudad", "type": "string"},
        {"name": "codigo_postal", "type": "string"},
        {"name": "provincia", "type": "string"},
    ],
}
 
VEHICULO_AVRO_SCHEMA = {
    "type": "record",
    "name": "Vehiculo",
    "namespace": "bdia2627.p1",
    "fields": [
        {"name": "dni_propietario", "type": "string"},  
        {"name": "matricula", "type": "string"},
        {"name": "bastidor", "type": "string"},
        {"name": "anio", "type": "int"},
        {"name": "fabricante", "type": "string"},
        {"name": "modelo", "type": "string"},
        {"name": "categoria", "type": "string"},
    ],
}
 
# Igual que el de arriba pero SIN "dni_propietario": para el modo
# anidado  esa referencia es redundante, el vehículo ya cuelga
# de su usuario.
VEHICULO_ANIDADO_AVRO_SCHEMA = {
    "type": "record",
    "name": "VehiculoAnidado",
    "namespace": "bdia2627.p1",
    "fields": [
        campo for campo in VEHICULO_AVRO_SCHEMA["fields"]
        if campo["name"] != "dni_propietario"
    ],
}
 
# Usuario + su lista de vehículos embebida (array de VehiculoAnidado).
USUARIO_ANIDADO_AVRO_SCHEMA = {
    "type": "record",
    "name": "UsuarioConVehiculos",
    "namespace": "bdia2627.p1",
    "fields": USUARIO_AVRO_SCHEMA["fields"] + [
        {
            "name": "vehiculos",
            "type": {"type": "array", "items": VEHICULO_ANIDADO_AVRO_SCHEMA},
        }
    ],
}
 
 
def guardar_avro(registros: list[dict], path: Path, schema: dict) -> None:
    if not registros:
        return
    with open(path, "wb") as f:
        avro_writer(f, schema, registros)


 
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera los datasets usuarios y (vehículos "
        "con Faker."
    )
    parser.add_argument(
        "--n-usuarios", type=int, default=1000,
        help="Número de usuarios a generar (por defecto: 50). "
        "La práctica pide probarlo con 1000, 10000 y 100000.",
    )
    parser.add_argument(
        "--lam", type=float, default=0.9,
        help="Lambda de la Poisson para el nº de vehículos por usuario.",
    )
    parser.add_argument(
        "--max-vehiculos", type=int, default=4,
        help="Límite superior del truncamiento [0, max_vehiculos].",
    )
    parser.add_argument(
        "--vehicles-json", type=Path, default= VEHICLES_JSON_PATH,
        help="Ruta al fichero JSON con el catálogo de vehículos.",
    )
    parser.add_argument(
        "--cp-csv", type=Path,
        default= CODIGOS_POSTALES_CSV_PATH,
        help="Ruta al CSV de códigos postales/municipios (INE).",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path(r"C:\Users\Nikita\Desktop\Bases de datos\Prácticas\P1"),
        help="Directorio donde guardar los ficheros generados.",
    )
    
    return parser.parse_args(argv)

def construir_usuarios_anidados(
    usuarios: list[dict], vehiculos: list[dict]
) -> list[dict]:
    """Devuelve una copia de `usuarios` donde cada usuario lleva
    embebida su propia lista de vehículos bajo la clave "vehiculos".
    Se quita "dni_propietario" de cada vehículo anidado."""
    vehiculos_por_dni: dict[str, list[dict]] = {}
    for v in vehiculos:
        vehiculo_sin_ref = {k: val for k, val in v.items() if k != "dni_propietario"}
        vehiculos_por_dni.setdefault(v["dni_propietario"], []).append(vehiculo_sin_ref)
 
    return [
        {**usuario, "vehiculos": vehiculos_por_dni.get(usuario["dni"], [])}
        for usuario in usuarios
    ]
 
 
def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
 
    
 
    fake = Faker("es_ES") #Idioma más región
    # add_provider acepta una INSTANCIA ya creada (no solo la clase),
    # así podemos pasarle las rutas de nuestros ficheros de datos.
    fake.add_provider(PersonProvider(fake, args.cp_csv))
    fake.add_provider(VehicleProvider(fake, args.vehicles_json))
 
    usuarios = generar_usuarios(args.n_usuarios, fake)
    vehiculos = generar_vehiculos(
        usuarios, fake, lam=args.lam, low=0, high=args.max_vehiculos
    ) #Low y high son los limites de truncamiento de poisson
 
    print(f"Usuarios generados:  {len(usuarios)}")
    print(f"Vehículos generados: {len(vehiculos)}")
    print(
        f"Media vehículos/usuario: {len(vehiculos) / len(usuarios):} "
        f"(teórica antes de truncar: {args.lam:})"
    )
 
    args.out_dir.mkdir(parents=True, exist_ok=True)
     # 2.1: CSV y Parquet, ficheros separados conectados por referencias
    guardar_csv(usuarios, args.out_dir / "usuarios.csv")
    guardar_csv(vehiculos, args.out_dir / "vehiculos.csv")
    guardar_parquet(usuarios, args.out_dir / "usuarios.parquet")
    guardar_parquet(vehiculos, args.out_dir / "vehiculos.parquet")

     # 2.2: JSONL y Avro, en los DOS modos 
     
    usuarios_anidados = construir_usuarios_anidados(usuarios, vehiculos)
 
    # 2.2.2  un fichero por dataset, con referencia (dni / dni_propietario)
    guardar_json(usuarios, args.out_dir / "usuarios.jsonl")
    guardar_json(vehiculos, args.out_dir / "vehiculos.jsonl")
    guardar_avro(usuarios, args.out_dir / "usuarios.avro", USUARIO_AVRO_SCHEMA)
    guardar_avro(vehiculos, args.out_dir / "vehiculos.avro", VEHICULO_AVRO_SCHEMA)
 
    # 2.2.1  un único fichero para todo, anidando vehículos en usuario
    guardar_json(usuarios_anidados, args.out_dir / "datos_anidados.jsonl")
    guardar_avro(
        usuarios_anidados,
        args.out_dir / "datos_anidados.avro",
        USUARIO_ANIDADO_AVRO_SCHEMA,
    )
 
    print(f"Ficheros guardados en: {args.out_dir}")
 
 
if __name__ == "__main__":
    main()
 

 