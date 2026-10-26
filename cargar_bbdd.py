#Guardar en SqLite :
#python cargar_bbdd.py --db-type sqlite --in-usuarios ".\salidas\10000\usuarios.csv" --in-vehiculos ".\salidas\10000\vehiculos.csv" --sqlite-path ".\salidas\10000\sqlite_csv.db"
#python cargar_bbdd.py --db-type sqlite --in-usuarios ".\salidas\10000\usuarios.parquet" --in-vehiculos ".\salidas\10000\vehiculos.parquet" --sqlite-path ".\salidas\10000\sqlite_parquet.db"
#python cargar_bbdd.py --db-type sqlite --in-usuarios ".\salidas\10000\usuarios.jsonl" --in-vehiculos ".\salidas\10000\vehiculos.jsonl" --sqlite-path ".\salidas\10000\sqlite_jsonl.db"
#python cargar_bbdd.py --db-type sqlite --in-usuarios ".\salidas\10000\usuarios.avro" --in-vehiculos ".\salidas\10000\vehiculos.avro" --sqlite-path ".\salidas\10000\sqlite_avro.db"
#Cambiando según 1000 ,10000 y 100000 usuarios

#Guardar en PostgreSQL:
#Definir $PG_HOST="localhost"
#PG_PORT="5432"
#PG_USER="postgres"
#PG_PASS="postgres"

#createdb -h $PG_HOST -p $PG_PORT -U $PG_USER practica_1000
#createdb -h $PG_HOST -p $PG_PORT -U $PG_USER practica_10000
#createdb -h $PG_HOST -p $PG_PORT -U $PG_USER practica_100000

#python cargar_bbdd.py --db-type postgres --in-usuarios ".\salidas\1000\usuarios.csv" --in-vehiculos ".\salidas\1000\vehiculos.csv" --db-host $PG_HOST --db-port $PG_PORT --db-name practica_1000 --db-user $PG_USER --db-pass $PG_PASS
#python cargar_bbdd.py --db-type postgres --in-usuarios ".\salidas\1000\usuarios.parquet" --in-vehiculos ".\salidas\1000\vehiculos.parquet" --db-host $PG_HOST --db-port $PG_PORT --db-name practica_1000 --db-user $PG_USER --db-pass $PG_PASS
#python cargar_bbdd.py --db-type postgres --in-usuarios ".\salidas\1000\usuarios.jsonl" --in-vehiculos ".\salidas\1000\vehiculos.jsonl" --db-host $PG_HOST --db-port $PG_PORT --db-name practica_1000 --db-user $PG_USER --db-pass $PG_PASS
#python cargar_bbdd.py --db-type postgres --in-usuarios ".\salidas\1000\usuarios.avro" --in-vehiculos ".\salidas\1000\vehiculos.avro" --db-host $PG_HOST --db-port $PG_PORT --db-name practica_1000 --db-user $PG_USER --db-pass $PG_PASS
#Cambiando según 1000 ,10000 y 100000 usuarios

#Guardar en MongoDB
#Definir MONGO_URI="mongodb://localhost:27017/"
#python cargar_bbdd.py --db-type mongo --in-usuarios ".\salidas\1000\usuarios.csv" --in-vehiculos ".\salidas\1000\vehiculos.csv" --mongo-uri $MONGO_URI --db-name practica_1000_csv --mongo-modo referenciado
#python cargar_bbdd.py --db-type mongo --in-usuarios ".\salidas\1000\usuarios.parquet" --in-vehiculos ".\salidas\1000\vehiculos.parquet" --mongo-uri $MONGO_URI --db-name practica_1000_parquet --mongo-modo referenciado
#python cargar_bbdd.py --db-type mongo --in-usuarios ".\salidas\1000\usuarios.jsonl" --in-vehiculos ".\salidas\1000\vehiculos.jsonl" --mongo-uri $MONGO_URI --db-name practica_1000_jsonl --mongo-modo referenciado
#python cargar_bbdd.py --db-type mongo --in-anidado ".\salidas\1000\datos_anidados.jsonl" --mongo-uri $MONGO_URI --db-name practica_1000_json_anidado
#python cargar_bbdd.py --db-type mongo --in-anidado ".\salidas\1000\datos_anidados.avro" --mongo-uri $MONGO_URI --db-name practica_1000_avro_anidado
#Cambiando según 1000 ,10000 y 100000 usuarios


import argparse
import csv
import json
import sqlite3
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
import pymongo


import pandas as pd
import fastavro



TAM_LOTE = 5000

COLS_USUARIO = [
    "dni", "nombre", "email", "telefono_movil", "telefono_fijo",
    "direccion", "ciudad", "codigo_postal", "provincia"
]

COLS_VEHICULO = [
    "matricula", "dni_propietario", "bastidor", "anio",
    "fabricante", "modelo", "categoria"
]


def cargar_registros(ruta: Path) -> list[dict]:
    """Carga registros desde .json, .jsonl, .csv, .parquet o .avro a una lista de diccionarios."""
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontro el archivo: {ruta}")

    ext = ruta.suffix.lower()

    if ext in [".json", ".jsonl"]:
        with open(ruta, "r", encoding="utf-8") as f:
            texto = f.read()
        if texto.lstrip().startswith("["):
            return json.loads(texto)
        return [json.loads(linea) for linea in texto.splitlines() if linea.strip()]

    elif ext == ".csv":
        registros = []
        with open(ruta, "r", encoding="utf-8") as f:
            lector = csv.DictReader(f)
            for fila in lector:
                # Convertir anio a int si existe y es digito para consistencia con DBs
                if "anio" in fila and fila["anio"]:
                    try:
                        fila["anio"] = int(fila["anio"])
                    except ValueError:
                        pass
                registros.append(dict(fila))
        return registros

    elif ext == ".parquet":
        if pd is None:
            raise ImportError("Para leer archivos .parquet necesitas instalar pandas y pyarrow: pip install pandas pyarrow")
        df = pd.read_parquet(ruta)
        # Reemplazar NaN por None para compatibilidad SQL / Mongo
        return df.where(pd.notnull(df), None).to_dict(orient="records")

    elif ext == ".avro":
        if fastavro is None:
            raise ImportError("Para leer archivos .avro necesitas instalar fastavro: pip install fastavro")
        registros = []
        with open(ruta, "rb") as f:
            lector_avro = fastavro.reader(f)
            for registro in lector_avro:
                registros.append(registro)
        return registros

    else:
        raise ValueError(f"Formato de archivo no soportado ({ext}). Formatos validos: .json, .jsonl, .csv, .parquet, .avro")


def trozear_listas(registros: list, tamano: int = TAM_LOTE):
    """Divide los registros en lotes mas pequenos."""
    for i in range(0, len(registros), tamano):
        yield registros[i:i + tamano]


def dict_to_tuple(registros: list[dict], columnas: list[str]) -> list[tuple]:
    """Convierte una lista de diccionarios a una lista de tuplas en el orden de columnas."""
    return [tuple(r.get(c) for c in columnas) for r in registros]


# SQLite
def guardar_en_sqlite(usuarios: list[dict], vehiculos: list[dict], db_path: Path):
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("DROP TABLE IF EXISTS vehiculos")
        con.execute("DROP TABLE IF EXISTS usuarios")
        con.execute("""
            CREATE TABLE usuarios (
                dni TEXT PRIMARY KEY, 
                nombre TEXT NOT NULL, 
                email TEXT,
                telefono_movil TEXT, 
                telefono_fijo TEXT, 
                direccion TEXT,
                ciudad TEXT, 
                codigo_postal TEXT, 
                provincia TEXT
            )
        """)
        con.execute("""
            CREATE TABLE vehiculos (
                matricula TEXT PRIMARY KEY,
                dni_propietario TEXT NOT NULL,
                bastidor TEXT NOT NULL UNIQUE,
                anio INTEGER NOT NULL, 
                fabricante TEXT, 
                modelo TEXT,
                categoria TEXT,
                FOREIGN KEY(dni_propietario) REFERENCES usuarios(dni)
            )
        """)
        con.execute("CREATE INDEX idx_vehiculos_dni ON vehiculos(dni_propietario)")

        tabla_usuarios = (f"INSERT OR IGNORE INTO usuarios ({', '.join(COLS_USUARIO)}) "
                  f"VALUES ({', '.join('?' * len(COLS_USUARIO))})")
        tabla_vehiculos = (f"INSERT OR IGNORE INTO vehiculos ({', '.join(COLS_VEHICULO)}) "
                   f"VALUES ({', '.join('?' * len(COLS_VEHICULO))})")

        with con:
            for lote in trozear_listas(usuarios):
                con.executemany(tabla_usuarios, dict_to_tuple(lote, COLS_USUARIO))
            for lote in trozear_listas(vehiculos):
                con.executemany(tabla_vehiculos, dict_to_tuple(lote, COLS_VEHICULO))
    finally:
        con.close()
    print(f"[SQLite] Datos guardados con exito en {db_path}")


# PostgreSQL
def guardar_en_postgres(usuarios: list[dict], vehiculos: list[dict], params: dict):
    con = psycopg2.connect(**params)
    try:
        with con, con.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS vehiculos CASCADE")
            cur.execute("DROP TABLE IF EXISTS usuarios CASCADE")
            cur.execute("""
                CREATE TABLE usuarios (
                    dni VARCHAR(20) PRIMARY KEY, 
                    nombre VARCHAR(255) NOT NULL, 
                    email VARCHAR(255), 
                    telefono_movil VARCHAR(20), 
                    telefono_fijo VARCHAR(20), 
                    direccion TEXT, 
                    ciudad VARCHAR(100), 
                    codigo_postal VARCHAR(10), 
                    provincia VARCHAR(100)
                )
            """)
            cur.execute("""
                CREATE TABLE vehiculos (
                    matricula VARCHAR(20) PRIMARY KEY,
                    dni_propietario VARCHAR(20) NOT NULL,
                    bastidor VARCHAR(50) NOT NULL UNIQUE,
                    anio INT NOT NULL, 
                    fabricante VARCHAR(100), 
                    modelo VARCHAR(100), 
                    categoria VARCHAR(50),
                    CONSTRAINT fk_usuario FOREIGN KEY(dni_propietario)
                        REFERENCES usuarios(dni)
                )
            """)
            cur.execute("CREATE INDEX idx_vehiculos_dni ON vehiculos(dni_propietario)")

            tabla_usuarios = f"INSERT INTO usuarios ({', '.join(COLS_USUARIO)}) VALUES %s ON CONFLICT (dni) DO NOTHING"
            tabla_vehiculos = f"INSERT INTO vehiculos ({', '.join(COLS_VEHICULO)}) VALUES %s ON CONFLICT (matricula) DO NOTHING"

            for lote in trozear_listas(usuarios):
                execute_values(cur, tabla_usuarios, dict_to_tuple(lote, COLS_USUARIO))
            for lote in trozear_listas(vehiculos):
                execute_values(cur, tabla_vehiculos, dict_to_tuple(lote, COLS_VEHICULO))
    finally:
        con.close()
    print(f"[PostgreSQL] Datos guardados con exito en '{params['dbname']}'")


# MongoDB
def guardar_en_mongo(
    usuarios: list[dict],
    vehiculos: list[dict] | None,
    uri: str,
    dbname: str,
    modo: str,
    es_anidado_directo: bool = False
):
    client = pymongo.MongoClient(uri)

    try:
        db = client[dbname]

        # Limpiamos las colecciones antes de insertar
        db.drop_collection("usuarios")

        if not es_anidado_directo:
            db.drop_collection("vehiculos")

       
        # Caso  fichero ya anidado
        
        if es_anidado_directo:

            # Eliminar usuarios duplicados por DNI
            usuarios_unicos = {}
            for usuario in usuarios:
                usuarios_unicos[usuario["dni"]] = usuario

            usuarios = list(usuarios_unicos.values())

            # Crear índices antes de insertar
            db.usuarios.create_index("dni", unique=True)
            db.usuarios.create_index("vehiculos.matricula")

            for lote in trozear_listas(usuarios):
                db.usuarios.insert_many(
                    [{**i} for i in lote],
                    ordered=False
                )

        
        # Caso  modo anidado a partir de usuarios + vehiculos
        
        elif modo == "anidado":

            # Eliminar usuarios duplicados por DNI
            usuarios_unicos = {}
            for usuario in usuarios:
                usuarios_unicos[usuario["dni"]] = usuario

            usuarios = list(usuarios_unicos.values())

            # Eliminar vehículos duplicados por matrícula
            vehiculos_unicos = {}
            for vehiculo in vehiculos:
                vehiculos_unicos[vehiculo["matricula"]] = vehiculo

            vehiculos = list(vehiculos_unicos.values())

            # Agrupar vehículos por DNI
            por_dni = {}

            for vehiculo in vehiculos:
                vehiculo_sin_dni = {
                    k: val
                    for k, val in vehiculo.items()
                    if k != "dni_propietario"
                }

                por_dni.setdefault(
                    vehiculo["dni_propietario"],
                    []
                ).append(vehiculo_sin_dni)

            # Crear índices antes de insertar
            db.usuarios.create_index("dni", unique=True)
            db.usuarios.create_index("vehiculos.matricula")

            for lote in trozear_listas(usuarios):
                docs = [
                    {
                        **i,
                        "vehiculos": por_dni.get(i["dni"], [])
                    }
                    for i in lote
                ]

                db.usuarios.insert_many(
                    docs,
                    ordered=False
                )

        
        # Caso  modo referenciado
       
        else:

            # Eliminar usuarios duplicados por DNI
            usuarios_unicos = {}
            for usuario in usuarios:
                usuarios_unicos[usuario["dni"]] = usuario

            usuarios = list(usuarios_unicos.values())

            # Eliminar vehículos duplicados por matrícula
            vehiculos_unicos = {}
            for vehiculo in vehiculos:
                vehiculos_unicos[vehiculo["matricula"]] = vehiculo

            vehiculos = list(vehiculos_unicos.values())

            # Crear índices ANTES de insertar
            db.usuarios.create_index(
                "dni",
                unique=True
            )

            db.vehiculos.create_index(
                "matricula",
                unique=True
            )

            db.vehiculos.create_index(
                "dni_propietario"
            )

            # Insertar usuarios
            for lote in trozear_listas(usuarios):
                db.usuarios.insert_many(
                    [{**i} for i in lote],
                    ordered=False
                )

            # Insertar vehículos
            for lote in trozear_listas(vehiculos):
                db.vehiculos.insert_many(
                    [{**j} for j in lote],
                    ordered=False
                )

    finally:
        client.close()

    print(
        f"[MongoDB] Datos guardados con exito en "
        f"'{dbname}', modo {modo}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Almacena datos generados en SGBD (Multi-formato).")
    parser.add_argument("--db-type", type=str, required=True,
                        choices=["sqlite", "postgres", "mongo"],
                        help="Base de datos a utilizar.")

    # Archivos planos / separados (JSON, JSONL, CSV, Parquet, Avro)
    parser.add_argument("--in-usuarios", type=Path, default=None,
                        help="Ruta a usuarios (csv, parquet, avro, jsonl)")
    parser.add_argument("--in-vehiculos", type=Path, default=None,
                        help="Ruta a vehiculos (csv, parquet, avro, jsonl)")

    # Archivo anidado directo (JSONL o Avro con vehiculos dentro de usuarios)
    parser.add_argument("--in-anidado", type=Path, default=None,
                        help="Ruta al fichero anidado directo (solo para MongoDB)")

    # SQLite
    parser.add_argument("--sqlite-path", type=Path, default=Path("datosFaker.db"))

    # PostgreSQL y MongoDB
    parser.add_argument("--db-host", type=str, default="localhost")
    parser.add_argument("--db-port", type=int, default=5432)
    parser.add_argument("--db-name", type=str, default="datosFaker_parquet1")
    parser.add_argument("--db-user", type=str, default="postgres")
    parser.add_argument("--db-pass", type=str, default="postgres")
    parser.add_argument("--mongo-uri", type=str, default="mongodb://localhost:27017/")
    parser.add_argument("--mongo-modo", choices=["anidado", "referenciado"],
                        default="referenciado")

    args = parser.parse_args(argv)

    # Validacion de argumentos
    if args.in_anidado:
        if args.db_type != "mongo":
            raise ValueError("El archivo anidado directo solo se puede cargar en MongoDB (--db-type mongo).")
        print(f"Cargando archivo anidado desde {args.in_anidado}...")
        usuarios_anidados = cargar_registros(args.in_anidado)
        print(f"  {len(usuarios_anidados)} usuarios con vehiculos anidados cargados.")

        t0 = time.perf_counter()
        guardar_en_mongo(usuarios_anidados, None, args.mongo_uri, args.db_name,
                         modo="anidado", es_anidado_directo=True)
        print(f"Tiempo de insercion: {time.perf_counter() - t0:.2f} s")
        return

    # Si no es anidado directo, necesitamos los dos ficheros planos
    if not args.in_usuarios or not args.in_vehiculos:
        # Valores por defecto si no se indican
        in_usuarios = args.in_usuarios or Path("usuarios.jsonl")
        in_vehiculos = args.in_vehiculos or Path("vehiculos.jsonl")
    else:
        in_usuarios = args.in_usuarios
        in_vehiculos = args.in_vehiculos

    print(f"Cargando datos desde {in_usuarios} y {in_vehiculos}...")
    usuarios = cargar_registros(in_usuarios)
    vehiculos = cargar_registros(in_vehiculos)
    print(f"  {len(usuarios)} usuarios, {len(vehiculos)} vehiculos leidos.")

    t0 = time.perf_counter()
    if args.db_type == "sqlite":
        guardar_en_sqlite(usuarios, vehiculos, args.sqlite_path)
    elif args.db_type == "postgres":
        pg_params = {
            "host": args.db_host, "port": args.db_port, "dbname": args.db_name,
            "user": args.db_user, "password": args.db_pass,
        }
        guardar_en_postgres(usuarios, vehiculos, pg_params)
    elif args.db_type == "mongo":
        guardar_en_mongo(usuarios, vehiculos, args.mongo_uri, args.db_name,
                         args.mongo_modo, es_anidado_directo=False)
    print(f"Tiempo de insercion: {time.perf_counter() - t0:.2f} s")


if __name__ == "__main__":
    main()