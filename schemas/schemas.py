from pydantic import BaseModel

class FriendRequestSchema(BaseModel):
  receiver_id: str

class FriendshipActionSchema(BaseModel):
  requester_id: str