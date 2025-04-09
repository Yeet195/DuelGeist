from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from passlib.context import CryptContext
from pydantic import BaseModel

from app.db.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.db import crud


router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/form", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_form(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if email already exists
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    # Check if username already exists
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Hash the password
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(password)
    
    # Create the user
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    
    # Add and commit
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user