import { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

import { authClient, AuthResponse, InviteResponse } from '../api/auth-client';
import { PillButton, Field, SectionTitle } from '../ui/form-controls';
import { theme } from '../theme/tokens';

type AuthMode = 'login' | 'carrier' | 'driver';

type AuthShellProps = {
  defaultApiBaseUrl: string;
  onAuthenticated: (response: AuthResponse, apiBaseUrl: string) => void;
};

export function AuthShell({ defaultApiBaseUrl, onAuthenticated }: AuthShellProps) {
  const [mode, setMode] = useState<AuthMode>('login');
  const [apiBaseUrl, setApiBaseUrl] = useState(defaultApiBaseUrl);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [inviteResult, setInviteResult] = useState<InviteResponse | null>(null);

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const [carrierCompanyName, setCarrierCompanyName] = useState('');
  const [carrierVatNumber, setCarrierVatNumber] = useState('');
  const [carrierFirstName, setCarrierFirstName] = useState('');
  const [carrierLastName, setCarrierLastName] = useState('');
  const [carrierPhone, setCarrierPhone] = useState('');
  const [carrierEmail, setCarrierEmail] = useState('');
  const [carrierPassword, setCarrierPassword] = useState('');

  const [driverInviteToken, setDriverInviteToken] = useState('');
  const [driverFirstName, setDriverFirstName] = useState('');
  const [driverLastName, setDriverLastName] = useState('');
  const [driverPhone, setDriverPhone] = useState('');
  const [driverEmail, setDriverEmail] = useState('');
  const [driverPassword, setDriverPassword] = useState('');

  async function submitLogin() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await authClient.login(normalizeBaseUrl(apiBaseUrl), {
        email: loginEmail,
        password: loginPassword,
      });
      onAuthenticated(response, normalizeBaseUrl(apiBaseUrl));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function submitCarrierRegistration() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await authClient.registerCarrier(normalizeBaseUrl(apiBaseUrl), {
        company_name: carrierCompanyName,
        vat_number: carrierVatNumber,
        first_name: carrierFirstName,
        last_name: carrierLastName,
        phone_number: carrierPhone || undefined,
        email: carrierEmail,
        password: carrierPassword,
      });
      setSuccess('Profilo trasportatore creato. Sessione aperta.');
      onAuthenticated(response, normalizeBaseUrl(apiBaseUrl));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function submitDriverRegistration() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await authClient.registerDriver(normalizeBaseUrl(apiBaseUrl), {
        invite_token: driverInviteToken,
        first_name: driverFirstName,
        last_name: driverLastName,
        phone_number: driverPhone || undefined,
        email: driverEmail,
        password: driverPassword,
      });
      setSuccess('Profilo autista creato da invito aziendale.');
      onAuthenticated(response, normalizeBaseUrl(apiBaseUrl));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function createDemoInvite() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    setInviteResult(null);
    try {
      const authResponse = await authClient.login(normalizeBaseUrl(apiBaseUrl), {
        email: loginEmail,
        password: loginPassword,
      });
      const invite = await authClient.createInvite(
        normalizeBaseUrl(apiBaseUrl),
        authResponse.tokens.access_token,
        { role: 'driver', validity_hours: 72 },
      );
      setInviteResult(invite);
      setSuccess('Codice invito autista generato dal profilo corrente.');
      onAuthenticated(authResponse, normalizeBaseUrl(apiBaseUrl));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <LinearGradient colors={[theme.colors.paper, '#efe1c5', '#d7e7df']} style={styles.hero}>
        <Text style={styles.kicker}>CargoFlow AI</Text>
        <Text style={styles.title}>Identita aziendale e onboarding operativo in un unico ingresso.</Text>
        <Text style={styles.subtitle}>
          Collega l'app al backend locale, registra il trasportatore, genera inviti per gli autisti
          e valida subito il flusso auth del MVP.
        </Text>
      </LinearGradient>

      <View style={styles.card}>
        <SectionTitle
          title="Connessione API"
          subtitle="Usa un indirizzo raggiungibile dal simulatore o dal telefono. Per Android emulator spesso 10.0.2.2:8000, per web 127.0.0.1:8000."
        />
        <Field label="API Base URL" value={apiBaseUrl} onChangeText={setApiBaseUrl} autoCapitalize="none" autoCorrect={false} />
      </View>

      <View style={styles.modeRow}>
        <ModeChip label="Login" active={mode === 'login'} onPress={() => setMode('login')} />
        <ModeChip label="Trasportatore" active={mode === 'carrier'} onPress={() => setMode('carrier')} />
        <ModeChip label="Autista" active={mode === 'driver'} onPress={() => setMode('driver')} />
      </View>

      {mode === 'login' ? (
        <View style={styles.card}>
          <SectionTitle title="Accedi" subtitle="Entra con un utente gia creato e apri la sessione mobile." />
          <Field label="Email" value={loginEmail} onChangeText={setLoginEmail} autoCapitalize="none" keyboardType="email-address" />
          <Field label="Password" value={loginPassword} onChangeText={setLoginPassword} secureTextEntry />
          <View style={styles.actionsRow}>
            <PillButton label="Accedi" onPress={submitLogin} disabled={busy} />
            <PillButton label="Genera Invito Driver" onPress={createDemoInvite} variant="secondary" disabled={busy} />
          </View>
        </View>
      ) : null}

      {mode === 'carrier' ? (
        <View style={styles.card}>
          <SectionTitle title="Registra Trasportatore" subtitle="Crea insieme azienda e titolare operativo." />
          <Field label="Ragione Sociale" value={carrierCompanyName} onChangeText={setCarrierCompanyName} />
          <Field label="Partita IVA" value={carrierVatNumber} onChangeText={setCarrierVatNumber} autoCapitalize="characters" />
          <Field label="Nome" value={carrierFirstName} onChangeText={setCarrierFirstName} />
          <Field label="Cognome" value={carrierLastName} onChangeText={setCarrierLastName} />
          <Field label="Telefono" value={carrierPhone} onChangeText={setCarrierPhone} keyboardType="phone-pad" />
          <Field label="Email" value={carrierEmail} onChangeText={setCarrierEmail} autoCapitalize="none" keyboardType="email-address" />
          <Field label="Password" value={carrierPassword} onChangeText={setCarrierPassword} secureTextEntry />
          <PillButton label="Crea Profilo Aziendale" onPress={submitCarrierRegistration} disabled={busy} />
        </View>
      ) : null}

      {mode === 'driver' ? (
        <View style={styles.card}>
          <SectionTitle title="Registra Autista" subtitle="Usa il codice invito generato dal trasportatore o dal disponente." />
          <Field label="Codice Invito" value={driverInviteToken} onChangeText={setDriverInviteToken} autoCapitalize="characters" />
          <Field label="Nome" value={driverFirstName} onChangeText={setDriverFirstName} />
          <Field label="Cognome" value={driverLastName} onChangeText={setDriverLastName} />
          <Field label="Telefono" value={driverPhone} onChangeText={setDriverPhone} keyboardType="phone-pad" />
          <Field label="Email" value={driverEmail} onChangeText={setDriverEmail} autoCapitalize="none" keyboardType="email-address" />
          <Field label="Password" value={driverPassword} onChangeText={setDriverPassword} secureTextEntry />
          <PillButton label="Attiva Profilo Autista" onPress={submitDriverRegistration} disabled={busy} />
        </View>
      ) : null}

      {busy ? (
        <View style={styles.feedbackCard}>
          <ActivityIndicator color={theme.colors.ember} />
          <Text style={styles.feedbackText}>Invio richiesta al backend...</Text>
        </View>
      ) : null}

      {error ? (
        <View style={[styles.feedbackCard, styles.feedbackError]}>
          <Text style={styles.feedbackTitle}>Errore</Text>
          <Text style={styles.feedbackText}>{error}</Text>
        </View>
      ) : null}

      {success ? (
        <View style={[styles.feedbackCard, styles.feedbackSuccess]}>
          <Text style={styles.feedbackTitle}>Confermato</Text>
          <Text style={styles.feedbackText}>{success}</Text>
          {inviteResult ? <Text style={styles.inviteCode}>Codice: {inviteResult.token}</Text> : null}
        </View>
      ) : null}
    </ScrollView>
  );
}

function ModeChip({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return <PillButton label={label} onPress={onPress} variant={active ? 'primary' : 'secondary'} />;
}

function normalizeBaseUrl(value: string) {
  return value.trim().replace(/\/$/, '');
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return 'Errore imprevisto';
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: theme.colors.paper,
  },
  content: {
    padding: 20,
    gap: 16,
  },
  hero: {
    borderRadius: theme.radius.lg,
    padding: 24,
    gap: 14,
  },
  kicker: {
    fontFamily: theme.font.body,
    textTransform: 'uppercase',
    letterSpacing: 2,
    color: theme.colors.ember,
    fontSize: 12,
  },
  title: {
    fontFamily: theme.font.heading,
    fontSize: 31,
    lineHeight: 37,
    color: theme.colors.ink,
  },
  subtitle: {
    fontFamily: theme.font.body,
    fontSize: 16,
    lineHeight: 24,
    color: theme.colors.muted,
  },
  card: {
    backgroundColor: theme.colors.card,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.line,
    padding: 18,
    gap: 14,
  },
  modeRow: {
    gap: 10,
  },
  actionsRow: {
    gap: 10,
  },
  feedbackCard: {
    borderRadius: theme.radius.md,
    padding: 18,
    backgroundColor: '#fffaf0',
    borderWidth: 1,
    borderColor: theme.colors.line,
    gap: 8,
  },
  feedbackError: {
    backgroundColor: '#fff0ec',
    borderColor: '#ecb7a8',
  },
  feedbackSuccess: {
    backgroundColor: '#eef7f1',
    borderColor: '#b8d8c2',
  },
  feedbackTitle: {
    fontFamily: theme.font.heading,
    fontSize: 20,
    color: theme.colors.ink,
  },
  feedbackText: {
    fontFamily: theme.font.body,
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.muted,
  },
  inviteCode: {
    fontFamily: theme.font.heading,
    fontSize: 24,
    color: theme.colors.pine,
  },
});
