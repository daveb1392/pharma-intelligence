from datetime import datetime

from pydantic import BaseModel


class PharmacyPrice(BaseModel):
    pharmacy_source: str
    site_code: str | None = None
    product_name: str | None = None
    current_price: float | None = None
    original_price: float | None = None
    discount_percentage: float | None = None
    discount_amount: float | None = None
    bank_discount_price: float | None = None
    bank_discount_bank_name: str | None = None
    bank_payment_offers: str | None = None
    requires_prescription: bool | None = None
    product_url: str | None = None
    image_url: str | None = None
    scraped_at: datetime | None = None


class ComparisonResponse(BaseModel):
    barcode: str
    product_name: str | None = None
    brand: str | None = None
    main_category: str | None = None
    image_url: str | None = None
    best_price: float | None = None
    highest_price: float | None = None
    savings: float | None = None
    pharmacies: list[PharmacyPrice] = []


class SearchResultItem(BaseModel):
    group_key: str | None = None
    barcode: str | None = None
    product_name: str | None = None
    brand: str | None = None
    image_url: str | None = None
    main_category: str | None = None
    requires_prescription: bool | None = None
    best_price: float | None = None
    pharmacy_count: int | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultItem] = []
    total: int = 0
    page: int = 1
    limit: int = 20


class CategoryItem(BaseModel):
    main_category: str
    product_count: int
    pharmacy_count: int | None = None
    min_price: float | None = None
    max_price: float | None = None


class PriceHistoryPoint(BaseModel):
    date: str
    price: float | None = None


class PharmacyPriceHistory(BaseModel):
    pharmacy_source: str
    data_points: list[PriceHistoryPoint] = []


class PriceHistoryResponse(BaseModel):
    barcode: str
    product_name: str | None = None
    history: list[PharmacyPriceHistory] = []
