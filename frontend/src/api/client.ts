import type {
  DiscoveredState,
  DiscoveryDetail,
  DiscoverySummary,
  EvidenceItem,
  StateNode,
  SystemStatus,
  TeamSummary,
  Transition,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body || path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  system: () => request<SystemStatus>("/system"),

  discoveries: (params: { discovery_type?: string; team?: string } = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v) as [string, string][]
    ).toString();
    return request<DiscoverySummary[]>(`/discoveries${qs ? `?${qs}` : ""}`);
  },
  discovery: (id: string) => request<DiscoveryDetail>(`/discoveries/${id}`),
  discoveryEvidence: (id: string) => request<EvidenceItem[]>(`/discoveries/${id}/evidence`),
  runDiscovery: () => request<DiscoverySummary[]>("/discoveries/run", { method: "POST" }),

  states: (params: { down?: number; min_sample_size?: number } = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
    ).toString();
    return request<StateNode[]>(`/states${qs ? `?${qs}` : ""}`);
  },
  state: (id: string) => request<StateNode>(`/states/${encodeURIComponent(id)}`),
  transitions: (id: string) => request<Transition[]>(`/states/${encodeURIComponent(id)}/transitions`),
  discoveredStates: () => request<DiscoveredState[]>("/states/discovered"),
  discoveredState: (id: string) => request<DiscoveredState>(`/states/discovered/${id}`),

  teams: () => request<TeamSummary[]>("/teams"),
};
