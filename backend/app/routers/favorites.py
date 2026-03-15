from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.dependencies import get_current_user, get_supabase_client
from app.schemas.auth import FavoriteRequest, FavoriteResponse

router = APIRouter()


@router.get("/favorites", response_model=list[FavoriteResponse])
def list_favorites(
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client),
):
    result = (
        db.table("user_favorites")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .execute()
    )

    return [FavoriteResponse(**item) for item in result.data or []]


@router.post("/favorites", response_model=FavoriteResponse, status_code=201)
def add_favorite(
    body: FavoriteRequest,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client),
):
    result = (
        db.table("user_favorites")
        .upsert(
            {
                "user_id": user["user_id"],
                "barcode": body.barcode,
                "product_name": body.product_name,
                "brand": body.brand,
                "image_url": body.image_url,
            },
            on_conflict="user_id,barcode",
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=400, detail="Error al guardar favorito")

    return FavoriteResponse(**result.data[0])


@router.delete("/favorites/{barcode}", status_code=204)
def remove_favorite(
    barcode: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client),
):
    db.table("user_favorites").delete().eq("user_id", user["user_id"]).eq(
        "barcode", barcode
    ).execute()
