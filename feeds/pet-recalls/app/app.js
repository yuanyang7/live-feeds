(() => {
  "use strict";

  const V = window.vibe || null;
  const KEYS = ["recalls", "advisories"];
  const POLL_MS = 60 * 1000;
  const DAY = 86400000;
  const RECENT_DAYS = 30;
  const MAX_BRANDS = 12;

  // ---- data source: vibeplat owner-data, or dev-data/*.json when run locally ----
  const ownerData = V && V.ownerData
    ? (k) => V.ownerData.entry(k)
    : async (k) => {
        const r = await fetch(`dev-data/${k}.json?t=${Date.now()}`);
        return r.ok ? r.json() : { value: null };
      };

  // ---- per-viewer prefs: vibe.storage when signed in, else localStorage ----
  const PREFS_KEY = "bowl-check";
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
      tagline: "Dog and cat food recalls, straight from the FDA.", petsLabel: "Your pets",
      dogs: "Dogs", cats: "Cats", both: "Both",
      petDog: "dogs", petCat: "cats", petBoth: "dogs and cats",
      clear: "No recalls for {p} in the last 30 days", recent: "{n} recalls for {p} in the last 30 days",
      recent1: "1 recall for {p} in the last 30 days", lastOne: "Most recent: {b}, {d}",
      mineHit: "{n} of them mention a brand you feed", mineHit1: "1 of them mentions a brand you feed",
      mineTitle: "Brands you feed", mineHint: "We'll flag recalls that mention them.",
      addBrand: "Add a brand, e.g. Purina", add: "Add", remove: "Remove {b}", noBrands: "No brands yet.",
      brandHits: "{n} in 2 yrs",
      search: "Search brand, product, lot code or UPC",
      recall: "Recall", advisory: "FDA advisory", closed: "Closed", isNew: "New", yours: "Your brand",
      dog: "Dog", cat: "Cat", pet: "Pet food",
      hz_bacteria: "Bacteria", hz_virus: "Bird flu", hz_foreign: "Foreign objects", hz_nutrient: "Nutrient levels",
      hz_toxin: "Toxins", hz_other: "Other",
      lotsTitle: "Check your package", lotsMore: "+ {n} more lots listed on FDA.gov", lotHits: "{n} lots match “{q}”", lotHits1: "1 lot matches “{q}”",
      company: "Company", phone: "Consumer line", updated: "Updated", status: "Status",
      closedLong: "FDA has closed this recall", readMore: "Read the full notice on FDA.gov",
      empty: "Nothing matches.", emptyPet: "No recalls for {p} in the last 2 years.", noData: "No data yet — the feed hasn't run.",
      windowNote: "Showing the last {n} years of FDA notices.", items: "{n} notices", item: "1 notice",
      checked: "Checked {t}", stale: "Last checked {t} · updates may be delayed", loading: "Loading…",
      offline: "Couldn't reach the feed. Retrying…",
      cadence: "checks every {h} hours", cadence1: "checks hourly",
      freshCheck: "Bowl Check reads the FDA's lists every {h} hours. While this page is open it refreshes itself, so new notices show up without reloading.",
      freshCheck1: "Bowl Check reads the FDA's lists every hour. While this page is open it refreshes itself, so new notices show up without reloading.",
      newToast: "{n} new notices — tap to see", newToast1: "1 new notice — tap to see",
      issue: "Source issue since {t}", ok: "Latest {t}",
      todoTitle: "If your pet's food is on the list",
      todo1: "Stop feeding it. Match the lot code, UPC and best-by date on your bag or can against the notice.",
      todo2: "Return it for a refund, or throw it away in a sealed bag where pets and wildlife can't reach it. Don't donate it.",
      todo3: "Wash bowls, scoops and storage bins, and your hands. Salmonella and Listeria can make people sick too.",
      todo4: "Call your vet if your pet has vomiting, diarrhea, lethargy or loss of appetite, and say what they ate.",
      todo5: "Got sick from food that isn't on the list? Tell the FDA:", todo5Link: "report a pet food complaint",
      aboutTitle: "What's in Bowl Check?",
      about: "Recall announcements that the FDA posts for dog and cat food, treats, supplements and milk replacers, plus the FDA's own \"do not feed\" advisories, which sometimes cover food the maker hasn't recalled. Feed for horses, livestock, birds and reptiles, and animal drugs, are left out.",
      sourcesTitle: "Sources",
      fine: "Not every recall gets a public announcement; smaller ones may only appear in the FDA's weekly Enforcement Report. Always check the full notice on FDA.gov. Bowl Check isn't affiliated with the FDA.",
    },
    zh: {
      tagline: "猫粮狗粮召回信息，直接来自美国 FDA。", petsLabel: "你的宠物",
      dogs: "狗", cats: "猫", both: "都有",
      petDog: "狗", petCat: "猫", petBoth: "猫狗",
      clear: "近 30 天没有{p}食品召回", recent: "近 30 天有 {n} 起{p}食品召回",
      recent1: "近 30 天有 1 起{p}食品召回", lastOne: "最近一起：{b}，{d}",
      mineHit: "其中 {n} 起涉及你关注的品牌", mineHit1: "其中 1 起涉及你关注的品牌",
      mineTitle: "你家用的品牌", mineHint: "召回提到这些品牌时会特别标出。",
      addBrand: "添加品牌，例如 Purina", add: "添加", remove: "移除 {b}", noBrands: "还没有添加品牌。",
      brandHits: "两年内 {n} 起",
      search: "搜索品牌、产品、批号或 UPC 条码",
      recall: "召回", advisory: "FDA 警示", closed: "已结束", isNew: "新", yours: "你的品牌",
      dog: "狗", cat: "猫", pet: "宠物食品",
      hz_bacteria: "细菌", hz_virus: "禽流感", hz_foreign: "异物", hz_nutrient: "营养素含量",
      hz_toxin: "毒素", hz_other: "其他",
      lotsTitle: "核对你的包装", lotsMore: "FDA 网站还列出另外 {n} 个批次", lotHits: "{n} 个批次匹配“{q}”", lotHits1: "1 个批次匹配“{q}”",
      company: "公司", phone: "消费者热线", updated: "更新于", status: "状态",
      closedLong: "FDA 已结束此次召回", readMore: "在 FDA 网站查看完整公告",
      empty: "没有匹配的结果。", emptyPet: "近两年没有{p}食品召回。", noData: "暂无数据——数据源尚未运行。",
      windowNote: "显示近 {n} 年的 FDA 公告。", items: "{n} 条", item: "1 条",
      checked: "{t}检查", stale: "上次检查：{t} · 可能有延迟", loading: "加载中…",
      offline: "暂时无法连接数据源，正在重试…",
      cadence: "每 {h} 小时检查", cadence1: "每小时检查",
      freshCheck: "Bowl Check 每 {h} 小时读取一次 FDA 列表。页面打开期间会自动刷新，新公告无需重新加载即可出现。",
      freshCheck1: "Bowl Check 每小时读取一次 FDA 列表。页面打开期间会自动刷新，新公告无需重新加载即可出现。",
      newToast: "{n} 条新公告 — 点击查看", newToast1: "1 条新公告 — 点击查看",
      issue: "数据源异常，始于{t}", ok: "最新 {t}",
      todoTitle: "如果你家宠物的食品在名单上",
      todo1: "立即停止喂食。对照公告核对包装上的批号、UPC 条码和保质期。",
      todo2: "退回商家退款，或装进密封袋丢弃，放在宠物和野生动物碰不到的地方。不要捐赠。",
      todo3: "清洗食盆、量勺和储粮桶，并洗手。沙门氏菌和李斯特菌也会让人生病。",
      todo4: "如果宠物出现呕吐、腹泻、精神萎靡或食欲不振，请联系兽医并说明吃过什么。",
      todo5: "吃了名单以外的食品出现问题？告诉 FDA：", todo5Link: "提交宠物食品投诉",
      aboutTitle: "Bowl Check 收录什么？",
      about: "FDA 发布的猫狗主粮、零食、营养补充剂和代乳粉的召回公告，以及 FDA 自己发出的“请勿喂食”警示（有时涉及厂商并未召回的产品）。马、家畜、鸟类和爬行动物饲料以及兽药不在收录范围内。",
      sourcesTitle: "数据来源",
      fine: "并非所有召回都会发布公告，较小的召回可能只出现在 FDA 每周的执法报告中。请以 FDA 网站上的完整公告为准。Bowl Check 与 FDA 无关联。",
    },
  };
  const t = (k, vars) => (STR[lang][k] || STR.en[k] || k).replace(/\{(\w+)\}/g, (_, n) => (vars && n in vars ? vars[n] : ""));
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-label]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nLabel)); });

  const locale = lang === "zh" ? "zh-CN" : "en-US";
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
  const lastDay = (it) => it.upd || it.date;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // ---- state ----
  const $ = (id) => document.getElementById(id);
  const view = { pet: "both", q: "" };
  let meta = null;
  const bySource = {};
  const fresh = new Set();   // ids that arrived while this page was open
  let newSince = 0;          // notices first seen after this (ms) are "new for you"
  let saved = {};
  let brands = [];
  const open = new Set();    // cards the viewer expanded, kept across re-renders

  function allItems() {
    const out = [];
    for (const k of KEYS) if (bySource[k]) out.push(...bySource[k].items);
    return out.sort((a, b) => lastDay(b).localeCompare(lastDay(a)) || b.seen.localeCompare(a.seen));
  }
  const forPet = (it) => view.pet === "both" || it.sp.includes(view.pet) || it.sp.includes("pet");
  const isNew = (it) => fresh.has(it.id) || Date.parse(it.seen) > newSince;
  const recent = (it) => dayMs(lastDay(it)) >= Date.now() - RECENT_DAYS * DAY;

  const fold = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[’‘]/g, "'");
  const digits = (s) => String(s || "").replace(/\D+/g, "");
  function hay(it) {
    if (!it._hay) it._hay = fold([it.brand, it.title, it.product, it.co, it.why, it.sum].join(" "));
    return it._hay;
  }
  const brandOf = (it) => brands.find((b) => {
    const f = fold(b);
    return f && new RegExp(`(^|[^a-z0-9])${f.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}([^a-z0-9]|$)`).test(hay(it));
  });

  // Every search word has to appear in the notice or in one row of its lot table.
  // Long numbers (UPCs, lot codes) also match a cell with its spaces and dashes removed.
  function inCell(tk, cell) {
    const d = digits(tk);
    return fold(cell).includes(tk) || (d.length >= 6 && digits(cell).includes(d));
  }
  function matches(it, tokens) {
    if (!tokens.length) return { ok: true, rows: [], viaLots: false };
    const rows = [];
    (it.lots ? it.lots.r : []).forEach((row, i) => {
      const inRow = (tk) => row.some((c) => inCell(tk, c));
      if (tokens.some(inRow) && tokens.every((tk) => inRow(tk) || hay(it).includes(tk))) rows.push(i);
    });
    const inNotice = tokens.every((tk) => hay(it).includes(tk));
    return { ok: inNotice || rows.length > 0, rows, viaLots: !inNotice };
  }

  const petWord = () => t(view.pet === "dog" ? "petDog" : view.pet === "cat" ? "petCat" : "petBoth");

  // ---- render ----
  function renderPets() {
    document.querySelectorAll("[data-pet]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.pet === view.pet)));
  }

  function renderGlance() {
    const el = $("glance");
    if (!meta) { el.innerHTML = ""; return; }
    const list = allItems().filter(forPet);
    const rec = list.filter(recent);
    const mine = rec.filter(brandOf);
    const last = list[0];
    const lead = rec.length === 0 ? t("clear", { p: petWord() })
      : rec.length === 1 ? t("recent1", { p: petWord() }) : t("recent", { n: rec.length, p: petWord() });
    const lines = [];
    if (mine.length) lines.push(`<b class="mine-hit">${esc(mine.length === 1 ? t("mineHit1") : t("mineHit", { n: mine.length }))}</b>`);
    if (last) lines.push(esc(t("lastOne", { b: last.brand || shortTitle(last), d: fmtDate.format(dayMs(lastDay(last))) })));
    el.className = "glance " + (mine.length ? "alert" : rec.length ? "warn" : "ok");
    el.innerHTML = `<span class="dot" aria-hidden="true"></span><div><p class="lead">${esc(lead)}</p>` +
      lines.map((l) => `<p>${l}</p>`).join("") + `</div>`;
  }

  function renderBrands() {
    const items = allItems();
    $("brands").innerHTML = brands.length
      ? brands.map((b) => {
          const n = items.filter((it) => brandOf(it) === b).length;
          return `<span class="brand${n ? " hit" : ""}">${esc(b)}${n ? `<small>${esc(t("brandHits", { n }))}</small>` : ""}` +
            `<button type="button" data-remove="${esc(b)}" aria-label="${esc(t("remove", { b }))}">×</button></span>`;
        }).join("")
      : `<span class="none">${esc(t("noBrands"))}</span>`;
  }

  // Advisories have no brand field; their headline is the FDA title minus its prefix.
  const shortTitle = (it) => (it.title || "").replace(/^FDA (?:Advisory|Alert|Cautions)[^:]*:\s*/i, "");

  function cardHtml(it, hit, q) {
    const rows = hit.rows;
    const brand = brandOf(it);
    const hz = it.hz || "other";
    const tags = [
      `<span class="kind ${it.kind}">${esc(t(it.kind))}</span>`,
      it.done ? `<span class="tag done">${esc(t("closed"))}</span>` : "",
      isNew(it) ? `<span class="tag new">${esc(t("isNew"))}</span>` : "",
      brand ? `<span class="tag mine">${esc(t("yours"))}</span>` : "",
    ].join("");
    const sp = it.sp.map((s) => `<span class="sp">${s === "dog" ? "🐶" : s === "cat" ? "🐱" : "🐾"} ${esc(t(s))}</span>`).join("");
    const head = it.brand || shortTitle(it);
    const sub = it.brand ? it.title || it.product : "";
    let lots = "";
    if (it.lots && it.lots.r.length) {
      const hitSet = new Set(rows);
      lots = `<h4>${esc(t("lotsTitle"))}</h4>` +
        (rows.length && q ? `<p class="lot-hits">${esc(t(rows.length === 1 ? "lotHits1" : "lotHits", { n: rows.length, q }))}</p>` : "") +
        `<div class="lots" tabindex="0"><table><thead><tr>${it.lots.h.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>` +
        it.lots.r.map((r, i) => `<tr${hitSet.has(i) ? ' class="hit"' : ""}>${r.map((c, j) => `<td data-h="${esc(it.lots.h[j] || "")}">${esc(c)}</td>`).join("")}</tr>`).join("") +
        `</tbody></table></div>` +
        (it.lots.more ? `<p class="more-lots"><a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(t("lotsMore", { n: it.lots.more }))}</a></p>` : "");
    }
    const photos = (it.img || []).length
      ? `<div class="photos">${it.img.map((src) => `<img data-src="${esc(src)}" alt="" referrerpolicy="no-referrer" decoding="async">`).join("")}</div>` : "";
    const dl = [
      it.co && [t("company"), esc(it.co)],
      it.tel && [t("phone"), `<a href="tel:${esc(it.tel.replace(/[^\d+]/g, ""))}">${esc(it.tel)}</a>`],
      it.upd && [t("updated"), esc(fmtDate.format(dayMs(it.upd)))],
      it.done && [t("status"), esc(it.note || t("closedLong"))],
    ].filter(Boolean);
    // A lot code or UPC search opens the card on the matching rows.
    const isOpen = open.has(it.id) || (hit.viaLots && rows.length > 0);
    return `<details class="card hz-${hz}${brand ? " is-mine" : ""}${fresh.has(it.id) ? " fresh" : ""}" data-id="${esc(it.id)}"${isOpen ? " open" : ""}>` +
      `<summary><div class="top"><time datetime="${esc(it.date)}">${esc(fmtDate.format(dayMs(lastDay(it))))}</time>${tags}</div>` +
      `<h3>${esc(head)}</h3>${sub ? `<p class="title">${esc(sub)}</p>` : ""}` +
      `<div class="chips">${sp}<span class="hz"><i></i>${esc(t("hz_" + hz))}</span></div>` +
      (it.why ? `<p class="why">${esc(it.why)}</p>` : "") +
      `</summary><div class="more">` +
      (it.sum ? `<p class="sum">${esc(it.sum)}</p>` : "") +
      lots +
      (it.ill ? `<blockquote>${esc(it.ill)}</blockquote>` : "") +
      photos +
      (dl.length ? `<dl>${dl.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>` : "") +
      `<a class="src" href="${esc(it.url)}" target="_blank" rel="noopener">${esc(t("readMore"))} →</a>` +
      `</div></details>`;
  }

  function renderList() {
    const main = $("list");
    main.removeAttribute("aria-busy");
    if (!meta) { main.innerHTML = `<p class="empty">${esc(t("noData"))}</p>`; return; }
    const q = view.q.trim();
    const tokens = fold(q).split(/\s+/).filter(Boolean);
    const list = [];
    for (const it of allItems()) {
      if (!forPet(it)) continue;
      const m = matches(it, tokens);
      if (m.ok) list.push([it, m]);
    }
    if (!list.length) {
      main.innerHTML = `<p class="empty">${esc(tokens.length ? t("empty") : t("emptyPet", { p: petWord() }))}</p>`;
      return;
    }
    const counts = new Map();
    for (const [it] of list) {
      const m = lastDay(it).slice(0, 7);
      counts.set(m, (counts.get(m) || 0) + 1);
    }
    let html = "", month = null;
    for (const [it, hit] of list) {
      const m = lastDay(it).slice(0, 7);
      if (m !== month) {
        const n = counts.get(m);
        html += `<h2 class="month"><span>${esc(fmtMonth.format(dayMs(m + "-01")))}</span><span>${esc(n === 1 ? t("item") : t("items", { n }))}</span></h2>`;
        month = m;
      }
      html += cardHtml(it, hit, q);
    }
    const years = Math.round(((meta && meta.windowDays) || 730) / 365);
    html += `<p class="window">${esc(t("windowNote", { n: years }))}</p>`;
    main.innerHTML = html;
    main.querySelectorAll("details[open]").forEach(loadPhotos);
  }

  function loadPhotos(card) {
    card.querySelectorAll("img[data-src]").forEach((img) => {
      img.src = img.dataset.src;
      img.removeAttribute("data-src");
    });
  }

  function renderStatus() {
    const el = $("status");
    if (!meta) { el.textContent = t("loading"); return; }
    const h = meta.checkEveryHours || 1;
    // Missing two runs in a row (plus slack) means something's off.
    const stale = Date.now() - Date.parse(meta.checkedAt) > (2 * h + 1) * 3600 * 1000;
    el.textContent = stale ? t("stale", { t: ago(meta.checkedAt) })
      : t("checked", { t: ago(meta.checkedAt) }) + " · " + (h === 1 ? t("cadence1") : t("cadence", { h }));
    el.classList.toggle("stale", stale);
  }

  function renderSources() {
    const h = (meta && meta.checkEveryHours) || 1;
    $("freshCheck").textContent = h === 1 ? t("freshCheck1") : t("freshCheck", { h });
    if (!meta) return;
    $("sources").innerHTML = meta.sources.map((s) =>
      `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a>` +
      (s.ok
        ? `<span>${s.latest ? esc(t("ok", { t: fmtDate.format(dayMs(s.latest)) })) : ""}</span>`
        : `<span class="bad">${esc(t("issue", { t: ago(s.failingSince || meta.checkedAt) }))}</span>`) +
      `</li>`).join("");
  }

  function renderAll() { renderStatus(); renderPets(); renderGlance(); renderBrands(); renderList(); renderSources(); }

  // ---- loading & live updates ----
  async function loadSource(code) {
    const e = await ownerData(code);
    if (e && e.value) bySource[code] = e.value;
  }

  async function refresh(initial) {
    let e;
    try { e = await ownerData("meta"); } catch (err) {
      if (initial) $("status").textContent = t("offline");
      return;
    }
    const next = e && e.value;
    if (!next) { if (initial) renderAll(); return; }
    const prevHash = (code) => (meta && (meta.sources.find((o) => o.code === code) || {}).hash) || null;
    const changed = next.sources.filter((s) => prevHash(s.code) !== s.hash);
    if (!initial && !changed.length) { meta = next; renderStatus(); renderSources(); return; }
    const before = new Set(allItems().map((it) => it.id));
    const failed = new Set();
    await Promise.all(changed.map((s) => loadSource(s.code).catch(() => failed.add(s.code))));
    // A source we couldn't fetch keeps its old hash, so the next poll tries again.
    next.sources = next.sources.map((s) => (failed.has(s.code) ? Object.assign({}, s, { hash: prevHash(s.code) }) : s));
    meta = next;
    if (!initial) {
      const added = allItems().filter((it) => !before.has(it.id));
      added.forEach((it) => fresh.add(it.id));
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

  function persist() { prefs.save(Object.assign(saved, { pet: view.pet, brands })); }

  // ---- events ----
  document.querySelector(".pets").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-pet]");
    if (!b) return;
    view.pet = b.dataset.pet;
    renderPets(); renderGlance(); renderList(); persist();
  });
  $("addBrand").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const input = $("brandInput");
    const b = input.value.replace(/\s+/g, " ").trim();
    if (b && !brands.some((x) => fold(x) === fold(b)) && brands.length < MAX_BRANDS) {
      brands.push(b);
      persist(); renderBrands(); renderGlance(); renderList();
    }
    input.value = "";
  });
  $("brands").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-remove]");
    if (!b) return;
    brands = brands.filter((x) => x !== b.dataset.remove);
    persist(); renderBrands(); renderGlance(); renderList();
  });
  let qTimer = 0;
  $("q").addEventListener("input", (ev) => {
    clearTimeout(qTimer);
    qTimer = setTimeout(() => { view.q = ev.target.value; renderList(); }, 150);
  });
  // "toggle" doesn't bubble; catch it on the way down.
  $("list").addEventListener("toggle", (ev) => {
    const card = ev.target;
    if (!card.matches || !card.matches("details.card")) return;
    if (card.open) { open.add(card.dataset.id); loadPhotos(card); } else open.delete(card.dataset.id);
  }, true);
  $("list").addEventListener("error", (ev) => {
    if (ev.target.tagName === "IMG") ev.target.remove();
  }, true);
  $("toast").addEventListener("click", () => {
    $("toast").hidden = true;
    view.q = ""; $("q").value = "";
    renderList();
    window.scrollTo({ top: $("list").offsetTop - 80, behavior: "smooth" });
  });
  const bar = document.querySelector(".bar");
  new IntersectionObserver(([e]) => bar.classList.toggle("stuck", e.intersectionRatio < 1), { threshold: [1], rootMargin: "-1px 0px 0px 0px" }).observe(bar);

  setInterval(() => { if (!document.hidden) refresh(false); }, POLL_MS);
  setInterval(renderStatus, 30 * 1000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(false); });

  (async () => {
    saved = await prefs.load();
    // First visit: the last two weeks count as new so the badge means something.
    newSince = saved.lastVisit ? Date.parse(saved.lastVisit) : Date.now() - 14 * DAY;
    if (["dog", "cat", "both"].includes(saved.pet)) view.pet = saved.pet;
    if (Array.isArray(saved.brands)) brands = saved.brands.filter((b) => typeof b === "string").slice(0, MAX_BRANDS);
    renderStatus(); renderPets(); renderBrands();
    await refresh(true);
    saved.lastVisit = new Date().toISOString();
    persist();
  })();
})();
