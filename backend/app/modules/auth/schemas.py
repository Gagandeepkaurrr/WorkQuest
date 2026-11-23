from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(StrictModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class Registration(Credentials):
    display_name: str = Field(min_length=1, max_length=80)


class EmailInput(StrictModel):
    email: EmailStr


class TokenInput(StrictModel):
    token: str = Field(min_length=20, max_length=128)


class ResetInput(TokenInput):
    password: str = Field(min_length=12, max_length=256)


class PasswordChange(StrictModel):
    current_password: str = Field(max_length=256)
    password: str = Field(min_length=12, max_length=256)


class UserView(StrictModel):
    id: UUID
    display_name: str
    email: str
    role: str
    email_verified: bool
    is_demo: bool
    ai_provider: str


class ProfileInput(StrictModel):
    display_name: str = Field(min_length=1, max_length=80)


class PreferencesInput(StrictModel):
    theme: Literal["light", "dark"] = "light"
    reduced_motion: bool = False
    onboarding_completed: bool = False
    workspace_layout: Literal["standard", "focus"] = "standard"


class DeleteInput(StrictModel):
    password: str = Field(max_length=256)
    confirmation: Literal["DELETE"]
