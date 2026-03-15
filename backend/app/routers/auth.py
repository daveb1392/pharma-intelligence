from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.dependencies import get_current_user, get_supabase_anon_client
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
def register(
    body: RegisterRequest,
    db: Client = Depends(get_supabase_anon_client),
):
    try:
        result = db.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result.user:
        raise HTTPException(status_code=400, detail="Error al crear cuenta")

    return AuthResponse(
        access_token=result.session.access_token if result.session else "",
        refresh_token=result.session.refresh_token if result.session else "",
        user_id=result.user.id,
        email=result.user.email or "",
    )


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    db: Client = Depends(get_supabase_anon_client),
):
    try:
        result = db.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not result.user or not result.session:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        user_id=result.user.id,
        email=result.user.email or "",
    )


@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(user_id=user["user_id"], email=user["email"])
