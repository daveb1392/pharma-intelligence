from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.dependencies import get_supabase_client
from app.schemas.product import ComparisonResponse, PharmacyPrice

router = APIRouter()


@router.get("/compare/{barcode}", response_model=ComparisonResponse)
def compare_prices(
    barcode: str,
    db: Client = Depends(get_supabase_client),
):
    result = (
        db.table("products")
        .select("*")
        .eq("barcode", barcode)
        .order("current_price", desc=False)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    pharmacies = []
    for p in result.data:
        pharmacies.append(
            PharmacyPrice(
                pharmacy_source=p["pharmacy_source"],
                site_code=p.get("site_code"),
                product_name=p.get("product_name"),
                current_price=p.get("current_price"),
                original_price=p.get("original_price"),
                discount_percentage=p.get("discount_percentage"),
                discount_amount=p.get("discount_amount"),
                bank_discount_price=p.get("bank_discount_price"),
                bank_discount_bank_name=p.get("bank_discount_bank_name"),
                bank_payment_offers=p.get("bank_payment_offers"),
                requires_prescription=p.get("requires_prescription"),
                product_url=p.get("product_url"),
                image_url=p.get("image_url"),
                scraped_at=p.get("scraped_at"),
            )
        )

    prices = [p.current_price for p in pharmacies if p.current_price is not None]
    best_price = min(prices) if prices else None
    highest_price = max(prices) if prices else None
    savings = (highest_price - best_price) if best_price and highest_price else None

    first = result.data[0]
    return ComparisonResponse(
        barcode=barcode,
        product_name=first.get("product_name"),
        brand=first.get("brand"),
        main_category=first.get("main_category"),
        image_url=first.get("image_url"),
        best_price=best_price,
        highest_price=highest_price,
        savings=savings,
        pharmacies=pharmacies,
    )
