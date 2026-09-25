from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(Credentials):
    full_name: str = Field(min_length=1, max_length=120)


class LoginRequest(Credentials):
    pass


class UserUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=120)
