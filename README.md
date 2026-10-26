# Generación y gestión de datos sintéticos con Python

## Descripción del proyecto

Este proyecto consiste en el desarrollo de un sistema de **generación, transformación y almacenamiento de datos sintéticos** utilizando Python. Su objetivo principal es crear conjuntos de datos realistas de usuarios y vehículos, garantizando la coherencia entre sus atributos y permitiendo trabajar con diferentes formatos de archivos y sistemas de bases de datos.

Para ello, desarrollamos un generador basado en la biblioteca **Faker**, incorporando proveedores personalizados capaces de crear información ficticia adaptada al contexto español. Entre los datos generados se encuentran nombres, DNI, números de teléfono, correos electrónicos, direcciones, códigos postales y provincias. También generamos vehículos con matrículas, números de bastidor, fabricantes, modelos, categorías y años de fabricación.

Uno de los aspectos más importantes fue garantizar la **integridad y consistencia de la información**. Por ejemplo, los códigos postales se corresponden con municipios y provincias reales, los vehículos tienen años de fabricación compatibles con sus modelos y cada vehículo está relacionado con un propietario.

## Desarrollo y funcionamiento

El sistema permite generar conjuntos de datos de diferentes tamaños, incluyendo escenarios de 1.000, 10.000 y 100.000 usuarios, para trabajar con distintos volúmenes de información.

Posteriormente, implementamos la exportación de los datos a cuatro formatos: **CSV, JSON/JSONL, Parquet y Avro**. Esto permite explorar distintas estructuras de almacenamiento, desde archivos de texto hasta formatos binarios utilizados en entornos de procesamiento de datos.

Además, desarrollamos un módulo para importar los archivos generados a tres sistemas de bases de datos:

- **SQLite:** almacenamiento relacional mediante tablas y claves foráneas.
- **PostgreSQL:** gestión de datos estructurados con integridad referencial.
- **MongoDB:** almacenamiento documental con estructuras referenciadas y anidadas.

La carga de información se realiza mediante procesamiento por lotes, facilitando la inserción de grandes cantidades de registros.

## Tecnologías y aprendizaje

Durante el desarrollo utilizamos Python, Faker, Pandas, PyArrow, Fastav
