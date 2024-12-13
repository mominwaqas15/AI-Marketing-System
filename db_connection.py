from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv() 

def create_db():

    DATABASE_URL = os.getenv("DATABASE_URL")

    engine = create_engine(DATABASE_URL)

    # Create a session class
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    print("Database Connection Established...")

    return engine, SessionLocal