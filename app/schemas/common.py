from pydantic import BaseModel, Field


class Page[T](BaseModel):
    items: list[T] = Field(description="Элементы страницы")
    total: int = Field(description="Всего записей")
    skip: int = Field(ge=0, description="Смещение")
    limit: int = Field(ge=1, le=200, description="Лимит на странице")


class Message(BaseModel):
    message: str
