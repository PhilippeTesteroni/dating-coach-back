import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, String, Integer, Enum, DateTime, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.database import Base


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class PreferredGender(str, enum.Enum):
    all = "all"
    male = "male"
    female = "female"


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
