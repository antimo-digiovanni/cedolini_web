import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

import { AppErrorBoundary } from './src/app/app-error-boundary';
import { WebPreviewScreen } from './src/app/web-preview-screen';

export default function App() {
  const [session, setSession] = useState<unknown>(null);
  const [apiBaseUrl, setApiBaseUrl] = useState('http://127.0.0.1:8000');
  const [booting, setBooting] = useState(Platform.OS !== 'web');

  useEffect(() => {
    if (Platform.OS === 'web') {
      return;
    }

    let active = true;

    async function bootstrap() {
      const { authClient } = require('./src/api/auth-client');
      const { clearSession, loadSession } = require('./src/auth/session-storage');

      try {
        const stored = await loadSession();
        if (!stored) {
          return;
        }

        const me = await authClient.me(stored.apiBaseUrl, stored.auth.tokens.access_token);
        if (!active) {
          return;
        }

        const hydratedSession = {
          ...stored.auth,
          user: me.user,
          company: me.company,
        };

        setSession(hydratedSession);
        setApiBaseUrl(stored.apiBaseUrl);
      } catch {
        await clearSession();
      } finally {
        if (active) {
          setBooting(false);
        }
      }
    }

    void bootstrap();

    return () => {
      active = false;
    };
  }, []);

  async function handleAuthenticated(response: unknown, baseUrl: string) {
    const { saveSession } = require('./src/auth/session-storage');
    setSession(response);
    setApiBaseUrl(baseUrl);
    await saveSession({ auth: response, apiBaseUrl: baseUrl });
  }

  async function handleLogout() {
    const { clearSession } = require('./src/auth/session-storage');
    setSession(null);
    await clearSession();
  }

  if (booting) {
    const { BootstrapScreen } = require('./src/app/bootstrap-screen');

    return (
      <>
        <StatusBar style="dark" />
        <BootstrapScreen />
      </>
    );
  }

  if (Platform.OS === 'web') {
    return (
      <AppErrorBoundary>
        <>
          <StatusBar style="dark" />
          <WebPreviewScreen apiBaseUrl={apiBaseUrl} />
        </>
      </AppErrorBoundary>
    );
  }

  const { SessionScreen } = require('./src/app/session-screen');
  const { AuthShell } = require('./src/auth/auth-shell');

  return (
    <AppErrorBoundary>
      <>
        <StatusBar style="dark" />
        {session ? (
          <SessionScreen
            session={session}
            apiBaseUrl={apiBaseUrl}
            onLogout={handleLogout}
          />
        ) : (
          <AuthShell
            defaultApiBaseUrl={apiBaseUrl}
            onAuthenticated={handleAuthenticated}
          />
        )}
      </>
    </AppErrorBoundary>
  );
}
