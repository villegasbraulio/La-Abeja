export interface VisitExperience {
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
  next_available_date: string | null;
}

export interface VisitTimeSlot {
  id: number;
  experience: string;
  experience_name: string;
  date: string;
  start_time: string;
  end_time: string;
  capacity: number;
  spots_available: number;
  guide_name: string;
}

export interface VisitPaymentSummary {
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

export interface VisitManualRefundSummary {
  id: string;
  status: string;
  status_label: string;
  amount: string;
  currency: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface VisitBooking {
  id: string;
  confirmation_code: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  experience_name: string;
  slot_date: string;
  slot_start_time: string;
  slot_end_time: string;
  guest_count: number;
  total_price: string;
  status: string;
  status_label: string;
  special_requests: string;
  dietary_restrictions: string[];
  hold_expires_at: string | null;
  guest_access_token: string | null;
  payment: VisitPaymentSummary | null;
  manual_refund: VisitManualRefundSummary | null;
  created_at: string;
}

export interface VisitBookingCreatePayload {
  time_slot: number;
  guest_count: number;
  customer_first_name: string;
  customer_last_name: string;
  customer_email: string;
  customer_phone: string;
  client_request_id?: string;
  special_requests?: string;
  dietary_restrictions?: string[];
}

export interface VisitBookingPreferenceResponse {
  booking: VisitBooking;
  preference: {
    booking_id: string;
    confirmation_code: string;
    preference_id: string;
    init_point: string | null;
    sandbox_init_point: string | null;
    hold_expires_at: string | null;
    hold_minutes: number;
    guest_access_token: string | null;
  };
}
