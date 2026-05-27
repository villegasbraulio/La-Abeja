import type { Order } from "./orders";

export interface BackofficeDashboard {
  total_wines: number;
  active_wines: number;
  featured_wines: number;
  low_stock_wines: number;
  categories: number;
  varietals: number;
  total_orders: number;
  pending_orders: number;
  low_stock_items: Array<{
    id: string;
    name: string;
    stock: number;
    low_stock_threshold: number;
  }>;
}

export interface BackofficeCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
  order: number;
  wines_count: number;
}

export interface BackofficeVarietal {
  id: number;
  name: string;
  slug: string;
  description: string;
  origin_region: string;
  wines_count: number;
}

export interface BackofficeWineImage {
  id?: number;
  url: string;
  alt_text: string;
  is_primary: boolean;
  order: number;
}

export interface BackofficeWineListItem {
  id: string;
  name: string;
  slug: string;
  sku: string;
  category: number;
  category_name: string;
  varietal: number;
  varietal_name: string;
  price: string;
  compare_at_price: string | null;
  stock: number;
  low_stock_threshold: number;
  is_active: boolean;
  is_featured: boolean;
  is_limited_edition: boolean;
  primary_image: string | null;
  stock_state: "out" | "low" | "healthy";
  gross_margin_percentage: number | null;
  updated_at: string;
}

export interface BackofficeWineDetail extends BackofficeWineListItem {
  blend_varietals: Array<Record<string, unknown>>;
  vintage_year: number;
  cost_price: string;
  alcohol_percentage: string;
  serving_temperature_min: number;
  serving_temperature_max: number;
  ageing_months: number;
  ageing_type: string;
  tannins: number;
  acidity: number;
  body: number;
  sweetness: number;
  fruit_intensity: number;
  description: string;
  tasting_notes: string;
  pairing_suggestions: string[];
  winemaker_notes: string;
  awards: Array<Record<string, unknown>>;
  meta_title: string;
  meta_description: string;
  images: BackofficeWineImage[];
  created_at: string;
}

export interface BackofficeWinePayload {
  name: string;
  slug?: string;
  sku: string;
  category: number;
  varietal: number;
  vintage_year: number;
  price: string;
  compare_at_price: string | null;
  cost_price: string;
  stock: number;
  low_stock_threshold: number;
  alcohol_percentage: string;
  serving_temperature_min: number;
  serving_temperature_max: number;
  ageing_months: number;
  ageing_type: string;
  tannins: number;
  acidity: number;
  body: number;
  sweetness: number;
  fruit_intensity: number;
  description: string;
  tasting_notes: string;
  pairing_suggestions: string[];
  winemaker_notes: string;
  awards: Array<Record<string, unknown>>;
  blend_varietals: Array<Record<string, unknown>>;
  meta_title: string;
  meta_description: string;
  is_featured: boolean;
  is_active: boolean;
  is_limited_edition: boolean;
  images: BackofficeWineImage[];
}

export interface BackofficeOrderListItem {
  id: string;
  order_number: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  status: string;
  status_label: string;
  payment_status: string | null;
  payment_status_label: string | null;
  shipping_method: string;
  shipping_method_label: string;
  total: string;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface BackofficeOrderDetail extends Order {
  customer_name: string;
  customer_email: string;
  customer_phone: string;
}
