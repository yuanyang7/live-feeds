(() => {
  "use strict";

  const V = window.vibe || null;
  const STATES = ["CA", "NY", "TX", "WA", "NJ"];
  const POLL_MS = 60 * 1000;
  const PAGE = 60;
  const DAY = 86400000;

  // ---- data source: vibeplat owner-data, or dev-data/*.json when run locally ----
  const ownerData = V && V.ownerData
    ? (k) => V.ownerData.entry(k)
    : async (k) => {
        const r = await fetch(`dev-data/${k}.json?t=${Date.now()}`);
        return r.ok ? r.json() : { value: null };
      };

  // ---- per-viewer prefs: vibe.storage when signed in, else localStorage ----
  const PREFS_KEY = "warn-watch";
  const prefs = {
    async load() {
      if (V && V.storage && V.authenticated) {
        try { const v = await V.storage.get("prefs"); if (v) return v; } catch (e) { /* guest or offline */ }
      }
      try { return JSON.parse(localStorage.getItem(PREFS_KEY)) || {}; } catch (e) { return {}; }
    },
    save(v) {
      try { localStorage.setItem(PREFS_KEY, JSON.stringify(v)); } catch (e) { /* blocked */ }
      if (V && V.storage && V.authenticated) V.storage.set("prefs", v).catch(() => {});
    },
  };

  // ---- i18n ----
  const lang = String((V && V.locale) || navigator.language || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
  const STR = {
    en: {
      tagline: "Layoff notices filed with US states, as they're posted.",
      statNotices: "Notices, last 30 days", statWorkers: "Workers, last 30 days", statNew: "New since your last visit",
      search: "Search company or city", latest: "Latest", largest: "Largest", all: "All",
      aboutTitle: "What's a WARN notice?",
      about: "Under the federal WARN Act, employers with 100+ workers must give 60 days' notice before a plant closing or mass layoff, and file it with the state. States publish these notices, and WARN Watch collects them in one place.",
      freshTitle: "How often is this updated?",
      freshCheck: "WARN Watch checks each state's official list every {h} hours.",
      freshCheck1: "WARN Watch checks each state's official list every hour.",
      freshStates: "States post new notices on their own schedules, usually a few times a week and often several days after the employer filed. New Jersey only lists the month a notice was posted.",
      freshPage: "While you have this page open, it refreshes itself every minute, so new notices appear without reloading.",
      cadence: "checks every {h} hours", cadence1: "checks hourly",
      sourcesTitle: "Sources",
      fine: "Data comes straight from state labor departments and can lag or be revised. Counts are what employers reported.",
      checked: "Checked {t}", stale: "Last checked {t} · updates may be delayed", loading: "Loading…",
      offline: "Couldn't reach the feed. Retrying…", noData: "No data yet — the feed hasn't run.",
      workers: "workers", worker: "worker", closure: "Closure", layoff: "Layoff", temp: "Temporary", isNew: "New",
      today: "Today", yesterday: "Yesterday", notices: "{n} notices", notice: "1 notice",
      posted: "Posted", effective: "Effective", reason: "Reason", industry: "Industry", type: "Type", source: "Source",
      monthOnly: "{m} (state lists month only)", viewSource: "{s} WARN list",
      empty: "No notices match.", more: "Show more", newToast: "{n} new notices — tap to see", newToast1: "1 new notice — tap to see",
      issue: "Source issue since {t}", ok: "Latest notice {t}", unknown: "?", dayWorkers: "{n} workers",
    },
    zh: {
      tagline: "美国各州公布的裁员通知（WARN），实时更新。",
      statNotices: "30天内通知", statWorkers: "30天内涉及人数", statNew: "上次来访后新增",
      search: "搜索公司或城市", latest: "最新", largest: "规模最大", all: "全部",
      aboutTitle: "什么是 WARN 通知？",
      about: "根据美国联邦 WARN 法案，100 人以上的雇主在关厂或大规模裁员前须提前 60 天通知，并向州政府备案。各州会公开这些通知，WARN Watch 把它们汇总在一处。",
      freshTitle: "多久更新一次？",
      freshCheck: "WARN Watch 每 {h} 小时检查一次各州的官方列表。",
      freshCheck1: "WARN Watch 每小时检查一次各州的官方列表。",
      freshStates: "各州按各自的节奏发布新通知，通常每周几次，且往往在雇主提交几天之后。新泽西州只公布通知发布的月份。",
      freshPage: "页面打开期间每分钟自动刷新，新通知无需重新加载即可出现。",
      cadence: "每 {h} 小时检查", cadence1: "每小时检查",
      sourcesTitle: "数据来源",
      fine: "数据直接来自各州劳工部门，可能有延迟或修订。人数为雇主申报数。",
      checked: "{t}检查", stale: "上次检查：{t} · 可能有延迟", loading: "加载中…",
      offline: "暂时无法连接数据源，正在重试…", noData: "暂无数据——数据源尚未运行。",
      workers: "人", worker: "人", closure: "关闭", layoff: "裁员", temp: "临时", isNew: "新",
      today: "今天", yesterday: "昨天", notices: "{n} 条通知", notice: "1 条通知",
      posted: "发布", effective: "生效", reason: "原因", industry: "行业", type: "类型", source: "来源",
      monthOnly: "{m}（该州仅公布月份）", viewSource: "{s} WARN 列表",
      empty: "没有匹配的通知。", more: "显示更多", newToast: "{n} 条新通知 — 点击查看", newToast1: "1 条新通知 — 点击查看",
      issue: "数据源异常，始于{t}", ok: "最新通知 {t}", unknown: "?", dayWorkers: "{n} 人",
    },
  };
  const t = (k, vars) => (STR[lang][k] || STR.en[k] || k).replace(/\{(\w+)\}/g, (_, n) => (vars && n in vars ? vars[n] : ""));
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });

  const locale = lang === "zh" ? "zh-CN" : "en-US";
  const fmtNum = new Intl.NumberFormat(locale);
  const fmtDay = new Intl.DateTimeFormat(locale, { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
  const fmtDate = new Intl.DateTimeFormat(locale, { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
  const fmtMonth = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric", timeZone: "UTC" });
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });

  function ago(iso) {
    const s = Math.round((Date.parse(iso) - Date.now()) / 1000);
    const a = Math.abs(s);
    if (a < 60) return rtf.format(0, "second");
    if (a < 3600) return rtf.format(Math.round(s / 60), "minute");
    if (a < 86400) return rtf.format(Math.round(s / 3600), "hour");
    return rtf.format(Math.round(s / 86400), "day");
  }
  const dayMs = (isoDate) => Date.parse(isoDate + "T00:00:00Z");
  const todayUtc = () => { const d = new Date(); return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()); };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // ---- state ----
  const $ = (id) => document.getElementById(id);
  const view = { state: "ALL", q: "", sort: "latest", limit: PAGE };
  let meta = null;
  const byState = {};
  const fresh = new Set();   // ids that arrived while this page was open
  let newSince = 0;          // notices first seen after this (ms) are "new for you"
  let saved = {};

  function allNotices() {
    const out = [];
    for (const code of STATES) {
      const p = byState[code];
      if (!p) continue;
      for (const n of p.notices) out.push(Object.assign({ st: code }, n));
    }
    return out;
  }
  const isNew = (n) => fresh.has(n.id) || Date.parse(n.seen) > newSince;

  function filtered() {
    const q = view.q.trim().toLowerCase();
    let list = allNotices().filter((n) =>
      (view.state === "ALL" || n.st === view.state) &&
      (!q || n.co.toLowerCase().includes(q) || (n.loc || "").toLowerCase().includes(q)));
    if (view.sort === "largest") list.sort((a, b) => (b.n || 0) - (a.n || 0) || b.posted.localeCompare(a.posted));
    else list.sort((a, b) => b.posted.localeCompare(a.posted) || b.seen.localeCompare(a.seen) || (b.n || 0) - (a.n || 0));
    return list;
  }

  // ---- render ----
  function renderStats() {
    const cutoff = todayUtc() - 30 * DAY;
    const scope = allNotices().filter((n) => view.state === "ALL" || n.st === view.state);
    const recent = scope.filter((n) => dayMs(n.posted) >= cutoff);
    $("statNotices").textContent = fmtNum.format(recent.length);
    $("statWorkers").textContent = fmtNum.format(recent.reduce((s, n) => s + (n.n || 0), 0));
    $("statNew").textContent = fmtNum.format(scope.filter(isNew).length);
  }

  function renderChips() {
    const all = allNotices();
    const count = (code) => all.filter((n) => code === "ALL" || n.st === code).length;
    const bad = (code) => meta && meta.states.some((s) => s.code === code && !s.ok);
    $("chips").innerHTML = ["ALL"].concat(STATES).map((code) =>
      `<button type="button" class="chip" data-state="${code}" aria-pressed="${view.state === code}">` +
      `${code === "ALL" ? esc(t("all")) : code}<small>${fmtNum.format(count(code))}</small>` +
      `${code !== "ALL" && bad(code) ? '<i class="warn-dot" aria-label="source issue"></i>' : ""}</button>`).join("");
  }

  function cardHtml(n) {
    const kind = n.kind ? `<span class="tag ${n.kind}">${esc(t(n.kind))}</span>` : "";
    const temp = n.tmp ? `<span class="tag layoff">${esc(t("temp"))}</span>` : "";
    const nw = isNew(n) ? `<span class="tag new">${esc(t("isNew"))}</span>` : "";
    const workers = n.n == null ? t("unknown") : fmtNum.format(n.n);
    const posted = n.pm ? t("monthOnly", { m: fmtMonth.format(dayMs(n.posted)) }) : fmtDate.format(dayMs(n.posted));
    const eff = n.eff ? (/^\d{4}-\d{2}-\d{2}$/.test(n.eff) ? fmtDate.format(dayMs(n.eff)) : n.eff) : "";
    const src = byState[n.st];
    const rows = [
      [t("posted"), esc(posted)],
      eff && [t("effective"), esc(eff)],
      n.kind && [t("type"), esc(t(n.kind)) + (n.tmp ? " · " + esc(t("temp")) : "")],
      n.why && [t("reason"), esc(n.why)],
      n.ind && [t("industry"), esc(n.ind)],
      src && [t("source"), `<a href="${esc(src.url)}" target="_blank" rel="noopener">${esc(t("viewSource", { s: src.name }))}</a>`],
    ].filter(Boolean);
    return `<details class="card${fresh.has(n.id) ? " fresh" : ""}" data-id="${esc(n.id)}">` +
      `<summary><div class="main"><h3>${esc(n.co)}</h3>` +
      `<div class="meta"><span class="st">${n.st}</span><span>${esc(n.loc)}</span>${kind}${temp}${nw}</div></div>` +
      `<div class="num${(n.n || 0) >= 250 ? " big" : ""}"><b>${workers}</b><span>${esc(n.n === 1 ? t("worker") : t("workers"))}</span></div>` +
      `</summary><dl>${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl></details>`;
  }

  function dayLabel(iso) {
    const d = dayMs(iso), today = todayUtc();
    if (d === today) return t("today");
    if (d === today - DAY) return t("yesterday");
    return fmtDay.format(d);
  }

  function renderList() {
    const list = filtered();
    const main = $("list");
    main.removeAttribute("aria-busy");
    if (!list.length) {
      main.innerHTML = `<p class="empty">${esc(meta ? t("empty") : t("noData"))}</p>`;
      return;
    }
    const shown = list.slice(0, view.limit);
    let html = "";
    if (view.sort === "latest") {
      const groups = new Map();
      for (const n of list) {
        const g = groups.get(n.posted) || { count: 0, workers: 0 };
        g.count++; g.workers += n.n || 0;
        groups.set(n.posted, g);
      }
      let last = null;
      for (const n of shown) {
        if (n.posted !== last) {
          const g = groups.get(n.posted);
          html += `<h2 class="day"><span>${esc(dayLabel(n.posted))}</span>` +
            `<span>${esc(g.count === 1 ? t("notice") : t("notices", { n: g.count }))} · ${esc(t("dayWorkers", { n: fmtNum.format(g.workers) }))}</span></h2>`;
          last = n.posted;
        }
        html += cardHtml(n);
      }
    } else {
      html = shown.map(cardHtml).join("");
    }
    if (list.length > shown.length) html += `<button type="button" class="more" id="more">${esc(t("more"))} (${fmtNum.format(list.length - shown.length)})</button>`;
    main.innerHTML = html;
  }

  function renderStatus() {
    const el = $("status"), live = $("live");
    if (!meta) { el.textContent = t("loading"); return; }
    const h = meta.checkEveryHours || 1;
    // Missing two scheduled runs in a row (plus slack for late Actions starts) means something's off.
    const stale = Date.now() - Date.parse(meta.checkedAt) > (2 * h + 1) * 3600 * 1000;
    el.textContent = stale ? t("stale", { t: ago(meta.checkedAt) })
      : t("checked", { t: ago(meta.checkedAt) }) + " · " + (h === 1 ? t("cadence1") : t("cadence", { h }));
    el.classList.toggle("stale", stale);
    live.classList.toggle("on", !stale);
  }

  function renderFreshness() {
    const h = (meta && meta.checkEveryHours) || 1;
    $("freshCheck").textContent = h === 1 ? t("freshCheck1") : t("freshCheck", { h });
  }

  function renderSources() {
    if (!meta) return;
    $("sources").innerHTML = meta.states.map((s) =>
      `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a>` +
      (s.ok
        ? `<span>${s.latest ? esc(t("ok", { t: fmtDate.format(dayMs(s.latest)) })) : ""}</span>`
        : `<span class="bad">${esc(t("issue", { t: ago(s.failingSince || meta.checkedAt) }))}</span>`) +
      `</li>`).join("");
  }

  function renderAll() { renderStatus(); renderStats(); renderChips(); renderList(); renderFreshness(); renderSources(); }

  // ---- loading & live updates ----
  async function loadState(code) {
    const e = await ownerData(`warn.${code}`);
    if (e && e.value) byState[code] = e.value;
  }

  async function refresh(initial) {
    let e;
    try { e = await ownerData("meta"); } catch (err) {
      if (initial) $("status").textContent = t("offline");
      return;
    }
    const next = e && e.value;
    if (!next) { if (initial) renderAll(); return; }
    const changed = next.states.filter((s) => !meta || (meta.states.find((o) => o.code === s.code) || {}).hash !== s.hash);
    const before = new Set(allNotices().map((n) => n.id));
    await Promise.all(changed.map((s) => loadState(s.code).catch(() => {})));
    meta = next;
    if (!initial) {
      const added = allNotices().filter((n) => !before.has(n.id));
      added.forEach((n) => fresh.add(n.id));
      if (added.length) showToast(added.length);
    }
    renderAll();
  }

  let toastTimer = 0;
  function showToast(n) {
    const el = $("toast");
    el.textContent = n === 1 ? t("newToast1") : t("newToast", { n });
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 8000);
  }

  // ---- events ----
  $("chips").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-state]");
    if (!b) return;
    view.state = b.dataset.state; view.limit = PAGE;
    renderChips(); renderStats(); renderList(); persist();
  });
  document.querySelector(".seg").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-sort]");
    if (!b) return;
    view.sort = b.dataset.sort; view.limit = PAGE;
    document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderList(); persist();
  });
  let qTimer = 0;
  $("q").addEventListener("input", (ev) => {
    clearTimeout(qTimer);
    qTimer = setTimeout(() => { view.q = ev.target.value; view.limit = PAGE; renderList(); }, 120);
  });
  $("list").addEventListener("click", (ev) => {
    if (ev.target.id === "more") { view.limit += PAGE; renderList(); }
  });
  $("toast").addEventListener("click", () => {
    $("toast").hidden = true;
    view.state = "ALL"; view.sort = "latest"; view.q = ""; $("q").value = ""; view.limit = PAGE;
    document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.sort === "latest")));
    renderAll();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  const bar = document.querySelector(".bar");
  new IntersectionObserver(([e]) => bar.classList.toggle("stuck", e.intersectionRatio < 1), { threshold: [1], rootMargin: "-1px 0px 0px 0px" }).observe(bar);

  function persist() { prefs.save(Object.assign(saved, { state: view.state, sort: view.sort })); }

  setInterval(() => { if (!document.hidden) refresh(false); }, POLL_MS);
  setInterval(renderStatus, 30 * 1000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(false); });

  (async () => {
    saved = await prefs.load();
    // First visit: treat the last few days as new so there's something to look at.
    newSince = saved.lastVisit ? Date.parse(saved.lastVisit) : Date.now() - 3 * DAY;
    if (STATES.includes(saved.state)) view.state = saved.state;
    if (saved.sort === "largest") {
      view.sort = "largest";
      document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.sort === "largest")));
    }
    renderStatus();
    await refresh(true);
    saved.lastVisit = new Date().toISOString();
    persist();
  })();
})();
