from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class UserResponse(BaseModel):
    user_id: str
    email: str


class FavoriteRequest(BaseModel):
    barcode: str
    product_name: str | None = None
    brand: str | None = None
    image_url: str | None = None


class FavoriteResponse(BaseModel):
    id: str
    barcode: str
    product_name: str | None = None
    brand: str | None = None
    image_url: str | None = None
    created_at: str | None = None


class AlertRequest(BaseModel):
    barcode: str
    product_name: str | None = None
    target_price: float | None = None
    alert_type: str = "price_drop"


class AlertResponse(BaseModel):
    id: str
    barcode: str
    product_name: str | None = None
    target_price: float | None = None
    alert_type: str
    is_active: bool = True
    created_at: str | None = None
