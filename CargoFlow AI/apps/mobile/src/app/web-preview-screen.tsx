import { useState } from 'react';

import { MobilePreviewShowcase } from './mobile-preview-showcase';

type WebPreviewScreenProps = {
  apiBaseUrl: string;
};

export function WebPreviewScreen({ apiBaseUrl }: WebPreviewScreenProps) {
  const [mode, setMode] = useState<'carrier' | 'driver'>('carrier');

  void apiBaseUrl;

  return <MobilePreviewShowcase mode={mode} onModeChange={setMode} />;
}
