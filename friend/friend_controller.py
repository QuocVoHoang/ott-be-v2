from fastapi import APIRouter, Depends, HTTPException
from models.models import Friendship, User
from database import get_db
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy import delete, or_
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
      Friendship.requester_id == current_user.id,
      Friendship.receiver_id == payload.receiver_id
    )
  )
  existing = result.scalars().first()
  if existing:
    raise HTTPException(status_code=400, detail="Request existed!")

  new_request = Friendship(
    requester_id=current_user.id,
    receiver_id=payload.receiver_id,
    status="PENDING"
  )
  db.add(new_request)
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
  result = await db.execute(
    select(Friendship).where(Friendship.id == friendship_id)
  )
  friendship = result.scalars().first()

  if not friendship:
    raise HTTPException(status_code=404, detail="Không tìm thấy mối quan hệ")

  await db.delete(friendship)
  await db.commit()

  message = "Đã từ chối lời mời kết bạn" if friendship.status == "pending" else "Đã hủy kết bạn"
  return {"message": message}