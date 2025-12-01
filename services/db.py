# services/db.py
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
DATABASE_URL = os.getenv("FARM_DATABASE_URL","postgresql+psycopg2://user:pass@localhost:5432/farmdb")
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
metadata = MetaData()
