from pydantic import BaseModel, Field


class OtpRequest(BaseModel):
    mobile: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')

class OtpVerify(BaseModel):
    mobile: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    otp: str = Field(..., min_length=4, max_length=10)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
