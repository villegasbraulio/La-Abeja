export type ShippingMethod = "standard" | "express" | "pickup";

export interface CheckoutItemPayload {
  wine_id: string;
  quantity: number;
}

export interface CheckoutShippingAddressPayload {
  recipient_name: string;
  street: string;
  number: string;
  floor_apt?: string;
  city: string;
  province: string;
  postal_code: string;
  country: string;
  phone: string;
}

export interface OrderCreatePayload {
  items: CheckoutItemPayload[];
  shipping_method: ShippingMethod;
  shipping_address: CheckoutShippingAddressPayload;
  notes?: string;
}

export interface OrderItem {
  id: number;
  wine_name: string;
  wine_sku: string;
  wine_slug: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
  primary_image: string | null;
}

export interface OrderPaymentSummary {
  id: string;
  status: string;
  status_detail: string;
  mp_preference_id: string;
  mp_payment_id: string;
  amount: string;
  payment_method: string;
  payment_type: string;
  installments: number;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  order_number: string;
  status: string;
  status_label: string;
  subtotal: string;
  discount_amount: string;
  shipping_cost: string;
  total: string;
  shipping_method: ShippingMethod;
  shipping_method_label: string;
  shipping_address: CheckoutShippingAddressPayload;
  tracking_number: string;
  estimated_delivery: string | null;
  notes: string;
  items: OrderItem[];
  payment: OrderPaymentSummary | null;
  created_at: string;
  updated_at: string;
}
