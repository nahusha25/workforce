import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_otp_hash,
    get_token_hash,
    verify_otp_hash,
)
from app.models.auth import OtpToken, RefreshToken
from app.modules.auth.repository import AuthRepository
from app.shared.sms import send_otp_sms


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = AuthRepository(db)

    async def request_otp(self, mobile: str) -> None:
        user = await self.repo.get_user_by_mobile(mobile)
        if not user:
            # Prevent user enumeration: do not throw error, simply return as if SMS was sent
            return

        # Generate 6 digit OTP
        otp_plain = f"{random.randint(100000, 999999)}"
        otp_hash = get_otp_hash(otp_plain)
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        
        otp_token = OtpToken(
            user_id=user.id,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
            is_used=False
        )
        await self.repo.create_otp(otp_token)
        
        # Send SMS
        await send_otp_sms(mobile, otp_plain)

    async def verify_otp(self, mobile: str, otp: str) -> tuple[str, str]:
        user = await self.repo.get_user_by_mobile(mobile)
        if not user:
            raise AuthError("Invalid credentials")

        otp_record = await self.repo.get_latest_otp(user.id)
        if not otp_record:
            raise AuthError("No pending OTP found")

        if otp_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise AuthError("OTP expired")

        if otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise AuthError("Maximum OTP attempts exceeded")

        if not verify_otp_hash(otp, otp_record.otp_hash):
            await self.repo.increment_otp_attempts(otp_record.id, otp_record.attempts + 1)
            raise AuthError("Invalid OTP")

        # Success
        await self.repo.mark_otp_used(otp_record.id)

        # Assuming employees exist. user.employees is a list (1:1), we might just use user_id
        # Let's get employee_id if possible, but user id is sufficient for auth for now.
        employee_id = None # We would query Employee table here if needed for token

        access_token = create_access_token(subject=user.id, role=user.role, employee_id=employee_id)
        refresh_token_plain = create_refresh_token(subject=user.id)
        refresh_token_hash = get_token_hash(refresh_token_plain)
        
        # Store refresh token
        await self.repo.revoke_refresh_tokens_for_user(user.id)
        
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        rt_record = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            is_revoked=False
        )
        await self.repo.create_refresh_token(rt_record)
        
        return access_token, refresh_token_plain

    async def refresh_token(self, refresh_token: str) -> tuple[str, str]:
        if not refresh_token:
            raise AuthError("Refresh token missing")
            
        token_hash = get_token_hash(refresh_token)

        rt_record = await self.repo.get_refresh_token(token_hash)
        if not rt_record:
            raise AuthError("Invalid or revoked refresh token")

        if rt_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise AuthError("Refresh token expired")

        user = await self.repo.get_user_by_id(rt_record.user_id)
        if not user or not user.is_active:
            raise AuthError("User inactive")

        # Rotate tokens
        await self.repo.revoke_refresh_tokens_for_user(user.id)

        access_token = create_access_token(subject=user.id, role=user.role)
        new_refresh_token_plain = create_refresh_token(subject=user.id)
        new_refresh_token_hash = get_token_hash(new_refresh_token_plain)
        
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_rt_record = RefreshToken(
            user_id=user.id,
            token_hash=new_refresh_token_hash,
            expires_at=expires_at,
            is_revoked=False
        )
        await self.repo.create_refresh_token(new_rt_record)
        
        return access_token, new_refresh_token_plain

    async def logout(self, user_id: uuid.UUID) -> None:
        await self.repo.revoke_refresh_tokens_for_user(user_id)
