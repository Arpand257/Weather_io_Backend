import sqlalchemy
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:arpan123@localhost:5432/weather_db"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE readings ADD COLUMN sunlight VARCHAR;"))
    except Exception as e:
        print("sunlight error:", e)
        
    try:
        conn.execute(text("ALTER TABLE readings ADD COLUMN rain VARCHAR;"))
    except Exception as e:
        print("rain error:", e)
        
    conn.commit()
    print("Database updated.")
