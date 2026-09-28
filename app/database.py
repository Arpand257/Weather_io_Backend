from sqlalchemy import create_engine, Column, Integer, Float, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# You can change these credentials or load from environment variables later
DATABASE_URL = "postgresql://postgres:arpan123@localhost:5432/weather_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Reading(Base):
    __tablename__ = "readings"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    temperature = Column(Float)
    humidity = Column(Float)
    pressure = Column(Float)
    air_quality = Column(Float)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def insert_reading(db, data: dict):
    db_reading = Reading(
        temperature=data.get("temperature"),
        humidity=data.get("humidity"),
        pressure=data.get("pressure"),
        air_quality=data.get("air_quality")
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading
def get_latest_reading(db: Session):
    return db.query(Reading).order_by(Reading.timestamp.desc()).first()

def get_history(db: Session, limit: int = 24):
    return db.query(Reading).order_by(Reading.timestamp.desc()).limit(limit).all()
