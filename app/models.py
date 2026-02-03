import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, String, Integer, Enum, DateTime, Text, Boolean, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class PreferredGender(str, enum.Enum):
    all = "all"
    male = "male"
    female = "female"


class ActorType(str, enum.Enum):
    character = "character"
    coach = "coach"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class UserProfile(Base):
    """
    User profile for Dating Coach app.
    
    Table: dc_user_profiles
    Prefix 'dc_' to namespace within shared shitty_apps database.
    """
    __tablename__ = "dc_user_profiles"
    
    # Primary key - matches identity.user_mappings.id
    user_id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False
    )
    
    # Profile data
    name = Column(String(100), nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    preferred_gender = Column(Enum(PreferredGender), default=PreferredGender.all)
    age_range_min = Column(Integer, default=18)
    age_range_max = Column(Integer, default=99)
    avatar_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=text("NOW()")
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("NOW()")
    )


class Conversation(Base):
    """
    Conversation/chat session.
    
    Table: dc_conversations
    """
    __tablename__ = "dc_conversations"
    
    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("dc_user_profiles.user_id"),
        nullable=False
    )
    
    # Mode & Actor
    mode_id = Column(String(50), nullable=False)  # category: training, analysis, reflection, free_practice
    submode_id = Column(String(50), nullable=False)  # specific mode: open_chat, first_contact, etc.
    actor_type = Column(Enum(ActorType), nullable=False)
    character_id = Column(String(50), nullable=True)  # null for some coach modes
    
    # Generated params (fixed at creation)
    difficulty_level = Column(Integer, nullable=True)
    model_age = Column(Integer, nullable=True)  # null for coach
    model_orientation = Column(String(20), nullable=True)  # null for coach
    language = Column(String(10), default="en")
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=text("NOW()")
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("NOW()")
    )
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at", passive_deletes=True)


class Message(Base):
    """
    Chat message.
    
    Table: dc_messages
    """
    __tablename__ = "dc_messages"
    
    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    
    conversation_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("dc_conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=text("NOW()")
    )
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
