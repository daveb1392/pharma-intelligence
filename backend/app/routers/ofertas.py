from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.dependencies import get_supabase_client
from app.services.data_filters import apply_freshness, clean_products

router = APIRouter()


@router.get("/ofertas/stats")
def get_ofertas_stats(db: Client = Depends(get_supabase_client)):
    discount_query = (
        db.table("products")
        .select("id", count="exact")
        .not_.is_("discount_percentage", "null")
        .gt("discount_percentage", 0)
        .limit(1)
    )
    discount_count = apply_freshness(discount_query).execute()
    bank_query = (
        db.table("products")
        .select("id", count="exact")
        .not_.is_("bank_discount_price", "null")
        .limit(1)
    )
    bank_count = apply_freshness(bank_query).execute()
    return {
        "discount_count": discount_count.count or 0,
        "bank_deal_count": bank_count.count or 0,
    }


@router.get("/ofertas/products")
def get_ofertas_products(
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    offer_type: str = Query("all", regex="^(all|discount|bank_deal)$"),
    min_discount: int | None = Query(None, ge=0, le=100),
    pharmacy: str | None = Query(None),
    category: str | None = Query(None),
    sort: str = Query("discount", regex="^(discount|price_asc|price_desc)$"),
    db: Client = Depends(get_supabase_client),
):
    offset = (page - 1) * limit

    query = db.table("products").select("*", count="exact")
    query = apply_freshness(query)

    if offer_type == "discount":
        query = query.not_.is_("discount_percentage", "null").gt("discount_percentage", 0)
    elif offer_type == "bank_deal":
        query = query.not_.is_("bank_discount_price", "null")
    else:
        # "all" — has either discount or bank deal
        # Supabase doesn't support OR easily, so use discount > 0 OR bank_discount_price not null
        # We'll use the `or_` filter
        query = query.or_("discount_percentage.gt.0,bank_discount_price.not.is.null")

    if min_discount is not None:
        query = query.not_.is_("discount_percentage", "null").gte("discount_percentage", min_discount)

    if pharmacy:
        query = query.eq("pharmacy_source", pharmacy)
    if category:
        query = query.eq("normalized_category", category)

    if sort == "discount":
        query = query.order("discount_percentage", desc=True)
    elif sort == "price_asc":
        query = query.order("current_price", desc=False)
    elif sort == "price_desc":
        query = query.order("current_price", desc=True)

    result = query.range(offset, offset + limit - 1).execute()

    return {
        "results": clean_products(result.data or []),
        "total": result.count or 0,
        "page": page,
        "limit": limit,
    }
