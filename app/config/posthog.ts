'use client';

import posthog from 'posthog-js';

declare global {
  interface Window {
    posthog?: typeof posthog;
  }
}

let initialized = false;

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com';

export function initPosthog() {
  if (typeof window === 'undefined') {
    return null;
  }

  if (!POSTHOG_KEY) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('[posthog] NEXT_PUBLIC_POSTHOG_KEY is not set; analytics disabled.');
    }
    return null;
  }

  if (!initialized) {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      capture_pageview: false,
      disable_session_recording: true,
      persistence: 'memory',
      person_profiles: 'never',
    });
    initialized = true;
    window.posthog = posthog;
  }

  return posthog;
}

export function captureTerminalEvent(event: string, properties: Record<string, unknown> = {}) {
  if (typeof window === 'undefined') {
    return;
  }

  const client = initPosthog();
  if (!client) {
    return;
  }

  client.capture(event, {
    ...properties,
    $process_person_profile: false,
  });
}
