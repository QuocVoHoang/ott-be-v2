from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from models.models import Message, Conversation
from database import get_db
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from types import SimpleNamespace
from typing import List

message_router = APIRouter()

class ConnectionManager:
  def __init__(self):
    self.active_connections: List[WebSocket] = []

  async def connect(self, websocket: WebSocket):
    await websocket.accept()
    self.active_connections.append(websocket)

  def disconnect(self, websocket: WebSocket):
    self.active_connections.remove(websocket)

  async def broadcast(self, message: dict):
    for connection in self.active_connections:
      await connection.send_json(message)

manager = ConnectionManager()

@message_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
  await manager.connect(websocket)
  try:
    while True:
      receive_message = await websocket.receive_json()
      data = SimpleNamespace(**receive_message)
      
      new_message = Message(
        conversation_id=data.conversation_id,
        sender_id=data.sender_id,
        content=data.content,
        type=data.type,
        file_url=data.file_url
      )
      
      try:
        db.add(new_message)
        await db.commit()
        await db.refresh(new_message)
        print("Message saved successfully:", new_message)
      except Exception as e:
        print("Database error:", str(e))

      await manager.broadcast(receive_message)
  except Exception as e:
    print("WebSocket error:", str(e))
  finally:
    manager.disconnect(websocket)
    
@message_router.get('/{conversation_id}')
async def get_conversation_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(Message).where(Message.conversation_id == conversation_id))
  messages = result.scalars().all()
  return messages
  
  