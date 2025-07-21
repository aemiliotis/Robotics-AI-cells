import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/robotics_ai')
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    api_key = Column(String(64), unique=True, nullable=True)
    
    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
    
    def generate_api_key(self):
        import secrets
        self.api_key = secrets.token_urlsafe(32)
        return self.api_key

class APILog(Base):
    __tablename__ = 'api_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    endpoint = Column(String(100))
    method = Column(String(10))
    timestamp = Column(DateTime, default=datetime.utcnow)
    status_code = Column(Integer)
    cell_used = Column(String(50))

def get_db() -> Session:  # Add type annotation
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def init_db():
    # Create all tables if they don't exist
    inspector = inspect(engine)
    
    if not inspector.has_table("users"):
        Base.metadata.create_all(bind=engine)
