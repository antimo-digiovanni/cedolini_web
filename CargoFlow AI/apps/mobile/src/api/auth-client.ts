export type UserRole = 'carrier_owner' | 'dispatcher' | 'driver' | 'admin';

export type Company = {
  id: string;
  legal_name: string;
  vat_number: string;
  compliance_blocked: boolean;
};

export type User = {
  id: string;
  company_id: string | null;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string | null;
  role: UserRole;
  is_active: boolean;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
};

export type AuthResponse = {
  tokens: TokenPair;
  user: User;
  company: Company | null;
};

export type CarrierRegistrationPayload = {
  company_name: string;
  vat_number: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone_number?: string;
};

export type DriverRegistrationPayload = {
  invite_token: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone_number?: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type InvitePayload = {
  role: 'driver' | 'dispatcher';
  validity_hours: number;
};

export type InviteResponse = {
  id: string;
  token: string;
  role: UserRole;
  is_active: boolean;
  expires_at: string | null;
};

export type MetricCard = {
  label: string;
  value: string;
  tone: 'ember' | 'pine' | 'sky';
};

export type TimelineItem = {
  id: string;
  title: string;
  subtitle: string;
  meta: string;
  status: 'live' | 'planned' | 'attention';
};

export type CarrierDashboardResponse = {
  metrics: MetricCard[];
  active_loads: TimelineItem[];
  live_auctions: TimelineItem[];
  compliance: TimelineItem[];
};

export type DriverDashboardResponse = {
  metrics: MetricCard[];
  assigned_trips: TimelineItem[];
  today_checklist: TimelineItem[];
  alerts: TimelineItem[];
};

export type VehicleKind = 'frigo' | 'telonato' | 'cassonato' | 'cisterna' | 'furgone';

export type LoadStatus = 'draft' | 'open' | 'auction_live' | 'assigned' | 'cancelled' | 'completed';

export type LoadCreatePayload = {
  title: string;
  origin_label: string;
  destination_label: string;
  pickup_window_start: string;
  delivery_window_end: string;
  budget_amount?: number;
  vehicle_kind: VehicleKind;
  adr_required: boolean;
  preferred_vehicle_id?: string;
};

export type LoadResponse = {
  id: string;
  company_id: string;
  preferred_vehicle_id: string | null;
  code: string;
  title: string;
  origin_label: string;
  destination_label: string;
  pickup_window_start: string;
  delivery_window_end: string;
  budget_amount: number | null;
  vehicle_kind: VehicleKind;
  adr_required: boolean;
  status: LoadStatus;
  created_at: string;
};

export type LoadListResponse = {
  items: LoadResponse[];
  total: number;
};

export type AuctionMode = 'reverse' | 'forward';

export type AuctionCreatePayload = {
  load_id?: string;
  load_code?: string;
  mode: AuctionMode;
  floor_price?: number;
  ceiling_price?: number;
  starts_at: string;
  ends_at: string;
};

export type AuctionResponse = {
  id: string;
  load_id: string;
  load_code: string;
  load_title: string;
  mode: AuctionMode;
  floor_price: number | null;
  ceiling_price: number | null;
  starts_at: string;
  ends_at: string;
  is_closed: boolean;
  created_at: string;
};

export type AuctionListResponse = {
  items: AuctionResponse[];
  total: number;
};

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  const contentType = response.headers.get('content-type') ?? '';
  const payload = contentType.includes('application/json') ? await response.json() : null;

  if (!response.ok) {
    const message = typeof payload?.detail === 'string' ? payload.detail : 'Request failed';
    throw new ApiError(message, response.status);
  }

  return payload as T;
}

export const authClient = {
  registerCarrier(baseUrl: string, payload: CarrierRegistrationPayload) {
    return request<AuthResponse>(baseUrl, '/api/auth/register/carrier', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  registerDriver(baseUrl: string, payload: DriverRegistrationPayload) {
    return request<AuthResponse>(baseUrl, '/api/auth/register/driver', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  login(baseUrl: string, payload: LoginPayload) {
    return request<AuthResponse>(baseUrl, '/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  me(baseUrl: string, accessToken: string) {
    return request<{ user: User; company: Company | null }>(baseUrl, '/api/auth/me', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  },
  createInvite(baseUrl: string, accessToken: string, payload: InvitePayload) {
    return request<InviteResponse>(baseUrl, '/api/auth/invites', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
    });
  },
  carrierDashboard(baseUrl: string, accessToken: string) {
    return request<CarrierDashboardResponse>(baseUrl, '/api/dashboard/carrier', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  },
  driverDashboard(baseUrl: string, accessToken: string) {
    return request<DriverDashboardResponse>(baseUrl, '/api/dashboard/driver', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  },
  createLoad(baseUrl: string, accessToken: string, payload: LoadCreatePayload) {
    return request<LoadResponse>(baseUrl, '/api/loads', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
    });
  },
  listLoads(baseUrl: string, accessToken: string) {
    return request<LoadListResponse>(baseUrl, '/api/loads', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  },
  createAuction(baseUrl: string, accessToken: string, payload: AuctionCreatePayload) {
    return request<AuctionResponse>(baseUrl, '/api/auctions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
    });
  },
  listAuctions(baseUrl: string, accessToken: string) {
    return request<AuctionListResponse>(baseUrl, '/api/auctions', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  },
};
