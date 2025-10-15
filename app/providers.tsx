'use client';

import { PostHogProvider } from '@posthog/react';
import { useEffect, useState } from 'react';
import { initPosthog } from '@/app/config/posthog';

export function Providers({ children }: { children: React.ReactNode }) {
  const [client, setClient] = useState<ReturnType<typeof initPosthog>>(null);

  useEffect(() => {
    const instance = initPosthog();
    if (instance) {
      setClient(instance);
    }
  }, []);

  if (!client) {
    return <>{children}</>;
  }

  return <PostHogProvider client={client}>{children}</PostHogProvider>;
}
