from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.dependencies import get_supabase_client
from app.schemas.product import CategoryItem
from app.services.data_filters import apply_freshness, clean_products

router = APIRouter()


@router.get("/categories", response_model=list[CategoryItem])
def list_categories(
    db: Client = Depends(get_supabase_client),
):
    result = (
        db.table("categories_mv")
        .select("*")
        .order("product_count", desc=True)
        .execute()
    )

    return [CategoryItem(**item) for item in result.data or []]


@router.get("/categories/{category}")
def get_category_products(
    category: str,
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    pharmacy: str | None = Query(None),
    brand: str | None = Query(None),
    requires_prescription: bool | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    has_discount: bool | None = Query(None),
    has_bank_deal: bool | None = Query(None),
    sort: str = Query("price_asc", regex="^(price_asc|price_desc|name_asc|discount)$"),
    db: Client = Depends(get_supabase_client),
):
    offset = (page - 1) * limit

    query = (
        db.table("products")
        .select("*", count="exact")
        .eq("normalized_category", category)
    )
    query = apply_freshness(query)

    if pharmacy:
        query = query.eq("pharmacy_source", pharmacy)
    if brand:
        query = query.ilike("brand", f"%{brand}%")
    if requires_prescription is not None:
        query = query.eq("requires_prescription", requires_prescription)
    if min_price is not None:
        query = query.gte("current_price", min_price)
    if max_price is not None:
        query = query.lte("current_price", max_price)
    if has_discount:
        query = query.not_.is_("discount_percentage", "null").gt("discount_percentage", 0)
    if has_bank_deal:
        query = query.not_.is_("bank_discount_price", "null")

    if sort == "price_asc":
        query = query.order("current_price", desc=False)
    elif sort == "price_desc":
        query = query.order("current_price", desc=True)
    elif sort == "name_asc":
        query = query.order("product_name", desc=False)
    elif sort == "discount":
        query = query.order("discount_percentage", desc=True)

    result = query.range(offset, offset + limit - 1).execute()

    return {
        "results": clean_products(result.data or []),
        "total": result.count or 0,
        "page": page,
        "limit": limit,
    }
