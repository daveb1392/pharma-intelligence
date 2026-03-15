from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from supabase import Client, create_client

from app.config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """Service role client for admin operations."""
    if settings.supabase_service_role_key:
        return create_client(settings.supabase_url, settings.supabase_service_role_key)
    return create_client(settings.supabase_url, settings.supabase_key)


@lru_cache()
def get_supabase_anon_client() -> Client:
    """Anon client for public/auth operations."""
    return create_client(settings.supabase_url, settings.supabase_key)


def get_current_user(request: Request, db: Client = Depends(get_supabase_anon_client)) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")

    token = auth_header.split(" ")[1]
    try:
        user_response = db.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido")
        return {"user_id": user.id, "email": user.email}
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


def get_optional_user(request: Request, db: Client = Depends(get_supabase_anon_client)) -> dict | None:
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None
