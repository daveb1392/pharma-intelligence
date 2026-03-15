from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.dependencies import get_supabase_client

router = APIRouter()

# Farma Center stored their logo instead of product images — filter it out
LOGO_URLS = [
    "https://f.fcdn.app/assets/commerce/www.farmacenter.com.py/c305_93b5/public/web/img/logo.svg",
]


@router.get("/home/stats")
def get_home_stats(db: Client = Depends(get_supabase_client)):
    total = db.table("products").select("id", count="exact").limit(1).execute()
    pharmacies = (
        db.table("products")
        .select("pharmacy_source")
        .limit(1000)
        .execute()
    )
    pharmacy_set = set(r["pharmacy_source"] for r in pharmacies.data or [])

    return {
        "total_products": total.count or 0,
        "pharmacy_count": len(pharmacy_set),
    }


@router.get("/home/top-discounts")
def get_top_discounts(
    limit: int = Query(12, ge=1, le=24),
    db: Client = Depends(get_supabase_client),
):
    # Get top discounts per pharmacy (3 each) to ensure mix
    all_products = []
    for pharmacy in ["farma_oliva", "punto_farma", "farma_center", "farmacia_catedral"]:
        result = (
            db.table("products")
            .select("*")
            .eq("pharmacy_source", pharmacy)
            .not_.is_("discount_percentage", "null")
            .gt("discount_percentage", 5)
            .lt("discount_percentage", 80)  # filter obviously bad data
            .order("discount_percentage", desc=True)
            .limit(limit // 4 + 1)
            .execute()
        )
        all_products.extend(result.data or [])

    # Sort combined results by discount and take top N
    all_products.sort(key=lambda x: x.get("discount_percentage", 0), reverse=True)
    return all_products[:limit]


@router.get("/home/bank-deals")
def get_bank_deals(
    limit: int = Query(8, ge=1, le=24),
    db: Client = Depends(get_supabase_client),
):
    result = (
        db.table("products")
        .select("*")
        .not_.is_("bank_discount_price", "null")
        .order("bank_discount_price", desc=False)
        .limit(limit)
        .execute()
    )
    return result.data or []


@router.get("/home/brands")
def get_brands(
    category: str | None = Query(None),
    pharmacy: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Client = Depends(get_supabase_client),
):
    """Get distinct brands with product counts."""
    query = db.table("products").select("brand").not_.is_("brand", "null")
    if category:
        query = query.eq("normalized_category", category)
    if pharmacy:
        query = query.eq("pharmacy_source", pharmacy)
    result = query.limit(5000).execute()

    brand_counts: dict[str, int] = {}
    for r in result.data or []:
        b = r.get("brand")
        if b:
            brand_counts[b] = brand_counts.get(b, 0) + 1

    sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"brand": b, "count": c} for b, c in sorted_brands[:limit]]


@router.get("/home/products")
def get_all_products(
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    pharmacy: str | None = Query(None),
    category: str | None = Query(None),
    brand: str | None = Query(None),
    requires_prescription: bool | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    has_discount: bool | None = Query(None),
    has_bank_deal: bool | None = Query(None),
    sort: str = Query("price_asc", regex="^(price_asc|price_desc|name_asc|discount)$"),
    db: Client = Depends(get_supabase_client),
):
    """Browse all products across all pharmacies with filters."""
    offset = (page - 1) * limit

    query = db.table("products").select("*", count="exact")

    if pharmacy:
        query = query.eq("pharmacy_source", pharmacy)
    if category:
        query = query.eq("normalized_category", category)
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
        "results": result.data or [],
        "total": result.count or 0,
        "page": page,
        "limit": limit,
    }
