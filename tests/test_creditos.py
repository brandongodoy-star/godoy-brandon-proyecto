import pytest

from creditos import nivel_de, puede_trabajar, puntos_por


@pytest.mark.parametrize(
    "creditos, nivel, categorias",
    [
        (0, "Aprendiz", ["estandar"]),
        (99, "Aprendiz", ["estandar"]),
        (100, "Técnico", ["estandar", "premium"]),
        (249, "Técnico", ["estandar", "premium"]),
        (250, "Maestro", ["estandar", "premium", "lujo"]),
        (5000, "Maestro", ["estandar", "premium", "lujo"]),
    ],
)
def test_nivel_segun_creditos(creditos, nivel, categorias):
    resultado = nivel_de(creditos)
    assert resultado["nombre"] == nivel
    assert resultado["categorias"] == categorias


def test_siguiente_nivel():
    assert nivel_de(0)["siguiente"] == {"nombre": "Técnico", "minimo": 100}
    assert nivel_de(150)["siguiente"] == {"nombre": "Maestro", "minimo": 250}
    assert nivel_de(300)["siguiente"] is None


def test_mas_creditos_dan_acceso_a_mejores_autos():
    assert puede_trabajar(0, "estandar")
    assert not puede_trabajar(99, "premium")
    assert puede_trabajar(100, "premium")
    assert not puede_trabajar(249, "lujo")
    assert puede_trabajar(250, "lujo")


@pytest.mark.parametrize(
    "calificacion, categoria, puntos",
    [
        ("excelente", "estandar", 20),
        ("bien", "estandar", 10),
        ("con problemas", "estandar", -10),
        ("rehacer", "estandar", -25),
        ("excelente", "premium", 30),
        ("excelente", "lujo", 40),
        ("rehacer", "lujo", -50),
    ],
)
def test_puntos_segun_resultado_y_auto(calificacion, categoria, puntos):
    assert puntos_por(calificacion, categoria) == puntos
