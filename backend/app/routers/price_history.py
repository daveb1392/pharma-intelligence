from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.dependencies import get_supabase_client
from app.schemas.product import (
    PharmacyPriceHistory,
    PriceHistoryPoint,
    PriceHistoryResponse,
)

router = APIRouter()


@router.get("/price-history/{barcode}", response_model=PriceHistoryResponse)
def get_price_history(
    barcode: str,
    days: int = Query(30, ge=7, le=365),
    pharmacy: str | None = Query(None),
    db: Client = Depends(get_supabase_client),
):
    # Get product IDs for this barcode
    products_result = (
        db.table("products")
        .select("id, pharmacy_source, product_name")
        .eq("barcode", barcode)
        .execute()
    )

    if not products_result.data:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    product_ids = [p["id"] for p in products_result.data]
    product_name = products_result.data[0].get("product_name")

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Get price history for all matching products
    query = (
        db.table("price_history")
        .select("pharmacy_source, current_price, recorded_at")
        .in_("product_id", product_ids)
        .gte("recorded_at", since)
        .order("recorded_at", desc=False)
    )

    if pharmacy:
        query = query.eq("pharmacy_source", pharmacy)

    history_result = query.execute()

    # Group by pharmacy
    pharmacy_data: dict[str, list[PriceHistoryPoint]] = {}
    for record in history_result.data or []:
        source = record["pharmacy_source"]
        if source not in pharmacy_data:
            pharmacy_data[source] = []
        pharmacy_data[source].append(
            PriceHistoryPoint(
                date=record["recorded_at"][:10],
                price=record.get("current_price"),
            )
        )

    history = [
        PharmacyPriceHistory(pharmacy_source=source, data_points=points)
        for source, points in pharmacy_data.items()
    ]

    return PriceHistoryResponse(
        barcode=barcode,
        product_name=product_name,
        history=history,
    )
