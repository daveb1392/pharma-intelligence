"use client";

import {
  Bell,
  ChevronRight,
  Heart,
  LogOut,
  Settings,
  User,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UserInfo {
  email: string;
  user_id: string;
}

export default function AccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [favCount, setFavCount] = useState(0);
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    // Fetch user info
    fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => data && setUser(data))
      .catch(() => {});

    // Fetch counts
    fetch(`${API_BASE}/api/favorites`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setFavCount(Array.isArray(data) ? data.length : 0))
      .catch(() => {});

    fetch(`${API_BASE}/api/alerts`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setAlertCount(Array.isArray(data) ? data.length : 0))
      .catch(() => {});
  }, []);

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    router.push("/");
  }

  const initials = user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "??";

  return (
    <div className="container mx-auto px-4 py-6 max-w-lg">
      {/* Profile header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
          {user ? (
            <span className="text-xl font-bold text-emerald-700">
              {initials}
            </span>
          ) : (
            <User className="h-7 w-7 text-emerald-600" />
          )}
        </div>
        <div>
          <h1 className="text-xl font-bold">
            {user ? "Mi Cuenta" : "Iniciá sesión"}
          </h1>
          {user && (
            <p className="text-sm text-muted-foreground">{user.email}</p>
          )}
          {!user && (
            <p className="text-sm text-muted-foreground">
              <Link href="/auth/login" className="text-emerald-600 hover:underline">
                Iniciar sesión
              </Link>
              {" o "}
              <Link href="/auth/registro" className="text-emerald-600 hover:underline">
                crear cuenta
              </Link>
            </p>
          )}
        </div>
      </div>

      {/* Quick stats */}
      {user && (
        <div className="grid grid-cols-2 gap-3 mb-6">
          <Card className="p-4 text-center">
            <Heart className="h-5 w-5 text-red-500 mx-auto mb-1" />
            <span className="text-2xl font-bold">{favCount}</span>
            <p className="text-xs text-muted-foreground">Favoritos</p>
          </Card>
          <Card className="p-4 text-center">
            <Bell className="h-5 w-5 text-blue-500 mx-auto mb-1" />
            <span className="text-2xl font-bold">{alertCount}</span>
            <p className="text-xs text-muted-foreground">Alertas</p>
          </Card>
        </div>
      )}

      {/* Navigation */}
      <div className="space-y-2">
        <Link href="/cuenta/favoritos">
          <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center">
                  <Heart className="h-5 w-5 text-red-500" />
                </div>
                <div>
                  <h3 className="font-medium text-sm">Mis Favoritos</h3>
                  <p className="text-xs text-muted-foreground">
                    Productos guardados para comparar
                  </p>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </Card>
        </Link>

        <Link href="/cuenta/alertas">
          <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
                  <Bell className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <h3 className="font-medium text-sm">Mis Alertas</h3>
                  <p className="text-xs text-muted-foreground">
                    Notificaciones de baja de precios
                  </p>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </Card>
        </Link>
      </div>

      {user && (
        <Button
          variant="outline"
          className="w-full mt-8"
          onClick={handleLogout}
        >
          <LogOut className="h-4 w-4 mr-2" />
          Cerrar Sesión
        </Button>
      )}
    </div>
  );
}
