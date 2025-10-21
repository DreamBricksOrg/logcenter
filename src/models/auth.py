from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class AdminLoginRequest(BaseModel):
  email: EmailStr = Field(..., description="Admin email")
  password: str = Field(..., min_length=3)


class AdminLoginResponse(BaseModel):
  api_key: str


class ProjectLoginRequest(BaseModel):
  api_key: str = Field(..., description="Project API Key")

class ProjectLoginResponse(BaseModel):
  project_id: str
  project_code: str
  role: str = "client"