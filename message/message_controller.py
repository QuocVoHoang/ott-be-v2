from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from models.models import Message, Conversation
from database import get_db
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from types import SimpleNamespace
from typing import List, Dict
from utils.utils import get_vn_time
from urllib.parse import urlparse
from bucket.bucket_controller import s3_client, S3_BUCKET_NAME

message_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Từ điển để lưu trữ kết nối theo conversation_id
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        # Khởi tạo danh sách cho conversation_id nếu chưa tồn tại
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

    def disconnect(self, websocket: WebSocket, conversation_id: str):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
            # Dọn dẹp danh sách cuộc trò chuyện trống
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    async def broadcast(self, message: dict, conversation_id: str):
        # Chỉ phát tin nhắn đến các client trong cuộc trò chuyện được chỉ định
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@message_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str, db: AsyncSession = Depends(get_db)):
    print(f"Nhận yêu cầu WebSocket cho conversation_id: {conversation_id}")
    # Kết nối WebSocket với conversation_id được chỉ định
    await manager.connect(websocket, conversation_id)
    try:
        while True:
            receive_message = await websocket.receive_json()
            print(f"Nhận tin nhắn: {receive_message}")
            data = SimpleNamespace(**receive_message)

            # Xử lý gửi tin nhắn
            if data.action == "send":
                # Xác minh rằng tin nhắn thuộc về cuộc trò chuyện đúng
                if str(data.conversation_id) != conversation_id:
                    continue  # Bỏ qua tin nhắn của các cuộc trò chuyện khác

                new_message = Message(
                    conversation_id=data.conversation_id,
                    sender_id=data.sender_id,
                    content=data.content,
                    type=data.type,
                    file_url=data.file_url
                )
                
                try:
                    db.add(new_message)
                    
                    # Cập nhật conversation
                    stmt = select(Conversation).where(Conversation.id == data.conversation_id)
                    result = await db.execute(stmt)
                    conversation = result.scalar_one_or_none()
                    if conversation:
                        conversation.updated_at = await get_vn_time()
                        conversation.last_message_id = new_message.id  # Cập nhật last_message_id
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
                    # Chỉ phát tin nhắn đến các client trong cuộc trò chuyện này
                    await manager.broadcast(message_dict, conversation_id)
                except Exception as e:
                    print("Lỗi cơ sở dữ liệu:", str(e))

            # Xử lý xóa tin nhắn
            elif data.action == "delete":
                message_id = data.message_id
                try:
                    stmt = select(Message).where(Message.id == message_id)
                    result = await db.execute(stmt)
                    message = result.scalar_one_or_none()
                    if message and str(message.conversation_id) == conversation_id:
                        await db.delete(message)
                        
                        # Cập nhật last_message_id
                        stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(1)
                        result = await db.execute(stmt)
                        last_message = result.scalar_one_or_none()
                        
                        stmt = select(Conversation).where(Conversation.id == conversation_id)
                        result = await db.execute(stmt)
                        conversation = result.scalar_one_or_none()
                        if conversation:
                            conversation.updated_at = await get_vn_time()
                            conversation.last_message_id = last_message.id if last_message else None
                            db.add(conversation)
                        
                        await db.commit()
                        
                        delete_dict = {
                            "action": "delete",
                            "message_id": message_id
                        }
                        # Chỉ phát thông báo xóa đến các client trong cuộc trò chuyện này
                        await manager.broadcast(delete_dict, conversation_id)
                except Exception as e:
                    print("Lỗi xóa:", str(e))

    except WebSocketDisconnect:
        print("WebSocket đã ngắt kết nối")
    except Exception as e:
        print("Lỗi WebSocket:", str(e))
    finally:
        manager.disconnect(websocket, conversation_id)

@message_router.get('/get-mess/{message_id}')
async def get_message_by_id(message_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalars().first()
    return message

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
    
    # Cập nhật last_message_id
    stmt = select(Message).where(Message.conversation_id == message.conversation_id).order_by(Message.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    last_message = result.scalar_one_or_none()
    
    stmt = select(Conversation).where(Conversation.id == message.conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    if conversation:
        conversation.updated_at = await get_vn_time()
        conversation.last_message_id = last_message.id if last_message else None  # Cập nhật last_message_id
        db.add(conversation)
    
    await db.delete(message)
    await db.commit()
    return {"message": "Message deleted successfully"}