from __future__ import annotations

from datetime import datetime
from typing import Literal, NotRequired, TypedDict

UserRole = Literal["owner", "admin", "groomer", "staff"]

class GroomerProfile(TypedDict):
    id: int
    bio: str

class UserRecord(TypedDict):
    id: int
    name: str
    email: str
    phone: str
    role: UserRole
    created_at: NotRequired[datetime]
    hashed_password: NotRequired[str]
    groomer_profile: NotRequired[GroomerProfile | None]