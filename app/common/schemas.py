"""
Shared Pydantic schemas.
"""

from pydantic import BaseModel


class PaginatedList[T](BaseModel):
    """Paginated list response shared by all modules."""

    items: list[T]
    total: int
    page: int
    per_page: int
