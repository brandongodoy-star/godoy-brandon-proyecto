"""Reglas de los créditos (la "fama") de los mecánicos.

Recepción califica cada trabajo al entregarlo. La calificación suma o resta créditos,
y los autos más valiosos valen más. Con más créditos el mecánico sube de nivel y
puede recibir autos de categorías más altas.
"""

CATEGORIAS = ("estandar", "premium", "lujo")
NOMBRE_CATEGORIA = {"estandar": "Estándar", "premium": "Premium", "lujo": "Lujo"}

# (nombre del nivel, créditos mínimos, categoría más alta que puede trabajar)
NIVELES = (
    ("Aprendiz", 0, "estandar"),
    ("Técnico", 100, "premium"),
    ("Maestro", 250, "lujo"),
)

PUNTOS_CALIFICACION = {"excelente": 20, "bien": 10, "con problemas": -10, "rehacer": -25}
MULTIPLICADOR_CATEGORIA = {"estandar": 1, "premium": 1.5, "lujo": 2}


def nivel_de(creditos: int) -> dict:
    """Nivel que corresponde a esos créditos, las categorías que permite y el siguiente nivel."""
    posicion = max(i for i, (_, minimo, _) in enumerate(NIVELES) if creditos >= minimo)
    nombre, minimo, categoria_maxima = NIVELES[posicion]
    siguiente = NIVELES[posicion + 1] if posicion + 1 < len(NIVELES) else None
    return {
        "nombre": nombre,
        "minimo": minimo,
        "categorias": list(CATEGORIAS[: CATEGORIAS.index(categoria_maxima) + 1]),
        "siguiente": {"nombre": siguiente[0], "minimo": siguiente[1]} if siguiente else None,
    }


def puede_trabajar(creditos: int, categoria: str) -> bool:
    return categoria in nivel_de(creditos)["categorias"]


def puntos_por(calificacion: str, categoria: str) -> int:
    """Créditos que gana (o pierde, si es negativo) un trabajo según su resultado y el auto."""
    return int(PUNTOS_CALIFICACION[calificacion] * MULTIPLICADOR_CATEGORIA[categoria])
