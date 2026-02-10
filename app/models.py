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


class SubscriptionStatus(str, enum.Enum):
    none = "none"
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


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

    # Relationships
    conversations = relationship("Conversation", back_populates="user_profile", passive_deletes=True)


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
        ForeignKey("dc_user_profiles.user_id", ondelete="CASCADE"),
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
    user_profile = relationship("UserProfile", back_populates="conversations")
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


class Subscription(Base):
    """
    User subscription for Dating Coach app.

    Table: dc_subscriptions
    Tracks subscription status. Credits system remains untouched —
    this is a parallel monetization path.
    """
    __tablename__ = "dc_subscriptions"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("dc_user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )

    status = Column(
        Enum(SubscriptionStatus),
        default=SubscriptionStatus.none,
        nullable=False
    )
    platform = Column(String(20), nullable=True)  # google_play, app_store
    product_id = Column(String(100), nullable=True)  # monthly_premium, yearly_premium
    purchase_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)

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


class MessageCounter(Base):
    """
    Free-tier message counter per user.

    Table: dc_message_counters
    Tracks how many messages a non-subscribed user has sent.
    Subscribed users bypass this check entirely.
    """
    __tablename__ = "dc_message_counters"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("dc_user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )

    message_count = Column(Integer, default=0, nullable=False)

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
