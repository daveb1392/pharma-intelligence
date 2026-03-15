from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.dependencies import get_supabase_client
from app.schemas.product import SearchResponse, SearchResultItem

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
def search_products(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    pharmacy: str | None = Query(None, description="Filtrar por farmacia"),
    category: str | None = Query(None, description="Filtrar por categoría"),
    db: Client = Depends(get_supabase_client),
):
    offset = (page - 1) * limit

    result = db.rpc(
        "search_products",
        {
            "search_query": q,
            "p_limit": limit,
            "p_offset": offset,
            "p_pharmacy": pharmacy,
            "p_category": category,
        },
    ).execute()

    data = result.data if result.data else {"results": [], "total": 0}

    results = []
    for item in data.get("results", []) or []:
        results.append(SearchResultItem(**item))

    return SearchResponse(
        results=results,
        total=data.get("total", 0),
        page=page,
        limit=limit,
    )
