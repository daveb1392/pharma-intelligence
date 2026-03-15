import {
  ArrowRight,
  BadgePercent,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Pill,
  Search,
  ShieldCheck,
  Store,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { SearchBar } from "@/components/layout/SearchBar";
import {
  browseProducts,
  getBankDeals,
  getBrands,
  getCategories,
  getHomeStats,
  getTopDiscounts,
} from "@/lib/api";
import type { ProductFilters } from "@/lib/api";
import { getCategoryMeta } from "@/lib/category-meta";
import {
  formatPrice,
  getPharmacy,
  getProductImage,
  PHARMACIES,
} from "@/lib/constants";

interface Props {
  searchParams: Promise<{
    page?: string;
    pharmacy?: string;
    category?: string;
    sort?: string;
    brand?: string;
    prescription?: string;
    min_price?: string;
    max_price?: string;
    discount?: string;
    bank_deal?: string;
  }>;
}

export default async function HomePage({ searchParams }: Props) {
  const sp = await searchParams;
  const page = parseInt(sp.page || "1", 10);
  const pharmacy = sp.pharmacy;
  const category = sp.category;
  const sort = sp.sort || "price_asc";
  const brand = sp.brand;
  const prescription = sp.prescription;
  const minPrice = sp.min_price;
  const maxPrice = sp.max_price;
  const discount = sp.discount;
  const bankDeal = sp.bank_deal;

  const filters: ProductFilters = {
    brand,
    prescription,
    min_price: minPrice,
    max_price: maxPrice,
    discount,
    bank_deal: bankDeal,
  };
  const hasFilters = !!(brand || prescription || minPrice || maxPrice || discount || bankDeal);

  const isFiltered = !!(pharmacy || category || sort !== "price_asc" || page > 1 || hasFilters);

  const [stats, categories, topDiscounts, bankDeals, data, brands] = await Promise.all([
    getHomeStats().catch(() => null),
    getCategories().catch(() => []),
    !isFiltered ? getTopDiscounts(12).catch(() => []) : Promise.resolve([]),
    !isFiltered ? getBankDeals(8).catch(() => []) : Promise.resolve([]),
    browseProducts(page, 24, pharmacy, category, sort, filters).catch(() => null),
    getBrands(category, pharmacy, 30).catch(() => []),
  ]);

  const totalPages = data ? Math.ceil(data.total / data.limit) : 0;

  function buildUrl(overrides: Record<string, string | undefined>) {
    const p = new URLSearchParams();
    const s = overrides.sort ?? sort;
    const ph = "pharmacy" in overrides ? overrides.pharmacy : pharmacy;
    const cat = "category" in overrides ? overrides.category : category;
    const pg = overrides.page ?? String(page);
    const br = "brand" in overrides ? overrides.brand : brand;
    const pr = "prescription" in overrides ? overrides.prescription : prescription;
    const mp = "min_price" in overrides ? overrides.min_price : minPrice;
    const xp = "max_price" in overrides ? overrides.max_price : maxPrice;
    const dc = "discount" in overrides ? overrides.discount : discount;
    const bd = "bank_deal" in overrides ? overrides.bank_deal : bankDeal;
    if (s && s !== "price_asc") p.set("sort", s);
    if (ph) p.set("pharmacy", ph);
    if (cat) p.set("category", cat);
    if (pg !== "1") p.set("page", pg);
    if (br) p.set("brand", br);
    if (pr) p.set("prescription", pr);
    if (mp) p.set("min_price", mp);
    if (xp) p.set("max_price", xp);
    if (dc) p.set("discount", dc);
    if (bd) p.set("bank_deal", bd);
    const qs = p.toString();
    return `/${qs ? `?${qs}` : ""}`;
  }

  return (
    <div>
      {/* Hero section */}
      {!isFiltered && (
        <div className="bg-gradient-to-br from-emerald-600 via-emerald-500 to-teal-500 text-white">
          <div className="container mx-auto px-4 py-12 md:py-16">
            <div className="max-w-2xl mx-auto text-center">
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">
                Compará precios de medicamentos
              </h1>
              <p className="text-emerald-100 text-lg mb-6">
                Encontrá el mejor precio en{" "}
                {stats
                  ? `${stats.total_products.toLocaleString("es-PY")} productos de ${stats.pharmacy_count} farmacias`
                  : "farmacias de Paraguay"}
              </p>
              <div className="max-w-xl mx-auto">
                <SearchBar size="large" />
              </div>
            </div>

            {/* Stats bar */}
            {stats && (
              <div className="flex items-center justify-center gap-6 md:gap-10 mt-8 text-sm">
                <div className="flex items-center gap-2">
                  <Pill className="h-4 w-4 text-emerald-200" />
                  <span className="text-emerald-100">
                    <strong className="text-white">
                      {stats.total_products.toLocaleString("es-PY")}
                    </strong>{" "}
                    productos
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Store className="h-4 w-4 text-emerald-200" />
                  <span className="text-emerald-100">
                    <strong className="text-white">
                      {stats.pharmacy_count}
                    </strong>{" "}
                    farmacias
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-200" />
                  <span className="text-emerald-100">
                    Actualizado <strong className="text-white">hoy</strong>
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="container mx-auto px-4">
        {/* Top Discounts Section - only on landing */}
        {!isFiltered && topDiscounts.length > 0 && (
          <section className="py-8 border-b">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-red-100">
                  <BadgePercent className="h-5 w-5 text-red-600" />
                </div>
                <h2 className="text-xl font-bold">Mejores Descuentos</h2>
              </div>
              <Link
                href="/ofertas"
                className="text-sm text-emerald-600 hover:text-emerald-700 font-medium flex items-center gap-1"
              >
                Ver todos <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {topDiscounts.map((product) => {
                const ph = getPharmacy(product.pharmacy_source);
                const img = getProductImage(product.image_url);
                const href = product.barcode
                  ? `/producto/${product.barcode}`
                  : "#";
                return (
                  <Link key={product.id} href={href}>
                    <Card className="group overflow-hidden hover:shadow-lg transition-all duration-200 h-full flex flex-col border-0 shadow-sm">
                      <div className="relative bg-gray-50 aspect-square flex items-center justify-center p-3">
                        {img ? (
                          <img
                            src={img}
                            alt={product.product_name || ""}
                            className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                          />
                        ) : (
                          <Pill className="h-10 w-10 text-muted-foreground/15" />
                        )}
                        {product.discount_percentage != null &&
                          product.discount_percentage > 0 && (
                            <span className="absolute top-1.5 left-1.5 bg-red-500 text-white text-[11px] font-bold px-1.5 py-0.5 rounded-md">
                              -{Math.round(product.discount_percentage)}%
                            </span>
                          )}
                        <span
                          className="absolute bottom-1.5 right-1.5 text-white text-[9px] font-medium px-1.5 py-0.5 rounded-md"
                          style={{ backgroundColor: ph.color }}
                        >
                          {ph.shortName}
                        </span>
                      </div>
                      <div className="p-2.5 flex flex-col flex-1">
                        <h3 className="text-[11px] font-medium leading-tight line-clamp-2 mb-1">
                          {product.product_name}
                        </h3>
                        <div className="mt-auto flex items-baseline gap-1.5">
                          <span className="text-sm font-bold text-emerald-600">
                            {formatPrice(product.current_price)}
                          </span>
                          {product.original_price != null &&
                            product.original_price >
                              (product.current_price || 0) && (
                              <span className="text-[10px] text-muted-foreground line-through">
                                {formatPrice(product.original_price)}
                              </span>
                            )}
                        </div>
                      </div>
                    </Card>
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* Bank Deals Section - only on landing */}
        {!isFiltered && bankDeals.length > 0 && (
          <section className="py-8 border-b">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-100">
                  <CreditCard className="h-5 w-5 text-blue-600" />
                </div>
                <h2 className="text-xl font-bold">Ofertas con Tarjeta</h2>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {bankDeals.map((product) => {
                const ph = getPharmacy(product.pharmacy_source);
                const img = getProductImage(product.image_url);
                const href = product.barcode
                  ? `/producto/${product.barcode}`
                  : "#";
                return (
                  <Link key={product.id} href={href}>
                    <Card className="group overflow-hidden hover:shadow-lg transition-all duration-200 h-full flex flex-col border-0 shadow-sm">
                      <div className="relative bg-gradient-to-b from-blue-50 to-white aspect-square flex items-center justify-center p-3">
                        {img ? (
                          <img
                            src={img}
                            alt={product.product_name || ""}
                            className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                          />
                        ) : (
                          <Pill className="h-10 w-10 text-muted-foreground/15" />
                        )}
                        <span
                          className="absolute bottom-1.5 right-1.5 text-white text-[9px] font-medium px-1.5 py-0.5 rounded-md"
                          style={{ backgroundColor: ph.color }}
                        >
                          {ph.shortName}
                        </span>
                      </div>
                      <div className="p-3 flex flex-col flex-1">
                        <h3 className="text-xs font-medium leading-tight line-clamp-2 mb-2">
                          {product.product_name}
                        </h3>
                        <div className="mt-auto">
                          {product.current_price != null && (
                            <span className="text-xs text-muted-foreground line-through">
                              {formatPrice(product.current_price)}
                            </span>
                          )}
                          <div className="flex items-center gap-1.5">
                            <Badge className="bg-blue-600 text-white text-xs hover:bg-blue-600">
                              {formatPrice(product.bank_discount_price)}
                            </Badge>
                            <span className="text-[10px] text-blue-600 font-medium">
                              c/tarjeta
                            </span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* Category Quick Links - only on landing */}
        {!isFiltered && categories.length > 0 && (
          <section className="py-8 border-b">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold">Categorías</h2>
              <Link
                href="/categorias"
                className="text-sm text-emerald-600 hover:text-emerald-700 font-medium flex items-center gap-1"
              >
                Ver todas <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="flex flex-wrap gap-2">
              {categories.slice(0, 20).map((cat) => {
                const meta = getCategoryMeta(cat.main_category);
                const CatIcon = meta.icon;
                return (
                  <Link
                    key={cat.main_category}
                    href={buildUrl({
                      category: cat.main_category,
                      page: "1",
                    })}
                    className="flex items-center gap-2 px-4 py-2 rounded-full border bg-white text-sm font-medium text-gray-700 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 transition-colors"
                  >
                    <CatIcon className="h-3.5 w-3.5 opacity-60" />
                    {cat.main_category}
                    <span className="text-xs text-muted-foreground">
                      {cat.product_count.toLocaleString("es-PY")}
                    </span>
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* Browse Products Section */}
        <section className="py-8">
          <div className="flex gap-6">
            {/* Sidebar */}
            <aside className="hidden lg:block w-56 shrink-0">
              <div className="sticky top-20">
                {/* Categories */}
                <div className="mb-6">
                  <h3 className="font-semibold text-sm mb-3 text-gray-500 uppercase tracking-wider">
                    Categorías
                  </h3>
                  <div className="space-y-0.5">
                    <Link
                      href={buildUrl({ category: undefined, page: "1" })}
                      className={`block text-sm px-3 py-2 rounded-lg transition-colors ${
                        !category
                          ? "bg-emerald-50 text-emerald-700 font-medium"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      Todos los productos
                    </Link>
                    {categories.map((cat) => {
                      const meta = getCategoryMeta(cat.main_category);
                      const CatIcon = meta.icon;
                      return (
                        <Link
                          key={cat.main_category}
                          href={buildUrl({
                            category:
                              category === cat.main_category
                                ? undefined
                                : cat.main_category,
                            page: "1",
                          })}
                          className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors ${
                            category === cat.main_category
                              ? "bg-emerald-50 text-emerald-700 font-medium"
                              : "text-muted-foreground hover:bg-muted"
                          }`}
                        >
                          <CatIcon className="h-3.5 w-3.5 shrink-0 opacity-60" />
                          <span className="truncate flex-1">
                            {cat.main_category}
                          </span>
                          <span className="text-[10px] text-muted-foreground/60 shrink-0">
                            {cat.product_count.toLocaleString("es-PY")}
                          </span>
                        </Link>
                      );
                    })}
                  </div>
                </div>

                {/* Pharmacies */}
                <div className="mb-6">
                  <h3 className="font-semibold text-sm mb-3 text-gray-500 uppercase tracking-wider">
                    Farmacias
                  </h3>
                  <div className="space-y-0.5">
                    <Link
                      href={buildUrl({ pharmacy: undefined, page: "1" })}
                      className={`block text-sm px-3 py-2 rounded-lg transition-colors ${
                        !pharmacy
                          ? "bg-emerald-50 text-emerald-700 font-medium"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      Todas
                    </Link>
                    {Object.entries(PHARMACIES).map(([key, ph]) => (
                      <Link
                        key={key}
                        href={buildUrl({
                          pharmacy: pharmacy === key ? undefined : key,
                          page: "1",
                        })}
                        className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors ${
                          pharmacy === key
                            ? "bg-emerald-50 text-emerald-700 font-medium"
                            : "text-muted-foreground hover:bg-muted"
                        }`}
                      >
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: ph.color }}
                        />
                        {ph.displayName}
                      </Link>
                    ))}
                  </div>
                </div>

                {/* Quick Filters */}
                <div className="mb-6">
                  <h3 className="font-semibold text-sm mb-3 text-gray-500 uppercase tracking-wider">
                    Filtros rápidos
                  </h3>
                  <div className="space-y-0.5">
                    <Link
                      href={buildUrl({
                        discount: discount === "true" ? undefined : "true",
                        page: "1",
                      })}
                      className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors ${
                        discount === "true"
                          ? "bg-red-50 text-red-700 font-medium"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      <BadgePercent className="h-3.5 w-3.5 shrink-0" />
                      Con descuento
                    </Link>
                    <Link
                      href={buildUrl({
                        bank_deal: bankDeal === "true" ? undefined : "true",
                        page: "1",
                      })}
                      className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors ${
                        bankDeal === "true"
                          ? "bg-blue-50 text-blue-700 font-medium"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      <CreditCard className="h-3.5 w-3.5 shrink-0" />
                      Con tarjeta bancaria
                    </Link>
                  </div>
                </div>

                {/* Prescription Filter */}
                <div className="mb-6">
                  <h3 className="font-semibold text-sm mb-3 text-gray-500 uppercase tracking-wider">
                    Receta
                  </h3>
                  <div className="space-y-0.5">
                    <Link
                      href={buildUrl({ prescription: undefined, page: "1" })}
                      className={`block text-sm px-3 py-2 rounded-lg transition-colors ${
                        !prescription
                          ? "bg-emerald-50 text-emerald-700 font-medium"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      Todos
                    </Link>
                    <Link
                      href={buildUrl({
                        prescription: prescription === "false" ? undefined : "false",
                        page: "1",
                      })}
                      className={`block text-sm px-3 py-2 rounded-lg transition-colors ${
                        prescription === "false"
                          ? "bg-emerald-50 text-emerald-700 font-medium"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      Sin receta
                    </Link>
                    <Link
                      href={buildUrl({
                        prescription: prescription === "true" ? undefined : "true",
                        page: "1",
                      })}
                      className={`block text-sm px-3 py-2 rounded-lg transition-colors ${
                        prescription === "true"
                          ? "bg-emerald-50 text-emerald-700 font-medium"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      Con receta
                    </Link>
                  </div>
                </div>

                {/* Price Range */}
                <div className="mb-6">
                  <h3 className="font-semibold text-sm mb-3 text-gray-500 uppercase tracking-wider">
                    Precio
                  </h3>
                  <div className="space-y-0.5">
                    {[
                      { label: "Todos", min: undefined, max: undefined },
                      { label: "Hasta ₲50.000", min: undefined, max: "50000" },
                      { label: "₲50.000 - ₲100.000", min: "50000", max: "100000" },
                      { label: "₲100.000 - ₲500.000", min: "100000", max: "500000" },
                      { label: "Más de ₲500.000", min: "500000", max: undefined },
                    ].map((range) => {
                      const isActive = minPrice === range.min && maxPrice === range.max;
                      return (
                        <Link
                          key={range.label}
                          href={buildUrl({
                            min_price: isActive ? undefined : range.min,
                            max_price: isActive ? undefined : range.max,
                            page: "1",
                          })}
                          className={`block text-sm px-3 py-2 rounded-lg transition-colors ${
                            isActive
                              ? "bg-emerald-50 text-emerald-700 font-medium"
                              : "text-muted-foreground hover:bg-muted"
                          }`}
                        >
                          {range.label}
                        </Link>
                      );
                    })}
                  </div>
                </div>

                {/* Brands */}
                {brands.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-semibold text-sm mb-3 text-gray-500 uppercase tracking-wider">
                      Marca / Lab
                    </h3>
                    <div className="space-y-0.5 max-h-48 overflow-y-auto">
                      {brand && (
                        <Link
                          href={buildUrl({ brand: undefined, page: "1" })}
                          className="block text-sm px-3 py-2 rounded-lg bg-emerald-50 text-emerald-700 font-medium transition-colors"
                        >
                          ✕ {brand}
                        </Link>
                      )}
                      {brands
                        .filter((b) => b.brand !== brand)
                        .map((b) => (
                          <Link
                            key={b.brand}
                            href={buildUrl({ brand: b.brand, page: "1" })}
                            className="flex items-center justify-between text-sm px-3 py-2 rounded-lg text-muted-foreground hover:bg-muted transition-colors"
                          >
                            <span className="truncate">{b.brand}</span>
                            <span className="text-[10px] text-muted-foreground/60 shrink-0 ml-2">
                              {b.count}
                            </span>
                          </Link>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            </aside>

            {/* Main content */}
            <div className="flex-1 min-w-0">
              {/* Active filters / title */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold">
                    {category || "Todos los productos"}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {data
                      ? `${data.total.toLocaleString("es-PY")} productos`
                      : "Cargando..."}
                    {pharmacy && (
                      <span>
                        {" "}
                        en{" "}
                        <strong className="text-foreground">
                          {getPharmacy(pharmacy).displayName}
                        </strong>
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex gap-1">
                  {[
                    { value: "price_asc", label: "Menor precio" },
                    { value: "price_desc", label: "Mayor precio" },
                    { value: "discount", label: "Descuento" },
                  ].map((opt) => (
                    <Link
                      key={opt.value}
                      href={buildUrl({ sort: opt.value, page: "1" })}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        sort === opt.value
                          ? "bg-emerald-600 text-white shadow-sm"
                          : "bg-muted text-muted-foreground hover:bg-muted/80"
                      }`}
                    >
                      {opt.label}
                    </Link>
                  ))}
                </div>
              </div>

              {/* Active filter tags */}
              {hasFilters && (
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {brand && (
                    <Link
                      href={buildUrl({ brand: undefined, page: "1" })}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 hover:bg-emerald-200 transition-colors"
                    >
                      Marca: {brand} ✕
                    </Link>
                  )}
                  {prescription === "true" && (
                    <Link
                      href={buildUrl({ prescription: undefined, page: "1" })}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800 hover:bg-orange-200 transition-colors"
                    >
                      Con receta ✕
                    </Link>
                  )}
                  {prescription === "false" && (
                    <Link
                      href={buildUrl({ prescription: undefined, page: "1" })}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 hover:bg-green-200 transition-colors"
                    >
                      Sin receta ✕
                    </Link>
                  )}
                  {(minPrice || maxPrice) && (
                    <Link
                      href={buildUrl({ min_price: undefined, max_price: undefined, page: "1" })}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 hover:bg-purple-200 transition-colors"
                    >
                      {minPrice && maxPrice
                        ? `₲${Number(minPrice).toLocaleString("es-PY")} - ₲${Number(maxPrice).toLocaleString("es-PY")}`
                        : minPrice
                          ? `Desde ₲${Number(minPrice).toLocaleString("es-PY")}`
                          : `Hasta ₲${Number(maxPrice).toLocaleString("es-PY")}`}{" "}
                      ✕
                    </Link>
                  )}
                  {discount === "true" && (
                    <Link
                      href={buildUrl({ discount: undefined, page: "1" })}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 hover:bg-red-200 transition-colors"
                    >
                      Con descuento ✕
                    </Link>
                  )}
                  {bankDeal === "true" && (
                    <Link
                      href={buildUrl({ bank_deal: undefined, page: "1" })}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 hover:bg-blue-200 transition-colors"
                    >
                      Con tarjeta ✕
                    </Link>
                  )}
                  <Link
                    href="/"
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                  >
                    Limpiar todo
                  </Link>
                </div>
              )}

              {/* Mobile filters */}
              <div className="lg:hidden mb-4 space-y-3">
                {/* Pharmacy pills */}
                <div className="flex gap-1.5 flex-wrap">
                  <Link
                    href={buildUrl({ pharmacy: undefined, page: "1" })}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                      !pharmacy
                        ? "bg-emerald-600 text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    Todas
                  </Link>
                  {Object.entries(PHARMACIES).map(([key, ph]) => (
                    <Link
                      key={key}
                      href={buildUrl({
                        pharmacy: pharmacy === key ? undefined : key,
                        page: "1",
                      })}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                        pharmacy === key
                          ? "text-white"
                          : "bg-muted text-muted-foreground"
                      }`}
                      style={
                        pharmacy === key ? { backgroundColor: ph.color } : {}
                      }
                    >
                      {ph.shortName}
                    </Link>
                  ))}
                </div>
                {/* Quick filter pills for mobile */}
                <div className="flex gap-1.5 flex-wrap">
                  <Link
                    href={buildUrl({
                      discount: discount === "true" ? undefined : "true",
                      page: "1",
                    })}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                      discount === "true"
                        ? "bg-red-500 text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    Con descuento
                  </Link>
                  <Link
                    href={buildUrl({
                      bank_deal: bankDeal === "true" ? undefined : "true",
                      page: "1",
                    })}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                      bankDeal === "true"
                        ? "bg-blue-500 text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    Con tarjeta
                  </Link>
                  <Link
                    href={buildUrl({
                      prescription: prescription === "false" ? undefined : "false",
                      page: "1",
                    })}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                      prescription === "false"
                        ? "bg-green-500 text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    Sin receta
                  </Link>
                </div>
              </div>

              {/* Product grid */}
              {!data || data.results.length === 0 ? (
                <div className="text-center py-16">
                  <Search className="h-12 w-12 text-muted-foreground/20 mx-auto mb-3" />
                  <p className="text-muted-foreground">
                    No se encontraron productos
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3">
                  {data.results.map((product) => {
                    const ph = getPharmacy(product.pharmacy_source);
                    const img = getProductImage(product.image_url);
                    const href = product.barcode
                      ? `/producto/${product.barcode}`
                      : "#";

                    return (
                      <Link key={product.id} href={href}>
                        <Card className="group overflow-hidden hover:shadow-lg transition-all duration-200 h-full flex flex-col border-0 shadow-sm">
                          <div className="relative bg-gray-50 aspect-square flex items-center justify-center p-4">
                            {img ? (
                              <img
                                src={img}
                                alt={product.product_name || ""}
                                className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                              />
                            ) : (
                              <Pill className="h-12 w-12 text-muted-foreground/15" />
                            )}
                            {product.discount_percentage != null &&
                              product.discount_percentage > 0 &&
                              product.discount_percentage < 80 && (
                                <span className="absolute top-2 left-2 bg-red-500 text-white text-[11px] font-bold px-2 py-0.5 rounded-md shadow-sm">
                                  -{Math.round(product.discount_percentage)}%
                                </span>
                              )}
                            <span
                              className="absolute bottom-2 right-2 text-white text-[10px] font-medium px-2 py-0.5 rounded-md shadow-sm"
                              style={{ backgroundColor: ph.color }}
                            >
                              {ph.shortName}
                            </span>
                          </div>
                          <div className="p-3 flex flex-col flex-1">
                            <h3 className="text-xs font-medium leading-tight line-clamp-2 mb-1">
                              {product.product_name}
                            </h3>
                            {product.brand && (
                              <p className="text-[11px] text-muted-foreground mb-2 truncate">
                                {product.brand}
                              </p>
                            )}
                            <div className="mt-auto">
                              <span className="text-base font-bold text-emerald-600">
                                {formatPrice(product.current_price)}
                              </span>
                              {product.original_price != null &&
                                product.original_price >
                                  (product.current_price || 0) && (
                                  <span className="text-[11px] text-muted-foreground line-through ml-2">
                                    {formatPrice(product.original_price)}
                                  </span>
                                )}
                              {product.bank_discount_price != null && (
                                <div className="mt-1">
                                  <Badge
                                    variant="secondary"
                                    className="text-[10px] bg-blue-50 text-blue-700 border-blue-200"
                                  >
                                    {formatPrice(product.bank_discount_price)}{" "}
                                    c/tarjeta
                                  </Badge>
                                </div>
                              )}
                            </div>
                          </div>
                        </Card>
                      </Link>
                    );
                  })}
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-8 pb-4">
                  {page > 1 && (
                    <Link
                      href={buildUrl({ page: String(page - 1) })}
                      className="flex items-center gap-1 px-4 py-2 rounded-lg bg-muted text-sm font-medium hover:bg-muted/80 transition-colors"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Anterior
                    </Link>
                  )}
                  <div className="flex items-center gap-1">
                    {Array.from(
                      { length: Math.min(5, totalPages) },
                      (_, i) => {
                        let pageNum: number;
                        if (totalPages <= 5) {
                          pageNum = i + 1;
                        } else if (page <= 3) {
                          pageNum = i + 1;
                        } else if (page >= totalPages - 2) {
                          pageNum = totalPages - 4 + i;
                        } else {
                          pageNum = page - 2 + i;
                        }
                        return (
                          <Link
                            key={pageNum}
                            href={buildUrl({ page: String(pageNum) })}
                            className={`w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors ${
                              page === pageNum
                                ? "bg-emerald-600 text-white shadow-sm"
                                : "bg-muted text-muted-foreground hover:bg-muted/80"
                            }`}
                          >
                            {pageNum}
                          </Link>
                        );
                      },
                    )}
                  </div>
                  {page < totalPages && (
                    <Link
                      href={buildUrl({ page: String(page + 1) })}
                      className="flex items-center gap-1 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 transition-colors shadow-sm"
                    >
                      Siguiente
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
