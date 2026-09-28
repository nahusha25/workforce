import uuid

from sqlalchemy import desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.auth import OtpToken, RefreshToken, User


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_mobile(self, mobile_id: str) -> User | None:
        stmt = select(User).where(User.mobile_id == mobile_id, User.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_latest_otp(self, user_id: uuid.UUID) -> OtpToken | None:
        stmt = select(OtpToken).where(
            OtpToken.user_id == user_id,
            OtpToken.is_used == False
        ).order_by(desc(OtpToken.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_otp(self, otp_token: OtpToken) -> OtpToken:
        self.db.add(otp_token)
        await self.db.commit()
        await self.db.refresh(otp_token)
        return otp_token

    async def mark_otp_used(self, otp_id: uuid.UUID) -> None:
        stmt = update(OtpToken).where(OtpToken.id == otp_id).values(is_used=True)
        await self.db.execute(stmt)
        await self.db.commit()

    async def increment_otp_attempts(self, otp_id: uuid.UUID, attempts: int) -> None:
        stmt = update(OtpToken).where(OtpToken.id == otp_id).values(attempts=attempts)
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_refresh_token(self, refresh_token: RefreshToken) -> RefreshToken:
        self.db.add(refresh_token)
        await self.db.commit()
        await self.db.refresh(refresh_token)
        return refresh_token
        
    async def revoke_refresh_tokens_for_user(self, user_id: uuid.UUID) -> None:
        stmt = update(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).values(is_revoked=True)
        await self.db.execute(stmt)
        await self.db.commit()
