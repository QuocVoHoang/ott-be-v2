from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    Enum
)
from sqlalchemy.orm import relationship
import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ARRAY 
import uuid
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
    )
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True, default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    conversations = relationship("ConversationParticipant", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password = pwd_context.hash(raw_password)

    def verify_password(self, raw_password):
        return pwd_context.verify(raw_password, self.password)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
    )
    name = Column(String, nullable=False)
    type = Column(Enum('private', 'group', name="conversation_type"), nullable=False)
    avatar_url = Column(String, nullable=True)

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
    )
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=True)
    type = Column(Enum('text', 'image', 'file', 'audio', 'video', name="message_type"), nullable=False, default='text')
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
    )
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="conversations")


