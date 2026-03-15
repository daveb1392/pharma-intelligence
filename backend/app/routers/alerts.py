from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.dependencies import get_current_user, get_supabase_client
from app.schemas.auth import AlertRequest, AlertResponse

router = APIRouter()


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client),
):
    result = (
        db.table("user_alerts")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .execute()
    )

    return [AlertResponse(**item) for item in result.data or []]


@router.post("/alerts", response_model=AlertResponse, status_code=201)
def create_alert(
    body: AlertRequest,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client),
):
    result = (
        db.table("user_alerts")
        .upsert(
            {
                "user_id": user["user_id"],
                "barcode": body.barcode,
                "product_name": body.product_name,
                "target_price": body.target_price,
                "alert_type": body.alert_type,
                "is_active": True,
            },
            on_conflict="user_id,barcode",
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=400, detail="Error al crear alerta")

    return AlertResponse(**result.data[0])


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    body: AlertRequest,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client),
):
    result = (
        db.table("user_alerts")
        .update(
            {
                "target_price": body.target_price,
                "alert_type": body.alert_type,
            }
        )
        .eq("id", alert_id)
        .eq("user_id", user["user_id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    return AlertResponse(**result.data[0])


@router.delete("/alerts/{alert_id}", status_code=204)
def delete_alert(
    alert_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client),
):
    db.table("user_alerts").delete().eq("id", alert_id).eq(
        "user_id", user["user_id"]
    ).execute()


@router.patch("/alerts/{alert_id}/toggle")
def toggle_alert(
    alert_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_client),
):
    # Get current state
    current = (
        db.table("user_alerts")
        .select("is_active")
        .eq("id", alert_id)
        .eq("user_id", user["user_id"])
        .execute()
    )

    if not current.data:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    new_state = not current.data[0]["is_active"]

    result = (
        db.table("user_alerts")
        .update({"is_active": new_state})
        .eq("id", alert_id)
        .eq("user_id", user["user_id"])
        .execute()
    )

    return {"is_active": new_state}
