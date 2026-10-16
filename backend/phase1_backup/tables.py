"""Imports every model so SQLAlchemy knows the tables, then creates them.
Add new model imports here as later phases add tables."""
from app.database.database import Base, engine
from app.models import sensor, vision, experience  # noqa: F401


def create_tables():
    Base.metadata.create_all(bind=engine)
