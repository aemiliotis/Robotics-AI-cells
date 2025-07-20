from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import timedelta
from typing import List, Dict, Any
import os
from pydantic import BaseModel
from database import SessionLocal, User, get_db, init_db
from auth import (
    authenticate_user, create_access_token, 
    get_current_user, verify_api_key, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from cell_loader import load_cells
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Load AI cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

app = FastAPI(
    title="Robotics AI Hub API",
    description="API for managing and executing robotics AI cells",
    version="1.0.0",
    docs_url="/api-docs",
    redoc_url=None
)

# CORS Configuration
origins = [
    "https://aemiliotis.github.io",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserOut(BaseModel):
    username: str
    email: str
    is_active: bool

class AIRequest(BaseModel):
    cells: List[str]
    data: Dict[str, Any]

class AIResponse(BaseModel):
    success: bool
    results: Dict[str, Any]
    error: str = None

class APIKeyResponse(BaseModel):
    api_key: str

# Routes
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=UserOut)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        username=user.username,
        email=user.email,
    )
    new_user.set_password(user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/generate-api-key", response_model=APIKeyResponse)
async def generate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    api_key = current_user.generate_api_key()
    db.commit()
    return {"api_key": api_key}

@app.get("/list-cells")
async def list_cells():
    """List all available AI cells"""
    return {"available_cells": list(ai_cells.keys())}

@app.post("/ai-api", response_model=AIResponse)
async def execute_cells(
    request: AIRequest,
    request_obj: Request = None,
    db: Session = Depends(get_db)
):
    """Execute one or more AI cells"""
    try:
        # Authentication
        user = None
        if request_obj:
            # Check for API key in headers
            api_key = request_obj.headers.get("x-api-key")
            if api_key:
                user = verify_api_key(api_key, db)
            # Else check for Bearer token
            elif "authorization" in request_obj.headers:
                try:
                    user = await get_current_user(
                        token=request_obj.headers["authorization"].split(" ")[1],
                        db=db
                    )
                except:
                    pass
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Execute cells
        results = {}
        for cell_name in request.cells:
            if cell_name not in ai_cells:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cell {cell_name} not found"
                )
            
            cell_input = request.data.get(cell_name, {})
            try:
                results[cell_name] = ai_cells[cell_name](cell_input)
            except Exception as e:
                logger.error(f"Error executing cell {cell_name}: {str(e)}")
                results[cell_name] = {"error": str(e)}
        
        # Log API call
        log_entry = APILog(
            user_id=user.id,
            endpoint="/ai-api",
            method="POST",
            status_code=200,
            cell_used=",".join(request.cells)
        )
        db.add(log_entry)
        db.commit()
        
        return {"success": True, "results": results}
    
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"status": "alive", "cells": list(ai_cells.keys())}

# Mount static files for documentation
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
