-- Run these commands in your PostgreSQL client (like pgAdmin, DBeaver, or psql)

-- 1. Create the database
CREATE DATABASE weather_db;

-- 2. Connect to the new database (if using psql)
-- \c weather_db

-- 3. (Optional) Our SQLAlchemy script (app/database.py) will automatically create 
-- the tables when the app runs, but if you want to create the readings table manually:
CREATE TABLE IF NOT EXISTS readings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    temperature FLOAT,
    humidity FLOAT,
    pressure FLOAT,
    air_quality FLOAT
);
