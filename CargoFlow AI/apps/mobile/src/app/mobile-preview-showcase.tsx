import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type PreviewMode = 'carrier' | 'driver';

type MobilePreviewShowcaseProps = {
  mode: PreviewMode;
  onModeChange?: (mode: PreviewMode) => void;
};

type PreviewViewModel = {
  modeLabel: string;
  heroTitle: string;
  heroCopy: string;
  heroMeta: string[];
  stats: Array<{ value: string; label: string; tone: 'blue' | 'amber' | 'mint' }>;
  marketTitle: string;
  cards: Array<{
    id: string;
    badge: string;
    badgeTone: 'cold' | 'warm' | 'mint';
    title: string;
    subtitle: string;
    tags: string[];
    leftMeta: string;
    rightMeta: string;
  }>;
  timelineTitle: string;
  timeline: Array<{ id: string; dot: string; title: string; subtitle: string; time: string; live?: boolean }>;
  assistantLabel: string;
  assistantTitle: string;
  assistantCopy: string;
  assistantActions: [string, string];
  navItems: string[];
  activeNav: string;
};

const views: Record<PreviewMode, PreviewViewModel> = {
  carrier: {
    modeLabel: 'Vista vettore',
    heroTitle: 'Logistica Veloce',
    heroCopy: 'Marketplace operativo compatto, con aste, viaggi e carichi in evidenza.',
    heroMeta: ['12 mezzi attivi', '4 aste live', 'Servizio 98,2%'],
    stats: [
      { value: '18', label: 'carichi oggi', tone: 'blue' },
      { value: '4', label: 'aste aperte', tone: 'amber' },
      { value: '92%', label: 'slot coperti', tone: 'mint' },
    ],
    marketTitle: 'Marketplace live',
    cards: [
      {
        id: 'carrier-1',
        badge: 'Frigo',
        badgeTone: 'cold',
        title: 'MILANO -> BERLINO',
        subtitle: 'Bilico frigo · farmaco · priorita alta',
        tags: ['ADR leggero', 'Baia 05:45', 'Ritorno utile'],
        leftMeta: '01h 14m rimasti',
        rightMeta: 'EUR 1.450',
      },
      {
        id: 'carrier-2',
        badge: 'Telonato',
        badgeTone: 'warm',
        title: 'ROMA -> PARIGI',
        subtitle: 'Asta live · 11 vettori invitati',
        tags: ['52 pallet', 'Pagamento 15gg', 'Chat aperta'],
        leftMeta: 'Termina in 45m',
        rightMeta: 'EUR 1.700',
      },
      {
        id: 'carrier-3',
        badge: 'Rapido',
        badgeTone: 'mint',
        title: 'VERONA -> MONACO',
        subtitle: 'Partenza serale · slot premium',
        tags: ['2 autisti', 'ETA 05:30', 'Firma digitale'],
        leftMeta: 'Pronto al match',
        rightMeta: 'EUR 980',
      },
    ],
    timelineTitle: 'Avanzamento viaggi',
    timeline: [
      { id: 'c-t1', dot: '1', title: 'Carico Milano', subtitle: 'Confermato e in attesa ingresso ribalta', time: '05:40' },
      { id: 'c-t2', dot: '2', title: 'Controllo confine', subtitle: 'Tratta autostradale libera, ETA aggiornata', time: '09:20' },
      { id: 'c-t3', dot: 'OK', title: 'Consegna Berlino', subtitle: 'Slot scarico prenotato dall assistente IA', time: '14:05', live: true },
    ],
    assistantLabel: 'Suggerimento IA',
    assistantTitle: 'Assistente CargoFlow',
    assistantCopy: 'Conviene chiudere ora l asta Roma -> Parigi: il miglior offerente puo confermare in meno di 3 minuti.',
    assistantActions: ['Accetta offerta', 'Apri dettagli'],
    navItems: ['Panoramica', 'Carichi', 'Aste', 'Profilo'],
    activeNav: 'Panoramica',
  },
  driver: {
    modeLabel: 'Vista autista',
    heroTitle: 'Luca Ferri',
    heroCopy: 'Cruscotto giornaliero pulito, con missione attiva, documenti e messaggi operativi.',
    heroMeta: ['Volvo FH 460', '2 missioni oggi', 'Valutazione 4,9'],
    stats: [
      { value: '2', label: 'missioni oggi', tone: 'blue' },
      { value: '1', label: 'CMR da inviare', tone: 'amber' },
      { value: '96%', label: 'puntualita', tone: 'mint' },
    ],
    marketTitle: 'Missioni e turni',
    cards: [
      {
        id: 'driver-1',
        badge: 'Frigo',
        badgeTone: 'cold',
        title: 'VERONA -> MONACO',
        subtitle: 'Missione attiva · geofence ok · ribalta prenotata',
        tags: ['T -4C', 'Dogana smart', 'Firma richiesta'],
        leftMeta: 'In consegna',
        rightMeta: '07:55 ETA',
      },
      {
        id: 'driver-2',
        badge: 'Hub',
        badgeTone: 'warm',
        title: 'TORINO -> LIONE',
        subtitle: 'Partenza prevista 05:30 · briefing letto',
        tags: ['Pedaggio incluso', 'Badge attivo', '2 messaggi'],
        leftMeta: 'Al carico',
        rightMeta: 'Partenza 06:10',
      },
      {
        id: 'driver-3',
        badge: 'Chat',
        badgeTone: 'mint',
        title: 'SALA OPERATIVA',
        subtitle: 'Canale operativo aperto con centrale e cliente',
        tags: ['4 non letti', 'Posizione live', 'Voce rapida'],
        leftMeta: 'Ultimo msg 2m fa',
        rightMeta: 'Rispondi',
      },
    ],
    timelineTitle: 'Roadbook dal vivo',
    timeline: [
      { id: 'd-t1', dot: 'A', title: 'Check mezzo', subtitle: 'Checklist completata senza anomalie', time: '04:50' },
      { id: 'd-t2', dot: 'B', title: 'Carico Verona', subtitle: 'Temperatura sigillata e documento validato', time: '05:35' },
      { id: 'd-t3', dot: 'OK', title: 'Scarico Monaco', subtitle: 'Cliente pronto. Restano 18 minuti alla finestra', time: '07:55', live: true },
    ],
    assistantLabel: 'Prossima azione',
    assistantTitle: 'Assistente di bordo',
    assistantCopy: 'Prima dello scarico prepara il CMR digitale: entrando nel geofence il cliente ricevera i dati precompilati.',
    assistantActions: ['Apri CMR', 'Chiama centrale'],
    navItems: ['Oggi', 'Chat', 'Documenti', 'Profilo'],
    activeNav: 'Oggi',
  },
};

export function MobilePreviewShowcase({ mode, onModeChange }: MobilePreviewShowcaseProps) {
  const view = views[mode];

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.phoneShell}>
        <View style={styles.topCard}>
          <View style={styles.statusRow}>
            <Text style={styles.statusPill}>CargoFlow AI</Text>
            <Text style={styles.statusPill}>Demo app</Text>
          </View>
          <Text style={styles.eyebrow}>Preview mobile</Text>
          <Text style={styles.title}>Interfaccia app React Native</Text>
          <Text style={styles.subtitle}>Questo e il passaggio corretto dal mock HTML alla schermata app vera.</Text>

          <View style={styles.switchRow}>
            <ModeButton label="Vettore" active={mode === 'carrier'} onPress={() => onModeChange?.('carrier')} />
            <ModeButton label="Autista" active={mode === 'driver'} onPress={() => onModeChange?.('driver')} />
          </View>

          <View style={styles.statsRow}>
            {view.stats.map((item) => (
              <View key={item.label} style={[styles.statCard, item.tone === 'blue' ? styles.statBlue : item.tone === 'amber' ? styles.statAmber : styles.statMint]}>
                <Text style={styles.statValue}>{item.value}</Text>
                <Text style={styles.statLabel}>{item.label}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={styles.heroCard}>
          <Text style={styles.heroEyebrow}>{view.modeLabel}</Text>
          <Text style={styles.heroTitle}>{view.heroTitle}</Text>
          <Text style={styles.heroCopy}>{view.heroCopy}</Text>
          <View style={styles.heroMetaRow}>
            {view.heroMeta.map((item) => (
              <View key={item} style={styles.heroPill}>
                <Text style={styles.heroPillText}>{item}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{view.marketTitle}</Text>
          <Text style={styles.sectionLink}>Aggiorna</Text>
        </View>

        <View style={styles.stack}>
          {view.cards.map((card) => (
            <View key={card.id} style={styles.marketCard}>
              <View style={[styles.badge, card.badgeTone === 'cold' ? styles.badgeCold : card.badgeTone === 'warm' ? styles.badgeWarm : styles.badgeMint]}>
                <Text style={styles.badgeText}>{card.badge}</Text>
              </View>
              <View style={styles.marketBody}>
                <Text style={styles.marketTitle}>{card.title}</Text>
                <Text style={styles.marketSubtitle}>{card.subtitle}</Text>
                <View style={styles.tagRow}>
                  {card.tags.map((tag) => (
                    <View key={tag} style={styles.tagPill}>
                      <Text style={styles.tagText}>{tag}</Text>
                    </View>
                  ))}
                </View>
                <View style={styles.metaRow}>
                  <Text style={styles.metaLeft}>{card.leftMeta}</Text>
                  <Text style={styles.metaRight}>{card.rightMeta}</Text>
                </View>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.timelineCard}>
          <View style={styles.sectionHeaderCompact}>
            <Text style={styles.sectionTitle}>{view.timelineTitle}</Text>
            <Text style={styles.sectionLink}>Apri mappa</Text>
          </View>
          <View style={styles.timelineList}>
            {view.timeline.map((item) => (
              <View key={item.id} style={styles.timelineRow}>
                <View style={[styles.timelineDot, item.live ? styles.timelineDotLive : null]}>
                  <Text style={[styles.timelineDotText, item.live ? styles.timelineDotTextLive : null]}>{item.dot}</Text>
                </View>
                <View style={styles.timelineCopy}>
                  <Text style={styles.timelineTitle}>{item.title}</Text>
                  <Text style={styles.timelineSubtitle}>{item.subtitle}</Text>
                </View>
                <Text style={styles.timelineTime}>{item.time}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={styles.assistantCard}>
          <View style={styles.assistantHead}>
            <View>
              <Text style={styles.eyebrow}>{view.assistantLabel}</Text>
              <Text style={styles.assistantTitle}>{view.assistantTitle}</Text>
            </View>
            <Text style={styles.statusPill}>Attivo</Text>
          </View>
          <Text style={styles.assistantCopy}>{view.assistantCopy}</Text>
          <View style={styles.assistantActions}>
            <ActionButton label={view.assistantActions[0]} primary />
            <ActionButton label={view.assistantActions[1]} />
          </View>
        </View>

        <View style={styles.bottomNav}>
          {view.navItems.map((item) => (
            <View key={item} style={[styles.navItem, item === view.activeNav ? styles.navItemActive : null]}>
              <Text style={[styles.navText, item === view.activeNav ? styles.navTextActive : null]}>{item}</Text>
            </View>
          ))}
        </View>
      </View>
    </ScrollView>
  );
}

function ModeButton({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return (
    <TouchableOpacity onPress={onPress} style={[styles.modeButton, active ? styles.modeButtonActive : null]}>
      <Text style={[styles.modeButtonText, active ? styles.modeButtonTextActive : null]}>{label}</Text>
    </TouchableOpacity>
  );
}

function ActionButton({ label, primary = false }: { label: string; primary?: boolean }) {
  return (
    <TouchableOpacity style={[styles.actionButton, primary ? styles.actionButtonPrimary : styles.actionButtonGhost]}>
      <Text style={[styles.actionButtonText, primary ? styles.actionButtonTextPrimary : styles.actionButtonTextGhost]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#d6e4f1',
  },
  content: {
    padding: 18,
  },
  phoneShell: {
    gap: 14,
  },
  topCard: {
    backgroundColor: 'rgba(255,255,255,0.84)',
    borderRadius: 26,
    padding: 18,
    borderWidth: 1,
    borderColor: 'rgba(16,32,51,0.08)',
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  statusPill: {
    backgroundColor: 'rgba(255,255,255,0.7)',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#617386',
    fontSize: 11,
    fontWeight: '700',
  },
  eyebrow: {
    color: '#6e7f94',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.6,
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  title: {
    color: '#102033',
    fontSize: 28,
    fontWeight: '700',
    lineHeight: 30,
  },
  subtitle: {
    marginTop: 8,
    color: '#5f7184',
    fontSize: 14,
    lineHeight: 20,
  },
  switchRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 16,
  },
  modeButton: {
    flex: 1,
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: 'center',
    backgroundColor: '#edf2f7',
  },
  modeButtonActive: {
    backgroundColor: '#1f5c9f',
  },
  modeButtonText: {
    color: '#516174',
    fontSize: 14,
    fontWeight: '700',
  },
  modeButtonTextActive: {
    color: '#ffffff',
  },
  statsRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 14,
  },
  statCard: {
    flex: 1,
    borderRadius: 22,
    paddingHorizontal: 12,
    paddingVertical: 14,
  },
  statBlue: {
    backgroundColor: '#deefff',
  },
  statAmber: {
    backgroundColor: '#ffefca',
  },
  statMint: {
    backgroundColor: '#daf5eb',
  },
  statValue: {
    color: '#102033',
    fontSize: 22,
    fontWeight: '700',
  },
  statLabel: {
    marginTop: 6,
    color: '#5f7184',
    fontSize: 12,
  },
  heroCard: {
    borderRadius: 28,
    padding: 22,
    backgroundColor: '#0f172a',
  },
  heroEyebrow: {
    color: '#95b8f9',
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 1.6,
    fontWeight: '700',
    marginBottom: 8,
  },
  heroTitle: {
    color: '#ffffff',
    fontSize: 30,
    fontWeight: '700',
    lineHeight: 32,
  },
  heroCopy: {
    marginTop: 8,
    color: '#cad8ef',
    fontSize: 14,
    lineHeight: 20,
  },
  heroMetaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginTop: 16,
  },
  heroPill: {
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.12)',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  heroPillText: {
    color: '#d8e6f7',
    fontSize: 12,
    fontWeight: '700',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  sectionHeaderCompact: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    color: '#102033',
    fontSize: 16,
    fontWeight: '700',
  },
  sectionLink: {
    color: '#1f5c9f',
    fontSize: 13,
    fontWeight: '700',
  },
  stack: {
    gap: 12,
  },
  marketCard: {
    flexDirection: 'row',
    gap: 12,
    padding: 14,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.84)',
    borderWidth: 1,
    borderColor: 'rgba(16,32,51,0.08)',
  },
  badge: {
    width: 74,
    minHeight: 74,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeCold: {
    backgroundColor: '#deefff',
  },
  badgeWarm: {
    backgroundColor: '#ffefca',
  },
  badgeMint: {
    backgroundColor: '#daf5eb',
  },
  badgeText: {
    color: '#23374d',
    fontSize: 13,
    fontWeight: '800',
  },
  marketBody: {
    flex: 1,
  },
  marketTitle: {
    color: '#102033',
    fontSize: 20,
    fontWeight: '700',
  },
  marketSubtitle: {
    marginTop: 4,
    color: '#5f7184',
    fontSize: 14,
    lineHeight: 19,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 10,
  },
  tagPill: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: 'rgba(17,32,51,0.05)',
  },
  tagText: {
    color: '#55677b',
    fontSize: 11,
    fontWeight: '700',
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
    gap: 12,
  },
  metaLeft: {
    color: '#c2410c',
    fontSize: 13,
    fontWeight: '700',
  },
  metaRight: {
    color: '#102033',
    fontSize: 13,
    fontWeight: '700',
  },
  timelineCard: {
    padding: 16,
    borderRadius: 26,
    backgroundColor: 'rgba(255,255,255,0.84)',
    borderWidth: 1,
    borderColor: 'rgba(16,32,51,0.08)',
  },
  timelineList: {
    gap: 12,
    marginTop: 10,
  },
  timelineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  timelineDot: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: '#e8f1fb',
    alignItems: 'center',
    justifyContent: 'center',
  },
  timelineDotLive: {
    backgroundColor: '#d7f7eb',
  },
  timelineDotText: {
    color: '#1f5c9f',
    fontSize: 12,
    fontWeight: '800',
  },
  timelineDotTextLive: {
    color: '#0d8a5d',
  },
  timelineCopy: {
    flex: 1,
  },
  timelineTitle: {
    color: '#102033',
    fontSize: 14,
    fontWeight: '700',
  },
  timelineSubtitle: {
    marginTop: 2,
    color: '#5f7184',
    fontSize: 12,
    lineHeight: 17,
  },
  timelineTime: {
    color: '#718398',
    fontSize: 12,
    fontWeight: '700',
  },
  assistantCard: {
    padding: 16,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.9)',
    borderWidth: 1,
    borderColor: 'rgba(16,32,51,0.08)',
  },
  assistantHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  assistantTitle: {
    color: '#102033',
    fontSize: 16,
    fontWeight: '700',
  },
  assistantCopy: {
    marginTop: 8,
    color: '#5f7184',
    fontSize: 14,
    lineHeight: 20,
  },
  assistantActions: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 12,
  },
  actionButton: {
    flex: 1,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
  },
  actionButtonPrimary: {
    backgroundColor: '#1f5c9f',
  },
  actionButtonGhost: {
    backgroundColor: 'rgba(31,92,159,0.08)',
  },
  actionButtonText: {
    fontSize: 13,
    fontWeight: '700',
  },
  actionButtonTextPrimary: {
    color: '#ffffff',
  },
  actionButtonTextGhost: {
    color: '#1f5c9f',
  },
  bottomNav: {
    flexDirection: 'row',
    gap: 8,
    padding: 10,
    borderRadius: 22,
    backgroundColor: 'rgba(255,255,255,0.84)',
    borderWidth: 1,
    borderColor: 'rgba(16,32,51,0.08)',
  },
  navItem: {
    flex: 1,
    borderRadius: 16,
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: 'rgba(17,32,51,0.04)',
  },
  navItemActive: {
    backgroundColor: '#1f5c9f',
  },
  navText: {
    color: '#607183',
    fontSize: 12,
    fontWeight: '700',
  },
  navTextActive: {
    color: '#ffffff',
  },
});