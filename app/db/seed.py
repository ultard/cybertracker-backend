from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import ParticipantLevel, Role, User
from app.models.enums import UserRoleName


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


async def seed_levels(session: AsyncSession) -> None:
    result = await session.execute(select(ParticipantLevel.id).limit(1))
    if result.scalar_one_or_none() is not None:
        return
    levels = [
        ("Bronze", 0, 10),
        ("Silver", 100, 20),
        ("Gold", 500, 30),
    ]
    for level_name, min_points, sort_order in levels:
        session.add(
            ParticipantLevel(name=level_name, min_points=min_points, sort_order=sort_order)
        )
    await session.flush()


async def seed_admin(session: AsyncSession) -> None:
    result = await session.execute(select(User.id).where(User.login == "admin").limit(1))
    if result.scalar_one_or_none() is not None:
        return
    role_result = await session.execute(
        select(Role).where(Role.name == UserRoleName.admin.value)
    )
    role = role_result.scalar_one()
    session.add(
        User(
            login="admin",
            password_hash=hash_password("admin123"),
            is_active=True,
            role_id=role.id,
        )
    )
    await session.flush()
