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

export interface SalesMetricsDashboard {
  summary: {
    period: string;
    start_at: string;
    end_at: string;
    order_count: number;
    total_revenue: string;
    average_order_value: string;
    bottles_sold: number;
  };
  timeline: {
    period: string;
    grain: string;
    results: Array<{
      period: string;
      order_count: number;
      total_revenue: string;
      bottles_sold: number;
    }>;
  };
  by_varietal: {
    results: Array<{
      varietal: string;
      bottles_sold: number;
      revenue: string;
      order_count: number;
    }>;
  };
  by_product: {
    results: Array<{
      sku: string;
      wine_name: string;
      bottles_sold: number;
      revenue: string;
      order_count: number;
    }>;
  };
  by_channel: {
    results: Array<{
      channel: string;
      order_count: number;
      total_revenue: string;
    }>;
  };
  margins: {
    results: Array<{
      sku: string;
      wine_name: string;
      bottles_sold: number;
      revenue: string;
      estimated_cost: string;
      estimated_margin: string;
    }>;
  };
  repeat_customers: {
    unique_customers: number;
    repeat_customers: number;
    repeat_rate: number;
    average_revenue_per_customer: string;
    top_repeat_customers: Array<{
      customer_email: string;
      order_count: number;
      revenue: string;
      last_order_at: string | null;
    }>;
  };
  funnel: {
    cart_count: number;
    order_count: number;
    paid_order_count: number;
    rejected_payment_count: number;
    cart_to_order_rate: number;
    order_to_paid_rate: number;
    cart_abandonment_rate: number;
  };
  incidents: {
    total_orders: number;
    refunded_orders: number;
    cancelled_orders: number;
    payment_failed_orders: number;
    incident_task_count: number;
    incident_rate: number;
  };
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

export interface BackofficeExperience {
  id: string;
  name: string;
  slug: string;
  experience_type: string;
  description: string;
  duration_minutes: number;
  price_per_person: string;
  min_guests: number;
  max_guests: number;
  includes: string[];
  highlights: string[];
  cover_image: string;
  gallery_images: string[];
  cancellation_hours: number;
  is_active: boolean;
  is_featured: boolean;
  bookings_count: number;
  slots_count: number;
}

export interface BackofficeTimeSlot {
  id: number;
  experience: string;
  experience_name: string;
  date: string;
  start_time: string;
  end_time: string;
  capacity: number;
  spots_available: number;
  booked_guests: number;
  guide_name: string;
  is_blocked: boolean;
  block_reason: string;
}

export interface BackofficeBooking {
  id: string;
  confirmation_code: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  experience_name: string;
  experience_type: string;
  slot_date: string;
  slot_start_time: string;
  slot_end_time: string;
  guest_count: number;
  total_price: string;
  status: string;
  special_requests: string;
  dietary_restrictions: string[];
  qr_code_url: string;
  checked_in_at: string | null;
  payment_status: string;
  payment_status_detail: string;
  manual_refund: {
    id: string;
    status: string;
    status_label: string;
    amount: string;
    currency: string;
    reason: string;
    note: string;
    operator: string | null;
    operator_email: string;
    created_at: string;
    updated_at: string;
    completed_at: string | null;
  } | null;
  reminder_24h_sent: boolean;
  reminder_1h_sent: boolean;
  hold_expires_at: string | null;
  created_at: string;
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

export interface BackofficeExperiencePayload {
  name: string;
  slug?: string;
  experience_type: string;
  description: string;
  duration_minutes: number;
  price_per_person: string;
  min_guests: number;
  max_guests: number;
  includes: string[];
  highlights: string[];
  cover_image: string;
  gallery_images: string[];
  cancellation_hours: number;
  is_active: boolean;
  is_featured: boolean;
}

export interface BackofficeBookingPayload {
  status: string;
  guest_count: number;
  special_requests: string;
  checked_in_at: string | null;
  manual_refund_status?: string;
  manual_refund_note?: string;
}

export interface BackofficeTimeSlotPayload {
  experience: string;
  date: string;
  start_time: string;
  end_time: string;
  capacity: number;
  guide_name: string;
  is_blocked: boolean;
  block_reason: string;
}
