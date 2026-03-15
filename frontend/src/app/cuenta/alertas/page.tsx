"use client";

import { Bell, Pill, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice } from "@/lib/constants";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Alert {
  id: string;
  barcode: string;
  product_name?: string;
  target_price?: number;
  alert_type: string;
  is_active: boolean;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }

    fetch(`${API_BASE}/api/alerts`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then(setAlerts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function toggleAlert(id: string) {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const res = await fetch(`${API_BASE}/api/alerts/${id}/toggle`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
    });

    if (res.ok) {
      const data = await res.json();
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === id ? { ...a, is_active: data.is_active } : a,
        ),
      );
    }
  }

  async function deleteAlert(id: string) {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    await fetch(`${API_BASE}/api/alerts/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });

    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-6 max-w-lg space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-lg">
      <h1 className="text-2xl font-bold mb-6">Mis Alertas</h1>

      {alerts.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-blue-50 mx-auto mb-4 flex items-center justify-center">
            <Bell className="h-10 w-10 text-blue-300" />
          </div>
          <p className="text-muted-foreground mb-2">
            No tenés alertas configuradas
          </p>
          <Link
            href="/"
            className="text-emerald-600 hover:underline text-sm"
          >
            Buscar productos para monitorear
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <Card
              key={alert.id}
              className={`p-4 transition-all ${
                !alert.is_active ? "opacity-60" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <Link
                  href={`/producto/${alert.barcode}`}
                  className="flex-1 min-w-0"
                >
                  <h3 className="font-medium text-sm leading-tight">
                    {alert.product_name || alert.barcode}
                  </h3>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge
                      variant={alert.is_active ? "default" : "secondary"}
                      className={`text-xs ${
                        alert.is_active
                          ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-100"
                          : ""
                      }`}
                    >
                      {alert.is_active ? "Activa" : "Pausada"}
                    </Badge>
                    {alert.target_price != null && (
                      <span className="text-xs text-muted-foreground">
                        Meta: {formatPrice(alert.target_price)}
                      </span>
                    )}
                  </div>
                </Link>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs h-8"
                    onClick={() => toggleAlert(alert.id)}
                  >
                    {alert.is_active ? "Pausar" : "Activar"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 hover:bg-red-50"
                    onClick={() => deleteAlert(alert.id)}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
