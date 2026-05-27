export interface CheckoutPreferenceResponse {
  order_id: string;
  order_number: string;
  preference_id: string;
  init_point: string | null;
  sandbox_init_point: string | null;
}
