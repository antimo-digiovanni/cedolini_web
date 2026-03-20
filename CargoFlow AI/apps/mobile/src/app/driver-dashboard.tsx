import { useState } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { AuthResponse } from '../api/auth-client';
import { DriverDashboardModel } from './dashboard-data';
import { PillButton } from '../ui/form-controls';
import { theme } from '../theme/tokens';

type DriverDashboardProps = {
  session: AuthResponse;
  apiBaseUrl: string;
  data: DriverDashboardModel;
  onLogout: () => Promise<void>;
};

type TopTab = 'missioni' | 'checklist' | 'chat';
type BottomTab = 'dashboard' | 'viaggi' | 'carichi' | 'messaggi' | 'profilo';

type MissionCardModel = {
  id: string;
  kind: string;
  kindTone: 'cold' | 'warm';
  title: string;
  subtitle: string;
  statusLabel: string;
  metaLabel: string;
  cta: string;
};

type DriverTripModel = {
  id: string;
  kind: string;
  kindTone: 'cold' | 'warm';
  statusLabel: string;
  routeLabel: string;
  progress: number;
};

export function DriverDashboard({ session, apiBaseUrl, data, onLogout }: DriverDashboardProps) {
  const [topTab, setTopTab] = useState<TopTab>('missioni');
  const [bottomTab, setBottomTab] = useState<BottomTab>('dashboard');
  const [showProfilePanel, setShowProfilePanel] = useState(false);

  const missionCards = buildMissionCards(data.assignedTrips);
  const checklistCards = buildChecklistCards(data.todayChecklist);
  const chatCards = buildChatCards(data.alerts);
  const tripCards = buildTripCards(data.assignedTrips);
  const activeCards = topTab === 'missioni' ? missionCards : topTab === 'checklist' ? checklistCards : chatCards;

  function selectBottomTab(tab: BottomTab) {
    setBottomTab(tab);
    if (tab === 'viaggi') {
      setTopTab('missioni');
      setShowProfilePanel(false);
      return;
    }
    if (tab === 'messaggi') {
      setTopTab('chat');
      setShowProfilePanel(false);
      return;
    }
    if (tab === 'profilo') {
      setShowProfilePanel(true);
      return;
    }
    if (tab === 'carichi') {
      setTopTab('checklist');
      setShowProfilePanel(false);
      return;
    }
    setShowProfilePanel(false);
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
            <Text style={styles.avatarText}>{getInitials(`${session.user.first_name} ${session.user.last_name}`)}</Text>
          </View>
          <View style={styles.profileCopy}>
            <Text style={styles.profileTitle}>{session.user.first_name} {session.user.last_name}</Text>
            <Text style={styles.profileSubtitle}>{session.company?.legal_name ?? 'Azienda collegata'} · Autista operativo</Text>
            <View style={styles.ratingRow}>
              <View style={styles.ratingPill}>
                <Text style={styles.ratingStar}>★</Text>
                <Text style={styles.ratingText}>4.9</Text>
              </View>
              <Text style={styles.ratingMeta}>{data.metrics[0]?.value ?? '0'} missioni oggi</Text>
            </View>
          </View>
          <View style={styles.bellWrap}>
            <Text style={styles.bellIcon}>◌</Text>
            {data.alerts.length > 0 ? <View style={styles.notificationDot} /> : null}
          </View>
        </View>

        <View style={styles.topTabs}>
          <TopTabButton label="I Miei Viaggi" active={topTab === 'missioni'} onPress={() => setTopTab('missioni')} />
          <TopTabButton label="Checklist" active={topTab === 'checklist'} onPress={() => setTopTab('checklist')} />
          <TopTabButton label="Chat" active={topTab === 'chat'} onPress={() => setTopTab('chat')} />
        </View>

        <View style={styles.aiBanner}>
          <View style={styles.aiBadge}>
            <Text style={styles.aiBadgeText}>AI</Text>
          </View>
          <Text style={styles.aiBannerText}>Missioni e alert prioritizzati in base a geofence, scadenze e documenti richiesti.</Text>
        </View>

        <View style={styles.marketList}>
          {activeCards.map((item) => (
            <MissionCard key={item.id} item={item} />
          ))}
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Progresso Viaggi</Text>
        </View>
        <View style={styles.tripList}>
          {tripCards.map((item) => (
            <TripProgressCard key={item.id} item={item} />
          ))}
        </View>

        <TouchableOpacity style={styles.managementToggle} onPress={() => setShowProfilePanel((current) => !current)}>
          <View>
            <Text style={styles.managementTitle}>Profilo e contesto</Text>
            <Text style={styles.managementSubtitle}>Dettagli account, endpoint connesso e azioni secondarie.</Text>
          </View>
          <Text style={styles.managementChevron}>{showProfilePanel ? '−' : '+'}</Text>
        </TouchableOpacity>

        {showProfilePanel ? (
          <View style={styles.managementPanel}>
            <View style={styles.metaCard}>
              <Text style={styles.metaLabel}>API</Text>
              <Text style={styles.metaValue}>{apiBaseUrl}</Text>
              <Text style={styles.metaLabel}>Email</Text>
              <Text style={styles.metaValue}>{session.user.email}</Text>
              <Text style={styles.metaLabel}>Azienda</Text>
              <Text style={styles.metaValue}>{session.company?.legal_name ?? 'non associata'}</Text>
            </View>
            <PillButton label="Disconnetti" onPress={() => void onLogout()} variant="secondary" />
          </View>
        ) : null}

        <View style={styles.bottomNav}>
          <BottomTabButton label="Dashboard" active={bottomTab === 'dashboard'} onPress={() => selectBottomTab('dashboard')} />
          <BottomTabButton label="Viaggi" active={bottomTab === 'viaggi'} onPress={() => selectBottomTab('viaggi')} />
          <BottomTabButton label="Check" active={bottomTab === 'carichi'} onPress={() => selectBottomTab('carichi')} />
          <BottomTabButton label="Messaggi" active={bottomTab === 'messaggi'} badge={data.alerts.length > 0 ? String(data.alerts.length) : undefined} onPress={() => selectBottomTab('messaggi')} />
          <BottomTabButton label="Profilo" active={bottomTab === 'profilo'} onPress={() => selectBottomTab('profilo')} />
        </View>
      </View>
    </ScrollView>
  );
}

function buildMissionCards(items: DriverDashboardModel['assignedTrips']): MissionCardModel[] {
  return items.slice(0, 3).map((item, index) => ({
    id: item.id,
    kind: index === 0 ? 'Frigo' : 'Telonato',
    kindTone: index === 0 ? 'cold' : 'warm',
    title: item.title,
    subtitle: item.subtitle,
    statusLabel: index === 0 ? 'In Consegna' : index === 1 ? 'Al Carico' : 'In partenza',
    metaLabel: item.meta,
    cta: 'Apri Viaggio',
  }));
}

function buildChecklistCards(items: DriverDashboardModel['todayChecklist']): MissionCardModel[] {
  return items.slice(0, 3).map((item, index) => ({
    id: item.id,
    kind: index === 0 ? 'Check' : 'Doc',
    kindTone: index === 0 ? 'cold' : 'warm',
    title: item.title,
    subtitle: item.subtitle,
    statusLabel: 'Da completare',
    metaLabel: item.meta,
    cta: 'Gestisci',
  }));
}

function buildChatCards(items: DriverDashboardModel['alerts']): MissionCardModel[] {
  if (items.length === 0) {
    return [
      {
        id: 'chat-empty',
        kind: 'Chat',
        kindTone: 'cold',
        title: 'Nessun alert urgente',
        subtitle: 'Messaggi e notifiche di viaggio compariranno qui',
        statusLabel: 'Allineato',
        metaLabel: 'Nessuna anomalia operativa rilevata',
        cta: 'Apri',
      },
    ];
  }

  return items.slice(0, 3).map((item, index) => ({
    id: item.id,
    kind: 'Chat',
    kindTone: index % 2 === 0 ? 'cold' : 'warm',
    title: item.title,
    subtitle: item.subtitle,
    statusLabel: 'Nuovo',
    metaLabel: item.meta,
    cta: 'Apri',
  }));
}

function buildTripCards(items: DriverDashboardModel['assignedTrips']): DriverTripModel[] {
  return items.slice(0, 2).map((item, index) => ({
    id: item.id,
    kind: index === 0 ? 'Frigo' : 'Telonato',
    kindTone: index === 0 ? 'cold' : 'warm',
    statusLabel: index === 0 ? 'In Consegna' : 'Al Carico',
    routeLabel: item.title.replace('Missione', '').trim(),
    progress: index === 0 ? 0.82 : 0.48,
  }));
}

function getInitials(value: string): string {
  return value
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
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

function MissionCard({ item }: { item: MissionCardModel }) {
  return (
    <View style={styles.marketCard}>
      <View style={[styles.kindBadge, item.kindTone === 'cold' ? styles.kindBadgeCold : styles.kindBadgeWarm]}>
        <Text style={styles.kindBadgeText}>{item.kind}</Text>
      </View>
      <View style={styles.marketMain}>
        <Text style={styles.marketTitle}>{item.title}</Text>
        <Text style={styles.marketSubtitle}>{item.subtitle}</Text>
        <View style={styles.marketMetaRow}>
          <Text style={styles.marketMetaPrimary}>{item.statusLabel}</Text>
          <Text style={styles.marketMetaSecondary}>{item.metaLabel}</Text>
        </View>
        <View style={styles.marketFooter}>
          <Text style={styles.marketPrice}>{item.metaLabel}</Text>
          <View style={styles.detailButton}>
            <Text style={styles.detailButtonText}>{item.cta}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

function TripProgressCard({ item }: { item: DriverTripModel }) {
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
    flex: 1,
    textAlign: 'right',
    fontFamily: theme.font.body,
    fontSize: 12,
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
