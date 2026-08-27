"""Declarative base shared by every ORM model.

Kept in its own module (rather than inline in models.py) so Alembic's
env.py can import just the metadata, without pulling in the models
themselves and their dependencies.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
