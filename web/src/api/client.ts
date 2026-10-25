import { useSyncExternalStore } from "react";
import { mockFeedSubscribe, mockRequest } from "./mock";
import type {
  AnalyzeRequest, AnalyzeResponse, Case, CaseCreate, ChaosSettings, CheckinResponse,
  CoordinatorAction, FeedMessage, Notification, ReadyStatus,
} from "./types";

const FORCE_MOCK = import.meta.env.VITE_MOCK === "1";

// "Demo data" flag: true when any response came from the mock layer.
let usingMock = FORCE_MOCK;
const subs = new Set<() => void>();
function setMock(v: boolean) {
  if (usingMock !== v) { usingMock = v; subs.forEach((s) => s()); }
}
export function useDemoMode() {
  return useSyncExternalStore((cb) => { subs.add(cb); return () => subs.delete(cb); }, () => usingMock);
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(method: string, path: string, body?: unknown, opts: { allowStatus?: number[] } = {}): Promise<T> {
  if (FORCE_MOCK) return (await mockRequest(method, path, body)) as T;
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    setMock(true);
    return (await mockRequest(method, path, body)) as T;
  }
  const isJson = res.headers.get("content-type")?.includes("json");
  // The dev proxy answers 5xx without JSON when the backend is down.
  if (!isJson && res.status >= 500) {
    setMock(true);
    return (await mockRequest(method, path, body)) as T;
  }
  setMock(false);
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok && !opts.allowStatus?.includes(res.status)) {
    const detail = typeof data === "object" && data && "detail" in data ? JSON.stringify((data as { detail: unknown }).detail) : String(data);
    throw new ApiError(res.status, detail || res.statusText);
  }
  return data as T;
}

export const api = {
  analyze: (b: AnalyzeRequest) => request<AnalyzeResponse>("POST", "/api/analyze", b),
  ready: () => request<ReadyStatus>("GET", "/readyz", undefined, { allowStatus: [503] }),
  getChaos: () => request<ChaosSettings>("GET", "/api/ops/chaos"),
  putChaos: (c: ChaosSettings) => request<ChaosSettings>("PUT", "/api/ops/chaos", c),
  feed: () => request<FeedMessage[]>("GET", "/api/feed"),
  feedNext: () => request<FeedMessage>("POST", "/api/feed/next"),
  feedReset: () => request<unknown>("POST", "/api/feed/reset"),
  createCase: (b: CaseCreate) => request<Case>("POST", "/api/cases", b),
  getCase: (id: string) => request<Case>("GET", `/api/cases/${encodeURIComponent(id)}`),
  stepDone: (id: string, step: string) =>
    request<Case>("POST", `/api/cases/${encodeURIComponent(id)}/steps/${encodeURIComponent(step)}/done`),
  checkin: (id: string, b: CheckinResponse) => request<Case>("POST", `/api/cases/${encodeURIComponent(id)}/checkin`, b),
  notifications: (caseId: string) => request<Notification[]>("GET", `/api/notifications?case_id=${encodeURIComponent(caseId)}`),
  queue: () => request<Case[]>("GET", "/api/coordinator/queue"),
  claim: (id: string, b: CoordinatorAction) => request<Case>("POST", `/api/coordinator/cases/${encodeURIComponent(id)}/claim`, b),
  resolve: (id: string, b: CoordinatorAction) => request<Case>("POST", `/api/coordinator/cases/${encodeURIComponent(id)}/resolve`, b),
};

/** Live feed: EventSource against the API, or the mock emitter in demo mode. */
export function subscribeFeed(onMessage: (m: FeedMessage) => void): () => void {
  if (FORCE_MOCK || usingMock) return mockFeedSubscribe(onMessage);
  const es = new EventSource("/api/feed/stream");
  es.addEventListener("message", (e) => {
    try { onMessage(JSON.parse((e as MessageEvent).data)); } catch { /* ignore malformed */ }
  });
  const off = mockFeedSubscribe(onMessage); // in case we fall back mid-session
  return () => { es.close(); off(); };
}
