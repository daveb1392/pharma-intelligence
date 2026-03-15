import {
  BadgePercent,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Pill,
  Tag,
} from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { getOfertasProducts, getOfertasStats } from "@/lib/api";
import { formatPrice, getPharmacy, getProductImage, PHARMACIES } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Ofertas - PrecioFarma",
  description: "Las mejores ofertas y descuentos en medicamentos de Paraguay",
};

interface Props {
  searchParams: Promise<{
    page?: string;
    type?: string;
    min_discount?: string;
    pharmacy?: string;
    category?: string;
    sort?: string;
  }>;
}

export default async function OfertasPage({ searchParams }: Props) {
  const sp = await searchParams;
  const page = parseInt(sp.page || "1", 10);
  const offerType = sp.type || "all";
  const minDiscount = sp.min_discount ? parseInt(sp.min_discount, 10) : undefined;
  const pharmacy = sp.pharmacy;
  const category = sp.category;
  const sort = sp.sort || "discount";

  const [stats, data] = await Promise.all([
    getOfertasStats().catch(() => null),
    getOfertasProducts(page, 24, offerType, minDiscount, pharmacy, category, sort).catch(
      () => null,
    ),
  ]);

  const totalPages = data ? Math.ceil(data.total / data.limit) : 0;

  function buildUrl(overrides: Record<string, string | undefined>) {
    const p = new URLSearchParams();
    const t = overrides.type ?? offerType;
    const s = overrides.sort ?? sort;
    const ph = "pharmacy" in overrides ? overrides.pharmacy : pharmacy;
    const md = "min_discount" in overrides ? overrides.min_discount : sp.min_discount;
    const pg = overrides.page ?? String(page);
    if (t && t !== "all") p.set("type", t);
    if (s && s !== "discount") p.set("sort", s);
    if (ph) p.set("pharmacy", ph);
    if (md) p.set("min_discount", md);
    if (pg !== "1") p.set("page", pg);
    const qs = p.toString();
    return `/ofertas${qs ? `?${qs}` : ""}`;
  }

  return (
    <div>
      {/* Hero */}
      <div className="bg-gradient-to-br from-red-500 via-orange-500 to-amber-500 text-white">
        <div className="container mx-auto px-4 py-10 md:py-14">
          <div className="max-w-2xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-1.5 rounded-full text-sm font-medium mb-4">
              <Tag className="h-4 w-4" />
              Ofertas y Descuentos
            </div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">
              Las mejores ofertas en medicamentos
            </h1>
            <p className="text-white/80 text-lg">
              Encontrá descuentos y promociones bancarias en farmacias de Paraguay
            </p>
            {stats && (
              <div className="flex items-center justify-center gap-6 mt-6 text-sm">
                <div className="flex items-center gap-2">
                  <BadgePercent className="h-4 w-4 text-white/70" />
                  <span>
                    <strong>{stats.discount_count.toLocaleString("es-PY")}</strong>{" "}
                    con descuento
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <CreditCard className="h-4 w-4 text-white/70" />
                  <span>
                    <strong>{stats.bank_deal_count.toLocaleString("es-PY")}</strong>{" "}
                    ofertas bancarias
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6">
        {/* Offer type tabs */}
        <div className="flex gap-2 mb-5">
          {[
            { value: "all", label: "Todos", icon: Tag },
            { value: "discount", label: "Descuentos", icon: BadgePercent },
            { value: "bank_deal", label: "Ofertas Bancarias", icon: CreditCard },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <Link
                key={tab.value}
                href={buildUrl({ type: tab.value, page: "1" })}
                className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  offerType === tab.value
                    ? "bg-red-500 text-white shadow-md"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </Link>
            );
          })}
        </div>

        {/* Filter row */}
        <div className="flex flex-wrap gap-2 mb-5">
          {/* Min discount pills */}
          {(offerType === "all" || offerType === "discount") && (
            <div className="flex gap-1 flex-wrap">
              {[
                { label: "Todos", value: undefined },
                { label: "10%+", value: "10" },
                { label: "20%+", value: "20" },
                { label: "30%+", value: "30" },
                { label: "50%+", value: "50" },
              ].map((opt) => (
                <Link
                  key={opt.label}
                  href={buildUrl({
                    min_discount: sp.min_discount === opt.value ? undefined : opt.value,
                    page: "1",
                  })}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    sp.min_discount === opt.value || (!sp.min_discount && !opt.value)
                      ? "bg-red-500 text-white"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {opt.label}
                </Link>
              ))}
            </div>
          )}

          {/* Pharmacy pills */}
          <div className="flex gap-1 flex-wrap">
            <Link
              href={buildUrl({ pharmacy: undefined, page: "1" })}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                !pharmacy
                  ? "bg-emerald-600 text-white"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
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
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
                style={pharmacy === key ? { backgroundColor: ph.color } : {}}
              >
                {ph.shortName}
              </Link>
            ))}
          </div>

          {/* Sort */}
          <div className="flex gap-1 flex-wrap ml-auto">
            {[
              { value: "discount", label: "Mayor descuento" },
              { value: "price_asc", label: "Menor precio" },
              { value: "price_desc", label: "Mayor precio" },
            ].map((opt) => (
              <Link
                key={opt.value}
                href={buildUrl({ sort: opt.value, page: "1" })}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  sort === opt.value
                    ? "bg-gray-800 text-white"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {opt.label}
              </Link>
            ))}
          </div>
        </div>

        {/* Results count */}
        <p className="text-sm text-muted-foreground mb-4">
          {data
            ? `${data.total.toLocaleString("es-PY")} ofertas encontradas`
            : "Cargando..."}
        </p>

        {/* Product grid */}
        {!data || data.results.length === 0 ? (
          <div className="text-center py-16">
            <Tag className="h-12 w-12 text-muted-foreground/20 mx-auto mb-3" />
            <p className="text-muted-foreground">No se encontraron ofertas</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
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
                          ? "bg-red-500 text-white shadow-sm"
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
                className="flex items-center gap-1 px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-medium hover:bg-red-600 transition-colors shadow-sm"
              >
                Siguiente
                <ChevronRight className="h-4 w-4" />
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
