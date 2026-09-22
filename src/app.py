import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import APIRouter, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from src.exceptions.handler import add_exception_handler
from src.routers.bus import router as bus_api
from src.routers.live import router as live_api
from src.routers.metro import router as metro_api
from src.services.live_activity import run_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(run_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task


app = FastAPI(
    title="MovGR",
    description=("API para información de transportes urbanos de Granada"),
    version="0.1.1",
    contact={
        "name": "Miguel Ángel Fernández Gutiérrez",
        "url": "https://mianfg.me",
        "email": "hello@mianfg.me",
    },
    lifespan=lifespan,
)

if cors_origins := os.getenv("CORS_ORIGINS"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


add_exception_handler(app)


@app.get("/")
async def health_check() -> Response:
    return Response(status_code=status.HTTP_200_OK)


router = APIRouter()

router.include_router(bus_api, prefix="/bus", tags=["bus"])
router.include_router(metro_api, prefix="/metro", tags=["metro"])
router.include_router(live_api, prefix="/live", tags=["live"])

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

    uvicorn.run("src.app:app", host="localhost", port=8080, reload=True, workers=1)


if __name__ == "__main__":
    run()
