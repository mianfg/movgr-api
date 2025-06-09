import csv
import os

import requests
from bs4 import BeautifulSoup

from src.exceptions.exceptions import (
    LineaNotFoundError,
    ParadaNotFoundError,
    ParadaRequestError,
)
from src.models.bus import LineaBus, LlegadasBus, ParadaBus, ProximoBus


def get_paradas() -> dict[int, ParadaBus]:
    with open(os.path.join(os.path.dirname(__file__), "../data/bus/paradas.csv"), "r") as file:
        reader = csv.reader(file)
        next(reader)
        paradas = {int(row[0]): ParadaBus(id=row[0], nombre=row[1]) for row in reader}
    return paradas


def get_lineas() -> dict[str, LineaBus]:
    with open(os.path.join(os.path.dirname(__file__), "../data/bus/lineas.csv"), "r") as file:
        reader = csv.reader(file)
        next(reader)
        lineas = {row[0]: LineaBus(id=row[0], nombre=row[1]) for row in reader}
    return lineas


paradas = get_paradas()
lineas = get_lineas()


def get_parada(id_parada: int) -> ParadaBus:
    try:
        return paradas[id_parada]
    except KeyError:
        raise ParadaNotFoundError from None


def get_linea(id_linea: str) -> LineaBus:
    try:
        return lineas[id_linea]
    except KeyError:
        raise LineaNotFoundError from None


def __perform_request(num_parada: int) -> dict:
    headers = {
        "accept": "*/*",
        "origin": "https://www.transportesrober.com",
        "referer": "https://www.transportesrober.com/flota/paradas.php",
    }

    files = {
        "excel": (None, ""),
        "parada": (None, str(num_parada)),
    }

    response = requests.post(
        "https://www.transportesrober.com/flota/paradas.php",
        headers=headers,
        files=files,
        timeout=5,
    )

    if response.status_code != 200:  # noqa: PLR2004
        raise ParadaRequestError

    return response


def get_llegadas_parada(num_parada: int) -> LlegadasBus:
    parada = get_parada(num_parada)

    req = __perform_request(num_parada)
    soup = BeautifulSoup(req.text, "html.parser")

    message = soup.find("div", {"class": "message"})
    if message:
        message_text = message.getText().strip()
        if "no existe" in message_text:
            raise ParadaNotFoundError from None
        return LlegadasBus(parada=parada, proximos=[])

    proximos: list[ProximoBus] = []
    table = soup.find("div", {"class": "tf"})
    if table:
        rows = table.find_all("div", {"class": "tfr"})
        for row in rows:
            cols = row.find_all("div", {"class": "tfcc"})
            cols_s = row.find_all("div", {"class": "tfccs"})
            if len(cols) >= 3:  # noqa: PLR2004
                id_linea = cols[0].find("div", {"class": "form_lle"}).getText().strip()
                try:
                    linea = get_linea(id_linea)
                except LineaNotFoundError:
                    linea = LineaBus(id=id_linea)
                destino = cols_s[0].getText().strip()
                minutos_text = cols[1].getText().strip()
                minutos = int(minutos_text) if minutos_text.isdigit() else 0
                proximos.append(
                    ProximoBus(
                        linea=linea,
                        destino=destino,
                        minutos=minutos,
                    ),
                )

    return LlegadasBus(parada=parada, proximos=proximos)


def get_lineas() -> dict:  # WIP
    def __get_url(num_parada: int) -> str:
        return f"https://www.transportesrober.com:9012/flotaenmovimiento/Transportes/parada.aspx?idparada={num_parada}"

    lineas = {}

    for id_linea in range(10000):
        print(id_linea, end="\r")
        req = requests.get(__get_url(id_linea), timeout=5)

        if req.status_code != 200:  # noqa: PLR2004
            continue

        soup = BeautifulSoup(req.text, "html.parser")
        entradas = soup.find("td", {"class": "tablacabecera"}).getText()

        if entradas == "Error":
            continue

        nombre = entradas.split(" - ")[0]

        lineas[id_linea] = nombre

        if id_linea % 100 == 0:
            print("\n", lineas, "\n")

    print("\n")
    return lineas
