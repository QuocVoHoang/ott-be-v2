from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from enum_data.enum_data import ConversationType


## USER INTERFACE
class INewUserData(BaseModel):
  username: Optional[str] = None
  email: Optional[str] = None
  password: Optional[str] = None

class IUpdateUserData(BaseModel):
  avatar_url: Optional[str] = None
  username: Optional[str] = None
  
class IUpdateUserAvatarData(BaseModel):
  avatar_url: Optional[str] = None
  
class IUpdateUserNameData(BaseModel):
  username: Optional[str] = None

class ILoginUserData(BaseModel):
  email: Optional[str] = None
  password: Optional[str] = None


## CONVERSATION INTERFACE
class INewConversationData(BaseModel):
  name: Optional[str] = None
  type: ConversationType
  avatar_url: str
  participants: List[str]
  created_by: str

class IUpdateConversationData(BaseModel):
  avatar_url: Optional[str] = None
  name: Optional[str] = None
  participants: List[str]
  email: str
  
class IUpdateConversationAvatarData(BaseModel):
  avatar_url: Optional[str] = None
  
class IUpdateConversationNameData(BaseModel):
  name: Optional[str] = None
  
class IUpdateConversationParticipantData(BaseModel):
  participants: List[str]
  
class IRemoveParticipantData(BaseModel):
  participant: str
  
class FriendRequestCreate(BaseModel):
  receiver_id: str