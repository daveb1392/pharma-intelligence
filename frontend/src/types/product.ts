export interface PharmacyPrice {
  pharmacy_source: string;
  site_code?: string;
  product_name?: string;
  current_price?: number;
  original_price?: number;
  discount_percentage?: number;
  discount_amount?: number;
  bank_discount_price?: number;
  bank_discount_bank_name?: string;
  bank_payment_offers?: string;
  requires_prescription?: boolean;
  product_url?: string;
  image_url?: string;
  scraped_at?: string;
}

export interface ComparisonData {
  barcode: string;
  product_name?: string;
  brand?: string;
  main_category?: string;
  image_url?: string;
  best_price?: number;
  highest_price?: number;
  savings?: number;
  pharmacies: PharmacyPrice[];
}

export interface SearchResultItem {
  group_key?: string;
  barcode?: string;
  product_name?: string;
  brand?: string;
  image_url?: string;
  main_category?: string;
  requires_prescription?: boolean;
  best_price?: number;
  pharmacy_count?: number;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total: number;
  page: number;
  limit: number;
}

export interface CategoryItem {
  main_category: string;
  product_count: number;
  pharmacy_count?: number;
  min_price?: number;
  max_price?: number;
}

export interface CategoryProductItem {
  id: string;
  pharmacy_source: string;
  site_code?: string;
  barcode?: string;
  product_name?: string;
  brand?: string;
  image_url?: string;
  main_category?: string;
  current_price?: number;
  original_price?: number;
  discount_percentage?: number;
  discount_amount?: number;
  bank_discount_price?: number;
  bank_discount_bank_name?: string;
  requires_prescription?: boolean;
  product_url?: string;
  scraped_at?: string;
}

export interface CategoryProductsResponse {
  results: CategoryProductItem[];
  total: number;
  page: number;
  limit: number;
}

export interface HomeStats {
  total_products: number;
  pharmacy_count: number;
}

export interface PriceHistoryPoint {
  date: string;
  price?: number;
}

export interface PharmacyPriceHistory {
  pharmacy_source: string;
  data_points: PriceHistoryPoint[];
}

export interface PriceHistoryData {
  barcode: string;
  product_name?: string;
  history: PharmacyPriceHistory[];
}
