from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import User, ConversationParticipant, Conversation
from sqlalchemy.future import select
from database import get_db
from interface.interface import (
  INewUserData, 
  IUpdateUserAvatarData, 
  IUpdateUserNameData, 
  ILoginUserData,
)
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()
import jwt

SECRET_KEY = "software_architecture"

user_router = APIRouter()

security = HTTPBearer()

@user_router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
  token = credentials.credentials
  try: 
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id: str = payload.get("sub")
    if user_id is None:
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: no user id", headers={"WWW-Authenticate": "Bearer"})
  except jwt.PyJWTError:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
  
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalars().first()
  
  if user is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
  return user

@user_router.get("/{user_id}")
async def get_user_by_id(user_id: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalars().all()
  return user



@user_router.get("/conversations/{user_id}")
async def get_user_conversations(user_id: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalars().first()
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  
  result = await db.execute(
    select(ConversationParticipant.conversation_id)
    .where(ConversationParticipant.user_id == user_id)
  )
  conversation_ids = [row[0] for row in result.fetchall()]

  if not conversation_ids:
    return {"message": "User is not in any conversation", "conversations": []}
  
  result = await db.execute(
    select(Conversation).where(Conversation.id.in_(conversation_ids))
  )
  conversations = result.scalars().all()

  return conversations


@user_router.post("/")
async def create_new_user(data: INewUserData, db: AsyncSession = Depends(get_db)):
  existing_user = await db.execute(select(User).where(User.email == data.email))
  if existing_user is None:
    raise HTTPException(status_code=404, detail="Email already registered!")

  new_user = User(
    username=data.username,
    email=data.email,
    password=data.password
  )
  new_user.set_password(new_user.password)
  db.add(new_user)
  
  payload = {
    "sub": new_user.id,
    "email": new_user.email,
    "exp": datetime.utcnow() + timedelta(hours=24)
  }
  
  await db.commit()
  await db.refresh(new_user)
  token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
  return {"access_token": token, "token_type": "bearer"}


@user_router.post("/signin")
async def login(data: ILoginUserData, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.email == data.email))
  user = result.scalars().first()
  
  if not user:
    raise HTTPException(status_code=404, detail="User is not existed!")

  if not user.verify_password(data.password):
    raise HTTPException(status_code=400, detail="Wrong password")
  
  payload = {
    "sub": user.id,
    "email": user.email,
    "exp": datetime.utcnow() + timedelta(hours=24)
  }
  token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
  return {"access_token": token, "token_type": "bearer"}

  
@user_router.put("/update-avatar/{user_id}")
async def update_user_avatar(user_id: str, data: IUpdateUserAvatarData, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalars().first()
  if user is None:
    raise HTTPException(status_code=404, detail="User not found")

  user.avatar_url = data.avatar_url
  user.updated_at = datetime.datetime.utcnow()
  
  await db.commit()
  await db.refresh(user)

  return {"message": "User avatar updated"}


@user_router.put("/update-username/{user_id}")
async def update_user_name(user_id: str, data: IUpdateUserNameData, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalars().first()
  if user is None:
    raise HTTPException(status_code=404, detail="User not found")

  user.username = data.username
  user.updated_at = datetime.datetime.utcnow()
  
  await db.commit()
  await db.refresh(user)

  return {"message": "User name updated"}


@user_router.delete("/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalars().first()
  if user is None:
    raise HTTPException(status_code=404, detail="User not found")
  await db.delete(user)
  await db.commit()

  return {"message": "User deleted successfully"}