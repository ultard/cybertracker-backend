from datetime import UTC, datetime

from sqlalchemy import select

from app.models import AuditLog, QRSession
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    model = AuditLog

    async def list_page(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        entity: str | None = None,
        user_id: int | None = None,
    ) -> tuple[list[AuditLog], int]:
        filters = []
        if entity:
            filters.append(AuditLog.entity == entity)
        if user_id is not None:
            filters.append(AuditLog.user_id == user_id)
        return await self._list_page(
            filters=filters,
            order_by=AuditLog.created_at.desc(),
            loads=[AuditLog.user],
            skip=skip,
            limit=limit,
        )


class QRRepository(BaseRepository):
    model = QRSession

    async def get_by_token(self, token: str) -> QRSession | None:
        result = await self.session.execute(select(QRSession).where(QRSession.token == token))
        return result.scalar_one_or_none()

    async def get_active_for_participant(self, participant_id: int) -> QRSession | None:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(QRSession)
            .where(
                QRSession.participant_id == participant_id,
                QRSession.used.is_(False),
                QRSession.expires_at > now,
            )
            .order_by(QRSession.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
