import * as cfg from "./config.js";
import * as cal from "./calendarClient.js";
import {
  DEFAULT_TEMPLATES,
  loadTemplates,
  resetTemplates,
  safeFormat,
  saveTemplates,
} from "./templateStore.js";
import {
  CATEGORIES as LINE_CATEGORIES,
  QUALITY_CHECKLIST,
  DEFAULT_LINE_TEMPLATES,
  loadLineTemplates,
  saveLineTemplates,
  resetLineTemplates,
  searchTemplates as searchLine,
} from "./lineTemplateStore.js";

// ===== Tab switching =====
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ===== Copy buttons =====
document.querySelectorAll(".copy").forEach(btn => {
  btn.addEventListener("click", async () => {
    const target = document.getElementById(btn.dataset.target);
    await navigator.clipboard.writeText(target.textContent);
    btn.classList.add("copied");
    const original = btn.textContent;
    btn.textContent = "✓ コピー済";
    setTimeout(() => {
      btn.classList.remove("copied");
      btn.textContent = original;
    }, 1500);
  });
});

// ===== Helpers =====
function setStatus(el, msg, kind = "") {
  el.textContent = msg;
  el.className = "status " + (kind ? kind : "");
}
function fmtDateForInput(d) {
  const yyyy = d.year, mm = String(d.month).padStart(2, "0"), dd = String(d.day).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}
function parseDateInput(s) {
  // "YYYY-MM-DD" → {year, month, day}
  const [y, m, d] = s.split("-").map(Number);
  return { year: y, month: m, day: d };
}

// ===== Initialize defaults =====
const today = cal.todayJstDate();
const tomorrow = (() => { const d = cal.dateAtJst(today.year, today.month, today.day); const dd = cal.addDays(d, 1); return cal.toJstParts(dd); })();
const plus14 = (() => { const d = cal.dateAtJst(today.year, today.month, today.day); const dd = cal.addDays(d, 14); return cal.toJstParts(dd); })();
const plus2 = (() => { const d = cal.dateAtJst(today.year, today.month, today.day); const dd = cal.addDays(d, 2); return cal.toJstParts(dd); })();
const plus4 = (() => { const d = cal.dateAtJst(today.year, today.month, today.day); const dd = cal.addDays(d, 4); return cal.toJstParts(dd); })();

document.getElementById("gen-start").value = fmtDateForInput(plus2);
document.getElementById("gen-end").value = fmtDateForInput(plus4);
document.getElementById("sug-start").value = fmtDateForInput(tomorrow);
document.getElementById("sug-end").value = fmtDateForInput(plus14);
document.getElementById("bk-date").value = fmtDateForInput(tomorrow);

// Populate staff dropdowns
function fillStaff(selectEl, defaultEmail) {
  selectEl.innerHTML = "";
  for (const email of cfg.EMAILS) {
    const opt = document.createElement("option");
    opt.value = email;
    opt.textContent = cfg.DISPLAY_NAMES[email] || email;
    if (email === defaultEmail) opt.selected = true;
    selectEl.appendChild(opt);
  }
}
fillStaff(document.getElementById("sug-staff"), "d.yokoyama@migi-nanameue.co.jp");
fillStaff(document.getElementById("bk-staff"), "y.hiraga@migi-nanameue.co.jp");

function updateDurationHint(staffEl, hintEl) {
  const email = staffEl.value;
  const dur = cfg.BOOKING_DURATION[email] || 60;
  const name = cfg.DISPLAY_NAMES[email] || email;
  hintEl.textContent = `所要時間: ${dur}分（${name}）`;
}
document.getElementById("sug-staff").addEventListener("change", e => {
  updateDurationHint(e.target, document.getElementById("sug-duration-hint"));
  // 担当者に応じて時間帯デフォルトを更新
  const h = cfg.BOOKABLE_HOURS[e.target.value] || { start: 10, end: 22 };
  document.getElementById("sug-h-start").value = h.start;
  document.getElementById("sug-h-end").value = h.end;
});
document.getElementById("bk-staff").addEventListener("change", e => updateDurationHint(e.target, document.getElementById("bk-duration-hint")));
updateDurationHint(document.getElementById("sug-staff"), document.getElementById("sug-duration-hint"));
updateDurationHint(document.getElementById("bk-staff"), document.getElementById("bk-duration-hint"));

// ===== Tab 1: 空き日程ジェネレーター =====
document.getElementById("gen-run").addEventListener("click", async () => {
  const status = document.getElementById("gen-status");
  const out = document.getElementById("gen-out");
  const brk = document.getElementById("gen-breakdown");
  out.textContent = ""; brk.textContent = "";
  const startD = parseDateInput(document.getElementById("gen-start").value);
  const endD = parseDateInput(document.getElementById("gen-end").value);
  setStatus(status, "カレンダー取得中…", "loading");
  try {
    const tmin = cal.dateAtJst(startD.year, startD.month, startD.day, 0, 0);
    const tmax = cal.dateAtJst(endD.year, endD.month, endD.day, 23, 59);
    const busyMap = await cal.fetchBusy(cfg.EMAILS, tmin, tmax);

    const lines = [];
    const brkLines = [];
    // 日を1日ずつイテレート
    let cur = { ...startD };
    while (true) {
      const dayD = cal.dateAtJst(cur.year, cur.month, cur.day);
      const dayEndJst = cal.dateAtJst(cur.year, cur.month, cur.day, 23, 59);
      // 集計: 全員のフィルタ後の空きの和
      const allFree = [];
      const perPerson = {};
      for (const email of cfg.EMAILS) {
        const minMin = cfg.MIN_SLOT_MINUTES[email] || 0;
        const ws = cal.dateAtJst(cur.year, cur.month, cur.day, 10, 0);
        const we = cal.dateAtJst(cur.year, cur.month, cur.day, 22, 0);
        const busy = busyMap[email] || [];
        const free = cal.freeWithinWindow(busy, ws, we);
        const filtered = free.filter(([s, e]) => (e - s) >= minMin * 60000);
        perPerson[email] = filtered;
        for (const x of filtered) allFree.push(x);
      }
      const unioned = cal.unionIntervals(allFree);
      const dateLbl = cal.fmtDateJst(dayD);
      if (unioned.length) {
        lines.push(`【${dateLbl}】${unioned.map(([s,e]) => `${cal.fmtHmJst(s)}-${cal.fmtHmJst(e)}`).join(" / ")}`);
      } else {
        lines.push(`【${dateLbl}】空きなし`);
      }
      brkLines.push(`【${dateLbl}】${unioned.length ? unioned.map(([s,e])=>`${cal.fmtHmJst(s)}-${cal.fmtHmJst(e)}`).join(" / ") : "空きなし"}`);
      for (const email of cfg.EMAILS) {
        const name = cfg.DISPLAY_NAMES[email] || email;
        const ints = perPerson[email];
        brkLines.push(`  ├ ${name}: ${ints.length ? ints.map(([s,e])=>`${cal.fmtHmJst(s)}-${cal.fmtHmJst(e)}`).join(" / ") : "なし"}`);
      }
      brkLines.push("");

      // 次の日へ
      const next = cal.addDays(cal.dateAtJst(cur.year, cur.month, cur.day), 1);
      const np = cal.toJstParts(next);
      const endJst = cal.dateAtJst(endD.year, endD.month, endD.day);
      if (next > endJst) break;
      cur = { year: np.year, month: np.month, day: np.day };
    }

    out.textContent = lines.join("\n");
    brk.textContent = brkLines.join("\n").trimEnd();
    setStatus(status, `生成完了（${lines.length}日分）`, "ok");
  } catch (err) {
    setStatus(status, `エラー: ${err.message}`, "error");
  }
});

// ===== Tab 2: 候補提案 =====
document.getElementById("sug-run").addEventListener("click", async () => {
  const status = document.getElementById("sug-status");
  const out = document.getElementById("sug-out");
  const skippedWrap = document.getElementById("sug-skipped-wrap");
  const skippedUl = document.getElementById("sug-skipped");
  out.textContent = ""; skippedUl.innerHTML = ""; skippedWrap.style.display = "none";

  const staffEmail = document.getElementById("sug-staff").value;
  const startD = parseDateInput(document.getElementById("sug-start").value);
  const endD = parseDateInput(document.getElementById("sug-end").value);
  const hStart = parseInt(document.getElementById("sug-h-start").value);
  const hEnd = parseInt(document.getElementById("sug-h-end").value);
  const dur = cfg.BOOKING_DURATION[staffEmail] || 60;
  const hours = cfg.BOOKABLE_HOURS[staffEmail] || { weekdays: [0,1,2,3,4,5,6] };
  const noWeekend = document.getElementById("sug-no-weekend").checked;
  let allowedWeekdays = [...hours.weekdays];
  if (noWeekend) {
    allowedWeekdays = allowedWeekdays.filter(wd => wd !== 5 && wd !== 6);
  }

  setStatus(status, "カレンダー取得中…", "loading");
  try {
    const tmin = cal.dateAtJst(startD.year, startD.month, startD.day, 0, 0);
    const tmax = cal.dateAtJst(endD.year, endD.month, endD.day, 23, 59);
    const busyMap = await cal.fetchBusy([staffEmail], tmin, tmax);
    const busy = busyMap[staffEmail] || [];
    const now = new Date();
    const minMs = dur * 60000;

    const lines = [];
    const skipped = [];
    let cur = { ...startD };
    while (true) {
      const dayD = cal.dateAtJst(cur.year, cur.month, cur.day);
      const wd = cal.toJstParts(dayD).weekday;
      const dateLbl = cal.fmtDateJst(dayD);
      if (!allowedWeekdays.includes(wd)) {
        skipped.push(`${dateLbl}: 営業対象外の曜日`);
      } else {
        const ws = cal.dateAtJst(cur.year, cur.month, cur.day, hStart, 0);
        const we = cal.dateAtJst(cur.year, cur.month, cur.day, hEnd, 0);
        let free = cal.freeWithinWindow(busy, ws, we);
        free = free.map(([s,e]) => [s < now ? now : s, e]).filter(([s,e]) => e > now && e > s);
        const longEnough = free.filter(([s,e]) => (e - s) >= minMs);
        const shortOnly = free.filter(([s,e]) => (e - s) < minMs);
        if (longEnough.length) {
          lines.push(`・${dateLbl} ${longEnough.map(([s,e]) => cal.fmtRangeJst(s,e)).join(", ")}`);
        } else if (shortOnly.length) {
          skipped.push(`${dateLbl}: 細切れの空きのみ (${shortOnly.map(([s,e]) => cal.fmtRangeJst(s,e)).join(", ")}) — ${dur}分未満`);
        } else {
          skipped.push(`${dateLbl}: 予定で埋まっています`);
        }
      }
      const next = cal.addDays(dayD, 1);
      const np = cal.toJstParts(next);
      const endJst = cal.dateAtJst(endD.year, endD.month, endD.day);
      if (next > endJst) break;
      cur = { year: np.year, month: np.month, day: np.day };
    }

    if (!lines.length) {
      setStatus(status, "候補が見つかりませんでした。", "error");
    } else {
      const tpl = (await loadTemplates()).suggest_dm;
      out.textContent = safeFormat(tpl, {
        slots: lines.join("\n"),
        staff: cfg.DISPLAY_NAMES[staffEmail] || staffEmail,
        duration: String(dur),
      });
      setStatus(status, `${lines.length}日分の候補を生成しました。`, "ok");
    }
    if (skipped.length) {
      skippedWrap.style.display = "block";
      for (const s of skipped) {
        const li = document.createElement("li");
        li.textContent = s;
        skippedUl.appendChild(li);
      }
    }
  } catch (err) {
    setStatus(status, `エラー: ${err.message}`, "error");
  }
});

// ===== Tab 3: 予約作成 =====
document.getElementById("bk-run").addEventListener("click", async () => {
  const status = document.getElementById("bk-status");
  const result = document.getElementById("bk-result");
  const dm = document.getElementById("bk-dm");
  const dmLabel = document.getElementById("bk-dm-label");
  const copyBtn = document.getElementById("bk-copy");
  result.innerHTML = ""; dm.textContent = "";
  dmLabel.style.display = "none"; copyBtn.style.display = "none";

  const staffEmail = document.getElementById("bk-staff").value;
  const instaName = document.getElementById("bk-insta").value.trim();
  const dateStr = document.getElementById("bk-date").value;
  const timeStr = document.getElementById("bk-time").value;
  if (!instaName) {
    setStatus(status, "インスタ名を入力してください。", "error");
    return;
  }
  const [hh, mm] = timeStr.split(":").map(Number);
  const dParts = parseDateInput(dateStr);
  const startDt = cal.dateAtJst(dParts.year, dParts.month, dParts.day, hh, mm);
  const dur = cfg.BOOKING_DURATION[staffEmail] || 60;
  const endDt = cal.addMinutes(startDt, dur);
  const staffName = cfg.DISPLAY_NAMES[staffEmail] || staffEmail;

  if (startDt < new Date()) {
    setStatus(status, "過去の日時は指定できません。", "error");
    return;
  }

  setStatus(status, `${staffName}さんの空き確認中…`, "loading");
  try {
    const busyMap = await cal.fetchBusy([staffEmail], startDt, endDt);
    const busy = busyMap[staffEmail] || [];
    if (busy.length) {
      setStatus(status, `❌ ${staffName}さんはその時間に予定があります。`, "error");
      return;
    }

    setStatus(status, "空いてるフォンブース検索中…", "loading");
    const phoneBox = await cal.findFreeResource(cfg.PHONE_BOX_RESOURCES, startDt, endDt);

    const attendees = [{ email: staffEmail }];
    if (phoneBox) attendees.push({ email: phoneBox, resource: true });
    for (const n of cfg.NOTIFY_EMAILS) attendees.push({ email: n, optional: true });

    const title = `${instaName}様 ${cfg.DEFAULT_MEETING_TITLE}`;
    const description =
      `インスタ名: ${instaName}\n担当: ${staffName}\n` +
      (phoneBox ? `フォンブース: ${cfg.PHONE_BOX_NAMES[phoneBox]}\n` : "") +
      "（kuukinittei 拡張から自動作成）";

    setStatus(status, "予定を作成中…", "loading");
    const event = await cal.createEventWithMeet({
      calendarId: "primary",
      title, start: startDt, end: endDt, description,
      attendees, sendUpdates: "all",
    });
    const meetLink = cal.extractMeetLink(event);

    setStatus(status, `🎉 予約完了！担当: ${staffName}（${dur}分）`, "ok");
    const phoneLine = phoneBox
      ? `<div><strong>フォンブース:</strong> ${cfg.PHONE_BOX_NAMES[phoneBox]}</div>`
      : `<div style="color:#ffc107;">⚠️ 空きフォンブース見つからず</div>`;
    result.innerHTML =
      phoneLine +
      (meetLink ? `<div><strong>Meetリンク:</strong> <a href="${meetLink}" target="_blank">${meetLink}</a></div>` : "") +
      `<div><strong>日時:</strong> ${cal.fmtDateJst(startDt)} ${cal.fmtHmJst(startDt)} 〜 ${cal.fmtHmJst(endDt)}</div>` +
      `<div><strong>タイトル:</strong> ${title}</div>` +
      (event.htmlLink ? `<div><a href="${event.htmlLink}" target="_blank">カレンダーで開く</a></div>` : "");

    const tpl = (await loadTemplates()).booking_dm;
    dm.textContent = safeFormat(tpl, {
      datetime: `${cal.fmtDateJst(startDt)} ${cal.fmtHmJst(startDt)} 〜 ${cal.fmtHmJst(endDt)}`,
      link: meetLink || "(Meetリンク取得失敗)",
      staff: staffName,
      insta: instaName,
      title,
      phone_box: phoneBox ? cfg.PHONE_BOX_NAMES[phoneBox] : "",
    });
    dmLabel.style.display = "block";
    copyBtn.style.display = "inline-block";
  } catch (err) {
    setStatus(status, `エラー: ${err.message}`, "error");
  }
});

// ===== Tab 4: テンプレート =====
async function initTemplatesTab() {
  const tpl = await loadTemplates();
  document.getElementById("tpl-booking").value = tpl.booking_dm;
  document.getElementById("tpl-suggest").value = tpl.suggest_dm;
}
initTemplatesTab();

document.getElementById("tpl-save").addEventListener("click", async () => {
  const booking = document.getElementById("tpl-booking").value;
  const suggest = document.getElementById("tpl-suggest").value;
  await saveTemplates({ booking_dm: booking, suggest_dm: suggest });
  setStatus(document.getElementById("tpl-status"), "✓ 保存しました（このChromeでのみ有効）", "ok");
});

document.getElementById("tpl-reset").addEventListener("click", async () => {
  await resetTemplates();
  document.getElementById("tpl-booking").value = DEFAULT_TEMPLATES.booking_dm;
  document.getElementById("tpl-suggest").value = DEFAULT_TEMPLATES.suggest_dm;
  setStatus(document.getElementById("tpl-status"), "↺ デフォルトに戻しました", "ok");
});

// ===== Tab 5: LINE返信補助 =====
let _lineTemplates = [];
let _activeCategory = null;   // null = 全て
let _activeSituation = null;  // null = フィルタなし

async function initLineTab() {
  _lineTemplates = await loadLineTemplates();
  renderLineCategories();
  renderLineSituations();
  renderLineResults(_lineTemplates);
  renderLineMgmtList();
  renderQualityChecklist();
}

function escHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// --- カテゴリバー ---
function renderLineCategories() {
  const container = document.getElementById("line-categories");
  container.innerHTML = "";
  const allBtn = document.createElement("button");
  allBtn.className = "line-cat-btn" + (_activeCategory === null ? " active" : "");
  allBtn.textContent = "全て";
  allBtn.addEventListener("click", () => {
    _activeCategory = null;
    _activeSituation = null;
    document.getElementById("line-search").value = "";
    renderLineCategories();
    renderLineSituations();
    renderLineResults(_lineTemplates);
  });
  container.appendChild(allBtn);

  for (const cat of LINE_CATEGORIES) {
    const btn = document.createElement("button");
    btn.className = "line-cat-btn" + (_activeCategory === cat.id ? " active" : "");
    btn.textContent = cat.label;
    btn.addEventListener("click", () => {
      _activeCategory = _activeCategory === cat.id ? null : cat.id;
      _activeSituation = null;
      document.getElementById("line-search").value = "";
      renderLineCategories();
      renderLineSituations();
      doLineFilter();
    });
    container.appendChild(btn);
  }
}

// --- シチュエーション タグ ---
function renderLineSituations() {
  const container = document.getElementById("line-situations");
  container.innerHTML = "";
  const pool = _activeCategory
    ? _lineTemplates.filter(t => t.category === _activeCategory)
    : _lineTemplates;

  for (const t of pool) {
    const btn = document.createElement("button");
    btn.className = "line-tag" + (_activeSituation === t.id ? " active" : "");
    btn.textContent = t.situation;
    btn.addEventListener("click", () => {
      if (_activeSituation === t.id) {
        _activeSituation = null;
        doLineFilter();
      } else {
        _activeSituation = t.id;
        renderLineResults([t]);
      }
      renderLineSituations();
    });
    container.appendChild(btn);
  }
}

// --- フィルタ / 検索 ---
function doLineFilter() {
  const query = document.getElementById("line-search").value.trim();
  let pool = _activeCategory
    ? _lineTemplates.filter(t => t.category === _activeCategory)
    : [..._lineTemplates];
  if (_activeSituation) {
    pool = pool.filter(t => t.id === _activeSituation);
  }
  if (query) {
    pool = searchLine(pool, query);
  }
  renderLineResults(pool);
}

// --- テンプレを1通目・2通目に分割 ---
function splitBody(body) {
  // 最後の \n\n で分割して共感パート(1通目)とクロージング(2通目)に分ける
  const idx = body.lastIndexOf("\n\n");
  if (idx === -1) return { part1: body, part2: "" };
  return { part1: body.substring(0, idx), part2: body.substring(idx + 2) };
}

// --- コピーブロック生成（クリックでコピー） ---
function makeCopyBlock(text, labelText, labelClass) {
  const wrap = document.createElement("div");

  // ラベル
  const lbl = document.createElement("div");
  lbl.className = `line-part-label ${labelClass}`;
  lbl.textContent = labelText;
  wrap.appendChild(lbl);

  // テキストブロック
  const block = document.createElement("div");
  block.className = "line-copy-block";
  block.textContent = text;

  const hint = document.createElement("span");
  hint.className = "copy-hint";
  hint.textContent = "タップでコピー";
  block.appendChild(hint);

  block.addEventListener("click", async () => {
    await navigator.clipboard.writeText(text);
    block.classList.add("copied");
    hint.textContent = "✓ コピー済";
    setTimeout(() => {
      block.classList.remove("copied");
      hint.textContent = "タップでコピー";
    }, 1500);
  });

  wrap.appendChild(block);
  return wrap;
}

// --- 結果カード描画 ---
function renderLineResults(results) {
  const container = document.getElementById("line-results");
  const countEl = document.getElementById("line-results-count");
  container.innerHTML = "";
  countEl.textContent = results.length
    ? `${results.length}件`
    : "一致するテンプレートがありません";

  for (const t of results) {
    const { part1, part2 } = splitBody(t.body);

    const card = document.createElement("div");
    card.className = "line-card";

    // ヘッダー
    const header = document.createElement("div");
    header.className = "line-card-header";
    const catLabel = (LINE_CATEGORIES.find(c => c.id === t.category) || {}).label || "";
    header.innerHTML =
      `<strong>${escHtml(t.situation)}</strong>` +
      `<span class="line-card-tags">${catLabel}</span>`;
    card.appendChild(header);

    // 1通目（クリックでコピー）
    card.appendChild(makeCopyBlock(part1, "① 共感", "line-part-label-1"));

    // 2通目（ある場合のみ）
    if (part2) {
      card.appendChild(makeCopyBlock(part2, "② クロージング", "line-part-label-2"));
    }

    container.appendChild(card);
  }
}

// --- 品質チェックリスト ---
function renderQualityChecklist() {
  const ul = document.getElementById("line-quality-checklist");
  ul.innerHTML = "";
  for (const item of QUALITY_CHECKLIST) {
    const li = document.createElement("li");
    li.textContent = item;
    ul.appendChild(li);
  }
}

// --- テンプレ管理 ---
function renderLineMgmtList() {
  const container = document.getElementById("line-mgmt-list");
  const countEl = document.getElementById("line-mgmt-count");
  container.innerHTML = "";
  countEl.textContent = _lineTemplates.length;

  for (const t of _lineTemplates) {
    const item = document.createElement("div");
    item.className = "line-mgmt-item";
    const info = document.createElement("div");
    info.className = "line-mgmt-item-info";
    const catLabel = (LINE_CATEGORIES.find(c => c.id === t.category) || {}).label || "";
    info.innerHTML =
      `<div class="mgmt-title">${escHtml(t.situation)}</div>` +
      `<div class="mgmt-tags">${catLabel} · ${t.tags.map(tag => "#" + escHtml(tag)).join(" ")}</div>`;
    const delBtn = document.createElement("button");
    delBtn.className = "line-del";
    delBtn.textContent = "削除";
    delBtn.addEventListener("click", async () => {
      _lineTemplates = _lineTemplates.filter(x => x.id !== t.id);
      await saveLineTemplates(_lineTemplates);
      renderLineMgmtList();
      renderLineSituations();
      doLineFilter();
      setStatus(document.getElementById("line-mgmt-status"), `「${t.situation}」を削除しました`, "ok");
    });
    item.appendChild(info);
    item.appendChild(delBtn);
    container.appendChild(item);
  }
}

// --- イベント ---
document.getElementById("line-search").addEventListener("input", () => {
  _activeSituation = null;
  renderLineSituations();
  doLineFilter();
});

document.getElementById("line-add-btn").addEventListener("click", async () => {
  const catEl = document.getElementById("line-new-cat");
  const sitEl = document.getElementById("line-new-situation");
  const tagsEl = document.getElementById("line-new-tags");
  const body1El = document.getElementById("line-new-body1");
  const body2El = document.getElementById("line-new-body2");
  const situation = sitEl.value.trim();
  const tags = tagsEl.value.split(/[,、\s]+/).map(s => s.trim()).filter(Boolean);
  const p1 = body1El.value.trim();
  const p2 = body2El.value.trim();
  if (!situation || !p1) {
    setStatus(document.getElementById("line-mgmt-status"), "シチュエーション名と1通目は必須です", "error");
    return;
  }
  const body = p2 ? p1 + "\n\n" + p2 : p1;
  _lineTemplates.push({
    id: "custom_" + Date.now(),
    category: catEl.value,
    situation,
    tags,
    body,
  });
  await saveLineTemplates(_lineTemplates);
  sitEl.value = ""; tagsEl.value = ""; body1El.value = ""; body2El.value = "";
  renderLineMgmtList();
  renderLineSituations();
  doLineFilter();
  setStatus(document.getElementById("line-mgmt-status"), `「${situation}」を追加しました`, "ok");
});

document.getElementById("line-reset-btn").addEventListener("click", async () => {
  await resetLineTemplates();
  _lineTemplates = DEFAULT_LINE_TEMPLATES.map(t => ({ ...t }));
  _activeCategory = null;
  _activeSituation = null;
  renderLineCategories();
  renderLineSituations();
  renderLineResults(_lineTemplates);
  renderLineMgmtList();
  setStatus(document.getElementById("line-mgmt-status"), "↺ デフォルトに戻しました", "ok");
});

initLineTab();
