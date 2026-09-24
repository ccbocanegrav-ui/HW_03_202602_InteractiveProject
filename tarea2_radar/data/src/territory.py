"""
Normalización territorial — Tarea 2, Fase 2.

Objetivo
--------
Convertir los nombres de departamentos y provincias encontrados en los
archivos de OECE a uno de los 25 departamentos del Perú, incluyendo Callao.

Regla de normalización
----------------------
1. Se limpia el texto:
   - mayúsculas
   - espacios sobrantes
   - eliminación de tildes
   - normalización de caracteres especiales
2. Si el valor coincide directamente con un departamento, se devuelve
   ese departamento.
3. Si el valor coincide con una provincia conocida, se devuelve el
   departamento al que pertenece.
4. Si no se puede identificar, se devuelve None.

IMPORTANTE:
------------
La normalización NO elimina procesos. Los procesos que no puedan ser
ubicados permanecen en el dataset con departamento=None y se reportan
como advertencia en la Fase 2.
"""

from __future__ import annotations

import re
import unicodedata


# ============================================================
# 25 DEPARTAMENTOS DEL PERÚ
# ============================================================

DEPARTAMENTOS = [
    "AMAZONAS",
    "ANCASH",
    "APURIMAC",
    "AREQUIPA",
    "AYACUCHO",
    "CAJAMARCA",
    "CALLAO",
    "CUSCO",
    "HUANCAVELICA",
    "HUANUCO",
    "ICA",
    "JUNIN",
    "LA LIBERTAD",
    "LAMBAYEQUE",
    "LIMA",
    "LORETO",
    "MADRE DE DIOS",
    "MOQUEGUA",
    "PASCO",
    "PIURA",
    "PUNO",
    "SAN MARTIN",
    "TACNA",
    "TUMBES",
    "UCAYALI",
]


# ============================================================
# NORMALIZACIÓN DE TEXTO
# ============================================================

def normalize_text(value) -> str | None:
    """
    Normaliza texto para comparación.

    Ejemplos:
        "Cusco"       -> "CUSCO"
        "CUSCÓ"       -> "CUSCO"
        " Junín "     -> "JUNIN"
        "San Martín"  -> "SAN MARTIN"
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text or text.lower() in {
        "nan",
        "none",
        "null",
        "n/a",
        "na",
    }:
        return None

    # Mayúsculas
    text = text.upper()

    # Eliminar tildes y diacríticos
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    # Normalizar caracteres especiales
    text = text.replace("’", "'")
    text = text.replace("-", " ")

    # Quitar caracteres que no sean letras, números o espacios
    text = re.sub(r"[^A-Z0-9\s]", " ", text)

    # Espacios múltiples
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# PROVINCIAS → DEPARTAMENTOS
# ============================================================
#
# Las claves están normalizadas SIN tildes.
#
# Fuente declarada para el proyecto:
# listado oficial de provincias/departamentos del Perú,
# contrastado con la división político-administrativa vigente.
#
# La tabla permite resolver el problema del campo "region" de OECE,
# que puede contener provincia en lugar de departamento.
# ============================================================

PROVINCIA_A_DEPARTAMENTO = {

    # AMAZONAS
    "CHACHAPOYAS": "AMAZONAS",
    "BAGUA": "AMAZONAS",
    "BONGARA": "AMAZONAS",
    "CONDORCANQUI": "AMAZONAS",
    "LUYA": "AMAZONAS",
    "RODRIGUEZ DE MENDOZA": "AMAZONAS",
    "RODRIGUEZ DE MENDOZA": "AMAZONAS",
    "UTCUBAMBA": "AMAZONAS",

    # ANCASH
    "HUARAZ": "ANCASH",
    "AIJA": "ANCASH",
    "ANTONIO RAYMONDI": "ANCASH",
    "ASUNCION": "ANCASH",
    "BOLOGNESI": "ANCASH",
    "CARHUAZ": "ANCASH",
    "CARLOS FERMIN FITZCARRALD": "ANCASH",
    "CASMA": "ANCASH",
    "CORONGO": "ANCASH",
    "HUARI": "ANCASH",
    "HUARMEY": "ANCASH",
    "HUAYLAS": "ANCASH",
    "MARISCAL LUZURIAGA": "ANCASH",
    "OCROS": "ANCASH",
    "PALLASCA": "ANCASH",
    "POMABAMBA": "ANCASH",
    "RECUAY": "ANCASH",
    "SANTA": "ANCASH",
    "SIHUAS": "ANCASH",
    "YUNGAY": "ANCASH",

    # APURIMAC
    "ABANCAY": "APURIMAC",
    "ANDAHUAYLAS": "APURIMAC",
    "ANTABAMBA": "APURIMAC",
    "AYMARAES": "APURIMAC",
    "COTABAMBAS": "APURIMAC",
    "CHINCHEROS": "APURIMAC",
    "GRAU": "APURIMAC",

    # AREQUIPA
    "AREQUIPA": "AREQUIPA",
    "CAMANA": "AREQUIPA",
    "CARAVELI": "AREQUIPA",
    "CASTILLA": "AREQUIPA",
    "CAYLLOMA": "AREQUIPA",
    "CONDESUYOS": "AREQUIPA",
    "ISLAY": "AREQUIPA",
    "LA UNION": "AREQUIPA",

    # AYACUCHO
    "HUAMANGA": "AYACUCHO",
    "CANGALLO": "AYACUCHO",
    "HUANCA SANCOS": "AYACUCHO",
    "HUANTA": "AYACUCHO",
    "LA MAR": "AYACUCHO",
    "LUCANAS": "AYACUCHO",
    "PARINACOCHAS": "AYACUCHO",
    "PAUCAR DEL SARA SARA": "AYACUCHO",
    "SUCRE": "AYACUCHO",
    "VICTOR FAJARDO": "AYACUCHO",
    "VILCAS HUAMAN": "AYACUCHO",

    # CAJAMARCA
    "CAJAMARCA": "CAJAMARCA",
    "CAJABAMBA": "CAJAMARCA",
    "CELENDIN": "CAJAMARCA",
    "CHOTA": "CAJAMARCA",
    "CONTUMAZA": "CAJAMARCA",
    "CUTERVO": "CAJAMARCA",
    "HUALGAYOC": "CAJAMARCA",
    "JAEN": "CAJAMARCA",
    "SAN IGNACIO": "CAJAMARCA",
    "SAN MARCOS": "CAJAMARCA",
    "SAN MIGUEL": "CAJAMARCA",
    "SAN PABLO": "CAJAMARCA",
    "SANTA CRUZ": "CAJAMARCA",

    # CALLAO
    "CALLAO": "CALLAO",
    "PROVINCIA CONSTITUCIONAL DEL CALLAO": "CALLAO",

    # CUSCO
    "CUSCO": "CUSCO",
    "ACOMAYO": "CUSCO",
    "ANTA": "CUSCO",
    "CALCA": "CUSCO",
    "CANAS": "CUSCO",
    "CANCHIS": "CUSCO",
    "CHUMBIVILCAS": "CUSCO",
    "ESPINAR": "CUSCO",
    "LA CONVENCION": "CUSCO",
    "PARURO": "CUSCO",
    "PAUCARTAMBO": "CUSCO",
    "QUISPICANCHI": "CUSCO",
    "URUBAMBA": "CUSCO",

    # HUANCAVELICA
    "HUANCAVELICA": "HUANCAVELICA",
    "ACOBAMBA": "HUANCAVELICA",
    "ANGARAES": "HUANCAVELICA",
    "CASTROVIRREYNA": "HUANCAVELICA",
    "CHURCAMPA": "HUANCAVELICA",
    "HUAYTARA": "HUANCAVELICA",
    "TAYACAJA": "HUANCAVELICA",

    # HUANUCO
    "HUANUCO": "HUANUCO",
    "AMBO": "HUANUCO",
    "DOS DE MAYO": "HUANUCO",
    "HUACAYBAMBA": "HUANUCO",
    "HUAMALIES": "HUANUCO",
    "LEONCIO PRADO": "HUANUCO",
    "MARAÑON": "HUANUCO",
    "MARANON": "HUANUCO",
    "PACHITEA": "HUANUCO",
    "PUERTO INCA": "HUANUCO",
    "LAURICOCHA": "HUANUCO",
    "YAROWILCA": "HUANUCO",

    # ICA
    "ICA": "ICA",
    "CHINCHA": "ICA",
    "NASCA": "ICA",
    "PALPA": "ICA",
    "PISCO": "ICA",

    # JUNIN
    "HUANCAYO": "JUNIN",
    "CONCEPCION": "JUNIN",
    "CHANCHAMAYO": "JUNIN",
    "JAUJA": "JUNIN",
    "JUNIN": "JUNIN",
    "SATIPO": "JUNIN",
    "TARMA": "JUNIN",
    "YAULI": "JUNIN",
    "CHUPACA": "JUNIN",

    # LA LIBERTAD
    "TRUJILLO": "LA LIBERTAD",
    "ASCOPE": "LA LIBERTAD",
    "BOLIVAR": "LA LIBERTAD",
    "CHEPEN": "LA LIBERTAD",
    "JULCAN": "LA LIBERTAD",
    "OTUZCO": "LA LIBERTAD",
    "PACASMAYO": "LA LIBERTAD",
    "PATAZ": "LA LIBERTAD",
    "SANCHEZ CARRION": "LA LIBERTAD",
    "SANTIAGO DE CHUCO": "LA LIBERTAD",
    "GRAN CHIMU": "LA LIBERTAD",
    "VIRU": "LA LIBERTAD",

    # LAMBAYEQUE
    "CHICLAYO": "LAMBAYEQUE",
    "FERRENAFE": "LAMBAYEQUE",
    "LAMBAYEQUE": "LAMBAYEQUE",

    # LIMA
    "LIMA": "LIMA",
    "BARRANCA": "LIMA",
    "CAJATAMBO": "LIMA",
    "CANTA": "LIMA",
    "CAÑETE": "LIMA",
    "CANETE": "LIMA",
    "HUARAL": "LIMA",
    "HUAROCHIRI": "LIMA",
    "HUAURA": "LIMA",
    "OYON": "LIMA",
    "YAUYOS": "LIMA",

    # LORETO
    "MAYNAS": "LORETO",
    "ALTO AMAZONAS": "LORETO",
    "LORETO": "LORETO",
    "MARISCAL RAMON CASTILLA": "LORETO",
    "REQUENA": "LORETO",
    "UCAYALI": "LORETO",
    "DATEM DEL MARANON": "LORETO",
    "PUTUMAYO": "LORETO",

    # MADRE DE DIOS
    "TAMBOPATA": "MADRE DE DIOS",
    "MANU": "MADRE DE DIOS",
    "TAHUAMANU": "MADRE DE DIOS",

    # MOQUEGUA
    "MARISCAL NIETO": "MOQUEGUA",
    "GENERAL SANCHEZ CERRO": "MOQUEGUA",
    "ILO": "MOQUEGUA",

    # PASCO
    "PASCO": "PASCO",
    "DANIEL ALCIDES CARRION": "PASCO",
    "OXAPAMPA": "PASCO",

    # PIURA
    "PIURA": "PIURA",
    "AYABACA": "PIURA",
    "HUANCABAMBA": "PIURA",
    "MORROPON": "PIURA",
    "PAITA": "PIURA",
    "SULLANA": "PIURA",
    "TALARA": "PIURA",
    "SECHURA": "PIURA",

    # PUNO
    "PUNO": "PUNO",
    "AZANGARO": "PUNO",
    "CARABAYA": "PUNO",
    "CHUCUITO": "PUNO",
    "EL COLLAO": "PUNO",
    "HUANCANE": "PUNO",
    "LAMPA": "PUNO",
    "MELGAR": "PUNO",
    "MOHO": "PUNO",
    "SAN ANTONIO DE PUTINA": "PUNO",
    "SAN ROMAN": "PUNO",
    "SANDIA": "PUNO",
    "YUNGUYO": "PUNO",

    # SAN MARTIN
    "MOYOBAMBA": "SAN MARTIN",
    "BELLAVISTA": "SAN MARTIN",
    "EL DORADO": "SAN MARTIN",
    "HUALLAGA": "SAN MARTIN",
    "LAMAS": "SAN MARTIN",
    "MARISCAL CACERES": "SAN MARTIN",
    "PICOTA": "SAN MARTIN",
    "RIOJA": "SAN MARTIN",
    "SAN MARTIN": "SAN MARTIN",
    "TOCACHE": "SAN MARTIN",

    # TACNA
    "TACNA": "TACNA",
    "CANDARAVE": "TACNA",
    "JORGE BASADRE": "TACNA",
    "TARATA": "TACNA",

    # TUMBES
    "TUMBES": "TUMBES",
    "CONTRALMIRANTE VILLAR": "TUMBES",
    "ZARUMILLA": "TUMBES",

    # UCAYALI
    "CORONEL PORTILLO": "UCAYALI",
    "ATALAYA": "UCAYALI",
    "PADRE ABAD": "UCAYALI",
    "PURUS": "UCAYALI",
}


# Normalizamos también las claves de la tabla por seguridad.
PROVINCIA_A_DEPARTAMENTO = {
    normalize_text(provincia): departamento
    for provincia, departamento in PROVINCIA_A_DEPARTAMENTO.items()
}


# ============================================================
# ALIAS FRECUENTES
# ============================================================

ALIASES_DEPARTAMENTO = {
    "ANCASH": "ANCASH",
    "ANCAHS": "ANCASH",
    "APURIMAC": "APURIMAC",
    "AREQUIPA": "AREQUIPA",
    "AYACUCHO": "AYACUCHO",
    "CAJAMARCA": "CAJAMARCA",
    "CALLAO": "CALLAO",
    "CUSCO": "CUSCO",
    "CUZCO": "CUSCO",
    "HUANCAVELICA": "HUANCAVELICA",
    "HUANUCO": "HUANUCO",
    "ICA": "ICA",
    "JUNIN": "JUNIN",
    "LA LIBERTAD": "LA LIBERTAD",
    "LIBERTAD": "LA LIBERTAD",
    "LAMBAYEQUE": "LAMBAYEQUE",
    "LIMA": "LIMA",
    "LORETO": "LORETO",
    "MADRE DE DIOS": "MADRE DE DIOS",
    "MOQUEGUA": "MOQUEGUA",
    "PASCO": "PASCO",
    "PIURA": "PIURA",
    "PUNO": "PUNO",
    "SAN MARTIN": "SAN MARTIN",
    "SAN MARTÍN": "SAN MARTIN",
    "TACNA": "TACNA",
    "TUMBES": "TUMBES",
    "UCAYALI": "UCAYALI",
    "AMAZONAS": "AMAZONAS",
}


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def normalize_department(value) -> str | None:
    """
    Convierte un departamento o provincia a uno de los 25 departamentos.

    Ejemplos
    --------
    >>> normalize_department("Cusco")
    'CUSCO'

    >>> normalize_department("Cuzco")
    'CUSCO'

    >>> normalize_department("Canas")
    'CUSCO'

    >>> normalize_department("Junín")
    'JUNIN'

    >>> normalize_department("San Martín")
    'SAN MARTIN'

    >>> normalize_department(None)
    None
    """

    value = normalize_text(value)

    if value is None:
        return None

    # 1. Coincidencia directa con departamento
    if value in DEPARTAMENTOS:
        return value

    # 2. Alias
    if value in ALIASES_DEPARTAMENTO:
        return ALIASES_DEPARTAMENTO[value]

    # 3. Provincia → departamento
    if value in PROVINCIA_A_DEPARTAMENTO:
        return PROVINCIA_A_DEPARTAMENTO[value]

    # 4. No identificado
    return None


# ============================================================
# FUNCIONES AUXILIARES PARA VALIDACIÓN
# ============================================================

def is_valid_department(value) -> bool:
    """Indica si el valor corresponde a uno de los 25 departamentos."""

    normalized = normalize_department(value)

    return normalized in DEPARTAMENTOS


def all_departments() -> list[str]:
    """Devuelve la lista de los 25 departamentos."""

    return DEPARTAMENTOS.copy()


def territory_diagnostic(values) -> dict:
    """
    Diagnóstico rápido de una columna territorial.

    Devuelve cuántos valores:
      - son departamentos directos,
      - son provincias recuperables,
      - no pudieron identificarse.
    """

    total = 0
    identified = 0
    unidentified = 0
    normalized_values = {}

    for value in values:
        total += 1

        normalized = normalize_department(value)

        if normalized is None:
            unidentified += 1
        else:
            identified += 1

            if normalized not in normalized_values:
                normalized_values[normalized] = 0

            normalized_values[normalized] += 1

    return {
        "total": total,
        "identificados": identified,
        "sin_identificar": unidentified,
        "tasa_match": (
            identified / total
            if total > 0
            else 0
        ),
        "por_departamento": normalized_values,
    }


# ============================================================
# PRUEBA DIRECTA
# ============================================================

if __name__ == "__main__":

    ejemplos = [
        "Cusco",
        "Cuzco",
        "CANAS",
        "Junín",
        "JUNIN",
        "San Martín",
        "HUARAZ",
        "Arequipa",
        "Callao",
        "Provincia Constitucional del Callao",
        "valor desconocido",
        None,
    ]

    print("=" * 60)
    print("PRUEBA DE NORMALIZACIÓN TERRITORIAL")
    print("=" * 60)

    for valor in ejemplos:
        resultado = normalize_department(valor)

        print(
            f"{str(valor):40s} -> {resultado}"
        )

    print()
    print(
        f"Departamentos válidos: {len(DEPARTAMENTOS)}"
    )

    print()
    print("Departamentos:")
    for departamento in DEPARTAMENTOS:
        print(f"  - {departamento}")