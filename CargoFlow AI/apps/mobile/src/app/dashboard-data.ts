import {
  AuthResponse,
  CarrierDashboardResponse,
  DriverDashboardResponse,
  MetricCard as MetricCardModel,
  TimelineItem as TimelineItemModel,
} from '../api/auth-client';

export type { MetricCardModel, TimelineItemModel };

export type CarrierDashboardModel = {
  metrics: MetricCardModel[];
  activeLoads: TimelineItemModel[];
  liveAuctions: TimelineItemModel[];
  compliance: TimelineItemModel[];
};

export type DriverDashboardModel = {
  metrics: MetricCardModel[];
  assignedTrips: TimelineItemModel[];
  todayChecklist: TimelineItemModel[];
  alerts: TimelineItemModel[];
};

export function mapCarrierDashboard(response: CarrierDashboardResponse): CarrierDashboardModel {
  return {
    metrics: response.metrics,
    activeLoads: response.active_loads,
    liveAuctions: response.live_auctions,
    compliance: response.compliance,
  };
}

export function mapDriverDashboard(response: DriverDashboardResponse): DriverDashboardModel {
  return {
    metrics: response.metrics,
    assignedTrips: response.assigned_trips,
    todayChecklist: response.today_checklist,
    alerts: response.alerts,
  };
}

export function buildCarrierDashboard(session: AuthResponse): CarrierDashboardModel {
  const companyLabel = session.company?.legal_name ?? 'Azienda';

  return {
    metrics: [
      { label: 'Carichi aperti', value: '12', tone: 'ember' },
      { label: 'Aste live', value: '4', tone: 'pine' },
      { label: 'Compliance score', value: session.company?.compliance_blocked ? '62/100' : '94/100', tone: 'sky' },
    ],
    activeLoads: [
      {
        id: 'load-1',
        title: 'MI -> DE | Frigo bi-temp',
        subtitle: `${companyLabel} · partenza domani 06:00`,
        meta: 'Budget 1.480 EUR · Termografo richiesto',
        status: 'live',
      },
      {
        id: 'load-2',
        title: 'VR -> FR | Telonato ADR',
        subtitle: 'Finestra carico 14:00-16:00',
        meta: 'Coils well opzionale · urgenza alta',
        status: 'attention',
      },
      {
        id: 'load-3',
        title: 'NA -> IT | Distribuzione multi-stop',
        subtitle: 'Stato: matching in corso',
        meta: '8 pallets · ultimo aggiornamento 12 min fa',
        status: 'planned',
      },
    ],
    liveAuctions: [
      {
        id: 'auction-1',
        title: 'Asta ribasso Milano-Amburgo',
        subtitle: '03:42 rimanenti',
        meta: 'Miglior offerta 1.260 EUR · 6 vettori attivi',
        status: 'live',
      },
      {
        id: 'auction-2',
        title: 'Asta rialzo Verona-Lione',
        subtitle: '08:15 rimanenti',
        meta: 'Base 980 EUR · ADR confermato',
        status: 'planned',
      },
    ],
    compliance: [
      {
        id: 'compliance-1',
        title: 'DURC aziendale',
        subtitle: 'Valido fino al 24/05/2026',
        meta: 'Nessun blocco operativo',
        status: 'planned',
      },
      {
        id: 'compliance-2',
        title: 'Polizza vettoriale',
        subtitle: 'Scade tra 9 giorni',
        meta: 'Rinnovo consigliato prima di nuove assegnazioni',
        status: 'attention',
      },
    ],
  };
}

export function buildDriverDashboard(session: AuthResponse): DriverDashboardModel {
  const driverName = `${session.user.first_name} ${session.user.last_name}`;

  return {
    metrics: [
      { label: 'Missioni oggi', value: '3', tone: 'pine' },
      { label: 'Check-in geofence', value: '2/3', tone: 'sky' },
      { label: 'Documenti da caricare', value: '1', tone: 'ember' },
    ],
    assignedTrips: [
      {
        id: 'trip-1',
        title: 'Missione TRIP-2048 | Bologna -> Monaco',
        subtitle: `${driverName} · scarico previsto 18:40`,
        meta: 'Stato: in transito · mezzo FR-782LK',
        status: 'live',
      },
      {
        id: 'trip-2',
        title: 'Missione TRIP-2053 | Verona -> Marsiglia',
        subtitle: 'Partenza prevista domani 05:30',
        meta: 'Richiesto CMR firmato e foto sigillo',
        status: 'planned',
      },
    ],
    todayChecklist: [
      {
        id: 'check-1',
        title: 'Conferma arrivo al carico',
        subtitle: 'Geofence non ancora completato',
        meta: 'Apri missione e invia posizione se necessario',
        status: 'attention',
      },
      {
        id: 'check-2',
        title: 'Scannerizza DDT',
        subtitle: 'Ultimo viaggio: documento mancante',
        meta: 'OCR disponibile dalla schermata missione',
        status: 'attention',
      },
      {
        id: 'check-3',
        title: 'Chat operativa',
        subtitle: '2 messaggi non letti',
        meta: 'Scheda viaggio sempre agganciata alla conversazione',
        status: 'live',
      },
    ],
    alerts: [
      {
        id: 'alert-1',
        title: 'Sosta stimata oltre finestra',
        subtitle: 'Possibile ritardo di 18 minuti',
        meta: 'Suggerito avviso automatico al disponente',
        status: 'attention',
      },
    ],
  };
}
