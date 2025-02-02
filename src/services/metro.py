"""Servicio para obtener información de paradas de metro."""

import re

import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from src.exceptions.exceptions import ParadaNotFoundError
from src.models.metro import (
    ParadaMetroModel,
    ProximoMetroModel,
)


def __similarity(str_1: str, str_2: str) -> float:
    ratio = float(fuzz.token_set_ratio(str_2, str_1) / 100)
    qratio = float(fuzz.QRatio(str_2, str_1) / 100)
    return max(ratio, qratio)


def __get_paradas() -> list[ParadaMetroModel]:
    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded",
        "dnt": "1",
        "origin": "https://metropolitanogranada.es",
        "priority": "u=0, i",
        "referer": "https://metropolitanogranada.es/horariosreal",
    }

    response = requests.post(
        "https://metropolitanogranada.es/MGhorariosreal.asp",
        headers=headers,
        timeout=5,
    )
    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, "html.parser")

    datos = [cell.getText().strip() for cell in soup.find_all("td")]
    paradas = [datos[i : i + 5] for i in range(0, len(datos), 5)]

    for parada in paradas:
        parada[1:] = ["".join(re.findall(r"\d+", col)) for col in parada[1:]]

    return {
        parada[0]: ParadaMetroModel(
            nombre=parada[0],
            proximos=sorted(
                [
                    ProximoMetroModel(
                        direccion="Armilla" if i >= 2 else "Albolote",  # noqa: PLR2004
                        minutos=int(col),
                    )
                    for i, col in enumerate(parada[1:])
                    if col
                ],
                key=lambda proximo: proximo.minutos,
            ),
        )
        for parada in paradas
    }


def __argmax(a: list) -> int:
    return max(range(len(a)), key=lambda x: a[x])


def get_parada_metro(
    nombre_parada: str,
    fuzzy: bool = True,
    fuzzy_threshold: float = 0.6,
) -> ParadaMetroModel:
    """Pedir información de parada de metro."""
    paradas = __get_paradas()

    if fuzzy:
        similarities = [__similarity(parada, nombre_parada) for parada in paradas]
        if max(similarities) < fuzzy_threshold:
            raise ParadaNotFoundError from None

        nombre_parada = list(paradas.keys())[__argmax(similarities)]

    if nombre_parada not in paradas:
        raise ParadaNotFoundError from None

    return paradas[nombre_parada]
