from fastapi import APIRouter, Depends, HTTPException
from models.models import Friendship, User, Conversation, ConversationParticipant
from database import get_db
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy import delete, or_, and_, func
from schemas.schemas import FriendRequestSchema, FriendshipActionSchema
from user.user_controller import get_current_user

friend_router = APIRouter()

@friend_router.get("/friend-list")
async def get_friend_list(
  db: AsyncSession = Depends(get_db), 
  current_user: User = Depends(get_current_user)
):
  result = await db.execute(
    select(Friendship)
    .where(
      or_(
        Friendship.requester_id == current_user.id,
        Friendship.receiver_id == current_user.id
      )
    )
    .options(
      selectinload(Friendship.requester),
      selectinload(Friendship.receiver)
    )
  )
  friend_list = result.scalars().all()
  return friend_list


@friend_router.post("/request")
async def send_friend_request(
  payload: FriendRequestSchema, 
  db: AsyncSession = Depends(get_db), 
  current_user: User = Depends(get_current_user)
):
  result = await db.execute(
    select(Friendship).where(
      or_(
        and_(
          Friendship.requester_id == current_user.id,
          Friendship.receiver_id == payload.receiver_id
        ),
        and_(
          Friendship.requester_id == payload.receiver_id,
          Friendship.receiver_id == current_user.id
        )
      )
    )
  )
  
  existing = result.scalars().first()
  if existing:
    return HTTPException(status_code=400, detail="Request existed!")

  new_request = Friendship(
    requester_id=current_user.id,
    receiver_id=payload.receiver_id,
    status="PENDING"
  )
  db.add(new_request)
  await db.commit()
  
  result = await db.execute(select(User).where(User.id == payload.receiver_id))
  receiver_user = result.scalars().first()
  if not receiver_user:
    raise HTTPException(status_code=404, detail="Receiver not found")
  conversation_name = f"{receiver_user.username}"
  
  new_conversation = Conversation(
    name=conversation_name,
    type="private",
    avatar_url="",
    created_by=current_user.id
  )
  db.add(new_conversation)
  await db.commit()
  await db.refresh(new_conversation)
  
  participants = [
    ConversationParticipant(conversation_id=new_conversation.id, user_id=current_user.id),
    ConversationParticipant(conversation_id=new_conversation.id, user_id=payload.receiver_id)
  ]
  db.add_all(participants)
  await db.commit()
  
  return new_request


@friend_router.put("/accept/{friendship_id}")
async def accept_friend_request(
  friendship_id: str,
  db: AsyncSession = Depends(get_db),
  current_user: User = Depends(get_current_user)
):
  result = await db.execute(
    select(Friendship).where(Friendship.id == friendship_id)
  )
  friendship = result.scalars().first()

  if not friendship:
    raise HTTPException(status_code=404, detail="Không tìm thấy lời mời")

  friendship.status = "ACCEPTED"
  friendship.updated_at = datetime.utcnow()

  await db.commit()
  await db.refresh(friendship)

  return {"message": "Đã chấp nhận lời mời kết bạn"}


@friend_router.delete("/remove/{friendship_id}")
async def cancel_or_remove_friend(
  friendship_id: str,
  db: AsyncSession = Depends(get_db),
  current_user: User = Depends(get_current_user)
):
  # Tìm Friendship
  result = await db.execute(
    select(Friendship).where(Friendship.id == friendship_id)
  )
  friendship = result.scalars().first()

  if not friendship:
    raise HTTPException(status_code=404, detail="Không tìm thấy mối quan hệ")

  # Xác định hai user_id liên quan
  user1_id = friendship.requester_id
  user2_id = friendship.receiver_id

  # Tìm Conversation liên quan
  conversation_result = await db.execute(
    select(Conversation)
    .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
    .where(
      Conversation.type == "private",
      ConversationParticipant.user_id.in_([user1_id, user2_id])
    )
    .group_by(Conversation.id)
    .having(
      func.count(ConversationParticipant.user_id) == 2
    )
  )
  conversation = conversation_result.scalars().first()

  # Xóa Conversation và ConversationParticipant nếu tìm thấy
  if conversation:
    await db.execute(
      delete(ConversationParticipant).where(
        ConversationParticipant.conversation_id == conversation.id
      )
    )
    await db.execute(
      delete(Conversation).where(
        Conversation.id == conversation.id
      )
    )

  # Xóa Friendship
  await db.delete(friendship)
  await db.commit()

  message = "Đã từ chối lời mời kết bạn" if friendship.status == "PENDING" else "Đã hủy kết bạn"
  return {"message": message}