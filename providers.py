import csv
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any
 
from faker import Faker
from faker.providers import BaseProvider

VEHICLES_JSON_PATH = Path(r"C:\Users\Nikita\Desktop\Bases de datos\Prácticas\P1\vehicles.json")
CODIGOS_POSTALES_CSV_PATH = Path(r"C:\Users\Nikita\Desktop\Bases de datos\Prácticas\P1\codigos_postales.csv")



fake = Faker("es_ES")

CATEGORIAS = {
    "Urbano": "Urbano",
    "Sedan": "Sedán",
    "Berlina": "Berlina",
    "Coupe": "Cupé",
    "Descapotable": "Descapotable",
    "Deportivo": "Deportivo",
    "Todoterreno": "Todoterreno",
    "Monovolumen": "Monovolumen",
    "SUV": "SUV",
    "Furgoneta": "Furgoneta",
}

class DNIProvider(BaseProvider):
    __letters= 'TRWAGMYFPDXBNJZSQVHLCKE'# letras válidas del dígito de control
    def dni_number(self) -> int:
        return self.random_int(min=111111, max=99999999) # número de 8 dígitos
    
    def dni_control_letter(self, num):
        return self.__letters[num% 23] # la letra de control
    def dni(self) -> str:
        num= self.dni_number()
        control = self.dni_control_letter(num)
        return f'{num:08d}-{control}'

fake.add_provider(DNIProvider) # Añade el providera fake para que pueda usar sus métodos

class TelefonoMovilProvider(BaseProvider):
    """Genera un teléfono móvil español: 9 dígitos, empieza por 6 o 7."""
 
    def telefono_movil(self) -> str:
        primero = self.random_element(("6" , "7"))
        resto = "".join(str(self.random_int(min=0, max=9)) for _ in range(8))
        return f"+34{primero}{resto}"
 
 
class TelefonoFijoProvider(BaseProvider):
    """Genera un teléfono fijo español: 9 dígitos, empieza por 8 o 9."""
 
    def telefono_fijo(self) -> str:
        primero = self.random_element(("8" , "9"))
        resto = "".join(str(self.random_int(min=0, max=9)) for _ in range(8))
        return f"+34{primero}{resto}"
 
 
class EmailProvider(BaseProvider):
    """Genera un email con pinta real a partir del nombre de la persona."""
 
    _DOMINIOS = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.es"]
 
    def email_de(self, nombre_completo: str) -> str:
        partes = nombre_completo.lower().split()
        base = ".".join(partes[:2]) if len(partes) >= 2 else partes[0]
        base = "".join(ch for ch in base if ch.isalnum() or ch == ".")
        sufijo = self.random_int(min=0, max=999)
        dominio = self.random_element(self._DOMINIOS)
        return f"{base}{sufijo}@{dominio}"
 
 
class CPCiudadProvider(BaseProvider):
    """Código postal + ciudad coherentes entre sí (dataset INE), y
    provincia coherente con el código postal (1.1). Necesita cargar un
    fichero externo, así que tiene su propio __init__."""
 
    _PROVINCIAS_POR_CP = {
        "01": "Álava", "02": "Albacete", "03": "Alicante",
        "04": "Almería", "05": "Ávila", "06": "Badajoz",
        "07": "Baleares", "08": "Barcelona", "09": "Burgos",
        "10": "Cáceres", "11": "Cádiz", "12": "Castellón",
        "13": "Ciudad Real", "14": "Córdoba", "15": "La Coruña",
        "16": "Cuenca", "17": "Gerona", "18": "Granada", "19": "Guadalajara",
        "20": "Guipúzcoa", "21": "Huelva", "22": "Huesca", "23": "Jaén",
        "24": "León", "25": "Lérida", "26": "La Rioja", "27": "Lugo",
        "28": "Madrid", "29": "Málaga", "30": "Murcia", "31": "Navarra",
        "32": "Orense", "33": "Asturias", "34": "Palencia",
        "35": "Las Palmas", "36": "Pontevedra", "37": "Salamanca",
        "38": "Santa Cruz de Tenerife", "39": "Cantabria", "40": "Segovia",
        "41": "Sevilla", "42": "Soria", "43": "Tarragona", "44": "Teruel",
        "45": "Toledo", "46": "Valencia", "47": "Valladolid",
        "48": "Vizcaya", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta",
        "52": "Melilla",
    }
 
    def __init__(self, generator, cp_csv_path: Path):
        super().__init__(generator)
        # Cargamos el dataset UNA sola vez (no en cada llamada).
        self._cp_municipio: list[tuple[str, str]] = []
        with open(cp_csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cp = row["codigo_postal"]
                # Descartamos prefijos inválidos (00xxx: errores del
                # propio dataset origen, no corresponden a ninguna
                # provincia real).
                if cp[:2] in self._PROVINCIAS_POR_CP:
                    self._cp_municipio.append((cp, row["municipio_nombre"]))
 
    def cp_ciudad(self) -> tuple[str, str]:
        """(codigo_postal, ciudad) tomados de una combinación real del
        dataset INE: CP y ciudad coherentes entre sí por construcción."""
        return self.random_element(self._cp_municipio)
 
    def provincia(self, codigo_postal: str) -> str:
        """Provincia coherente con el código postal dado."""
        return self._PROVINCIAS_POR_CP[codigo_postal[:2]]


class DireccionProvider(BaseProvider):
      
    def direccion(self, ciudad: str, codigo_postal: str) -> str:
        calle = fake.address()
        return f"{calle}, {codigo_postal} {ciudad}"  

class PersonProvider(
    DNIProvider,
    TelefonoMovilProvider,
    TelefonoFijoProvider,
    EmailProvider,
    CPCiudadProvider,
    DireccionProvider,
):
    """Provider "compuesto": junta todas las piezas de persona de
    arriba en una sola clase, así que tiene disponibles TODOS sus
    métodos: dni(), telefono_movil(), telefono_fijo(), email_de(),
    cp_ciudad(), provincia() y direccion().
 
    (El nº de vehículos por persona, antes generado aquí con una
    Poisson truncada, se ha movido a generar_datos.py: la Poisson deja
    de ser responsabilidad de un Provider de Faker y pasa a ser un
    filtro del propio generador sobre el CSV de vehículos — ver
    `poisson_truncada()` en ese fichero.)
 
    Solo CPCiudadProvider necesita cargar un fichero en su __init__,
    así que el __init__ de la clase unión delega en el suyo (que a su
    vez llama a BaseProvider.__init__ mediante super()); el resto de
    piezas no necesitan inicialización propia."""
 
    def __init__(self, generator, cp_csv_path: Path):
        CPCiudadProvider.__init__(self, generator, cp_csv_path)

class MatriculaProvider(BaseProvider):
    """Matrícula española: histórica (<=1999) o actual (>=2000), 1.2.3."""
 
    _LETRAS_ACTUAL = "BCDFGHJKLMNPRSTVWXYZ"  # sin vocales, Ñ ni Q
 
    # Códigos de provincia de las matrículas históricas (formato
    # PROV-NNNN-LL, p.ej. M-1234-AB). Sistema distinto al de los CP.
    _CODIGOS_PROVINCIA_HISTORICOS = [
        "A", "AB", "AL", "AV", "B", "BA", "BI", "BU", "C", "CA", "CC", "CE",
        "CO", "CR", "CS", "CU", "GC", "GE", "GI", "GR", "GU", "H", "HU", "J",
        "L", "LE", "LO", "LU", "M", "MA", "ML", "MU", "NA", "O", "OR", "P",
        "PM", "PO", "S", "SA", "SE", "SG", "SO", "SS", "T", "TE", "TF", "TO",
        "V", "VA", "VI", "Z", "ZA",
    ]

    def matricula(self, year: int) -> str:
        if year <= 1999:
            provincia = self.random_element(self._CODIGOS_PROVINCIA_HISTORICOS)
            numero = self.random_int(min=0, max=9999)
            letras = "".join(
                self.random_elements(
                    elements=self._LETRAS_ACTUAL, length=2, unique=False
                )
            )
            return f"{provincia}-{numero:04d}-{letras}"
 
        numero = self.random_int(min=0, max=9999)
        letras = "".join(
            self.random_elements(
                elements=self._LETRAS_ACTUAL, length=3, unique=False
            )
        )
        return f"{numero:04d}-{letras}"

class BastidorProvider(BaseProvider):
    """Número de bastidor: 17 caracteres alfanuméricos, sin I/O/Q
    (como el VIN real, estándar ISO 3779)."""
 
    _CHARSET = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
 
    def bastidor(self) -> str:
        return "".join(
            self.random_elements(elements=self._CHARSET, length=17, unique=False)
        )

class CatalogoVehiculoProvider(BaseProvider):
    """Fabricante, modelo, categoría y periodo de producción, a partir
    del catálogo suministrado en vehicles.json (1.2.4). Necesita
    cargar ese fichero, así que tiene su propio __init__."""
 
    def __init__(self, generator, catalog_path: Path):
        super().__init__(generator)
        with open(catalog_path, encoding="utf-8") as f:
            catalog: dict[str, Any] = json.load(f)
 
        # Aplanamos el catálogo a una lista de tuplas
        # (fabricante, modelo, categoria, periodos_produccion).
        self._modelos: list[tuple[str, str, str, list[dict]]] = []
        for fabricante, modelos in catalog.items():
            for modelo, info in modelos.items():
                self._modelos.append(
                    (fabricante, modelo, info["category"], info["production"])
                )
 
    def vehicle_model(self) -> tuple[str, str, str, list[dict]]:
        """(fabricante, modelo, categoria, periodos_produccion) elegidos
        uniformemente del catálogo."""
        return self.random_element(self._modelos)
 
    def vehicle_year(self, periods: list[dict]) -> int:
        """Año válido: se elige uno de los periodos de producción del
        modelo (puede haber varias etapas) y se sortea un año dentro.
        `fin == 9999` indica que el modelo sigue en producción hoy."""
        CURRENT_YEAR = datetime.now().year
        periodo = self.random_element(periods)
        inicio = periodo["inicio"]
        fin = periodo["fin"]
        if fin == 9999:
            fin = CURRENT_YEAR
        fin = min(fin, CURRENT_YEAR)
        if fin < inicio:
            fin = inicio
        return self.random_int(min=inicio, max=fin)
 
 
 
class VehicleProvider(MatriculaProvider, BastidorProvider, CatalogoVehiculoProvider):
    """Provider compuesto: junta matrícula, bastidor y catálogo de
    vehículos en una sola clase, con todos sus métodos disponibles:
    matricula(), bastidor(), vehicle_model(), vehicle_year()."""
 
    def __init__(self, generator, catalog_path: Path):
        CatalogoVehiculoProvider.__init__(self, generator, catalog_path)
 
 
 
