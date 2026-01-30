const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://admin:8080';

async function fetchAPI(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    cache: 'no-store',
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function getUserCard(telegramId: string) {
  return fetchAPI(`/analytics/user/${telegramId}/card`);
}

export async function getUserActivity(telegramId: string) {
  return fetchAPI(`/analytics/user/${telegramId}/activity`);
}

export async function manageSubscription(telegramId: string, action: string, days?: number) {
  return fetchAPI(`/analytics/user/${telegramId}/subscription`, {
    method: 'POST',
    body: JSON.stringify({ action, days }),
  });
}

export async function manageImages(telegramId: string, action: string, amount?: number) {
  return fetchAPI(`/analytics/user/${telegramId}/images`, {
    method: 'POST',
    body: JSON.stringify({ action, amount }),
  });
}

export async function manageFeatures(telegramId: string, action: string, featureCode: string) {
  return fetchAPI(`/analytics/user/${telegramId}/features`, {
    method: 'POST',
    body: JSON.stringify({ action, feature_code: featureCode }),
  });
}

export async function deleteUser(telegramId: string) {
  return fetchAPI(`/analytics/user/${telegramId}`, {
    method: 'DELETE',
  });
}
