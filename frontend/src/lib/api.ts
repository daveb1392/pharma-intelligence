import type {
  CategoryItem,
  CategoryProductItem,
  CategoryProductsResponse,
  ComparisonData,
  HomeStats,
  PriceHistoryData,
  SearchResponse,
} from "@/types/product";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ProductFilters {
  brand?: string;
  prescription?: string; // "true" | "false"
  min_price?: string;
  max_price?: string;
  discount?: string; // "true"
  bank_deal?: string; // "true"
}

export interface BrandItem {
  brand: string;
  count: number;
}

function appendFilterParams(params: URLSearchParams, filters: ProductFilters) {
  if (filters.brand) params.set("brand", filters.brand);
  if (filters.prescription === "true") params.set("requires_prescription", "true");
  if (filters.prescription === "false") params.set("requires_prescription", "false");
  if (filters.min_price) params.set("min_price", filters.min_price);
  if (filters.max_price) params.set("max_price", filters.max_price);
  if (filters.discount === "true") params.set("has_discount", "true");
  if (filters.bank_deal === "true") params.set("has_bank_deal", "true");
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API Error: ${res.status}`);
  }

  return res.json();
}

// Server-side fetch helpers (no auth needed for public data)
export async function searchProducts(
  q: string,
  page = 1,
  pharmacy?: string,
  category?: string,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, page: String(page) });
  if (pharmacy) params.set("pharmacy", pharmacy);
  if (category) params.set("category", category);
  return apiFetch(`/api/search?${params}`);
}

export async function getComparison(barcode: string): Promise<ComparisonData> {
  return apiFetch(`/api/compare/${barcode}`);
}

export async function getPriceHistory(
  barcode: string,
  days = 30,
): Promise<PriceHistoryData> {
  return apiFetch(`/api/price-history/${barcode}?days=${days}`);
}

export async function getCategories(): Promise<CategoryItem[]> {
  return apiFetch("/api/categories");
}

export async function getCategoryProducts(
  category: string,
  page = 1,
  limit = 24,
  pharmacy?: string,
  sort?: string,
  filters?: ProductFilters,
): Promise<CategoryProductsResponse> {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  if (pharmacy) params.set("pharmacy", pharmacy);
  if (sort) params.set("sort", sort);
  if (filters) appendFilterParams(params, filters);
  return apiFetch(
    `/api/categories/${encodeURIComponent(category)}?${params}`,
  );
}

export async function getHomeStats(): Promise<HomeStats> {
  return apiFetch("/api/home/stats");
}

export async function getTopDiscounts(
  limit = 8,
): Promise<CategoryProductItem[]> {
  return apiFetch(`/api/home/top-discounts?limit=${limit}`);
}

export async function getBankDeals(
  limit = 8,
): Promise<CategoryProductItem[]> {
  return apiFetch(`/api/home/bank-deals?limit=${limit}`);
}

export async function getBrands(
  category?: string,
  pharmacy?: string,
  limit = 50,
): Promise<BrandItem[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (category) params.set("category", category);
  if (pharmacy) params.set("pharmacy", pharmacy);
  return apiFetch(`/api/home/brands?${params}`);
}

export async function browseProducts(
  page = 1,
  limit = 24,
  pharmacy?: string,
  category?: string,
  sort?: string,
  filters?: ProductFilters,
): Promise<CategoryProductsResponse> {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  if (pharmacy) params.set("pharmacy", pharmacy);
  if (category) params.set("category", category);
  if (sort) params.set("sort", sort);
  if (filters) appendFilterParams(params, filters);
  return apiFetch(`/api/home/products?${params}`);
}

// Ofertas
export interface OfertasStats {
  discount_count: number;
  bank_deal_count: number;
}

export async function getOfertasStats(): Promise<OfertasStats> {
  return apiFetch("/api/ofertas/stats");
}

export async function getOfertasProducts(
  page = 1,
  limit = 24,
  offerType = "all",
  minDiscount?: number,
  pharmacy?: string,
  category?: string,
  sort = "discount",
): Promise<CategoryProductsResponse> {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
    offer_type: offerType,
    sort,
  });
  if (minDiscount != null) params.set("min_discount", String(minDiscount));
  if (pharmacy) params.set("pharmacy", pharmacy);
  if (category) params.set("category", category);
  return apiFetch(`/api/ofertas/products?${params}`);
}

// Client-side authenticated fetch
export function createAuthFetch(token: string) {
  return async function authFetch<T>(
    path: string,
    options?: RequestInit,
  ): Promise<T> {
    return apiFetch(path, {
      ...options,
      headers: {
        Authorization: `Bearer ${token}`,
        ...options?.headers,
      },
    });
  };
}
