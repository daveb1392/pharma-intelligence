"use client";

import { Heart, Home, Search, Tag, User } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", icon: Home, label: "Inicio" },
  { href: "/buscar", icon: Search, label: "Buscar" },
  { href: "/ofertas", icon: Tag, label: "Ofertas", accent: true },
  { href: "/cuenta/favoritos", icon: Heart, label: "Favoritos" },
  { href: "/cuenta", icon: User, label: "Cuenta" },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t bg-background md:hidden">
      <div className="flex items-center justify-around h-16 px-2">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center justify-center gap-0.5 w-16 h-12 rounded-lg transition-colors ${
                isActive
                  ? "text-emerald-600"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <item.icon className={`h-5 w-5 ${isActive && item.accent ? "text-red-500" : ""}`} />
              <span className={`text-[10px] font-medium ${isActive && item.accent ? "text-red-500" : ""}`}>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
