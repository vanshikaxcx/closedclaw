const GST_API_BASE_URL = (
  process.env.NEXT_PUBLIC_GST_API_URL ??
  process.env.REACT_APP_GST_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.REACT_APP_API_URL ??
  'http://localhost:8000'
).replace(/\/$/, '');

const SESSION_KEY = 'arthsetu_session_v2';

interface SessionLike {
  token?: string;
  merchantId?: string;
  merchant_id?: string;
}

function parseError(payload: any, status: number): string {
  const detail = payload?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.error === 'string') {
      return detail.error;
    }
    return JSON.stringify(detail);
  }
  if (typeof payload?.error === 'string') {
    return payload.error;
  }
  if (status >= 500) {
    return 'GST service unavailable';
  }
  return 'GST request failed';
}

function emitToastError(message: string): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.dispatchEvent(
    new CustomEvent('arthsetu:toast', {
      detail: {
        variant: 'error',
        message,
      },
    }),
  );
}

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    if (!raw) {
      return {};
    }

    const session = JSON.parse(raw) as SessionLike;
    const merchantId = session.merchantId ?? session.merchant_id;

    return {
      ...(session.token ? { Authorization: `Bearer ${session.token}` } : {}),
      ...(merchantId ? { 'X-Merchant-Id': merchantId } : {}),
    };
  } catch {
    return {};
  }
}

async function parseJson(response: Response): Promise<any> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function gstRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...getAuthHeaders(),
    ...(init?.headers as Record<string, string> | undefined),
  };

  const body = init?.body;
  if (!(body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  let response: Response;
  try {
    response = await fetch(`${GST_API_BASE_URL}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'GST network request failed';
    emitToastError(message);
    throw new Error(message);
  }

  const payload = await parseJson(response);
  if (!response.ok) {
    const message = parseError(payload, response.status);
    emitToastError(message);
    throw new Error(message);
  }

  return payload as T;
}

export const gstApiClient = {
  get<T>(path: string): Promise<T> {
    return gstRequest<T>(path, { method: 'GET' });
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return gstRequest<T>(path, {
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return gstRequest<T>(path, {
      method: 'PUT',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  },
};
