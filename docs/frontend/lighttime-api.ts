// Typed client for the LightTime backend. Copy to src/lib/lighttime-api.ts in the frontend repo.
// The backend test tests/test_contract.py checks these field names. Do not rename them here.
// The console's own types are the authority for Crew, history, station, check-in, thread and reminder shapes.
// See docs/specs/2026-11-14-console-data-design.md.

export type Stop = "station" | "moon" | "mars" | "sun";
export type Mode = "doctor_live" | "crew_first" | "ship_alone";
export type Level = "nominal" | "advisory" | "caution" | "warning" | "emergency";
export type Story = "stage" | "full" | "real";

/** The four colours on screen. Add an SOS token next to ok, watch and alert. */
export const LEVEL_LABEL: Record<Level, "OK" | "WATCH" | "ALERT" | "SOS"> = {
  nominal: "OK", advisory: "WATCH", caution: "WATCH", warning: "ALERT", emergency: "SOS",
};

export interface StopState {
  stop: Stop; label: string; link_up: boolean;
  delay_s: number;        // one way, mission seconds. For "sun" show "No link" and ignore this
  mode: Mode; who_decides: string; light_time_source: string;
  path_km: number;        // delay x speed of light
  round_trip_s: number;   // 2 x delay: the earliest a reply can come back
  plays_as_s: number;     // real seconds one leg takes in the demo
  ship_ai_role: string;
}
export interface MissionState extends StopState {
  speedup: number; stops: StopState[]; mission_day: number; platform: string;
  now: string;            // the ship's clock (UTC): count down from this, never from the browser's clock
  ship_ai: { name: string; line: string; version: string; parts: { name: string; does: string }[] };
}

export interface Reading {
  id: number; crew_id: number; at: string; source: string; signal_ok: boolean; context: string | null;
  heart_rate: number | null; spo2: number | null; skin_temp: number | null; bp_sys: number | null;
  bp_dia: number | null; glucose: number | null; sleep_hours: number | null; mood: number | null;
}
export interface UsualRange { low: number; high: number; n: number }
export interface CrewMember {      // the ship AI's fields; the console's Crew type has the rest
  id: string; name: string; role: string; level: Level;
  latest: Reading | null; typed: Reading | null; usual: { heart_rate: UsualRange | null };
  week: Record<string, (number | null)[]>;   // seven daily values per console metric, oldest first; the last is today's
  simulated: boolean;                         // the daily values come from the generated month
  is_cmo: boolean; restricted: boolean;
}

export interface Lookahead {
  now: number; per_min: number; eta_s: number; red_line: number;
  at: string; red_line_at: string;      // count down to red_line_at
  reply_s: number | null; earth_in_time: boolean;
  agreement: number;
}
export interface Timeline {
  raised_at: string; acknowledged_at: string | null; sent_at: string | null;
  earth_eta_s: number | null; earth_at: string | null;
  earliest_reply_at: string | null;     // count down to this for "earliest reply". Demo clock: never compare with red_line_at
  earth_after_s: number | null;           // true one-way seconds the report left with. Print this, not earth_at
  earliest_reply_after_s: number | null;  // true round-trip seconds. Print this, not earliest_reply_at
  reply_at: string | null; resolved_at: string | null;
}
export interface Alert {
  id: string; crew_id: string; crew: string; at: string; level: Level; vital: string;   // "A1", "C1"
  restricted: boolean;
  state: "OK" | "WATCH" | "ALERT" | "RECHECK" | "SOS";
  stage: "raised" | "acknowledged" | "sent" | "replied" | "resolved";
  metric: string; rule: string | null; symptoms: string[];
  value: number | null; unit: string | null; reason: string; source: string | null; auto: boolean;
  raised_by: "console" | "lighttime" | "crew";   // a console rule, the ship AI, or a person pressing SOS
  nasa_risk: string; steps: string[]; steps_done: number[]; next_step: string | null; acknowledged_by: string | null;
  cleared_at: string | null; cleared_by: string | null; cleared_note: string | null;
  why: string[];                        // how the ship reached this alert. Show it
  timeline: Timeline; lookahead: Lookahead | null; speak: string | null;
}

export interface LinkMessage {
  id: number; direction: "to_earth" | "to_ship";
  kind: "report" | "update" | "message" | "reply" | "summary";
  priority: number; payload: Record<string, unknown>; status: "queued" | "in_flight" | "delivered";
  in_reply_to: number | null; created_at: string; sent_at: string | null; deliver_at: string | null;
  delay_s: number | null; eta_s: number | null;       // eta_s: mission seconds left
  arrives_after_s: number | null; earliest_reply_after_s: number | null;
}
export interface EarthInbox { link_up: boolean; delay_s: number; mode: Mode; who_decides: string; messages: LinkMessage[] }
export interface Habitat {
  cabin: { temp_c: number; humidity_pct: number; co2_ppm: number; as_of: string };
  radiation: { total_mgy_day: number; gcr_mgy_day: number; saa_mgy_day: number; as_of: string } | null;
  source: string; url: string; kind: string;
}
export interface Source { id: string; agency: string; name: string; kind: "live" | "file" | "hand"; url: string; used_for: string; as_of: string }
export interface Network {
  passes: { dish: string; craft: string; round_trip_s: number }[]; source: string; url: string;
  dsn_one_way_s: number | null; horizons_one_way_s: number; differ_s: number | null;
}
/** One sensor stream of one suit minute in the health log (GET /api/base/packets). Simulated. */
export interface Packet {
  crew_id: string; suit_id: string; ts: string; mission_day: number; location: string;
  source: "ecg" | "chest_band" | "ppg" | "thermistor" | "imu";
  metric: "hr" | "resp" | "spo2" | "temp_c" | "skin_temp_c" | "activity_g";
  value: number; unit: string; signal_quality: number; window_s: number;
  sent_to_ground: false;                // the ship sends reports and summaries, never a raw packet
  ack: null;
  state?: "OK" | "ALERT" | "RECHECK";   // RECHECK under 0.6 signal; else only spo2 and temp_c are judged
  baseline?: [number, number]; rule?: string;
}
/** Each sensor's lowest signal over the newest hour of packets (GET /api/base/stream-health). */
export interface StreamHealth {
  sensors: { source: Packet["source"]; lowest_signal_quality: number; state: "OK" | "RECHECK" }[];
  window_minutes: number; simulated: boolean;
}
export type CheckIn = Partial<Pick<Reading, "bp_sys" | "bp_dia" | "glucose" | "sleep_hours" | "mood" | "spo2" | "heart_rate">>;

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000";

async function call<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(BASE + path, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return (await response.json()) as T;
}

export const api = {
  // ship
  state: () => call<MissionState>("/api/base/state"),
  dial: (stop: Stop) => call<{ state: StopState; flushed: number }>("/api/base/dial", { stop }),
  crew: () => call<CrewMember[]>("/api/base/crew"),
  readings: (crewId: string | number, limit = 120) => call<Reading[]>(`/api/base/crew/${crewId}/readings?limit=${limit}`),
  alerts: () => call<Alert[]>("/api/base/alerts?open=1"),
  allAlerts: () => call<Alert[]>("/api/base/alerts"),
  acknowledge: (id: string | number, by: string) => call<Alert>(`/api/base/alerts/${id}/ack`, { by }),
  tickStep: (id: string | number, index: number) => call<Alert>(`/api/base/alerts/${id}/steps`, { index }),
  sendToEarth: (id: string | number) => call<Alert>(`/api/base/alerts/${id}/send`, {}),
  resolve: (id: string | number, by: string, note: string) => call<Alert>(`/api/base/alerts/${id}/clear`, { by, note }),
  message: (text: string, from: string, alertId?: string | number) =>
    call<LinkMessage>("/api/base/messages", { text, from, alert_id: alertId ?? null }),
  sos: (crewId: string | number) => call<Alert>("/api/base/sos", { crew_id: crewId }),
  checkIn: (crewId: string | number, values: CheckIn) =>
    call<{ reading: Reading; alerts: Alert[] }>("/api/base/readings", { ...values, crew_id: crewId, source: "typed" }),
  outbox: () => call<LinkMessage[]>("/api/base/outbox"),    // everything that has left the ship: "What Earth has seen"
  inbox: () => call<LinkMessage[]>("/api/base/inbox"),
  habitat: () => call<Habitat>("/api/base/habitat"),
  sources: () => call<Source[]>("/api/base/sources"),
  sendSummaries: () => call<{ sent: number; pruned: number }>("/api/base/summary/send", {}),
  // demo controls
  reset: () => call<{ ok: boolean }>("/api/base/reset", {}),
  startStory: (name: Story, replay = true) => call<{ ok: boolean }>("/api/base/scenario/start", { name, replay }),
  stopStory: () => call<{ ok: boolean }>("/api/base/scenario/stop", {}),
  startDemo: () => call<{ ok: boolean; name: string; state: StopState }>("/api/base/demo/start", {}),
  // Earth
  earthInbox: () => call<EarthInbox>("/api/earth/inbox"),
  earthOutbox: () => call<LinkMessage[]>("/api/earth/outbox"),
  earthReply: (text: string, messageId?: number, from = "Flight surgeon") =>
    call<LinkMessage>("/api/earth/reply", { text, message_id: messageId ?? null, from }),
  network: () => call<Network>("/api/earth/network"),
};

const spoken = new Set<string>();
/** Say an alert's line once per alert and level. Call it from a client component. */
export function speakOnce(alert: Alert): void {
  if (!alert.speak || typeof window === "undefined") return;
  const key = `${alert.id}:${alert.level}:${alert.at}`;
  if (spoken.has(key)) return;
  spoken.add(key);
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(alert.speak));
}
