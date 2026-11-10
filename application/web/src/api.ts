import Keycloak from "keycloak-js";

export type Asset = {
  asset_id: string;
  name: string;
  asset_type: string;
  zone: string;
  criticality: "low" | "moderate" | "high" | "critical";
  owner: string;
};

export type EventRecord = {
  id: number;
  source: "wazuh" | "suricata" | "zeek";
  observed_at: string;
  event_type: string;
  severity: string;
  summary: string;
  sensor: string | null;
  src_ip: string | null;
  src_port: number | null;
  dest_ip: string | null;
  dest_port: number | null;
  protocol: string | null;
};

export type EventSource = EventRecord["source"];

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? "http://localhost:8080",
  realm: "sgif-lab",
  clientId: "sgif-web",
});

let initialization: Promise<boolean> | undefined;

export function initializeIdentity(): Promise<boolean> {
  initialization ??= keycloak.init({
    onLoad: "login-required",
    pkceMethod: "S256",
    checkLoginIframe: false,
  });
  return initialization;
}

export function userRoles(): string[] {
  return keycloak.tokenParsed?.realm_access?.roles ?? [];
}

export async function identityToken(): Promise<string> {
  if (!keycloak.authenticated) {
    throw new Error("Sign-in required");
  }
  await keycloak.updateToken(30);
  return keycloak.token ?? "";
}

export function signOut(): void {
  void keycloak.logout({ redirectUri: window.location.origin });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await identityToken();
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  assets: () => request<Asset[]>("/api/v1/assets"),
  events: () => request<EventRecord[]>("/api/v1/events?limit=250"),
  createAsset: (asset: Omit<Asset, "asset_id"> & { asset_id: string }) =>
    request<{ asset_id: string }>("/api/v1/assets", { method: "POST", body: JSON.stringify(asset) }),
  importEvents: (source: EventSource, content: string) =>
    request<{ accepted: number; duplicates: number }>("/api/v1/events/import", {
      method: "POST",
      body: JSON.stringify({ source, content }),
    }),
};