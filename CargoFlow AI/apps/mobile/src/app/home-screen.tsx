import { LinearGradient } from 'expo-linear-gradient';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { RolePanel } from '../components/role-panel';
import { theme } from '../theme/tokens';

const pillars = [
  'Aste realtime con timer visibile e storico offerte',
  'Matching carichi-mezzi basato su compatibilita tecnica e area',
  'Tracking missione con geofencing e stati automatici',
  'OCR DDT e CMR per ridurre inserimenti manuali',
];

const carrierBullets = [
  'Gestione flotta, mezzi speciali, documenti e compliance',
  'Pubblicazione carichi, aste al ribasso o rialzo e assegnazione missioni',
  'Controllo rating, blacklist, fee per transazione e premium visibility',
];

const driverBullets = [
  'Missioni assegnate con chat operativa legata alla scheda viaggio',
  'Invio posizione, stato missione e prova consegna',
  'Scansione documenti e ricerca vocale in mobilita',
];

export function HomeScreen() {
  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <LinearGradient colors={[theme.colors.paper, '#efe1c5', '#d7e7df']} style={styles.hero}>
        <Text style={styles.kicker}>CargoFlow AI</Text>
        <Text style={styles.title}>Lo scambio carichi esce dai gruppi chat e diventa un sistema operativo.</Text>
        <Text style={styles.subtitle}>
          Un'app mobile per trasportatori e autisti che unisce marketplace, esecuzione missione,
          compliance documentale e automazione AI.
        </Text>

        <View style={styles.badgeRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeLabel}>Realtime Auctions</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeLabel}>OCR + Voice</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeLabel}>Secure Logistics Graph</Text>
          </View>
        </View>
      </LinearGradient>

      <View style={styles.panelStack}>
        <RolePanel
          eyebrow="Profilo aziendale"
          title="Trasportatore"
          bullets={carrierBullets}
          accent={theme.colors.ember}
        />
        <RolePanel
          eyebrow="Profilo operativo"
          title="Autista"
          bullets={driverBullets}
          accent={theme.colors.pine}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Motore MVP</Text>
        <View style={styles.pillarGrid}>
          {pillars.map((pillar) => (
            <View key={pillar} style={styles.pillarCard}>
              <Text style={styles.pillarText}>{pillar}</Text>
            </View>
          ))}
        </View>
      </View>

      <View style={styles.sectionBanner}>
        <Text style={styles.sectionBannerTitle}>Roadmap tecnica</Text>
        <Text style={styles.sectionBannerText}>
          Prima identita, flotta e compliance. Poi marketplace, aste, missione operativa e AI.
          La piattaforma nasce mobile-first ma con backend modulare e dominio tracciabile.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: theme.colors.paper,
  },
  content: {
    padding: 20,
    gap: 18,
  },
  hero: {
    borderRadius: theme.radius.lg,
    padding: 24,
    gap: 16,
    minHeight: 280,
    justifyContent: 'flex-end',
  },
  kicker: {
    fontFamily: theme.font.body,
    textTransform: 'uppercase',
    letterSpacing: 2.5,
    color: theme.colors.ember,
    fontSize: 12,
  },
  title: {
    fontFamily: theme.font.heading,
    fontSize: 34,
    lineHeight: 39,
    color: theme.colors.ink,
    maxWidth: 520,
  },
  subtitle: {
    fontFamily: theme.font.body,
    fontSize: 16,
    lineHeight: 24,
    color: theme.colors.muted,
    maxWidth: 560,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  badge: {
    backgroundColor: 'rgba(255, 253, 248, 0.82)',
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: theme.colors.line,
  },
  badgeLabel: {
    fontFamily: theme.font.body,
    color: theme.colors.ink,
    fontSize: 13,
  },
  panelStack: {
    gap: 14,
  },
  section: {
    gap: 14,
  },
  sectionTitle: {
    fontFamily: theme.font.heading,
    fontSize: 28,
    color: theme.colors.ink,
  },
  pillarGrid: {
    gap: 12,
  },
  pillarCard: {
    backgroundColor: '#fffaf0',
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.line,
    padding: 18,
  },
  pillarText: {
    fontFamily: theme.font.body,
    color: theme.colors.ink,
    fontSize: 16,
    lineHeight: 23,
  },
  sectionBanner: {
    backgroundColor: theme.colors.pine,
    borderRadius: theme.radius.lg,
    padding: 22,
    gap: 8,
  },
  sectionBannerTitle: {
    fontFamily: theme.font.heading,
    fontSize: 24,
    color: '#f9f4e8',
  },
  sectionBannerText: {
    fontFamily: theme.font.body,
    fontSize: 15,
    lineHeight: 23,
    color: '#d7ede7',
  },
});
