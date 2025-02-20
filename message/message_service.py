# from fastapi import WebSocket, WebSocketDisconnect
# from datetime import datetime
# from typing import List, Optional, Dict
# from models.models import Message


# class WebSocketManager:
#   def __init__(self):
#     self.active_connections: Dict[str, List[WebSocket]] = {}

#   async def connect(self, websocket: WebSocket, user_id: str):
#     await websocket.accept()
#     if user_id not in self.active_connections:
#       self.active_connections[user_id] = []
#     self.active_connections[user_id].append(websocket)

#   def disconnect(self, websocket: WebSocket, user_id: str):
#     if user_id in self.active_connections:
#       self.active_connections[user_id].remove(websocket)
#       if not self.active_connections[user_id]:
#         del self.active_connections[user_id]

#   # async def broadcast(self, message_data: dict, conversation_id: str):
#   #   """Chỉ gửi tin nhắn cho những người tham gia trong cuộc hội thoại."""
#   #   try:
#   #     conversation = await conversation_collection.find_one({"_id": ObjectId(conversation_id)})
#   #   except InvalidId:
#   #     return
      
#   #   if not conversation:
#   #     return

#   #   participants = conversation["participants"]
#   #   to_remove = []
    
#   #   for field in ["created_at", "updated_at"]:
#   #     if field in message_data and isinstance(message_data[field], datetime):
#   #       message_data[field] = message_data[field].isoformat()

#   #   for user_id in participants:
#   #     if user_id in self.active_connections:
#   #       for connection in self.active_connections[user_id]:
#   #         try:
#   #           print("Sending message to:", user_id)
#   #           await connection.send_json(message_data)
#   #         except Exception as e:
#   #           print(f"Error sending message to {user_id}: {e}")
#   #           to_remove.append((user_id, connection))

#   #   for user_id, connection in to_remove:
#   #     self.disconnect(connection, user_id) 
            
# websocket_manager = WebSocketManager()

# def message_helper(message) -> dict:
#   return {
#     "id": str(message["_id"]),
#     "sender": message.get("sender"),
#     "content": message.get("content"),
#     "timestamp": message.get("timestamp"),
#   }


