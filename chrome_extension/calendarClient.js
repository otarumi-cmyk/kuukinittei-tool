// Google Calendar API クライアント（FreeBusy + Events + Meetリンク + 候補生成）
import { TZ, WEEKDAYS_JP } from "./config.js";

const API_BASE = "https://www.googleapis.com/calendar/v3";

// ===== OAuth =====
export function getAuthToken(interactive = true) {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive }, (token) => {
      if (chrome.runtime.lastError || !token) {
        reject(new Error(chrome.runtime.lastError?.message || "認証失敗"));
        return;
      }
      resolve(token);
    });
  });
}

export function clearCachedToken(token) {
  return new Promise((resolve) => {
    chrome.identity.removeCachedAuthToken({ token }, () => resolve());
  });
}

async function apiFetch(path, options = {}) {
  const token = await getAuthToken();
  const url = `${API_BASE}${path}`;
  const opts = {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  };
  let resp = await fetch(url, opts);
  if (resp.status === 401) {
    // トークン失効→キャッシュクリアして再認証
    await clearCachedToken(token);
    const newToken = await getAuthToken();
    opts.headers.Authorization = `Bearer ${newToken}`;
    resp = await fetch(url, opts);
  }
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
  }
  return resp.json();
}

// ===== Helpers =====
export function toJstParts(d) {
  // d は Date オブジェクト。JSTの月/日/時/分/曜日を返す。
  const fmt = new Intl.DateTimeFormat("ja-JP", {
    timeZone: TZ,
    year: "numeric", month: "numeric", day: "numeric",
    hour: "numeric", minute: "numeric", weekday: "short", hour12: false,
  });
  const parts = Object.fromEntries(fmt.formatToParts(d).map(p => [p.type, p.value]));
  // 月 火 水 ... のリストでindexを取る
  const wdMap = { "月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6 };
  return {
    year: parseInt(parts.year),
    month: parseInt(parts.month),
    day: parseInt(parts.day),
    hour: parseInt(parts.hour) % 24,
    minute: parseInt(parts.minute),
    weekday: wdMap[parts.weekday] ?? 0,
  };
}

// JSTで指定日時のDateを作る
export function dateAtJst(year, month, day, hour = 0, minute = 0) {
  // UTC基準で日本時間を作る: JST = UTC+9
  // year-month-day hh:mm JST = year-month-day (hh-9):mm UTC
  return new Date(Date.UTC(year, month - 1, day, hour - 9, minute));
}

export function addDays(d, n) {
  const r = new Date(d);
  r.setUTCDate(r.getUTCDate() + n);
  return r;
}

export function addMinutes(d, n) {
  return new Date(d.getTime() + n * 60000);
}

export function todayJstDate() {
  const p = toJstParts(new Date());
  return { year: p.year, month: p.month, day: p.day };
}

export function fmtTimeJst(d) {
  const p = toJstParts(d);
  return p.minute === 0 ? `${p.hour}時` : `${p.hour}:${String(p.minute).padStart(2, "0")}`;
}
export function fmtHmJst(d) {
  const p = toJstParts(d);
  return `${String(p.hour).padStart(2, "0")}:${String(p.minute).padStart(2, "0")}`;
}
export function fmtDateJst(d) {
  const p = toJstParts(d);
  return `${p.month}/${p.day}(${WEEKDAYS_JP[p.weekday]})`;
}
export function fmtRangeJst(s, e) {
  const sp = toJstParts(s), ep = toJstParts(e);
  const sw = sp.minute === 0, ew = ep.minute === 0;
  if (sw && ew) return `${sp.hour}~${ep.hour}時`;
  if (sw) return `${sp.hour}時~${ep.hour}:${String(ep.minute).padStart(2,"0")}`;
  if (ew) return `${sp.hour}:${String(sp.minute).padStart(2,"0")}~${ep.hour}時`;
  return `${sp.hour}:${String(sp.minute).padStart(2,"0")}~${ep.hour}:${String(ep.minute).padStart(2,"0")}`;
}

// ===== FreeBusy =====
export async function fetchBusy(emails, timeMin, timeMax) {
  const body = {
    timeMin: timeMin.toISOString(),
    timeMax: timeMax.toISOString(),
    timeZone: TZ,
    items: emails.map(e => ({ id: e })),
  };
  const result = await apiFetch("/freeBusy", {
    method: "POST",
    body: JSON.stringify(body),
  });
  const out = {};
  for (const [email, info] of Object.entries(result.calendars || {})) {
    if (info.errors) throw new Error(`${email}: ${JSON.stringify(info.errors)}`);
    out[email] = (info.busy || []).map(p => [new Date(p.start), new Date(p.end)]);
  }
  return out;
}

// ===== Free interval logic =====
export function freeWithinWindow(busy, windowStart, windowEnd) {
  // busy は [Date, Date] のリスト
  const clipped = [];
  for (const [s, e] of busy) {
    if (e <= windowStart || s >= windowEnd) continue;
    clipped.push([s < windowStart ? windowStart : s, e > windowEnd ? windowEnd : e]);
  }
  clipped.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const [s, e] of clipped) {
    if (merged.length && s <= merged[merged.length - 1][1]) {
      merged[merged.length - 1][1] = new Date(Math.max(merged[merged.length - 1][1].getTime(), e.getTime()));
    } else {
      merged.push([s, e]);
    }
  }
  const free = [];
  let cursor = windowStart;
  for (const [s, e] of merged) {
    if (cursor < s) free.push([cursor, s]);
    if (cursor < e) cursor = e;
  }
  if (cursor < windowEnd) free.push([cursor, windowEnd]);
  return free;
}

export function unionIntervals(intervals) {
  if (!intervals.length) return [];
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  const merged = [[sorted[0][0], sorted[0][1]]];
  for (let i = 1; i < sorted.length; i++) {
    const [s, e] = sorted[i];
    const last = merged[merged.length - 1];
    if (s <= last[1]) last[1] = new Date(Math.max(last[1].getTime(), e.getTime()));
    else merged.push([s, e]);
  }
  return merged;
}

// ===== Event creation =====
export async function createEventWithMeet({
  calendarId = "primary",
  title,
  start,
  end,
  description = "",
  attendees = [],
  sendUpdates = "none",
}) {
  const body = {
    summary: title,
    description,
    start: { dateTime: start.toISOString(), timeZone: TZ },
    end: { dateTime: end.toISOString(), timeZone: TZ },
    conferenceData: {
      createRequest: {
        requestId: crypto.randomUUID(),
        conferenceSolutionKey: { type: "hangoutsMeet" },
      },
    },
  };
  if (attendees.length) body.attendees = attendees;
  const qs = new URLSearchParams({
    conferenceDataVersion: "1",
    sendUpdates,
  });
  return apiFetch(
    `/calendars/${encodeURIComponent(calendarId)}/events?${qs}`,
    { method: "POST", body: JSON.stringify(body) }
  );
}

export function extractMeetLink(event) {
  const ep = (event.conferenceData?.entryPoints || []).find(e => e.entryPointType === "video");
  return ep?.uri || event.hangoutLink || null;
}

// ===== Find free resource =====
export async function findFreeResource(resourceEmails, start, end) {
  if (!resourceEmails.length) return null;
  const busyMap = await fetchBusy(resourceEmails, start, end);
  for (const email of resourceEmails) {
    const busy = busyMap[email] || [];
    if (busy.length === 0) return email;
  }
  return null;
}
