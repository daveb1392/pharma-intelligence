from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import alerts, auth, categories, comparison, favorites, home, ofertas, price_history, search

app = FastAPI(
    title="PrecioFarma API",
    description="API de comparación de precios de farmacias en Paraguay",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api", tags=["Búsqueda"])
app.include_router(comparison.router, prefix="/api", tags=["Comparación"])
app.include_router(price_history.router, prefix="/api", tags=["Historial de Precios"])
app.include_router(categories.router, prefix="/api", tags=["Categorías"])
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(favorites.router, prefix="/api", tags=["Favoritos"])
app.include_router(alerts.router, prefix="/api", tags=["Alertas"])
app.include_router(home.router, prefix="/api", tags=["Home"])
app.include_router(ofertas.router, prefix="/api", tags=["Ofertas"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "preciofarma-api"}
