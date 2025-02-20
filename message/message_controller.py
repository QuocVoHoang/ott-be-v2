from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from message.message_service import websocket_manager
from models.models import Message
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

message_router = APIRouter()

## test ting

@message_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
  await websocket.accept()
  while True:
    content = await websocket.receive_json()
    print('content', content)
    await websocket.send_json(content)