export const API_URL =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "https://api.schedulelink.tech";

const TOKEN_KEY = "schedulelink_token";
const REFRESH_KEY = "schedulelink_refresh";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access: string, refresh?: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, access);
  if (refresh) window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, { ...opts, headers });
  if (!res.ok) {
    let body: any = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    const err = new Error(typeof body === "string" ? body : body?.detail || `Request failed: ${res.status}`);
    (err as any).status = res.status;
    (err as any).body = body;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const fetcher = (path: string) => api(path);
