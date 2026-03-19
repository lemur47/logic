"""
Shared CRUD utilities.
"""

from sqlalchemy.orm import Session


def paginate(
    db: Session,
    model: type,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    search_field: str = "name",
    order_field: str = "updated_at",
    order_desc: bool = True,
    options: list | None = None,
) -> tuple[list, int]:
    """Generic paginated query with optional search and eager loading."""
    query = db.query(model)

    if search:
        field = getattr(model, search_field)
        query = query.filter(field.ilike(f"%{search}%"))

    total = query.count()

    if options:
        for opt in options:
            query = query.options(opt)

    order_col = getattr(model, order_field)
    if order_desc:
        order_col = order_col.desc()
    query = query.order_by(order_col)

    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()

    return items, total


def get_by_id(
    db: Session,
    model: type,
    record_id: int,
    options: list | None = None,
):
    """Get a single record by ID with optional eager loading."""
    query = db.query(model).filter(model.id == record_id)
    if options:
        for opt in options:
            query = query.options(opt)
    return query.first()


def delete_by_id(db: Session, model: type, record_id: int) -> bool:
    """Delete a record by ID. Returns False if not found."""
    record = get_by_id(db, model, record_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True
