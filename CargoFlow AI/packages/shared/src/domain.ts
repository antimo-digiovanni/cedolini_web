export type UserRole = 'carrier_owner' | 'dispatcher' | 'driver' | 'admin';

export type VehicleKind = 'frigo' | 'telonato' | 'cassonato' | 'cisterna' | 'furgone';

export type AuctionMode = 'reverse' | 'forward';

export type TripStatus =
  | 'draft'
  | 'assigned'
  | 'heading_to_pickup'
  | 'arrived_at_pickup'
  | 'loaded'
  | 'in_transit'
  | 'arrived_at_delivery'
  | 'delivered'
  | 'closed';

export type ComplianceDocumentType = 'durc' | 'insurance' | 'carrier_register' | 'driving_license' | 'cmr' | 'ddt';

export interface RoutePreference {
  originCountry: string;
  destinationCountry: string;
  originRegion?: string;
  destinationRegion?: string;
}

export interface VehicleEquipment {
  biTemperature?: boolean;
  meatHooks?: boolean;
  thermograph?: boolean;
  coilWell?: boolean;
  liftAxle?: boolean;
  adr?: boolean;
}

export interface CompanySummary {
  id: string;
  legalName: string;
  vatNumber: string;
  role: 'carrier';
  complianceScore: number;
}

export interface LoadSummary {
  id: string;
  code: string;
  originLabel: string;
  destinationLabel: string;
  pickupWindowStart: string;
  deliveryWindowEnd: string;
  vehicleKind: VehicleKind;
  auctionMode: AuctionMode;
  budgetAmount?: number;
}

export interface TripCard {
  id: string;
  loadCode: string;
  driverName: string;
  status: TripStatus;
  originLabel: string;
  destinationLabel: string;
  scheduledPickupAt: string;
}
