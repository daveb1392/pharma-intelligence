"use client";

import { Heart, Pill, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Favorite {
  id: string;
  barcode: string;
  product_name?: string;
  brand?: string;
  image_url?: string;
}

export default function FavoritesPage() {
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }

    fetch(`${API_BASE}/api/favorites`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then(setFavorites)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function removeFavorite(id: string) {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    await fetch(`${API_BASE}/api/favorites/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });

    setFavorites((prev) => prev.filter((f) => f.id !== id));
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-6 max-w-2xl space-y-3">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 gap-3">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Mis Favoritos</h1>

      {favorites.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-red-50 mx-auto mb-4 flex items-center justify-center">
            <Heart className="h-10 w-10 text-red-300" />
          </div>
          <p className="text-muted-foreground mb-2">
            No tenés productos guardados
          </p>
          <Link
            href="/"
            className="text-emerald-600 hover:underline text-sm"
          >
            Buscar productos para guardar
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {favorites.map((fav) => (
            <Card
              key={fav.id}
              className="group overflow-hidden hover:shadow-lg transition-all duration-200 relative"
            >
              <Link href={`/producto/${fav.barcode}`}>
                <div className="bg-gray-50 aspect-square flex items-center justify-center p-3">
                  {fav.image_url ? (
                    <img
                      src={fav.image_url}
                      alt={fav.product_name || ""}
                      className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                    />
                  ) : (
                    <Pill className="h-12 w-12 text-muted-foreground/30" />
                  )}
                </div>
                <div className="p-3">
                  <h3 className="text-xs font-medium leading-tight line-clamp-2">
                    {fav.product_name || fav.barcode}
                  </h3>
                  {fav.brand && (
                    <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
                      {fav.brand}
                    </p>
                  )}
                </div>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                className="absolute top-1 right-1 h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity bg-white/80 hover:bg-red-50"
                onClick={() => removeFavorite(fav.id)}
              >
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
