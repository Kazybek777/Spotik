import os
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext

from app.database import get_db
from app.models import User

router = APIRouter()

config_data = {
    'GOOGLE_CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID'),
    'GOOGLE_CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET')
}

starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)

oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


@router.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get('/callback')
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')

    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")

    email = user_info.get('email')
    name = user_info.get('name')
    picture = user_info.get('picture')

    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            name=name,
            picture=picture,
            provider='google',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session['user'] = {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'picture': user.picture
    }

    return RedirectResponse(url='/')


@router.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/docs')


@router.get('/me')
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    session_user = request.session.get('user')

    if not session_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == session_user['id']).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'picture': user.picture,
        'provider': user.provider,
        'created_at': user.created_at
    }


@router.post('/register')
async def register(user_data: UserCreate, db: Session = Depends(get_db)):

    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user_data.password)

    new_user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
        provider='local',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name
    }


@router.post('/login-password')
async def login_password(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    request.session['user'] = {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'picture': user.picture
    }

    return {"message": "Login successful"}

