# database.py
import os
import psycopg2
from psycopg2 import sql
from werkzeug.security import generate_password_hash, check_password_hash

def get_db():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                api_key VARCHAR(64) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS cell_usage (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                cell_name VARCHAR(100) NOT NULL,
                executed_at TIMESTAMP DEFAULT NOW()
            );
            """)
            conn.commit()
