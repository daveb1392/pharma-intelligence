import { Pill } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { getCategories } from "@/lib/api";
import { getCategoryMeta } from "@/lib/category-meta";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Categorias - PrecioFarma",
  description: "Explorá categorías de productos farmacéuticos en Paraguay",
};

export default async function CategoriesPage() {
  let categories;
  try {
    categories = await getCategories();
  } catch {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <p className="text-muted-foreground">Error al cargar categorías</p>
      </div>
    );
  }

  const totalProducts = categories.reduce(
    (acc, cat) => acc + cat.product_count,
    0,
  );

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Categorías</h1>
        <p className="text-muted-foreground mt-1">
          {totalProducts.toLocaleString("es-PY")} productos en{" "}
          {categories.length} categorías
        </p>
      </div>

      {/* Top categories - larger cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {categories.slice(0, 6).map((cat) => {
          const meta = getCategoryMeta(cat.main_category);
          const Icon = meta.icon;
          return (
            <Link
              key={cat.main_category}
              href={`/categorias/${encodeURIComponent(cat.main_category)}`}
            >
              <div className="group relative overflow-hidden rounded-2xl p-6 h-40 flex flex-col justify-between transition-all duration-300 hover:scale-[1.02] hover:shadow-xl">
                <div
                  className={`absolute inset-0 bg-gradient-to-br ${meta.gradient} opacity-90 group-hover:opacity-100 transition-opacity`}
                />
                <Icon className="absolute -right-4 -bottom-4 h-32 w-32 text-white/10" />
                <div className="relative z-10">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-white/20 backdrop-blur-sm">
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-white">
                      {cat.main_category}
                    </h3>
                  </div>
                </div>
                <div className="relative z-10 flex items-center justify-between">
                  <span className="text-sm text-white/80">
                    {cat.product_count.toLocaleString("es-PY")} productos
                  </span>
                  {cat.pharmacy_count != null && (
                    <span className="text-xs text-white/60 bg-white/10 px-2 py-0.5 rounded-full">
                      {cat.pharmacy_count} farmacias
                    </span>
                  )}
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Rest of categories - compact cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {categories.slice(6).map((cat) => {
          const meta = getCategoryMeta(cat.main_category);
          const Icon = meta.icon;
          return (
            <Link
              key={cat.main_category}
              href={`/categorias/${encodeURIComponent(cat.main_category)}`}
            >
              <div
                className={`group flex items-center gap-3 p-4 rounded-xl border ${meta.accent} hover:shadow-md transition-all duration-200 hover:scale-[1.01]`}
              >
                <div
                  className={`p-2 rounded-lg bg-gradient-to-br ${meta.gradient} shrink-0`}
                >
                  <Icon className="h-4 w-4 text-white" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-medium truncate">
                    {cat.main_category}
                  </h3>
                  <p className="text-xs opacity-70">
                    {cat.product_count.toLocaleString("es-PY")} productos
                  </p>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
