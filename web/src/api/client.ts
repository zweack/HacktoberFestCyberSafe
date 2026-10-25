import { useSyncExternalStore } from "react";
import { mockFeedSubscribe, mockRequest } from "./mock";
import type {
  AnalyzeRequest, AnalyzeResponse, Case, CaseCreate, ChaosSettings, CheckinResponse,
  CoordinatorAction, FeedMessage, Notification, ReadyStatus,
} from "./types";

// Demo mode is explicit: only VITE_MOCK=1 serves sample data. A real request that fails
// is shown as an error; it never quietly turns into a sample answer or a fake case.
export const DEMO_MODE = import.meta.env.VITE_MOCK === "1";
export function useDemoMode() {
  return DEMO_MODE;
}

const TIMEOUT_MS = 20_000;

export class ApiError extends Error {
  /** status 0 = no answer from the server (offline or timed out). */
  constructor(public status: number, message: string, public detail?: unknown) { super(message); }
  get offline() { return this.status === 0; }
}

// ---------------------------------------------------------------- staff token

const STAFF_KEY = "staffToken";
const staffSubs = new Set<() => void>();
export function getStaffToken() { return sessionStorage.getItem(STAFF_KEY) ?? ""; }
export function setStaffToken(v: string) {
  if (v) sessionStorage.setItem(STAFF_KEY, v); else sessionStorage.removeItem(STAFF_KEY);
  staffSubs.forEach((s) => s());
}
export function useStaffToken() {
  return useSyncExternalStore((cb) => { staffSubs.add(cb); return () => staffSubs.delete(cb); }, getStaffToken);
}

// ---------------------------------------------------------------- requests

type Opts = { allowStatus?: number[]; staff?: boolean; headers?: Record<string, string>; signal?: AbortSignal };

async function request<T>(method: string, path: string, body?: unknown, opts: Opts = {}): Promise<T> {
  if (DEMO_MODE) return (await mockRequest(method, path, body)) as T;
  const headers: Record<string, string> = { ...opts.headers };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.staff && getStaffToken()) headers["X-Staff-Token"] = getStaffToken();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  opts.signal?.addEventListener("abort", () => ctrl.abort());
  let res: Response;
  try {
    res = await fetch(path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined, signal: ctrl.signal });
  } catch {
    throw new ApiError(0, "The server did not answer.");
  } finally {
    clearTimeout(timer);
  }
  const isJson = res.headers.get("content-type")?.includes("json");
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok && !opts.allowStatus?.includes(res.status)) {
    const detail = typeof data === "object" && data && "detail" in data ? (data as { detail: unknown }).detail : data;
    const msg = typeof detail === "string" ? detail
      : detail && typeof detail === "object" && "message" in detail ? String((detail as { message: unknown }).message)
      : res.statusText;
    // The dev proxy answers 5xx without JSON when the backend is down.
    throw new ApiError(!isJson && res.status >= 500 ? 0 : res.status, msg || res.statusText, detail);
  }
  return data as T;
}

const enc = encodeURIComponent;
const staff = { staff: true };

export const api = {
  analyze: (b: AnalyzeRequest, signal?: AbortSignal) => request<AnalyzeResponse>("POST", "/api/analyze", b, { signal }),
  ready: () => request<ReadyStatus>("GET", "/readyz", undefined, { allowStatus: [503] }),
  getChaos: () => request<ChaosSettings>("GET", "/api/ops/chaos", undefined, staff),
  putChaos: (c: ChaosSettings) => request<ChaosSettings>("PUT", "/api/ops/chaos", c, staff),
  feed: () => request<FeedMessage[]>("GET", "/api/feed"),
  feedNext: () => request<FeedMessage>("POST", "/api/feed/next"),
  feedReset: () => request<unknown>("POST", "/api/feed/reset"),
  /** idempotencyKey: reuse the same key when retrying, so a retry never opens a second case. */
  createCase: (b: CaseCreate, idempotencyKey: string) =>
    request<Case>("POST", "/api/cases", b, { headers: { "Idempotency-Key": idempotencyKey } }),
  getCase: (id: string) => request<Case>("GET", `/api/cases/${enc(id)}`),
  stepDone: (id: string, step: string) => request<Case>("POST", `/api/cases/${enc(id)}/steps/${enc(step)}/done`),
  checkin: (id: string, b: CheckinResponse) => request<Case>("POST", `/api/cases/${enc(id)}/checkin`, b),
  notifications: (caseId: string) => request<Notification[]>("GET", `/api/notifications?case_id=${enc(caseId)}`),
  queue: () => request<Case[]>("GET", "/api/coordinator/queue", undefined, staff),
  claim: (id: string, b: CoordinatorAction) => request<Case>("POST", `/api/coordinator/cases/${enc(id)}/claim`, b, staff),
  resolve: (id: string, b: CoordinatorAction) => request<Case>("POST", `/api/coordinator/cases/${enc(id)}/resolve`, b, staff),
};

/** Live feed. onOpen fires on every (re)connect so the page can reload the snapshot. */
export function subscribeFeed(onMessage: (m: FeedMessage) => void, onOpen?: () => void, onDown?: () => void): () => void {
  if (DEMO_MODE) return mockFeedSubscribe(onMessage);
  const es = new EventSource("/api/feed/stream");
  es.addEventListener("open", () => onOpen?.());
  es.addEventListener("error", () => onDown?.());
  es.addEventListener("message", (e) => {
    try { onMessage(JSON.parse((e as MessageEvent).data)); } catch { /* ignore malformed */ }
  });
  return () => es.close();
}

/** Merge by id, newest first; keeps messages that arrived on the stream before a snapshot. */
export function mergeFeed(a: FeedMessage[], b: FeedMessage[]): FeedMessage[] {
  const byId = new Map<string, FeedMessage>();
  for (const m of [...a, ...b]) byId.set(m.id, m);
  return [...byId.values()].sort((x, y) => y.received_at.localeCompare(x.received_at));
}

// ---------------------------------------------------------------- the person's own case

const RECENT_CASE = "recentCase";
export const recentCase = {
  get: () => localStorage.getItem(RECENT_CASE),
  set: (id: string) => localStorage.setItem(RECENT_CASE, id),
  clear: () => localStorage.removeItem(RECENT_CASE),
};
