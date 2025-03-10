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
  IUpdateUserData
)
from datetime import timedelta
from utils.utils import get_vn_time
import os
from dotenv import load_dotenv
load_dotenv()
from authlib.jose import jwt

SECRET_KEY = "quoc_secret_key"

user_router = APIRouter()

security = HTTPBearer()

@user_router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
  try: 
    token = credentials.credentials
    # payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    payload = jwt.decode(token, SECRET_KEY)
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


@user_router.get("/info-email/{email}")
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
  try:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
      raise HTTPException(status_code=404, detail="User not found")

    return {
      "id": user.id,
      "username": user.username,
      "email": user.email,
      "avatar_url": user.avatar_url,
      "created_at": user.created_at
    }
  
  except Exception as e:
    print(f"Error fetching user: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal Server Error")


@user_router.get("/info-id/{user_id}")
async def get_user_by_id(user_id: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.id == user_id))
  user = result.scalars().first()
  return user


@user_router.get("/{email}/conversations")
async def get_user_conversations(email: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User.id).where(User.email == email))
  userid = result.scalars().first()
  if not userid:
    raise HTTPException(status_code=404, detail="User not found")
  
  result = await db.execute(
    select(ConversationParticipant.conversation_id)
    .where(ConversationParticipant.user_id == userid)
  )
  conversation_ids = [row[0] for row in result.fetchall()]

  if not conversation_ids:
    return {"message": "User is not in any conversation", "conversations": []}
  
  result = await db.execute(
    select(Conversation).where(Conversation.id.in_(conversation_ids))
  )
  conversations = result.scalars().all()

  return conversations


@user_router.post("/signup")
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
  await db.commit()
  await db.refresh(new_user)
  
  payload = {
    "sub": new_user.id,
    "email": new_user.email,
    "exp": await get_vn_time() + timedelta(hours=24)
  }
  
  # token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
  token = jwt.encode({"alg": "HS256"}, payload, SECRET_KEY)
  return {"access_token": token, "token_type": "bearer"}


# @user_router.post("/signup-phone")
# async def create_or_login_phone_user(data: IPhoneUser, db: AsyncSession = Depends(get_db)):
#   result = await db.execute(select(User).where(User.email == data.phone_number))
#   existing_user = result.scalars().first()

#   if existing_user:
#     payload = {
#       "sub": existing_user.id,
#       "email": existing_user.email,
#       "exp": await get_vn_time() + timedelta(hours=24)
#     }
#     token = jwt.encode({"alg": "HS256"}, payload, SECRET_KEY)
#     return {"access_token": token, "token_type": "bearer"}
  
#   new_user = User(
#     username=data.phone_number,
#     email=data.phone_number,
#     password=data.phone_number
#   )
#   new_user.set_password(new_user.password)
  
#   db.add(new_user)
#   await db.commit()
#   await db.refresh(new_user)

#   payload = {
#     "sub": new_user.id,
#     "phone_number": new_user.email,
#     "exp": await get_vn_time() + timedelta(hours=24)
#   }
#   token = jwt.encode({"alg": "HS256"}, payload, SECRET_KEY)

#   return {"access_token": token, "token_type": "bearer"}


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
    "exp": await get_vn_time() + timedelta(hours=24)
  }
  # token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
  token = jwt.encode({"alg": "HS256"}, payload, SECRET_KEY)
  return {"access_token": token, "token_type": "bearer"}

@user_router.put("/update/{email}")
async def update_user_avatar(email: str, data: IUpdateUserData, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.email == email))
  user = result.scalars().first()
  if user is None:
    raise HTTPException(status_code=404, detail="User not found")

  user.avatar_url = data.avatar_url
  user.username = data.username
  user.updated_at = await get_vn_time()
  
  await db.commit()
  await db.refresh(user)

  return user
  
@user_router.put("/update-avatar/{email}")
async def update_user_avatar(email: str, data: IUpdateUserAvatarData, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.email == email))
  user = result.scalars().first()
  if user is None:
    raise HTTPException(status_code=404, detail="User not found")

  user.avatar_url = data.avatar_url
  user.updated_at = await get_vn_time()
  
  await db.commit()
  await db.refresh(user)

  return {"message": "User avatar updated"}


@user_router.put("/update-username/{email}")
async def update_user_name(email: str, data: IUpdateUserNameData, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.email == email))
  user = result.scalars().first()
  if user is None:
    raise HTTPException(status_code=404, detail="User not found")

  user.username = data.username
  user.updated_at = await get_vn_time()
  
  await db.commit()
  await db.refresh(user)

  return {"message": "User name updated"}


@user_router.delete("/{email}")
async def delete_user(email: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.email == email))
  user = result.scalars().first()
  if user is None:
    raise HTTPException(status_code=404, detail="User not found")
  await db.delete(user)
  await db.commit()

  return {"message": "User deleted successfully"}