from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import Discipline, User
from app.models.enums import UserRole

_DISCIPLINES: list[tuple[str, str | None]] = [
    ("Counter Strike 2", "Тактический шутер от первого лица (Valve)."),
    ("Dota 2", "MOBA 5×5 (Valve)."),
    ("Valorant", "Тактический шутер с героями (Riot Games)."),
    ("League of Legends", "MOBA 5×5 (Riot Games)."),
    ("Rocket League", "Футбол на машинах (Psyonix)."),
]


async def seed_disciplines(session: AsyncSession) -> None:
    """Идемпотентно добавляет базовые игровые дисциплины (по уникальному name)."""
    for name, description in _DISCIPLINES:
        result = await session.execute(
            select(Discipline.id).where(Discipline.name == name).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            continue
        session.add(Discipline(name=name, description=description))
    await session.flush()


async def seed_admin(session: AsyncSession) -> None:
    result = await session.execute(select(User.id).where(User.login == "admin").limit(1))
    if result.scalar_one_or_none() is not None:
        return
    session.add(
        User(
            login="admin",
            first_name="Андрей",
            last_name="Васильев",
            password_hash=hash_password("admin123"),
            is_active=True,
            role=UserRole.admin.value,
        )
    )
    await session.flush()
