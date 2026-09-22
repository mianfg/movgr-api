from fastapi import APIRouter, Response, status

from src.models.live import LiveSubscribeRequest, LiveUnsubscribeRequest
from src.services.live_activity import subscribe, unsubscribe

router = APIRouter()


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def live_subscribe(body: LiveSubscribeRequest) -> Response:
    subscribe(body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def live_unsubscribe(body: LiveUnsubscribeRequest) -> Response:
    unsubscribe(body.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
