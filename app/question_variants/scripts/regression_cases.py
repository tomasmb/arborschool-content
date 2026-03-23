"""Curated deterministic regression cases for the hard-variants pipeline.

These cases are derived from official source QTI so they remain stable even if
generated benchmark artifacts are cleaned from the repository.
"""

from __future__ import annotations


STRUCTURAL_REGRESSION_CASES = [
    {
        "name": "Q28 approved direct proportion preserves setup",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q28",
        "replacements": [
            ("600 ml de suero", "450 ml de suero"),
            ("<mn>1200</mn><mfrac><mtext>ml</mtext><mtext>h</mtext></mfrac>", "<mn>900</mn><mfrac><mtext>ml</mtext><mtext>h</mtext></mfrac>"),
        ],
        "expected_ok": True,
    },
    {
        "name": "Q55 approved representation stays primary",
        "test_id": "seleccion-regular-2026",
        "question_id": "Q55",
        "replacements": [
            (
                "Una persona está jugando un nuevo juego en línea en el cual se pueden escoger distintos personajes. Cada personaje tiene cinco habilidades, con un puntaje de 0 a 100 en cada habilidad.",
                "En un videojuego de estrategia se puede elegir entre varios avatares. Cada avatar tiene cinco atributos calificados entre 0 y 100.",
            ),
            (
                "En el siguiente diagrama se representan las habilidades de uno de los personajes.",
                "En el siguiente diagrama se muestra el perfil de atributos de uno de esos avatares.",
            ),
            ("¿Cuál es la habilidad más débil de este personaje?", "¿Qué atributo presenta el menor puntaje en este avatar?"),
        ],
        "expected_ok": True,
    },
    {
        "name": "Q11 rejected affine substitution drift",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q11",
        "replacements": [
            (
                "<mn>160&#160;934</mn>\n        <mo>&#183;</mo>\n        <mi>x</mi>",
                "<mn>160&#160;934</mn>\n        <mo>&#183;</mo>\n        <mi>x</mi>\n        <mo>+</mo>\n        <mn>1000</mn>",
            ),
        ],
        "expected_ok": False,
        "reason_contains": "forma de tarea cambió",
    },
    {
        "name": "Q24 rejected shifted trinomial form",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q24",
        "replacements": [
            (
                "<p>¿Cuál de las siguientes expresiones es igual a <math xmlns=\"http://www.w3.org/1998/Math/MathML\"><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><mn>5</mn><mi>x</mi><mo>-</mo><mn>6</mn></math>?</p>",
                "<p>¿Cuál de las siguientes expresiones es igual a (x+2)^2 - 10?</p>",
            ),
        ],
        "expected_ok": False,
        "reason_contains": "formas desplazadas",
    },
    {
        "name": "Q60 rejected statistic target drift",
        "test_id": "Prueba-invierno-2025",
        "question_id": "Q60",
        "replacements": [
            (
                "En un grupo de datos, la desviación de un dato se calcula como <math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>x</mi><mo>-</mo><mi>p</mi></math>, tal que <math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>x</mi></math> es el dato y <math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>p</mi></math> es el promedio de los datos del grupo.",
                "En este grupo se trabajará directamente con los datos originales, sin calcular transformaciones previas.",
            ),
            (
                "Si se calcula la desviación a cada uno de estos cinco datos, ¿cuál sería su mediana?",
                "Considerando los datos originales, ¿cuál sería su mediana?",
            ),
        ],
        "expected_ok": False,
        "reason_contains": "dominio estadístico objetivo",
    },
]
