// Mirror of backend/app/schemas.py. Change together with docs/API.md.

export type Language = "en" | "hi";
export type Channel = "sms" | "email" | "whatsapp" | "call" | "other";
export type Situation = "received" | "in_progress" | "victim";
export type Verdict = "safe" | "suspicious" | "scam";

export interface Contact {
  id: string;
  name: string;
  description: string;
  phone?: string | null;
  url?: string | null;
  region: string;
  category: string;
  source_url: string;
  name_hi?: string | null;
  description_hi?: string | null;
}

export interface Signal {
  id: string;
  label: string;
  weight: number;
  evidence?: string | null;
}

export interface ActionStep {
  id: string;
  title: string;
  detail: string;
  urgent: boolean;
  contact_id?: string | null;
}

export interface AnalyzeRequest {
  text: string;
  channel?: Channel;
  sender?: string | null;
  situation?: Situation;
  language?: Language;
}

export interface AnalyzeResponse {
  verdict: Verdict;
  risk_score: number;
  scam_type?: string | null;
  situation: Situation;
  headline: string;
  explanation: string;
  signals: Signal[];
  steps: ActionStep[];
  contacts: Contact[];
  language: Language;
  ai_used: boolean;
  ai_error?: string | null;
}

export type CaseStatus = "open" | "checking_in" | "escalated" | "claimed" | "resolved";

export interface CaseStep extends ActionStep {
  done: boolean;
  done_at?: string | null;
}

export interface CaseCreate {
  person_name: string;
  language?: Language;
  situation?: Situation;
  description: string;
  amount_lost_inr?: number | null;
  telegram_chat_id?: string | null;
  trusted_contact_name?: string | null;
  trusted_contact_telegram_chat_id?: string | null;
  analysis?: AnalyzeResponse | null;
}

export interface TimelineEvent {
  at: string;
  kind: string;
  message: string;
}

export interface Case {
  id: string;
  created_at: string;
  updated_at: string;
  status: CaseStatus;
  person_name: string;
  language: Language;
  situation: Situation;
  description: string;
  amount_lost_inr?: number | null;
  telegram_chat_id?: string | null;
  trusted_contact_name?: string | null;
  trusted_contact_telegram_chat_id?: string | null;
  analysis?: AnalyzeResponse | null;
  steps: CaseStep[];
  workflow_id?: string | null;
  checkins_sent: number;
  unanswered_checkins: number;
  coordinator?: string | null;
  timeline: TimelineEvent[];
}

export type CheckinAnswer = "done" | "not_yet" | "need_help";

export interface CheckinResponse {
  answer: CheckinAnswer;
  note?: string | null;
}

export interface CoordinatorAction {
  coordinator: string;
  note?: string | null;
}

export type NotificationChannel = "in_app" | "telegram";
export type NotificationStatus = "pending" | "sent" | "failed";

export interface Notification {
  id: string;
  created_at: string;
  case_id?: string | null;
  channel: NotificationChannel;
  recipient: string;
  message: string;
  status: NotificationStatus;
  attempts: number;
  last_error?: string | null;
}

export interface FeedMessage {
  id: string;
  received_at: string;
  channel: Channel;
  sender: string;
  subject?: string | null;
  text: string;
  analysis?: AnalyzeResponse | null;
}

export interface ChaosSettings {
  telegram_failure_rate: number;
  llm_down: boolean;
  slow_analyze_ms: number;
}

export interface ReadyStatus {
  status: "ready" | "not_ready";
  checks: Record<string, unknown>;
}
