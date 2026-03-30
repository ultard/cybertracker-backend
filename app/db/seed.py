from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import Discipline, Role, User
from app.models.enums import UserRoleName

_DISCIPLINES: list[tuple[str, str | None, int]] = [
    ("Counter-Strike 2", "Тактический шутер от первого лица (Valve).", 16),
    ("Dota 2", "MOBA 5×5 (Valve).", 12),
    ("Valorant", "Тактический шутер с героями (Riot Games).", 16),
    ("League of Legends", "MOBA 5×5 (Riot Games).", 12),
    ("Rocket League", "Футбол на машинах (Psyonix).", 0),
]


async def seed_roles(session: AsyncSession) -> None:
    result = await session.execute(select(Role.id).limit(1))
    if result.scalar_one_or_none() is not None:
        return
    roles = [
        (UserRoleName.admin.value, "Администратор системы"),
        (UserRoleName.organizer.value, "Организатор турниров"),
        (UserRoleName.judge.value, "Судья"),
        (UserRoleName.manager.value, "Руководитель / аналитик"),
        (UserRoleName.player.value, "Игрок"),
        (UserRoleName.spectator.value, "Зритель"),
    ]
    for role_name, role_description in roles:
        session.add(Role(name=role_name, description=role_description))
    await session.flush()


async def seed_disciplines(session: AsyncSession) -> None:
    """Идемпотентно добавляет базовые игровые дисциплины (по уникальному name)."""
    for name, description, min_age in _DISCIPLINES:
        result = await session.execute(
            select(Discipline.id).where(Discipline.name == name).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            continue
        session.add(Discipline(name=name, description=description, min_age=min_age))
    await session.flush()


async def seed_admin(session: AsyncSession) -> None:
    result = await session.execute(select(User.id).where(User.login == "admin").limit(1))
    if result.scalar_one_or_none() is not None:
        return
    role_result = await session.execute(select(Role).where(Role.name == UserRoleName.admin.value))
    role = role_result.scalar_one()
    session.add(
        User(
            login="admin",
            first_name="Андрей",
            last_name="Васильев",
            password_hash=hash_password("admin123"),
            is_active=True,
            role_id=role.id,
        )
    )
    await session.flush()
