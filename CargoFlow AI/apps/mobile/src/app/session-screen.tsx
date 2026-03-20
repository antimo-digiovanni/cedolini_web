import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { authClient, AuthResponse, InviteResponse } from '../api/auth-client';
import { CarrierDashboard } from './carrier-dashboard';
import { DriverDashboard } from './driver-dashboard';
import {
  buildCarrierDashboard,
  buildDriverDashboard,
  mapCarrierDashboard,
  mapDriverDashboard,
} from './dashboard-data';
import { PillButton, SectionTitle } from '../ui/form-controls';
import { theme } from '../theme/tokens';

type SessionScreenProps = {
  session: AuthResponse;
  apiBaseUrl: string;
  onLogout: () => Promise<void>;
};

export function SessionScreen({ session, apiBaseUrl, onLogout }: SessionScreenProps) {
  const [invite, setInvite] = useState<InviteResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [carrierData, setCarrierData] = useState(() => buildCarrierDashboard(session));
  const [driverData, setDriverData] = useState(() => buildDriverDashboard(session));

  async function refreshDashboard(showLoader = false) {
    if (showLoader) {
      setLoadingDashboard(true);
    }
    try {
      if (session.user.role === 'driver') {
        const response = await authClient.driverDashboard(apiBaseUrl, session.tokens.access_token);
        setDriverData(mapDriverDashboard(response));
        return;
      }

      const response = await authClient.carrierDashboard(apiBaseUrl, session.tokens.access_token);
      setCarrierData(mapCarrierDashboard(response));
    } catch {
      setCarrierData(buildCarrierDashboard(session));
      setDriverData(buildDriverDashboard(session));
    } finally {
      if (showLoader) {
        setLoadingDashboard(false);
      }
    }
  }

  useEffect(() => {
    void refreshDashboard(true);
  }, [apiBaseUrl, session]);

  async function generateDriverInvite() {
    setBusy(true);
    setMessage(null);
    try {
      const response = await authClient.createInvite(apiBaseUrl, session.tokens.access_token, {
        role: 'driver',
        validity_hours: 72,
      });
      setInvite(response);
      setMessage('Invito autista generato con successo.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Errore nella generazione invito');
    } finally {
      setBusy(false);
    }
  }

  if (session.user.role === 'driver') {
    if (loadingDashboard) {
      return <LoadingScreen label="Carico dashboard autista" />;
    }
    return <DriverDashboard session={session} apiBaseUrl={apiBaseUrl} data={driverData} onLogout={onLogout} />;
  }

  if (session.user.role === 'carrier_owner' || session.user.role === 'dispatcher' || session.user.role === 'admin') {
    if (loadingDashboard) {
      return <LoadingScreen label="Carico dashboard trasportatore" />;
    }
    return (
      <CarrierDashboard
        session={session}
        apiBaseUrl={apiBaseUrl}
        onGenerateInvite={generateDriverInvite}
        onReloadDashboard={() => refreshDashboard(false)}
        data={carrierData}
        invite={invite}
        message={message}
        busy={busy}
        onLogout={onLogout}
      />
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.hero}>
        <Text style={styles.kicker}>Sessione Attiva</Text>
        <Text style={styles.title}>
          {session.user.first_name} {session.user.last_name}
        </Text>
        <Text style={styles.subtitle}>
          {session.user.role} · {session.company?.legal_name ?? 'Utente senza azienda'}
        </Text>
      </View>

      <View style={styles.card}>
        <SectionTitle title="Sessione" subtitle="Questa vista conferma che il mobile parla con gli endpoint auth del backend." />
        <InfoRow label="API" value={apiBaseUrl} />
        <InfoRow label="Email" value={session.user.email} />
        <InfoRow label="Company ID" value={session.user.company_id ?? 'non associato'} />
        <InfoRow label="Access Token" value={`${session.tokens.access_token.slice(0, 24)}...`} />
      </View>

      <View style={styles.card}>
        <SectionTitle title="Azioni rapide" subtitle="Per il profilo aziendale puoi già generare inviti per gli autisti." />
        <PillButton label="Genera Invito Autista" onPress={generateDriverInvite} disabled={busy} />
        <PillButton label="Disconnetti" onPress={() => void onLogout()} variant="secondary" />
        {message ? <Text style={styles.message}>{message}</Text> : null}
        {invite ? <Text style={styles.inviteCode}>{invite.token}</Text> : null}
      </View>
    </ScrollView>
  );
}

function LoadingScreen({ label }: { label: string }) {
  return (
    <View style={styles.loadingScreen}>
      <View style={styles.loadingCard}>
        <Text style={styles.feedbackTitle}>{label}</Text>
        <Text style={styles.feedbackText}>Recupero dati dal backend con fallback locale in caso di indisponibilita.</Text>
      </View>
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  loadingScreen: {
    flex: 1,
    backgroundColor: theme.colors.paper,
    justifyContent: 'center',
    padding: 20,
  },
  loadingCard: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.line,
    padding: 20,
    gap: 10,
  },
  feedbackTitle: {
    fontFamily: theme.font.heading,
    fontSize: 24,
    color: theme.colors.ink,
  },
  feedbackText: {
    fontFamily: theme.font.body,
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.muted,
  },
  screen: {
    flex: 1,
    backgroundColor: theme.colors.paper,
  },
  content: {
    padding: 20,
    gap: 16,
  },
  hero: {
    backgroundColor: theme.colors.pine,
    borderRadius: theme.radius.lg,
    padding: 24,
    gap: 8,
  },
  kicker: {
    fontFamily: theme.font.body,
    textTransform: 'uppercase',
    letterSpacing: 2,
    color: '#c7f0e2',
    fontSize: 12,
  },
  title: {
    fontFamily: theme.font.heading,
    fontSize: 30,
    color: '#fff8ee',
  },
  subtitle: {
    fontFamily: theme.font.body,
    fontSize: 16,
    lineHeight: 23,
    color: '#dbece7',
  },
  card: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.line,
    padding: 18,
    gap: 12,
  },
  infoRow: {
    gap: 4,
  },
  infoLabel: {
    fontFamily: theme.font.body,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: theme.colors.muted,
  },
  infoValue: {
    fontFamily: theme.font.body,
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.ink,
  },
  message: {
    fontFamily: theme.font.body,
    color: theme.colors.muted,
    fontSize: 15,
    lineHeight: 22,
  },
  inviteCode: {
    fontFamily: theme.font.heading,
    fontSize: 26,
    color: theme.colors.ember,
  },
});
