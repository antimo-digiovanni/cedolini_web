import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import {
  authClient,
  AuctionCreatePayload,
  AuctionMode,
  AuctionResponse,
  AuthResponse,
  InviteResponse,
  LoadCreatePayload,
  LoadResponse,
  VehicleKind,
} from '../api/auth-client';
import { CarrierDashboardModel } from './dashboard-data';
import { Field, PillButton } from '../ui/form-controls';
import { theme } from '../theme/tokens';

type CarrierDashboardProps = {
  session: AuthResponse;
  apiBaseUrl: string;
  onGenerateInvite: () => Promise<void>;
  onReloadDashboard: () => Promise<void>;
  data: CarrierDashboardModel;
  invite: InviteResponse | null;
  message: string | null;
  busy: boolean;
  onLogout: () => Promise<void>;
};

type TopTab = 'offers' | 'auctions' | 'chat';
type BottomTab = 'dashboard' | 'aste' | 'carichi' | 'messaggi' | 'profilo';

type BoardItem = {
  id: string;
  kind: string;
  kindTone: 'cold' | 'warm';
  title: string;
  subtitle: string;
  distance: string;
  priceLabel: string;
  expiryLabel: string;
  detailLabel: string;
};

type TripItem = {
  id: string;
  kind: string;
  kindTone: 'cold' | 'warm';
  statusLabel: string;
  routeLabel: string;
  progress: number;
};

export function CarrierDashboard({
  session,
  apiBaseUrl,
  onGenerateInvite,
  onReloadDashboard,
  data,
  invite,
  message,
  busy,
  onLogout,
}: CarrierDashboardProps) {
  const [topTab, setTopTab] = useState<TopTab>('auctions');
  const [bottomTab, setBottomTab] = useState<BottomTab>('dashboard');
  const [showManagement, setShowManagement] = useState(false);
  const [loadForm, setLoadForm] = useState(() => buildInitialLoadForm());
  const [loadBusy, setLoadBusy] = useState(false);
  const [loadMessage, setLoadMessage] = useState<string | null>(null);
  const [loads, setLoads] = useState<LoadResponse[]>([]);
  const [loadsBusy, setLoadsBusy] = useState(true);
  const [loadsMessage, setLoadsMessage] = useState<string | null>(null);
  const [auctionForm, setAuctionForm] = useState(() => buildInitialAuctionForm());
  const [auctionBusy, setAuctionBusy] = useState(false);
  const [auctionMessage, setAuctionMessage] = useState<string | null>(null);
  const [auctions, setAuctions] = useState<AuctionResponse[]>([]);
  const [auctionsBusy, setAuctionsBusy] = useState(true);
  const [auctionsMessage, setAuctionsMessage] = useState<string | null>(null);

  useEffect(() => {
    void refreshLoads(true);
  }, [apiBaseUrl, session.tokens.access_token]);

  useEffect(() => {
    void refreshAuctions(true);
  }, [apiBaseUrl, session.tokens.access_token]);

  async function refreshLoads(showLoader = false) {
    if (showLoader) {
      setLoadsBusy(true);
    }
    setLoadsMessage(null);
    try {
      const response = await authClient.listLoads(apiBaseUrl, session.tokens.access_token);
      setLoads(response.items);
    } catch (error) {
      setLoads([]);
      setLoadsMessage(error instanceof Error ? error.message : 'Errore nel caricamento carichi');
    } finally {
      if (showLoader) {
        setLoadsBusy(false);
      }
    }
  }

  async function refreshAuctions(showLoader = false) {
    if (showLoader) {
      setAuctionsBusy(true);
    }
    setAuctionsMessage(null);
    try {
      const response = await authClient.listAuctions(apiBaseUrl, session.tokens.access_token);
      setAuctions(response.items);
    } catch (error) {
      setAuctions([]);
      setAuctionsMessage(error instanceof Error ? error.message : 'Errore nel caricamento aste');
    } finally {
      if (showLoader) {
        setAuctionsBusy(false);
      }
    }
  }

  async function submitLoad() {
    setLoadBusy(true);
    setLoadMessage(null);
    try {
      const payload = toLoadPayload(loadForm);
      const created = await authClient.createLoad(apiBaseUrl, session.tokens.access_token, payload);
      setLoadMessage(`Carico ${created.code} creato con successo.`);
      setLoadForm(buildInitialLoadForm());
      await Promise.all([onReloadDashboard(), refreshLoads(false)]);
    } catch (error) {
      setLoadMessage(error instanceof Error ? error.message : 'Errore nella creazione del carico');
    } finally {
      setLoadBusy(false);
    }
  }

  async function submitAuction() {
    setAuctionBusy(true);
    setAuctionMessage(null);
    try {
      const payload = toAuctionPayload(auctionForm);
      const created = await authClient.createAuction(apiBaseUrl, session.tokens.access_token, payload);
      setAuctionMessage(`Asta ${created.load_code} creata con successo.`);
      setAuctionForm(buildInitialAuctionForm());
      await Promise.all([onReloadDashboard(), refreshLoads(false), refreshAuctions(false)]);
    } catch (error) {
      setAuctionMessage(error instanceof Error ? error.message : 'Errore nella creazione asta');
    } finally {
      setAuctionBusy(false);
    }
  }

  const offerItems = buildOfferItems(loads, data.activeLoads);
  const auctionItems = buildAuctionItems(auctions, data.liveAuctions);
  const tripItems = buildTripItems(loads, data.activeLoads);
  const chatItems = buildChatItems(message, invite, loadMessage, auctionMessage);
  const activeItems = topTab === 'offers' ? offerItems : topTab === 'chat' ? chatItems : auctionItems;
  const specialization = inferSpecialization(loads, auctions);
  const suggestionRoute = activeItems[0]?.title ?? 'tratte preferite IT-DE/FR';
  const notificationCount = [message, invite?.token, loadMessage, auctionMessage].filter(Boolean).length;

  function selectBottomTab(tab: BottomTab) {
    setBottomTab(tab);
    if (tab === 'aste') {
      setTopTab('auctions');
      setShowManagement(false);
      return;
    }
    if (tab === 'carichi') {
      setTopTab('offers');
      setShowManagement(false);
      return;
    }
    if (tab === 'messaggi') {
      setTopTab('chat');
      setShowManagement(false);
      return;
    }
    if (tab === 'profilo') {
      setShowManagement(true);
      return;
    }
    setShowManagement(false);
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.shell}>
        <View style={styles.deviceHeader}>
          <Text style={styles.clock}>9:41</Text>
          <View style={styles.statusDots}>
            <View style={styles.statusDot} />
            <View style={styles.statusDot} />
            <View style={styles.statusDotWide} />
          </View>
        </View>

        <View style={styles.profileRow}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{getInitials(session.company?.legal_name ?? session.user.first_name)}</Text>
          </View>
          <View style={styles.profileCopy}>
            <Text style={styles.profileTitle}>{session.company?.legal_name ?? 'Logistica Veloce'}</Text>
            <Text style={styles.profileSubtitle}>Specializzati · {specialization}</Text>
            <View style={styles.ratingRow}>
              <View style={styles.ratingPill}>
                <Text style={styles.ratingStar}>★</Text>
                <Text style={styles.ratingText}>{session.company?.compliance_blocked ? '4.3' : '4.8'}</Text>
              </View>
              <Text style={styles.ratingMeta}>{data.metrics[0]?.label ?? 'Carichi rilevanti'}</Text>
            </View>
          </View>
          <View style={styles.bellWrap}>
            <Text style={styles.bellIcon}>◌</Text>
            {notificationCount > 0 ? <View style={styles.notificationDot} /> : null}
          </View>
        </View>

        <View style={styles.topTabs}>
          <TopTabButton label="Le Mie Offerte" active={topTab === 'offers'} onPress={() => setTopTab('offers')} />
          <TopTabButton label="Aste Attive" active={topTab === 'auctions'} onPress={() => setTopTab('auctions')} />
          <TopTabButton label="Chat" active={topTab === 'chat'} onPress={() => setTopTab('chat')} />
        </View>

        <View style={styles.aiBanner}>
          <View style={styles.aiBadge}>
            <Text style={styles.aiBadgeText}>AI</Text>
          </View>
          <Text style={styles.aiBannerText}>Carichi rilevanti basati sulle tratte attive: {suggestionRoute}.</Text>
        </View>

        <View style={styles.marketList}>
          {activeItems.map((item) => (
            <MarketCard key={item.id} item={item} />
          ))}
          {(topTab === 'offers' && loadsBusy) || (topTab === 'auctions' && auctionsBusy) ? (
            <Text style={styles.inlineMessage}>Caricamento dati operativi...</Text>
          ) : null}
          {topTab === 'offers' && loadsMessage ? <Text style={styles.inlineMessage}>{loadsMessage}</Text> : null}
          {topTab === 'auctions' && auctionsMessage ? <Text style={styles.inlineMessage}>{auctionsMessage}</Text> : null}
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>I Tuoi Viaggi</Text>
        </View>
        <View style={styles.tripList}>
          {tripItems.map((item) => (
            <TripProgressCard key={item.id} item={item} />
          ))}
        </View>

        <TouchableOpacity style={styles.managementToggle} onPress={() => setShowManagement((current) => !current)}>
          <View>
            <Text style={styles.managementTitle}>Gestione rapida</Text>
            <Text style={styles.managementSubtitle}>Inviti, creazione carichi e aste senza sporcare la home principale.</Text>
          </View>
          <Text style={styles.managementChevron}>{showManagement ? '−' : '+'}</Text>
        </TouchableOpacity>

        {showManagement ? (
          <View style={styles.managementPanel}>
            <View style={styles.quickActionsRow}>
              <PillButton label="Genera Invito" onPress={() => void onGenerateInvite()} disabled={busy} />
              <PillButton label="Disconnetti" onPress={() => void onLogout()} variant="secondary" />
            </View>
            {message ? <Text style={styles.inlineMessage}>{message}</Text> : null}
            {invite ? <Text style={styles.inviteCode}>Invito: {invite.token}</Text> : null}

            <View style={styles.formBlock}>
              <Text style={styles.formTitle}>Nuovo carico</Text>
              <Field
                label="Titolo"
                value={loadForm.title}
                onChangeText={(value) => setLoadForm((current) => ({ ...current, title: value }))}
                placeholder="Bilico frigo Milano -> Berlino"
              />
              <View style={styles.gridRow}>
                <View style={styles.gridColumn}>
                  <Field label="Origine" value={loadForm.originLabel} onChangeText={(value) => setLoadForm((current) => ({ ...current, originLabel: value }))} placeholder="Milano" />
                </View>
                <View style={styles.gridColumn}>
                  <Field label="Destinazione" value={loadForm.destinationLabel} onChangeText={(value) => setLoadForm((current) => ({ ...current, destinationLabel: value }))} placeholder="Berlino" />
                </View>
              </View>
              <View style={styles.gridRow}>
                <View style={styles.gridColumn}>
                  <Field label="Pickup ISO" value={loadForm.pickupWindowStart} onChangeText={(value) => setLoadForm((current) => ({ ...current, pickupWindowStart: value }))} autoCapitalize="none" placeholder="2026-03-17T06:00:00" />
                </View>
                <View style={styles.gridColumn}>
                  <Field label="Delivery ISO" value={loadForm.deliveryWindowEnd} onChangeText={(value) => setLoadForm((current) => ({ ...current, deliveryWindowEnd: value }))} autoCapitalize="none" placeholder="2026-03-17T18:00:00" />
                </View>
              </View>
              <View style={styles.gridRow}>
                <View style={styles.gridColumn}>
                  <Field label="Budget EUR" value={loadForm.budgetAmount} onChangeText={(value) => setLoadForm((current) => ({ ...current, budgetAmount: value }))} keyboardType="numeric" placeholder="1450" />
                </View>
                <View style={styles.gridColumn}>
                  <Field label="Mezzo" value={loadForm.vehicleKind} onChangeText={(value) => setLoadForm((current) => ({ ...current, vehicleKind: value as VehicleKind }))} autoCapitalize="none" placeholder="frigo" />
                </View>
              </View>
              <Field label="ADR richiesto" value={loadForm.adrRequired} onChangeText={(value) => setLoadForm((current) => ({ ...current, adrRequired: value }))} autoCapitalize="none" placeholder="no" />
              <PillButton label={loadBusy ? 'Creazione in corso' : 'Crea carico'} onPress={() => void submitLoad()} disabled={loadBusy} />
              {loadMessage ? <Text style={styles.inlineMessage}>{loadMessage}</Text> : null}
            </View>

            <View style={styles.formBlock}>
              <Text style={styles.formTitle}>Nuova asta</Text>
              <View style={styles.gridRow}>
                <View style={styles.gridColumn}>
                  <Field label="Codice carico" value={auctionForm.loadCode} onChangeText={(value) => setAuctionForm((current) => ({ ...current, loadCode: value }))} autoCapitalize="characters" placeholder="LD2603-0001" />
                </View>
                <View style={styles.gridColumn}>
                  <Field label="Modalita" value={auctionForm.mode} onChangeText={(value) => setAuctionForm((current) => ({ ...current, mode: value as AuctionMode }))} autoCapitalize="none" placeholder="reverse" />
                </View>
              </View>
              <View style={styles.gridRow}>
                <View style={styles.gridColumn}>
                  <Field label="Prezzo base" value={auctionForm.floorPrice} onChangeText={(value) => setAuctionForm((current) => ({ ...current, floorPrice: value }))} keyboardType="numeric" placeholder="1200" />
                </View>
                <View style={styles.gridColumn}>
                  <Field label="Prezzo massimo" value={auctionForm.ceilingPrice} onChangeText={(value) => setAuctionForm((current) => ({ ...current, ceilingPrice: value }))} keyboardType="numeric" placeholder="1500" />
                </View>
              </View>
              <View style={styles.gridRow}>
                <View style={styles.gridColumn}>
                  <Field label="Start ISO" value={auctionForm.startsAt} onChangeText={(value) => setAuctionForm((current) => ({ ...current, startsAt: value }))} autoCapitalize="none" placeholder="2026-03-16T10:00:00" />
                </View>
                <View style={styles.gridColumn}>
                  <Field label="End ISO" value={auctionForm.endsAt} onChangeText={(value) => setAuctionForm((current) => ({ ...current, endsAt: value }))} autoCapitalize="none" placeholder="2026-03-16T14:00:00" />
                </View>
              </View>
              <PillButton label={auctionBusy ? 'Creazione in corso' : 'Crea asta'} onPress={() => void submitAuction()} disabled={auctionBusy} />
              {auctionMessage ? <Text style={styles.inlineMessage}>{auctionMessage}</Text> : null}
            </View>

            <View style={styles.metaCard}>
              <Text style={styles.metaLabel}>API</Text>
              <Text style={styles.metaValue}>{apiBaseUrl}</Text>
              <Text style={styles.metaLabel}>Email</Text>
              <Text style={styles.metaValue}>{session.user.email}</Text>
              <Text style={styles.metaLabel}>Partita IVA</Text>
              <Text style={styles.metaValue}>{session.company?.vat_number ?? 'non disponibile'}</Text>
            </View>
          </View>
        ) : null}

        <View style={styles.bottomNav}>
          <BottomTabButton label="Dashboard" active={bottomTab === 'dashboard'} onPress={() => selectBottomTab('dashboard')} />
          <BottomTabButton label="Aste" active={bottomTab === 'aste'} onPress={() => selectBottomTab('aste')} />
          <BottomTabButton label="Cerca Carico" active={bottomTab === 'carichi'} onPress={() => selectBottomTab('carichi')} />
          <BottomTabButton label="Messaggi" active={bottomTab === 'messaggi'} badge={notificationCount > 0 ? String(notificationCount) : undefined} onPress={() => selectBottomTab('messaggi')} />
          <BottomTabButton label="Profilo" active={bottomTab === 'profilo'} onPress={() => selectBottomTab('profilo')} />
        </View>
      </View>
    </ScrollView>
  );
}

type LoadFormState = {
  title: string;
  originLabel: string;
  destinationLabel: string;
  pickupWindowStart: string;
  deliveryWindowEnd: string;
  budgetAmount: string;
  vehicleKind: VehicleKind;
  adrRequired: string;
};

type AuctionFormState = {
  loadCode: string;
  mode: AuctionMode;
  floorPrice: string;
  ceilingPrice: string;
  startsAt: string;
  endsAt: string;
};

function buildInitialLoadForm(): LoadFormState {
  return {
    title: '',
    originLabel: '',
    destinationLabel: '',
    pickupWindowStart: buildIsoOffset(6),
    deliveryWindowEnd: buildIsoOffset(18),
    budgetAmount: '',
    vehicleKind: 'frigo',
    adrRequired: 'no',
  };
}

function buildInitialAuctionForm(): AuctionFormState {
  return {
    loadCode: '',
    mode: 'reverse',
    floorPrice: '',
    ceilingPrice: '',
    startsAt: buildIsoOffset(1),
    endsAt: buildIsoOffset(5),
  };
}

function buildIsoOffset(offsetHours: number): string {
  const value = new Date(Date.now() + offsetHours * 60 * 60 * 1000);
  return value.toISOString().slice(0, 19);
}

function toLoadPayload(form: LoadFormState): LoadCreatePayload {
  return {
    title: form.title.trim(),
    origin_label: form.originLabel.trim(),
    destination_label: form.destinationLabel.trim(),
    pickup_window_start: form.pickupWindowStart.trim(),
    delivery_window_end: form.deliveryWindowEnd.trim(),
    budget_amount: form.budgetAmount.trim() ? Number(form.budgetAmount) : undefined,
    vehicle_kind: form.vehicleKind,
    adr_required: form.adrRequired.trim().toLowerCase() === 'yes',
  };
}

function toAuctionPayload(form: AuctionFormState): AuctionCreatePayload {
  return {
    load_code: form.loadCode.trim().toUpperCase(),
    mode: form.mode,
    floor_price: form.floorPrice.trim() ? Number(form.floorPrice) : undefined,
    ceiling_price: form.ceilingPrice.trim() ? Number(form.ceilingPrice) : undefined,
    starts_at: form.startsAt.trim(),
    ends_at: form.endsAt.trim(),
  };
}

function inferSpecialization(loads: LoadResponse[], auctions: AuctionResponse[]): string {
  const kinds = [...loads.map((item) => item.vehicle_kind), ...auctions.map((item) => inferKindFromTitle(item.load_title))];
  const first = kinds.find(Boolean);
  if (first === 'telonato') {
    return 'Bilico Telonato';
  }
  if (first === 'furgone') {
    return 'Furgone Espresso';
  }
  return 'Bilico Frigo';
}

function buildOfferItems(loads: LoadResponse[], fallbackItems: CarrierDashboardModel['activeLoads']): BoardItem[] {
  if (loads.length > 0) {
    return loads.slice(0, 3).map((load) => ({
      id: load.id,
      kind: humanizeKind(load.vehicle_kind),
      kindTone: load.vehicle_kind === 'frigo' ? 'cold' : 'warm',
      title: `${load.origin_label.toUpperCase()} -> ${load.destination_label.toUpperCase()}`,
      subtitle: `${humanizeKind(load.vehicle_kind)}${load.adr_required ? ' · ADR' : ''}`,
      distance: buildDistance(load.origin_label, load.destination_label),
      priceLabel: typeof load.budget_amount === 'number' ? `Offerta Attuale: €${Math.round(load.budget_amount)}` : 'Offerta da definire',
      expiryLabel: statusToCopy(load.status),
      detailLabel: 'Vedi Dettagli',
    }));
  }

  return fallbackItems.slice(0, 3).map((item, index) => ({
    id: item.id,
    kind: index % 2 === 0 ? 'Frigo' : 'Telonato',
    kindTone: index % 2 === 0 ? 'cold' : 'warm',
    title: item.title,
    subtitle: item.subtitle,
    distance: '1,030 km',
    priceLabel: item.meta,
    expiryLabel: statusToCopy(item.status),
    detailLabel: 'Vedi Dettagli',
  }));
}

function formatIso(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function buildAuctionItems(auctions: AuctionResponse[], fallbackItems: CarrierDashboardModel['liveAuctions']): BoardItem[] {
  if (auctions.length > 0) {
    return auctions.slice(0, 3).map((auction, index) => ({
      id: auction.id,
      kind: inferKindFromTitle(auction.load_title),
      kindTone: index % 2 === 0 ? 'cold' : 'warm',
      title: auction.load_title.toUpperCase(),
      subtitle: `${auction.load_code} · ${auction.mode === 'reverse' ? 'Asta ribasso' : 'Asta rialzo'}`,
      distance: buildDistanceFromTitle(auction.load_title),
      priceLabel: buildAuctionPriceLabel(auction),
      expiryLabel: buildAuctionExpiryLabel(auction),
      detailLabel: 'Vedi Dettagli',
    }));
  }

  return fallbackItems.slice(0, 3).map((item, index) => ({
    id: item.id,
    kind: index % 2 === 0 ? 'Frigo' : 'Telonato',
    kindTone: index % 2 === 0 ? 'cold' : 'warm',
    title: item.title,
    subtitle: item.subtitle,
    distance: '1,020 km',
    priceLabel: item.meta,
    expiryLabel: statusToCopy(item.status),
    detailLabel: 'Vedi Dettagli',
  }));
}

function buildTripItems(loads: LoadResponse[], fallbackItems: CarrierDashboardModel['activeLoads']): TripItem[] {
  if (loads.length > 0) {
    return loads.slice(0, 2).map((load, index) => ({
      id: load.id,
      kind: humanizeKind(load.vehicle_kind),
      kindTone: load.vehicle_kind === 'frigo' ? 'cold' : 'warm',
      statusLabel: load.status === 'auction_live' ? 'In offerta' : load.status === 'open' ? 'In pubblicazione' : 'In consegna',
      routeLabel: `${load.origin_label.toUpperCase()} -> ${load.destination_label.toUpperCase()}`,
      progress: index === 0 ? 0.78 : 0.44,
    }));
  }

  return fallbackItems.slice(0, 2).map((item, index) => ({
    id: item.id,
    kind: index === 0 ? 'Frigo' : 'Telonato',
    kindTone: index === 0 ? 'cold' : 'warm',
    statusLabel: index === 0 ? 'In Consegna' : 'Al Carico',
    routeLabel: item.title.replace('|', '').trim(),
    progress: index === 0 ? 0.82 : 0.47,
  }));
}

function buildChatItems(
  message: string | null,
  invite: InviteResponse | null,
  loadMessage: string | null,
  auctionMessage: string | null,
): BoardItem[] {
  const notes = [
    invite ? `Codice invito pronto: ${invite.token}` : null,
    message,
    loadMessage,
    auctionMessage,
  ].filter((item): item is string => Boolean(item));

  if (notes.length === 0) {
    return [
      {
        id: 'chat-empty',
        kind: 'Chat',
        kindTone: 'cold',
        title: 'Nessun messaggio urgente',
        subtitle: 'Le comunicazioni operative compariranno qui',
        distance: 'Chat aziendale',
        priceLabel: 'Inviti, note e azioni recenti',
        expiryLabel: 'Tutto aggiornato',
        detailLabel: 'Apri Chat',
      },
    ];
  }

  return notes.slice(0, 3).map((note, index) => ({
    id: `chat-${index}`,
    kind: 'Chat',
    kindTone: index % 2 === 0 ? 'cold' : 'warm',
    title: note,
    subtitle: 'Aggiornamento operativo',
    distance: 'Messaggi recenti',
    priceLabel: 'Stato sincronizzato con backend',
    expiryLabel: 'Nuovo',
    detailLabel: 'Apri',
  }));
}

function buildDistance(origin: string, destination: string): string {
  const seed = origin.length * 17 + destination.length * 13;
  const value = 850 + (seed % 320);
  return `${value.toLocaleString('it-IT')} km`;
}

function buildDistanceFromTitle(title: string): string {
  const seed = title.length * 23;
  const value = 780 + (seed % 410);
  return `${value.toLocaleString('it-IT')} km`;
}

function buildAuctionPriceLabel(auction: AuctionResponse): string {
  if (typeof auction.floor_price === 'number') {
    return `Prezzo Base: €${Math.round(auction.floor_price)}`;
  }
  if (typeof auction.ceiling_price === 'number') {
    return `Prezzo Max: €${Math.round(auction.ceiling_price)}`;
  }
  return 'Prezzo in definizione';
}

function buildAuctionExpiryLabel(auction: AuctionResponse): string {
  const end = new Date(auction.ends_at);
  const minutes = Math.max(1, Math.round((end.getTime() - Date.now()) / 60000));
  if (minutes <= 60) {
    return `Termina in ${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;
  return `${hours}h ${restMinutes}m rimasti`;
}

function statusToCopy(status: 'live' | 'planned' | 'attention' | LoadResponse['status']): string {
  if (status === 'attention' || status === 'open') {
    return 'Appena inserito';
  }
  if (status === 'live' || status === 'auction_live') {
    return '01h 14m rimasti';
  }
  if (status === 'assigned') {
    return 'Missione confermata';
  }
  return 'In pianificazione';
}

function humanizeKind(kind: VehicleKind): string {
  if (kind === 'frigo') {
    return 'Frigo';
  }
  if (kind === 'telonato') {
    return 'Telonato';
  }
  if (kind === 'furgone') {
    return 'Furgone';
  }
  if (kind === 'cisterna') {
    return 'Cisterna';
  }
  return 'Cassonato';
}

function inferKindFromTitle(title: string): VehicleKind {
  const normalized = title.toLowerCase();
  if (normalized.includes('telon')) {
    return 'telonato';
  }
  if (normalized.includes('furg')) {
    return 'furgone';
  }
  if (normalized.includes('cistern')) {
    return 'cisterna';
  }
  if (normalized.includes('casson')) {
    return 'cassonato';
  }
  return 'frigo';
}

function getInitials(value: string): string {
  return value
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

function TopTabButton({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return (
    <TouchableOpacity style={[styles.topTabButton, active ? styles.topTabButtonActive : null]} onPress={onPress}>
      <Text style={[styles.topTabText, active ? styles.topTabTextActive : null]}>{label}</Text>
    </TouchableOpacity>
  );
}

function BottomTabButton({
  label,
  active,
  badge,
  onPress,
}: {
  label: string;
  active: boolean;
  badge?: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={styles.bottomTabButton} onPress={onPress}>
      <View style={styles.bottomIconWrap}>
        <View style={[styles.bottomIcon, active ? styles.bottomIconActive : null]} />
        {badge ? (
          <View style={styles.bottomBadge}>
            <Text style={styles.bottomBadgeText}>{badge}</Text>
          </View>
        ) : null}
      </View>
      <Text style={[styles.bottomTabText, active ? styles.bottomTabTextActive : null]}>{label}</Text>
    </TouchableOpacity>
  );
}

function MarketCard({ item }: { item: BoardItem }) {
  return (
    <View style={styles.marketCard}>
      <View style={[styles.kindBadge, item.kindTone === 'cold' ? styles.kindBadgeCold : styles.kindBadgeWarm]}>
        <Text style={styles.kindBadgeText}>{item.kind}</Text>
      </View>
      <View style={styles.marketMain}>
        <Text style={styles.marketTitle}>{item.title}</Text>
        <Text style={styles.marketSubtitle}>{item.subtitle}</Text>
        <View style={styles.marketMetaRow}>
          <Text style={styles.marketMetaPrimary}>{item.expiryLabel}</Text>
          <Text style={styles.marketMetaSecondary}>{item.distance}</Text>
        </View>
        <View style={styles.marketFooter}>
          <Text style={styles.marketPrice}>{item.priceLabel}</Text>
          <View style={styles.detailButton}>
            <Text style={styles.detailButtonText}>{item.detailLabel}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

function TripProgressCard({ item }: { item: TripItem }) {
  return (
    <View style={styles.tripCard}>
      <View style={[styles.tripKindBadge, item.kindTone === 'cold' ? styles.kindBadgeCold : styles.kindBadgeWarm]}>
        <Text style={styles.kindBadgeText}>{item.kind}</Text>
      </View>
      <View style={styles.tripMain}>
        <Text style={styles.tripStatus}>{item.statusLabel}: <Text style={styles.tripRoute}>{item.routeLabel}</Text></Text>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${Math.round(item.progress * 100)}%` }]} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#dfe9f5',
  },
  content: {
    padding: 18,
    alignItems: 'center',
  },
  shell: {
    width: '100%',
    maxWidth: 430,
    backgroundColor: '#ffffff',
    borderRadius: 30,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 22,
    shadowColor: '#223b5a',
    shadowOpacity: 0.12,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 16 },
    elevation: 10,
  },
  deviceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  clock: {
    fontFamily: theme.font.heading,
    fontSize: 16,
    color: '#161f2c',
  },
  statusDots: {
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
  },
  statusDot: {
    width: 5,
    height: 5,
    borderRadius: 999,
    backgroundColor: '#111827',
  },
  statusDotWide: {
    width: 18,
    height: 8,
    borderRadius: 999,
    backgroundColor: '#111827',
  },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: '#d9ecff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontFamily: theme.font.heading,
    fontSize: 16,
    color: '#214d7b',
  },
  profileCopy: {
    flex: 1,
    gap: 2,
  },
  profileTitle: {
    fontFamily: theme.font.heading,
    fontSize: 17,
    color: '#111827',
  },
  profileSubtitle: {
    fontFamily: theme.font.body,
    fontSize: 13,
    color: '#596579',
  },
  ratingRow: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
    marginTop: 2,
  },
  ratingPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#fff5d9',
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  ratingStar: {
    color: '#d59510',
    fontSize: 12,
  },
  ratingText: {
    fontFamily: theme.font.heading,
    fontSize: 12,
    color: '#5c4200',
  },
  ratingMeta: {
    fontFamily: theme.font.body,
    fontSize: 12,
    color: '#677285',
  },
  bellWrap: {
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  bellIcon: {
    fontSize: 18,
    color: '#111827',
  },
  notificationDot: {
    position: 'absolute',
    top: 2,
    right: 2,
    width: 7,
    height: 7,
    borderRadius: 999,
    backgroundColor: '#ef4444',
  },
  topTabs: {
    flexDirection: 'row',
    marginTop: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#dde5ef',
  },
  topTabButton: {
    paddingVertical: 10,
    paddingHorizontal: 8,
    marginRight: 14,
  },
  topTabButtonActive: {
    borderBottomWidth: 2,
    borderBottomColor: '#245da6',
  },
  topTabText: {
    fontFamily: theme.font.body,
    fontSize: 14,
    color: '#637082',
  },
  topTabTextActive: {
    color: '#1d4f91',
    fontFamily: theme.font.heading,
  },
  aiBanner: {
    flexDirection: 'row',
    gap: 10,
    alignItems: 'center',
    backgroundColor: '#eef4ff',
    borderRadius: 14,
    padding: 12,
    marginTop: 12,
    marginBottom: 14,
  },
  aiBadge: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#d9ebff',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#9bc2f2',
  },
  aiBadgeText: {
    fontFamily: theme.font.heading,
    fontSize: 11,
    color: '#215b9b',
  },
  aiBannerText: {
    flex: 1,
    fontFamily: theme.font.body,
    fontSize: 13,
    lineHeight: 18,
    color: '#30455f',
  },
  marketList: {
    gap: 10,
  },
  marketCard: {
    flexDirection: 'row',
    gap: 12,
    backgroundColor: '#ffffff',
    borderRadius: 18,
    padding: 10,
    borderWidth: 1,
    borderColor: '#dde5ef',
    shadowColor: '#243b53',
    shadowOpacity: 0.06,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
    elevation: 2,
  },
  kindBadge: {
    width: 58,
    minHeight: 58,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  kindBadgeCold: {
    backgroundColor: '#dff1ff',
  },
  kindBadgeWarm: {
    backgroundColor: '#fff0cf',
  },
  kindBadgeText: {
    fontFamily: theme.font.heading,
    fontSize: 13,
    textAlign: 'center',
    color: '#2b4158',
  },
  marketMain: {
    flex: 1,
    gap: 4,
  },
  marketTitle: {
    fontFamily: theme.font.heading,
    fontSize: 18,
    color: '#101828',
  },
  marketSubtitle: {
    fontFamily: theme.font.heading,
    fontSize: 14,
    color: '#1f2937',
  },
  marketMetaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 10,
  },
  marketMetaPrimary: {
    fontFamily: theme.font.body,
    fontSize: 13,
    color: '#cf4b34',
  },
  marketMetaSecondary: {
    fontFamily: theme.font.body,
    fontSize: 13,
    color: '#5d6b7d',
  },
  marketFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 10,
    marginTop: 2,
  },
  marketPrice: {
    flex: 1,
    fontFamily: theme.font.body,
    fontSize: 13,
    color: '#111827',
  },
  detailButton: {
    backgroundColor: '#2b67ad',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  detailButtonText: {
    fontFamily: theme.font.heading,
    fontSize: 12,
    color: '#ffffff',
  },
  sectionHeader: {
    marginTop: 16,
    marginBottom: 10,
  },
  sectionTitle: {
    fontFamily: theme.font.heading,
    fontSize: 16,
    color: '#141b26',
  },
  tripList: {
    gap: 10,
  },
  tripCard: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#dde5ef',
    padding: 10,
  },
  tripKindBadge: {
    width: 58,
    minHeight: 46,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  tripMain: {
    flex: 1,
    gap: 8,
  },
  tripStatus: {
    fontFamily: theme.font.body,
    fontSize: 13,
    color: '#4b5563',
  },
  tripRoute: {
    fontFamily: theme.font.heading,
    color: '#111827',
  },
  progressTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: '#e5e7eb',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: '#3cb85b',
  },
  managementToggle: {
    marginTop: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#dde5ef',
    backgroundColor: '#f7f9fc',
    padding: 14,
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 10,
    alignItems: 'center',
  },
  managementTitle: {
    fontFamily: theme.font.heading,
    fontSize: 15,
    color: '#111827',
  },
  managementSubtitle: {
    fontFamily: theme.font.body,
    fontSize: 12,
    lineHeight: 17,
    color: '#64748b',
    maxWidth: 270,
  },
  managementChevron: {
    fontFamily: theme.font.heading,
    fontSize: 24,
    color: '#2b67ad',
  },
  managementPanel: {
    marginTop: 12,
    gap: 12,
  },
  quickActionsRow: {
    gap: 10,
  },
  formBlock: {
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#dde5ef',
    backgroundColor: '#ffffff',
    padding: 14,
    gap: 10,
  },
  formTitle: {
    fontFamily: theme.font.heading,
    fontSize: 15,
    color: '#111827',
  },
  gridRow: {
    flexDirection: 'row',
    gap: 12,
    flexWrap: 'wrap',
  },
  gridColumn: {
    flex: 1,
    minWidth: 140,
  },
  metaCard: {
    borderRadius: 18,
    backgroundColor: '#f7f9fc',
    padding: 14,
    gap: 4,
    borderWidth: 1,
    borderColor: '#dde5ef',
  },
  metaLabel: {
    fontFamily: theme.font.body,
    fontSize: 11,
    textTransform: 'uppercase',
    color: '#6b7280',
    letterSpacing: 1.2,
  },
  metaValue: {
    fontFamily: theme.font.body,
    fontSize: 13,
    color: '#111827',
    marginBottom: 6,
  },
  inlineMessage: {
    fontFamily: theme.font.body,
    fontSize: 12,
    lineHeight: 18,
    color: '#6b7280',
  },
  inviteCode: {
    fontFamily: theme.font.heading,
    fontSize: 14,
    color: '#2b67ad',
  },
  bottomNav: {
    marginTop: 18,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    paddingTop: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  bottomTabButton: {
    alignItems: 'center',
    gap: 4,
    flex: 1,
  },
  bottomIconWrap: {
    position: 'relative',
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bottomIcon: {
    width: 16,
    height: 16,
    borderRadius: 4,
    borderWidth: 1.5,
    borderColor: '#8b96a6',
    backgroundColor: 'transparent',
  },
  bottomIconActive: {
    borderColor: '#2b67ad',
    backgroundColor: '#dcecff',
  },
  bottomTabText: {
    fontFamily: theme.font.body,
    fontSize: 11,
    color: '#6b7280',
    textAlign: 'center',
  },
  bottomTabTextActive: {
    color: '#2b67ad',
    fontFamily: theme.font.heading,
  },
  bottomBadge: {
    position: 'absolute',
    top: -4,
    right: -6,
    minWidth: 16,
    height: 16,
    borderRadius: 999,
    backgroundColor: '#ef4444',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  bottomBadgeText: {
    fontFamily: theme.font.heading,
    fontSize: 10,
    color: '#ffffff',
  },
});
