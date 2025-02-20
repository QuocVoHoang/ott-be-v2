from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Conversation, User, ConversationParticipant
from interface.interface import (
    INewConversationData, 
    IUpdateConversationAvatarData, 
    IUpdateConversationNameData, 
    IUpdateConversationParticipantData,
    IRemoveParticipantData
)
from sqlalchemy.future import select
import datetime
from database import get_db

conversation_router = APIRouter()

@conversation_router.get("/{conversation_id}")
async def get_conversation_by_id(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    return conversation

@conversation_router.get("/users/{conversation_id}")
async def get_conversation_users(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConversationParticipant).where(ConversationParticipant.conversation_id == conversation_id))
    users = result.scalars().all()
    return users

@conversation_router.post("/")
async def create_new_conversation(data: INewConversationData, db: AsyncSession = Depends(get_db)):
    if data.type not in ["private", "group"]:
        raise HTTPException(status_code=400, detail="Invalid conversation type")
    
    if len(data.participants) < 2:
        raise HTTPException(status_code=400, detail="At least 2 participants required")
    
    result = await db.execute(select(User.id).where(User.id == data.created_by))
    creator = result.scalars().first()
    if not creator:
        raise HTTPException(status_code=400, detail="Creator does not exist")

    result = await db.execute(select(User.id).where(User.id.in_(data.participants)))
    existing_users = {row[0] for row in result.fetchall()}
    missing_users = set(data.participants) - existing_users
    if missing_users:
        raise HTTPException(status_code=400, detail=f"Users not found: {missing_users}")

    new_conversation = Conversation(
        name=data.name,
        type=data.type,
        created_by=data.created_by
    )
    
    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)
    
    participants_records = [
        ConversationParticipant(
            conversation_id=new_conversation.id,
            user_id=user_id
        )
        for user_id in data.participants
    ]
    db.add_all(participants_records)
    await db.commit()

    return {
        "message": "Conversation created successfully",
        "conversation": new_conversation,
        "participants": data.participants
    }


@conversation_router.put("/update-avatar/{conversation_id}")
async def update_conversation_name(conversation_id: str, data: IUpdateConversationAvatarData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.avatar_url = data.avatar_url
    conversation.updated_at = datetime.datetime.utcnow()
    
    await db.commit()
    await db.refresh(conversation)

    return {"message": "Conversation avatar updated"}


@conversation_router.put("/update-name/{conversation_id}")
async def update_conversation_name(conversation_id: str, data: IUpdateConversationNameData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.name = data.name
    conversation.updated_at = datetime.datetime.utcnow()
    
    await db.commit()
    await db.refresh(conversation)

    return {"message": "Conversation name updated"}


@conversation_router.put("/add-participants/{conversation_id}")
async def update_conversation_add_participants(conversation_id: str, data: IUpdateConversationParticipantData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(select(User.id).where(User.id.in_(data.participants)))
    existing_users = {row[0] for row in result.fetchall()}
    missing_users = set(data.participants) - existing_users
    
    if missing_users:
        raise HTTPException(status_code=400, detail=f"Users not found: {missing_users}")

    result = await db.execute(
        select(ConversationParticipant.user_id)
        .where(ConversationParticipant.conversation_id == conversation_id, 
            ConversationParticipant.user_id.in_(data.participants))
    )

    existing_participants = {row[0] for row in result.fetchall()}

    new_users = list(set(data.participants) - existing_participants)
    
    if not new_users:
        raise HTTPException(status_code=400, detail="All users are already in conversation")

    new_participants = [
        ConversationParticipant(conversation_id=conversation_id, user_id=user_id)
        for user_id in new_users
    ]
    db.add_all(new_participants)
    await db.commit()

    return {
        "message": "Users added successfully",
        "conversation_id": conversation_id,
        "added_users": new_users
    }


@conversation_router.put("/remove-participant/{conversation_id}")
async def update_conversation_remove_participant(conversation_id: str, data: IRemoveParticipantData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(ConversationParticipant)
        .where(
            ConversationParticipant.conversation_id == conversation_id, 
            ConversationParticipant.user_id == data.participant
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=400, detail=f"User not in conversation")
    
    await db.delete(user)
    
    await db.commit()

    return {
        "message": "User removed successfully",
        "conversation_id": conversation_id,
        "removed_user": data.participant
    }


@conversation_router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conversation)
    await db.commit()
    return {"message": "Conversation deleted successfully"}