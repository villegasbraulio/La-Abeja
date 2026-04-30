export interface WineListItem {
  id: string;
  name: string;
  slug: string;
  vintage_year: number;
  price: string;
  compare_at_price: string | null;
  discount_percentage: number | null;
  varietal_name: string;
  category_name: string;
  primary_image: string | null;
  average_rating: number | null;
  review_count: number;
  is_in_stock: boolean;
  is_featured: boolean;
  is_limited_edition: boolean;
  alcohol_percentage: string;
}

export interface CatalogCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
  order: number;
}

export interface CatalogVarietal {
  id: number;
  name: string;
  slug: string;
  description: string;
  origin_region: string;
}

export interface WineImage {
  id: number;
  url: string;
  alt_text: string;
  is_primary: boolean;
  order: number;
}

export interface WineReview {
  id: string;
  rating: number;
  title: string;
  body: string;
  user_name: string;
  is_verified_purchase: boolean;
  created_at: string;
}

export interface WineTastingProfile {
  tannins: number;
  acidity: number;
  body: number;
  sweetness: number;
  fruit_intensity: number;
}

export interface WineDetail extends WineListItem {
  description: string;
  tasting_notes: string;
  winemaker_notes: string;
  pairing_suggestions: string[];
  awards: Array<Record<string, unknown>>;
  blend_varietals: Array<Record<string, unknown>>;
  ageing_months: number;
  ageing_type: string;
  serving_temperature_min: number;
  serving_temperature_max: number;
  tasting_profile: WineTastingProfile;
  images: WineImage[];
  recent_reviews: WineReview[];
  stock: number;
  sku: string;
}

export interface CatalogResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: WineListItem[];
}

export interface CatalogFilters {
  search?: string;
  category?: string;
  varietal?: string;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  featured?: boolean;
}
