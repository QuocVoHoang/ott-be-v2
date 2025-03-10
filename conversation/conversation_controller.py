from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Conversation, User, ConversationParticipant
from interface.interface import (
    INewConversationData, 
    IUpdateConversationAvatarData, 
    IUpdateConversationNameData, 
    IUpdateConversationParticipantData,
    IRemoveParticipantData,
    IUpdateConversationData
)
from sqlalchemy.future import select
from sqlalchemy import delete
from utils.utils import get_vn_time
from database import get_db

conversation_router = APIRouter()

@conversation_router.get("/{conversation_id}")
async def get_conversation_by_id(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """params: conversation_id"""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    
    result = await db.execute(select(ConversationParticipant.user_id).where(ConversationParticipant.conversation_id == conversation_id))
    user_ids = result.scalars().all()
    
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()
    
    return {
        "conversation": conversation,
        "users": users
    }


@conversation_router.get("/users/{conversation_id}")
async def get_conversation_users(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """params: conversation_id"""    
    result = await db.execute(select(ConversationParticipant.user_id).where(ConversationParticipant.conversation_id == conversation_id))
    user_ids = result.scalars().all()
    
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()
    
    return users


@conversation_router.post("/")
async def create_new_conversation(data: INewConversationData, db: AsyncSession = Depends(get_db)):
    """params: participants are emails"""
    if data.type not in ["private", "group"]:
        raise HTTPException(status_code=400, detail="Invalid conversation type")
    
    if len(data.participants) < 2:
        raise HTTPException(status_code=400, detail="At least 2 participants required")
    
    result = await db.execute(select(User.id).where(User.email == data.created_by))
    creator = result.scalars().first()
    if not creator:
        raise HTTPException(status_code=400, detail="Creator does not exist")

    result = await db.execute(select(User.id, User.email).where(User.email.in_(data.participants)))
    user_ids = result.scalars().all()

    new_conversation = Conversation(
        name=data.name,
        type=data.type,
        avatar_url=data.avatar_url,
        created_by=creator
    )
    
    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)
    
    participants_records = [
        ConversationParticipant(
            conversation_id=new_conversation.id,
            user_id=user_id
        )
        for user_id in user_ids
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
    conversation.updated_at = await get_vn_time()
    
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
    conversation.updated_at = await get_vn_time()
    
    await db.commit()
    await db.refresh(conversation)

    return {"message": "Conversation name updated"}


@conversation_router.put("/update/{conversation_id}")
async def update_conversation_name(conversation_id: str, data: IUpdateConversationData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.name = data.name
    conversation.avatar_url = data.avatar_url
    conversation.updated_at = await get_vn_time()
    
    result = await db.execute(select(User.id).where(User.email.in_(data.participants)))
    user_ids = result.scalars().all()
    
    result = await db.execute(
        select(ConversationParticipant.user_id)
        .where(ConversationParticipant.conversation_id == conversation_id)
    )
    existing_participants = set(result.scalars().all())
    new_user_ids = set(user_ids)
    participants_to_remove = existing_participants - new_user_ids
    participants_to_add = new_user_ids - existing_participants

    if participants_to_remove:
        await db.execute(
            delete(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id.in_(participants_to_remove)
            )
        )
    if participants_to_add:
        new_participants = [
            ConversationParticipant(conversation_id=conversation_id, user_id=user_id)
            for user_id in participants_to_add
        ]
        db.add_all(new_participants)

    await db.commit()
    await db.refresh(conversation)
    
    result = await db.execute(select(User.id).where(User.email == data.email))
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


@conversation_router.put("/add-participants/{conversation_id}")
async def update_conversation_add_participants(conversation_id: str, data: IUpdateConversationParticipantData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalars().first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(select(User.id).where(User.email.in_(data.participants)))
    user_ids = result.scalars().all()

    result = await db.execute(
        select(ConversationParticipant.user_id)
        .where(ConversationParticipant.conversation_id == conversation_id, 
            ConversationParticipant.user_id.in_(user_ids))
    )
    
    existing_participants = {row[0] for row in result.all()} 
    new_user_ids = [user_id for user_id in user_ids if user_id not in existing_participants]

    new_participants = [
        ConversationParticipant(conversation_id=conversation_id, user_id=user_id)
        for user_id in new_user_ids
    ]
    
    db.add_all(new_participants)
    await db.commit()

    return {
        "message": "Users added successfully",
        "conversation_id": conversation_id,
        "added_users": data.participants
    }


@conversation_router.put("/remove-participant/{conversation_id}")
async def update_conversation_remove_participant(conversation_id: str, data: IRemoveParticipantData, db: AsyncSession = Depends(get_db)):        
    result = await db.execute(select(User.id).where(User.email == data.participant))
    userid = result.scalars().first()
    if userid is None:
        raise HTTPException(status_code=404, detail="User not register")

    result = await db.execute(
        select(ConversationParticipant)
        .where(
            ConversationParticipant.conversation_id == conversation_id, 
            ConversationParticipant.user_id == userid
        )
    )
    user = result.scalars().first()
    print('user.id', user.id)

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