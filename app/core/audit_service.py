from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None = None,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        changes=changes,
    )
    session.add(log)
    await session.flush()
    return log
