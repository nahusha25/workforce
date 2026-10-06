
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.auth import User
from app.modules.auth.schemas import OtpRequest, OtpVerify, TokenResponse
from app.modules.auth.service import AuthService

router = APIRouter()

@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(payload: OtpRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.request_otp(payload.mobile)
    return {"message": "OTP sent successfully"}

@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(payload: OtpVerify, response: Response, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    access_token, refresh_token = await service.verify_otp(payload.mobile, payload.otp)
    
    # Set httpOnly secure cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Must be False for http://localhost in dev
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )
    
    return TokenResponse(access_token=access_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token_val = request.cookies.get("refresh_token")
    if not refresh_token_val:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    service = AuthService(db)
    access_token, new_refresh_token = await service.refresh_token(refresh_token_val)
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,  # Must be False for http://localhost in dev
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )
    
    return TokenResponse(access_token=access_token)

@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    user_id = current_user.id
    await service.logout(user_id)
    
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}
