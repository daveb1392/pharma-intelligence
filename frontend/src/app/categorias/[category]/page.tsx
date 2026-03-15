import { BadgePercent, CreditCard, Pill } from "lucide-react";
import Link from "next/link";
import type { Metadata } from "next";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { getBrands, getCategoryProducts } from "@/lib/api";
import type { ProductFilters } from "@/lib/api";
import { formatPrice, getPharmacy, getProductImage, PHARMACIES } from "@/lib/constants";

interface Props {
  params: Promise<{ category: string }>;
  searchParams: Promise<{
    page?: string;
    sort?: string;
    pharmacy?: string;
    brand?: string;
    prescription?: string;
    min_price?: string;
    max_price?: string;
    discount?: string;
    bank_deal?: string;
  }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  const decoded = decodeURIComponent(category);
  return {
    title: `${decoded} - PrecioFarma`,
    description: `Compará precios de ${decoded} en farmacias de Paraguay`,
  };
}

const SORT_OPTIONS = [
  { value: "price_asc", label: "Menor precio" },
  { value: "price_desc", label: "Mayor precio" },
  { value: "name_asc", label: "Nombre A-Z" },
  { value: "discount", label: "Mayor descuento" },
];

export default async function CategoryPage({ params, searchParams }: Props) {
  const { category } = await params;
  const sp = await searchParams;
  const decoded = decodeURIComponent(category);
  const page = parseInt(sp.page || "1", 10);
  const sort = sp.sort || "price_asc";
  const pharmacy = sp.pharmacy;
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

  let data;
  let brands: { brand: string; count: number }[] = [];
  try {
    [data, brands] = await Promise.all([
      getCategoryProducts(decoded, page, 24, pharmacy, sort, filters),
      getBrands(decoded, pharmacy, 30),
    ]);
  } catch {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <p className="text-muted-foreground">Error al cargar productos</p>
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / data.limit);
  const basePath = `/categorias/${encodeURIComponent(decoded)}`;

  function buildUrl(overrides: Record<string, string | undefined>) {
    const p = new URLSearchParams();
    const newSort = overrides.sort ?? sort;
    const newPharmacy = "pharmacy" in overrides ? overrides.pharmacy : pharmacy;
    const newPage = overrides.page ?? String(page);
    const br = "brand" in overrides ? overrides.brand : brand;
    const pr = "prescription" in overrides ? overrides.prescription : prescription;
    const mp = "min_price" in overrides ? overrides.min_price : minPrice;
    const xp = "max_price" in overrides ? overrides.max_price : maxPrice;
    const dc = "discount" in overrides ? overrides.discount : discount;
    const bd = "bank_deal" in overrides ? overrides.bank_deal : bankDeal;
    if (newSort && newSort !== "price_asc") p.set("sort", newSort);
    if (newPharmacy) p.set("pharmacy", newPharmacy);
    if (newPage !== "1") p.set("page", newPage);
    if (br) p.set("brand", br);
    if (pr) p.set("prescription", pr);
    if (mp) p.set("min_price", mp);
    if (xp) p.set("max_price", xp);
    if (dc) p.set("discount", dc);
    if (bd) p.set("bank_deal", bd);
    const qs = p.toString();
    return `${basePath}${qs ? `?${qs}` : ""}`;
  }

  return (
    <div className="container mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{decoded}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {data.total.toLocaleString("es-PY")} productos
        </p>
      </div>

      {/* Filters */}
      <div className="space-y-3 mb-6">
        <div className="flex flex-wrap gap-2">
          {/* Sort */}
          <div className="flex gap-1 flex-wrap">
            {SORT_OPTIONS.map((opt) => (
              <Link
                key={opt.value}
                href={buildUrl({ sort: opt.value, page: "1" })}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  sort === opt.value
                    ? "bg-emerald-600 text-white"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {opt.label}
              </Link>
            ))}
          </div>

          {/* Pharmacy filter */}
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
        </div>

        {/* Quick filters row */}
        <div className="flex gap-1.5 flex-wrap">
          <Link
            href={buildUrl({
              discount: discount === "true" ? undefined : "true",
              page: "1",
            })}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              discount === "true"
                ? "bg-red-500 text-white"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            <BadgePercent className="h-3 w-3" />
            Con descuento
          </Link>
          <Link
            href={buildUrl({
              bank_deal: bankDeal === "true" ? undefined : "true",
              page: "1",
            })}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              bankDeal === "true"
                ? "bg-blue-500 text-white"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            <CreditCard className="h-3 w-3" />
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
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            Sin receta
          </Link>
          <Link
            href={buildUrl({
              prescription: prescription === "true" ? undefined : "true",
              page: "1",
            })}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              prescription === "true"
                ? "bg-orange-500 text-white"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            Con receta
          </Link>

          {/* Price range pills */}
          {[
            { label: "Hasta ₲50k", min: undefined, max: "50000" },
            { label: "₲50k-100k", min: "50000", max: "100000" },
            { label: "₲100k-500k", min: "100000", max: "500000" },
            { label: "₲500k+", min: "500000", max: undefined },
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
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-purple-500 text-white"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {range.label}
              </Link>
            );
          })}
        </div>

        {/* Brand pills */}
        {brands.length > 0 && (
          <div className="flex gap-1.5 flex-wrap">
            {brand && (
              <Link
                href={buildUrl({ brand: undefined, page: "1" })}
                className="px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500 text-white transition-colors"
              >
                {brand} ✕
              </Link>
            )}
            {brands
              .filter((b) => b.brand !== brand)
              .slice(0, 15)
              .map((b) => (
                <Link
                  key={b.brand}
                  href={buildUrl({ brand: b.brand, page: "1" })}
                  className="px-3 py-1.5 rounded-full text-xs font-medium bg-muted text-muted-foreground hover:bg-muted/80 transition-colors"
                >
                  {b.brand}
                </Link>
              ))}
          </div>
        )}

        {/* Active filter tags */}
        {hasFilters && (
          <div className="flex items-center gap-1.5">
            <Link
              href={basePath}
              className="text-xs text-muted-foreground hover:text-foreground underline"
            >
              Limpiar filtros
            </Link>
          </div>
        )}
      </div>

      {/* Product grid */}
      {data.results.length === 0 ? (
        <p className="text-center text-muted-foreground py-12">
          No se encontraron productos en esta categoría
        </p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {data.results.map((product) => {
            const ph = getPharmacy(product.pharmacy_source);
            const href = product.barcode
              ? `/producto/${product.barcode}`
              : product.product_url || "#";

            return (
              <Link key={product.id} href={href}>
                <Card className="group overflow-hidden hover:shadow-lg transition-all duration-200 h-full flex flex-col">
                  {/* Image */}
                  <div className="relative bg-gray-50 aspect-square flex items-center justify-center p-3">
                    {getProductImage(product.image_url) ? (
                      <img
                        src={getProductImage(product.image_url)!}
                        alt={product.product_name || ""}
                        className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                      />
                    ) : (
                      <Pill className="h-12 w-12 text-muted-foreground/30" />
                    )}
                    {/* Discount badge */}
                    {product.discount_percentage != null &&
                      product.discount_percentage > 0 && (
                        <span className="absolute top-2 left-2 bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                          -{Math.round(product.discount_percentage)}%
                        </span>
                      )}
                    {/* Pharmacy badge */}
                    <span
                      className="absolute bottom-2 right-2 text-white text-[10px] font-medium px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: ph.color }}
                    >
                      {ph.shortName}
                    </span>
                  </div>

                  {/* Info */}
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
                        product.original_price > (product.current_price || 0) && (
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
                            {formatPrice(product.bank_discount_price)} c/banco
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
        <div className="flex items-center justify-center gap-2 mt-8">
          {page > 1 && (
            <Link
              href={buildUrl({ page: String(page - 1) })}
              className="px-4 py-2 rounded-lg bg-muted text-sm font-medium hover:bg-muted/80 transition-colors"
            >
              Anterior
            </Link>
          )}
          <span className="text-sm text-muted-foreground px-3">
            Página {page} de {totalPages}
          </span>
          {page < totalPages && (
            <Link
              href={buildUrl({ page: String(page + 1) })}
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 transition-colors"
            >
              Siguiente
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
