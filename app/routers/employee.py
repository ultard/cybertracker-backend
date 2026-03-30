from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import write_audit
from app.deps import get_db, require_roles
from app.models import Employee, User
from app.models.enums import UserRoleName
from app.repositories import EmployeeRepository
from app.schemas.common import Page
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate

router = APIRouter()
Admin = Annotated[User, Depends(require_roles(UserRoleName.admin))]


def _to_employee_read(employee: Employee) -> EmployeeRead:
    return EmployeeRead.model_validate(employee)


@router.get("", response_model=Page[EmployeeRead], summary="Список сотрудников")
async def list_employees(
    _: Admin,
    session: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    position: str | None = None,
) -> Page[EmployeeRead]:
    employee_repository = EmployeeRepository(session)
    rows, total = await employee_repository.list_page(skip=skip, limit=limit, position=position)
    return Page(
        items=[_to_employee_read(employee) for employee in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать сотрудника",
)
async def create_employee(
    user: Admin,
    data: EmployeeCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeRead:
    employee = Employee(
        user_id=data.user_id,
        first_name=data.first_name,
        last_name=data.last_name,
        patronymic=data.patronymic,
        position=data.position,
        phone=data.phone,
        email=data.email,
        hired_at=data.hired_at,
        fired_at=data.fired_at,
        is_judge=data.is_judge,
        notes=data.notes,
    )
    session.add(employee)
    await session.flush()
    await write_audit(
        session,
        user_id=user.id,
        action="employee.create",
        entity="Employee",
        entity_id=employee.id,
    )
    await session.commit()
    employee_repository = EmployeeRepository(session)
    created_employee = await employee_repository.get_by_id(employee.id)
    assert created_employee
    return _to_employee_read(created_employee)


@router.get(
    "/{employee_id}",
    response_model=EmployeeRead,
    summary="Сотрудник по ID",
)
async def get_employee(
    _: Admin,
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeRead:
    employee_repository = EmployeeRepository(session)
    employee = await employee_repository.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _to_employee_read(employee)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeRead,
    summary="Обновить сотрудника",
)
async def update_employee(
    user: Admin,
    employee_id: int,
    data: EmployeeUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeRead:
    employee_repository = EmployeeRepository(session)
    employee = await employee_repository.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(employee, key, value)
    await write_audit(
        session,
        user_id=user.id,
        action="employee.update",
        entity="Employee",
        entity_id=employee.id,
    )
    await session.commit()
    updated_employee = await employee_repository.get_by_id(employee_id)
    assert updated_employee
    return _to_employee_read(updated_employee)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить сотрудника",
)
async def delete_employee(
    user: Admin,
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    employee_repository = EmployeeRepository(session)
    employee = await employee_repository.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await write_audit(
        session,
        user_id=user.id,
        action="employee.delete",
        entity="Employee",
        entity_id=employee.id,
    )
    await session.delete(employee)
    await session.commit()
