import * as SecureStore from 'expo-secure-store';

import { AuthResponse } from '../api/auth-client';

const sessionKey = 'cargoflow.auth.session';
const baseUrlKey = 'cargoflow.auth.base-url';

export type PersistedSession = {
  auth: AuthResponse;
  apiBaseUrl: string;
};

export async function saveSession(payload: PersistedSession): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(sessionKey, JSON.stringify(payload.auth)),
    SecureStore.setItemAsync(baseUrlKey, payload.apiBaseUrl),
  ]);
}

export async function loadSession(): Promise<PersistedSession | null> {
  const [rawSession, apiBaseUrl] = await Promise.all([
    SecureStore.getItemAsync(sessionKey),
    SecureStore.getItemAsync(baseUrlKey),
  ]);

  if (!rawSession || !apiBaseUrl) {
    return null;
  }

  try {
    return {
      auth: JSON.parse(rawSession) as AuthResponse,
      apiBaseUrl,
    };
  } catch {
    await clearSession();
    return null;
  }
}

export async function clearSession(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(sessionKey),
    SecureStore.deleteItemAsync(baseUrlKey),
  ]);
}
