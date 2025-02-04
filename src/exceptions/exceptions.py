class BusGranadaAPIError(Exception):
    pass


class ParadaNotFoundError(BusGranadaAPIError):
    pass


class LineaNotFoundError(BusGranadaAPIError):
    pass


class ParadaRequestError(BusGranadaAPIError):
    pass
