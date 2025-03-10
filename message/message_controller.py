from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from models.models import Message, Conversation
from database import get_db
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from types import SimpleNamespace
from typing import List
from utils.utils import get_vn_time
from urllib.parse import urlparse
from bucket.bucket_controller import s3_client, S3_BUCKET_NAME

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

      # Handle send message
      if data.action == "send":
        new_message = Message(
          conversation_id=data.conversation_id,
          sender_id=data.sender_id,
          content=data.content,
          type=data.type,
          file_url=data.file_url
        )
        
        try:
          db.add(new_message)
          
          stmt = select(Conversation).where(Conversation.id == data.conversation_id)
          result = await db.execute(stmt)
          conversation = result.scalar_one_or_none()
          if conversation:
            conversation.updated_at = await get_vn_time()
            db.add(conversation)
          
          await db.commit()
          await db.refresh(new_message)
          
          message_dict = {
            "action": "send",
            "id": new_message.id,
            "conversation_id": new_message.conversation_id,
            "sender_id": new_message.sender_id,
            "content": new_message.content,
            "type": new_message.type,
            "file_url": new_message.file_url
          }
          await manager.broadcast(message_dict)
        except Exception as e:
          print("Database error:", str(e))

      # handle delete message
      elif data.action == "delete":
          message_id = data.message_id
          try:
            stmt = select(Message).where(Message.id == message_id)
            result = await db.execute(stmt)
            message = result.scalar_one_or_none()
            if message:
              await db.delete(message)
              await db.commit()
              
              delete_dict = {
                "action": "delete",
                "message_id": message_id
              }
              await manager.broadcast(delete_dict)
          except Exception as e:
            print("Delete error:", str(e))

  except Exception as e:
    print("WebSocket error:", str(e))
  finally:
    manager.disconnect(websocket)
    
@message_router.get('/{conversation_id}')
async def get_conversation_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(Message).where(Message.conversation_id == conversation_id))
  messages = result.scalars().all()
  return messages

@message_router.delete("/{message_id}")
async def delete_conversation(message_id: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(Message).where(Message.id == message_id))
  message = result.scalars().first()
  
  if message is None:
    raise HTTPException(status_code=404, detail="Message not found")
  
  if message.file_url:
    parsed_url = urlparse(message.file_url)
    filename = parsed_url.path.lstrip("/")
    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=filename)
    
  await db.delete(message)
  await db.commit()
  return {"message": "Conversation deleted successfully"}
