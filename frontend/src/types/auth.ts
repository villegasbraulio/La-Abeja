export interface AuthUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  birth_date: string | null;
  avatar: string;
  preferred_varietals: string[];
  newsletter_subscribed: boolean;
  is_staff: boolean;
  full_name: string;
}

export interface AuthSession {
  access: string;
  refresh: string;
  user: AuthUser;
}
