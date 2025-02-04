import csv
import os
import re

import requests
from bs4 import BeautifulSoup

from src.exceptions.exceptions import ParadaNotFoundError
from src.models.metro import (
    LlegadasMetro,
    ParadaMetro,
    ProximoMetro,
)


def get_paradas() -> list[ParadaMetro]:
    with open(os.path.join(os.path.dirname(__file__), "../data/metro/paradas.csv"), "r") as file:
        reader = csv.reader(file)
        next(reader)
        paradas = [ParadaMetro(linea=row[0], id=row[1], nombre=row[2]) for row in reader]
    return paradas


paradas = get_paradas()


def get_llegadas() -> list[LlegadasMetro]:
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
    paradas_soup = [datos[i : i + 5] for i in range(0, len(datos), 5)]

    for parada in paradas_soup:
        parada[1:] = ["".join(re.findall(r"\d+", col)) for col in parada[1:]]

    return [
        LlegadasMetro(
            parada=parada,
            proximos=sorted(
                [
                    ProximoMetro(
                        direccion="Armilla" if i >= 2 else "Albolote",  # noqa: PLR2004
                        minutos=int(col),
                    )
                    for i, col in enumerate(parada_soup[1:])
                    if col
                ],
                key=lambda proximo: proximo.minutos,
            ),
        )
        for parada_soup, parada in zip(paradas_soup, paradas)
    ]


def get_llegadas_parada(id_parada: str) -> ProximoMetro:
    proximos = get_llegadas()
    for proximo in proximos:
        if proximo.parada.id == id_parada:
            return proximo
    raise ParadaNotFoundError from None
