from fastapi import APIRouter, FastAPI, status
from fastapi.responses import Response

from src.exceptions.handler import add_exception_handler
from src.routers.bus import router as bus_api
from src.routers.metro import router as metro_api

app = FastAPI(
    title="MovGR",
    description=("API para información de transportes urbanos de Granada"),
    version="0.1.0",
    contact={
        "name": "Miguel Ángel Fernández Gutiérrez",
        "url": "https://mianfg.me",
        "email": "hello@mianfg.me",
    },
)


add_exception_handler(app)


@app.get("/")
async def health_check() -> Response:
    return Response(status_code=status.HTTP_200_OK)


router = APIRouter()

router.include_router(bus_api, prefix="/bus", tags=["bus"])
router.include_router(metro_api, prefix="/metro", tags=["metro"])

app.include_router(router)

try:
    from mangum import Mangum

    handler = Mangum(
        app,
        api_gateway_base_path=None,
        lifespan="off",
    )
except ImportError:
    handler = None


def run() -> None:
    import uvicorn

    uvicorn.run("src.app:app", host="localhost", port=8080, reload=True, workers=3)


if __name__ == "__main__":
    run()
