from os import getenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
