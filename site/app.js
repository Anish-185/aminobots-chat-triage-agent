/* Triage Desk front end. Over ~150 lines because one no-build file renders the story, the demo
   desk, the drawer, the try-your-own form and the results, all from real site/data (ADR 0003). */
"use strict";

const API = document.querySelector('meta[name="triage-api"]')?.content || "";
const REDUCE = matchMedia("(prefers-reduced-motion: reduce)").matches;
const GRADE = {
  act: { stamp: "Act", file: "runs/actions.jsonl" },
  seek_approval: { stamp: "Ask approval", file: "runs/approvals.jsonl" },
  hand_off: { stamp: "Hand off", file: "runs/handoffs.jsonl" },
  refuse: { stamp: "Refuse", file: "runs/alerts.jsonl" },
};
const INTENT = {
  delivery_slot_change: "Delivery slot change", order_change: "Order change", status_query: "Status query",
  invoice_request: "Invoice request", payout_details_change: "Bank details change", refund_request: "Refund request",
  complaint: "Complaint", other: "Other request",
};
const FLAG_TEXT = {
  time_unspecified: "slot day or time not stated", outlet_ambiguous: "sender has several outlets; which one is unclear",
  referent_unresolved: "refers to a message that cannot be found", intent_unclear: "what is asked is unclear",
  possible_forward: "may be forwarded from someone else", injection_attempt: "the message tries to give the system orders",
};
const flagText = (flags) => flags.map((f) => `${FLAG_TEXT[f] ?? f} (${f})`).join("; ") || "none";
const STATE_TEXT = { CONFIRMED: "Confirmed", AMBIGUOUS: "Ambiguous", UNCONFIRMED: "Unconfirmed" };
const D = { manifest: [], runs: {}, policy: null, results: null, rules: [], byRequest: new Map(), demoChat: null };

/* ---------- tiny DOM helper: text is always set as text, never parsed as HTML ---------- */
function el(tag, props = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "style") n.setAttribute("style", v);
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (k in n && k !== "list") n[k] = v;
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) n.append(k instanceof Node ? k : String(k));
  return n;
}
const $ = (s, r = document) => r.querySelector(s);
const getJSON = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); });
const isTelugu = (t) => /[ఀ-౿]/.test(t || "");
const last4 = (p) => (p ? `•••• ${p.replace(/\D/g, "").slice(-4)}` : "unknown");
const hhmm = (ts) => (ts ? ts.slice(11, 16) : "");
const day = (ts) => (ts ? new Date(ts).toLocaleDateString("en-IN", { day: "numeric", month: "short" }) : "");
const pct = (x) => `${Math.round(x * 100)}%`;
const ruleById = (id) => D.rules.find((r) => r.id === id);
const isStaff = (m) => /aminobots/i.test(m.display_name || "");

function stamp(grade, rule, size = "") {
  return el("span", { class: `stamp ${size}`.trim(), "data-grade": grade },
    GRADE[grade]?.stamp ?? grade, rule ? el("small", {}, rule) : null);
}
function badge(state) {
  return el("span", { class: "badge", "data-state": state }, STATE_TEXT[state] ?? state);
}
function senderName(msg) {
  return msg.display_name || `Unknown number ${last4(msg.phone)}`;
}
function bubble(m, i, ev = new Set()) {
  if (m.kind === "system") {
    return el("div", { class: "bubble system", style: `--i:${i}` }, m.text.replace(/\+91[\d ]{10,}/g, (p) => last4(p)));
  }
  const text = m.kind === "media" ? "<Media omitted>" : m.text;
  return el("div", { class: `bubble${isStaff(m) ? " staff" : ""}${ev.has(m.id) ? " ev" : ""}`, style: `--i:${i}`, "data-mid": m.id },
    el("div", { class: "who" }, el("span", {}, senderName(m)), el("time", { datetime: m.ts }, hhmm(m.ts))),
    el("div", { lang: isTelugu(text) ? "te" : null }, text),
    el("div", { class: "mid" }, m.id));
}

/* ---------- data ---------- */
async function loadData() {
  const [manifest, policy, results] = await Promise.all([
    getJSON("data/manifest.json"), getJSON("data/policy.json"), getJSON("data/results.json"),
  ]);
  Object.assign(D, { manifest, policy, results, rules: [...policy.rules, policy.default] });
  const runs = await Promise.all(manifest.map((m) => getJSON(`data/${m.file}`)));
  manifest.forEach((m, i) => { D.runs[m.id] = runs[i]; });
}

/* ---------- hero ---------- */
function renderHero() {
  const run = D.runs.d07;
  const host = $("[data-hero-chat]");
  if (!run || !host) return;
  const req = run.requests[0];
  const msgs = run.messages.filter((m) => m.kind !== "system").slice(0, 8);
  msgs.forEach((m, i) => {
    const b = bubble(m, i);
    if (m.id === req.candidate.primary_msg_id) {
      b.append(el("span", { class: "bubble-stamp", style: `--n:${msgs.length}`, "aria-hidden": "true" }, stamp(req.grade, req.rule_id)));
    }
    host.append(b);
  });
  host.append(el("p", { class: "vh" }, `Result: ${GRADE[req.grade].stamp}, rule ${req.rule_id}. ${req.identity.reason}.`));
}

/* ---------- story ---------- */
const STEP_TITLES = ["The chat arrives", "Noise dims", "The model describes", "Code checks the sender", "Ten rules, most cautious wins", "Logged, not executed"];

function buildScene(host) {
  const run = D.runs[host.dataset.scene];
  if (!run) return;
  const reqs = run.requests;
  const focus = reqs.find((r) => r.candidate.refers_to_msg_id) || reqs.find((r) => r.grade === "refuse") || reqs[0];
  const fc = focus.candidate;
  const evAll = new Set(reqs.flatMap((r) => r.candidate.evidence_msg_ids));
  const idx = (id) => run.messages.findIndex((m) => m.id === id);
  // window: the focus request's evidence and referent, one message either side
  const evIdx = [...fc.evidence_msg_ids, fc.refers_to_msg_id].filter(Boolean).map(idx).filter((i) => i >= 0);
  const lo = Math.max(0, Math.min(...evIdx) - 1), hi = Math.min(run.messages.length, Math.max(...evIdx) + 2);
  const window = run.messages.slice(lo, hi);
  const textMsgs = run.messages.filter((m) => m.kind !== "system").length;
  const matched = focus.matched_rules;
  const file = GRADE[focus.grade].file;
  const log = run.log.find((l) => l.request_id === focus.request_id);
  const notes = [
    `${run.messages.length} messages, ${hhmm(run.messages[0].ts)} to ${hhmm(run.now)}. ${textMsgs - evAll.size} of them are greetings, banter or noise.`,
    `${evAll.size} messages carry the ${reqs.length} real request${reqs.length > 1 ? "s" : ""}. The rest fade.`,
    `It names each request, the messages that show it${fc.refers_to_msg_id ? ", and what a follow-up refers to" : ""}. It decides nothing.`,
    "The phone number is looked up in the roster. What people claim in the chat never counts.",
    `Every rule is checked. ${matched.length} match; ${focus.rule_id} is the most cautious, so it decides.`,
    `The action is written to ${file}, marked simulated. Nothing is sent.`,
  ];

  const steps = el("ol", { class: "steps" }, STEP_TITLES.map((t, i) => el("li", {}, el("h4", {}, t), el("p", {}, notes[i]))));
  const chat = el("div", { class: "scene-chat", role: "list", "aria-label": `Messages ${window[0].id} to ${window.at(-1).id} of dev chat ${host.dataset.scene}` },
    lo > 0 ? el("p", { class: "more-pill" }, `${lo} earlier messages`) : null,
    window.map((m, i) => { const b = bubble(m, i, evAll); b.setAttribute("role", "listitem"); return b; }),
    hi < run.messages.length ? el("p", { class: "more-pill" }, `${run.messages.length - hi} later messages`) : null);

  const stampDelay = `${D.rules.length * 130 + 300}ms`;
  const dockets = el("div", { class: "dockets" }, reqs.slice(0, 3).map((r, n) => el("article", {
    class: `docket${r === focus ? " focus" : ""}`, style: `--stamp-delay:${stampDelay}`, "aria-label": `Request ${n + 1}: ${r.candidate.gloss}`,
  },
  el("span", { class: "no" }, `Docket ${n + 1} of ${reqs.length}${r.candidate.refers_to_msg_id ? `, follows up ${r.candidate.refers_to_msg_id}` : ""}`),
  el("h4", {}, INTENT[r.candidate.intent]),
  el("p", {}, r.candidate.gloss),
  el("div", { class: "ids" }, r.candidate.evidence_msg_ids.map((id) => el("span", { class: "chip" }, id)),
    r.candidate.status !== "open" ? el("span", { class: "tag" }, r.candidate.status) : null,
    r.candidate.flags.map((f) => el("span", { class: "tag", title: f }, FLAG_TEXT[f] ?? f))),
  r === focus ? el("span", { class: "docket-stamp" }, stamp(r.grade, r.rule_id, "lg")) : null)));

  const id = focus.identity;
  const primary = run.messages[idx(fc.primary_msg_id)];
  const whoCard = el("div", { class: "who-card" }, el("div", { class: "who-inner" },
    el("div", { class: "who-face front", "aria-hidden": "true" },
      el("h4", {}, "Who sent this?"), el("p", { class: "big-q" }, "?"),
      el("p", { class: "reason" }, `Display name “${primary.display_name || "none"}”, phone ${last4(primary.phone)}`)),
    el("div", { class: "who-face back" },
      el("h4", {}, "Roster lookup ", badge(id.state)),
      el("dl", {},
        el("dt", {}, "Phone"), el("dd", {}, last4(focus.requester_phone)),
        el("dt", {}, "Role"), el("dd", {}, id.role || "not in roster"),
        el("dt", {}, "Outlets"), el("dd", {}, id.outlets.join(", ") || "none"),
        el("dt", {}, "Authorised"), el("dd", {}, id.authorised ? "yes" : "no")),
      el("p", { class: "reason" }, id.reason))));

  const rules = el("ol", { class: "rules", "aria-label": "All rules checked" }, D.rules.map((r, i) => el("li", {
    class: `${matched.includes(r.id) ? "matched" : ""}${r.id === focus.rule_id ? " decider" : ""}`,
    "data-grade": r.grade, style: `--i:${i}`,
  }, el("b", {}, r.id), el("span", {}, r.text), el("span", { class: "mark" }, matched.includes(r.id) ? (r.id === focus.rule_id ? "decides" : "matches") : "no"))));

  const logText = log ? JSON.stringify({ request_id: log.request_id, grade: log.grade, rule_id: log.rule_id, evidence_msg_ids: log.evidence_msg_ids, requester: log.requester, action: log.action, simulated: log.simulated }) : "";
  const code = el("code", { "data-full": logText }, logText);
  const logline = el("pre", { class: "logline", "aria-label": `Simulated log line appended to ${file}` }, el("span", { class: "sim" }, "simulated"), `→ ${file}\n`, code);
  const alert = focus.grade === "refuse" ? el("div", { class: "alert", role: "note" },
    el("h4", {}, "Security alert raised (simulated)"),
    el("p", {}, `${INTENT[fc.intent]} asked by ${id.state === "UNCONFIRMED" ? "a number not in the roster" : senderName(primary)}. Nobody acts on it; the security team is told. ${focus.identity.reason}.`)) : null;

  let thread = null;
  if (fc.refers_to_msg_id) {
    thread = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    thread.setAttribute("class", "thread");
    thread.setAttribute("aria-hidden", "true");
  }
  const pin = el("div", { class: "scene-pin" },
    el("h3", { class: "scene-title" }, host.dataset.title),
    steps, chat,
    el("div", { class: "scene-desk" }, dockets, el("div", { class: "desk-row" }, whoCard, rules), logline, alert));
  if (thread) pin.append(thread);
  host.className = "scene";
  host.append(pin);

  const scene = { host, pin, steps, code, logText, thread, from: fc.primary_msg_id, to: fc.refers_to_msg_id, stage: 0, typed: false };
  return scene;
}

function drawThread(s) {
  if (!s.thread) return;
  const a = $(`[data-mid="${s.from}"]`, s.pin), b = $(`[data-mid="${s.to}"]`, s.pin);
  if (!a || !b) return;
  const box = s.pin.getBoundingClientRect(), ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
  const x1 = ra.right - box.left + 4, y1 = ra.top - box.top + ra.height / 2;
  const x2 = rb.right - box.left + 4, y2 = rb.top - box.top + rb.height / 2;
  const bend = Math.max(x1, x2) + 34;
  const ns = "http://www.w3.org/2000/svg";
  s.thread.replaceChildren();
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", `M${x1},${y1} C${bend},${y1} ${bend},${y2} ${x2 + 6},${y2}`);
  const label = document.createElementNS(ns, "text");
  const ly = (y1 + y2) / 2, lx = bend - 4;
  label.setAttribute("x", lx); label.setAttribute("y", ly);
  label.setAttribute("text-anchor", "middle");
  label.setAttribute("transform", `rotate(-90 ${lx} ${ly})`);
  label.textContent = `refers to ${s.to}`;
  s.thread.append(path, label);
  s.thread.style.setProperty("--len", Math.ceil(path.getTotalLength()));
}

function setStage(s, n) {
  if (s.stage === n) return;
  s.stage = n;
  for (let i = 1; i <= 6; i++) s.pin.classList.toggle(`at-${i}`, n >= i);
  [...s.steps.children].forEach((li, i) => {
    li.toggleAttribute("aria-current", false);
    if (i + 1 === n) li.setAttribute("aria-current", "step");
    li.classList.toggle("done", i + 1 < n);
  });
  if (n >= 3) drawThread(s);
  if (n >= 6 && !s.typed) typeLog(s);
}

function typeLog(s) {
  s.typed = true;
  if (REDUCE || !s.logText) return;
  let i = 0;
  s.code.textContent = "";
  const t = setInterval(() => {
    i += 3;
    s.code.textContent = s.logText.slice(0, i);
    if (i >= s.logText.length) clearInterval(t);
  }, 16);
}

function initStory() {
  const scenes = [...document.querySelectorAll("[data-scene]")].map(buildScene).filter(Boolean);
  const pinned = window.gsap && window.ScrollTrigger && !REDUCE && matchMedia("(min-width: 861px)").matches;
  if (!pinned) {
    document.documentElement.classList.add("static");
    scenes.forEach((s) => setStage(s, 6));
    return;
  }
  gsap.registerPlugin(ScrollTrigger);
  scenes.forEach((s) => {
    setStage(s, 1);
    ScrollTrigger.create({
      trigger: s.pin, start: "top top", end: () => `+=${window.innerHeight * 4}`, pin: true, pinSpacing: true,
      onUpdate: (self) => setStage(s, 1 + Math.min(5, Math.floor(self.progress * 6))),
    });
  });
  addEventListener("resize", () => scenes.forEach((s) => s.stage >= 3 && drawThread(s)));
}

/* ---------- requests table + drawer (demo desk and try-your-own) ---------- */
function renderRun(run, host) {
  host.replaceChildren();
  if (run.status === "UNPROCESSED") {
    host.append(el("div", { class: "unprocessed", role: "status" },
      el("h3", {}, "Unprocessed: the whole chat goes to a person"),
      el("p", {}, "The run failed before any request could be graded, so nothing is decided automatically. This is not “no requests”."),
      el("p", {}, el("strong", {}, "Reason: "), run.error || "unknown"),
      run.log?.[0] ? el("pre", { class: "json" }, JSON.stringify(run.log[0], null, 1)) : null));
    return;
  }
  const llm = run.llm || {};
  host.append(el("p", { class: "run-meta" },
    `${run.messages.length} messages, last at ${hhmm(run.now)} on ${day(run.now)}. ${run.requests.length} request${run.requests.length === 1 ? "" : "s"}`,
    run.internal_requests.length ? `, ${run.internal_requests.length} internal (logged, not listed)` : "",
    run.rejected.length ? `, ${run.rejected.length} dropped for unknown message IDs` : "",
    `. Model ${run.model}${llm.cached ? " (cached answer, 0 requests)" : llm.latency_s ? ` in ${Math.round(llm.latency_s)} s` : ""}; policy v${run.policy_version}.`));
  if (!run.requests.length) {
    host.append(el("p", { class: "empty" }, "The model found no requests in this chat. Every message was read; the run itself succeeded."));
    return;
  }
  const rows = run.requests.map((r) => {
    D.byRequest.set(r.request_id, { r, run });
    const rule = ruleById(r.rule_id);
    const open = () => openDrawer(r.request_id);
    return el("tr", { "data-rules": r.matched_rules.join(" "), "data-request": r.request_id, onclick: (e) => { if (!e.target.closest("button, .rule-id")) open(); } },
      el("td", { class: "gloss" }, el("button", { class: "open-btn", type: "button", onclick: open, "aria-haspopup": "dialog" }, r.candidate.gloss),
        el("small", {}, `${INTENT[r.candidate.intent]}${r.candidate.status !== "open" ? `, ${r.candidate.status}` : ""}`)),
      el("td", {}, el("div", {}, r.requester_name || `Unknown ${last4(r.requester_phone)}`), badge(r.identity.state)),
      el("td", {}, stamp(r.grade, null, "sm")),
      el("td", {}, el("span", { class: "rule-id", tabindex: "0", "aria-describedby": `tip-${r.request_id}` }, r.rule_id,
        el("span", { class: "tip", role: "tooltip", id: `tip-${r.request_id}` }, rule?.text || ""))),
      el("td", {}, r.candidate.evidence_msg_ids.join(" ")),
      el("td", {}, r.grade === "seek_approval" ? decideButtons(r) : null));
  });
  host.append(el("div", { class: "table-scroll" }, el("table", { class: "req-table" },
    el("caption", { class: "vh" }, "Requests found in this chat"),
    el("thead", {}, el("tr", {}, ["Request", "Sender", "Stamp", "Rule", "Evidence", "Decision"].map((h) => el("th", { scope: "col" }, h)))),
    el("tbody", {}, rows))));
}

/* approve / reject: client-side only, sessionStorage */
const DKEY = "triage-desk-decisions";
function readDecisions() { try { return JSON.parse(sessionStorage.getItem(DKEY)) || []; } catch { return []; } }
function writeDecisions(list) { try { sessionStorage.setItem(DKEY, JSON.stringify(list)); } catch {} }
function decideButtons(r) {
  const prior = readDecisions().find((d) => d.request_id === r.request_id);
  const box = el("div", { class: "decide" });
  const show = (decision) => box.replaceChildren(
    el("span", { class: "stamp sm", "data-grade": decision === "approved" ? "act" : "refuse" }, decision),
    el("span", { class: "sim-note" }, "simulated"));
  if (prior) { show(prior.decision); return box; }
  const act = (decision) => (e) => {
    e.stopPropagation();
    writeDecisions([...readDecisions(), { request_id: r.request_id, gloss: r.candidate.gloss, decision, at: new Date().toISOString(), simulated: true }]);
    show(decision);
    renderDecisions();
  };
  box.append(el("button", { type: "button", onclick: act("approved") }, "Approve"),
    el("button", { type: "button", onclick: act("rejected") }, "Reject"));
  return box;
}
function renderDecisions() {
  const host = $("[data-decisions]");
  const list = readDecisions();
  host.replaceChildren(...(list.length ? list.map((d) => el("li", {}, `${d.decision === "approved" ? "Approved" : "Rejected"}: ${d.gloss} (simulated, ${new Date(d.at).toLocaleTimeString()})`))
    : [el("li", {}, "None yet. Requests stamped “Ask approval” have Approve and Reject buttons.")]));
}

function openDrawer(requestId) {
  const { r, run } = D.byRequest.get(requestId);
  const c = r.candidate;
  const ev = new Set(c.evidence_msg_ids);
  const dlg = $("[data-drawer]");
  $("#drawer-title").replaceChildren(c.gloss, " ", stamp(r.grade, r.rule_id, "sm"));
  const ents = Object.entries(c.entities).filter(([, v]) => v != null);
  const kv = (pairs) => el("dl", { class: "kv" }, pairs.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
  const log = run.log.find((l) => l.request_id === r.request_id);
  const chat = el("div", { class: "mini-chat" }, run.messages.map((m, i) => bubble(m, i, ev)));
  $("[data-drawer-body]").replaceChildren(el("ol", { class: "dsteps" },
    el("li", {}, el("h3", {}, "The chat, evidence highlighted"), chat),
    el("li", {}, el("h3", {}, "What the model described"), kv([
      ["Intent", INTENT[c.intent]], ["Gloss", c.gloss], ["Primary message", c.primary_msg_id], ["Evidence", c.evidence_msg_ids.join(", ")],
      ["Refers to", c.refers_to_msg_id || "nothing earlier"], ["Status", c.status], ["Uncertainty flags", flagText(c.flags)],
      ...ents.map(([k, v]) => [k.replace(/_/g, " "), String(v)]),
    ])),
    el("li", {}, el("h3", {}, "Who sent it (code)"), kv([
      ["State", badge(r.identity.state)], ["Phone", last4(r.requester_phone)], ["Role", r.identity.role || "not in roster"],
      ["Outlets", r.identity.outlets.join(", ") || "none"], ["Authorised", r.identity.authorised ? "yes" : "no"],
      ["On behalf", r.identity.on_behalf ? (r.identity.on_behalf_verified ? "yes, verified" : "yes, not verified") : "no"],
      ["Reason", r.identity.reason],
    ])),
    el("li", {}, el("h3", {}, "Every rule checked (code)"), el("ul", { class: "check-list" }, D.rules.map((rule) => {
      const m = r.matched_rules.includes(rule.id);
      return el("li", { class: `${m ? "matched" : ""}${rule.id === r.rule_id ? " decider" : ""}`, "data-grade": rule.grade },
        el("b", {}, rule.id), el("span", {}, rule.text), el("span", {}, rule.id === r.rule_id ? "decides" : m ? "matches" : "no"));
    })), el("p", { class: "hint" }, "The most cautious matching grade wins; the lowest-numbered rule with that grade is cited.")),
    el("li", {}, el("h3", {}, "Routed and logged (simulated)"), el("p", {}, `Appended to ${GRADE[r.grade].file}. Nothing is executed.`),
      log ? el("pre", { class: "json" }, JSON.stringify(log, null, 1)) : null),
    el("li", {}, el("h3", {}, "Trace"), el("p", {}, "No trace recorded for this run: Langfuse is off in the demo (its keys are empty, and the website process never traces)."))));
  dlg.showModal();
  requestAnimationFrame(() => $(".mini-chat .ev", dlg)?.scrollIntoView({ block: "center" }));
}

/* ---------- demo desk ---------- */
function initDemo() {
  const tabs = $("[data-chat-tabs]");
  const panel = $("[data-demo-run]");
  panel.id = "demo-panel";
  const select = (id, focus) => {
    D.demoChat = id;
    [...tabs.children].forEach((b) => { const on = b.dataset.chat === id; b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; if (on && focus) b.focus(); });
    panel.setAttribute("aria-labelledby", `tab-${id}`);
    renderRun(D.runs[id], panel);
  };
  D.manifest.forEach((m) => tabs.append(el("button", {
    type: "button", role: "tab", id: `tab-${m.id}`, "aria-controls": "demo-panel", "data-chat": m.id, onclick: () => select(m.id),
  }, el("span", {}, m.id), m.title)));
  tabs.addEventListener("keydown", (e) => {
    const ids = D.manifest.map((m) => m.id);
    const i = ids.indexOf(D.demoChat);
    const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: ids.length - 1 }[e.key];
    if (next == null) return;
    e.preventDefault();
    select(ids[(next + ids.length) % ids.length], true);
  });
  select(D.manifest[0].id);
  renderDecisions();
  const dlg = $("[data-drawer]");
  $("[data-close]", dlg).addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
}

/* ---------- how it works: rules table ---------- */
function initRules() {
  $("[data-policy-version]").textContent = D.policy.version;
  const note = $("[data-rule-note]");
  const tbody = $("[data-rules-table] tbody");
  const light = (id, on) => {
    document.querySelectorAll("[data-demo-run] tr[data-rules]").forEach((tr) => tr.classList.toggle("rule-hit", on && tr.dataset.rules.split(" ").includes(id)));
    if (!on) { note.textContent = ""; return; }
    const run = D.runs[D.demoChat];
    const n = run.requests.filter((r) => r.matched_rules.includes(id)).length;
    const decides = run.requests.filter((r) => r.rule_id === id).length;
    note.textContent = `${id} matched ${n} of ${run.requests.length} requests in ${D.demoChat} and decided ${decides}.`;
  };
  D.rules.forEach((r) => {
    const tr = el("tr", { tabindex: "0", onmouseenter: () => light(r.id, true), onmouseleave: () => light(r.id, false), onfocus: () => light(r.id, true), onblur: () => light(r.id, false) },
      el("td", {}, r.id), el("td", {}, r.text, r.id === D.policy.default.id ? " (default)" : ""), el("td", {}, stamp(r.grade, null, "sm")));
    tbody.append(tr);
  });
}

/* ---------- try your own ---------- */
const CLERK = [
  [0, "Reading the chat line by line…"],
  [4, "The free model is describing the requests. This usually takes 1–4 minutes."],
  [60, "Still reading. Free models queue at busy hours; nothing is lost while we wait."],
  [150, "Checking senders and rules is instant once the model answers."],
  [240, "Close to the 5-minute limit. If it runs out, the whole chat goes to a person, never to “no requests”."],
];
function initTry() {
  const form = $("[data-try-form]"), status = $("[data-try-status]"), out = $("[data-try-run]"), err = $("[data-form-error]");
  const text = $("#chat-text"), key = $("#api-key");
  $("#chat-file").addEventListener("change", async (e) => {
    const f = e.target.files[0];
    if (f) text.value = await f.text();
  });
  $("[data-load-sample]").addEventListener("click", async () => {
    text.value = await fetch("data/sample.txt").then((r) => r.text());
    text.focus();
  });
  const down = () => status.replaceChildren(el("div", { class: "down", role: "alert" },
    el("p", {}, el("strong", {}, "The local API is not running. "), "Start it from the project folder, then try again:"),
    el("code", {}, "uv run python -m triage.serve")));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.textContent = "";
    if (!text.value.trim()) { err.textContent = "Paste a chat export or upload a .txt file first."; text.focus(); return; }
    try { if (!(await fetch(`${API}/api/health`)).ok) throw new Error(); } catch { down(); return; }
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    out.replaceChildren();
    const start = Date.now();
    const line = el("p", {}), secs = el("span", { class: "elapsed", "aria-hidden": "true" }, "0s");
    status.replaceChildren(el("div", { class: "clerk" }, el("span", { class: "pad", "aria-hidden": "true" }), secs, line));
    const tick = () => {
      const s = Math.floor((Date.now() - start) / 1000);
      secs.textContent = `${s}s`;
      const msg = CLERK.filter(([t]) => s >= t).at(-1)[1];
      if (line.textContent !== msg) line.textContent = msg;
    };
    tick();
    const timer = setInterval(tick, 1000);
    const body = { chat: text.value };
    if (key.value.trim()) body.key = key.value.trim();
    key.value = ""; // used once: the field is cleared as soon as the request is built
    try {
      const res = await fetch(`${API}/api/triage`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        status.replaceChildren(el("div", { class: "down", role: "alert" }, el("p", {}, el("strong", {}, `The API answered ${res.status}. `),
          typeof data.detail === "string" ? data.detail : "The chat could not be sent; check its format and size.")));
      } else {
        status.replaceChildren(el("p", {}, `Done in ${Math.round((Date.now() - start) / 1000)} s.`));
        renderRun(data, out);
      }
    } catch { down(); }
    finally { clearInterval(timer); btn.disabled = false; }
  });
}

/* ---------- results ---------- */
function initResults() {
  const R = D.results, M = R.metrics;
  $("[data-results-sub]").textContent = `Dev split, ${R.n_chats} chats, ${M.n_gold} gold requests. Model ${R.model}, prompt ${R.prompt}, policy ${R.policy}, eval tag ${R.tag}.`;
  const counters = [
    [M.f1, "Detection F1", `precision ${pct(M.precision)}, recall ${pct(M.recall)}`, 2],
    [M.grade_accuracy, "Grade accuracy", "stamp matches the hand label", 2],
    [M.approval_load * 100, "Approval load", "% of “act” requests sent for approval", 0, "%"],
    [M.over_autonomy_high_risk, "High-risk over-autonomy", "requests stamped less cautious than gold", 0],
    [M.notional_cost_usd, "Notional cost", "USD at paid-model prices; billed $0", 2, "", "$"],
  ];
  const host = $("[data-counters]");
  counters.forEach(([v, lbl, sub, dp, suf = "", pre = ""]) => {
    const num = el("span", { class: "num", "data-to": v, "data-dp": dp, "data-pre": pre, "data-suf": suf }, `${pre}${v.toFixed(dp)}${suf}`);
    host.append(el("div", { class: "counter" }, num, el("span", { class: "lbl" }, lbl), el("span", { class: "sub" }, sub)));
  });
  const gates = {
    high_risk_over_autonomy_is_0: "No high-risk request stamped less cautious than gold",
    unconfirmed_sender_recall_is_1: "Every unconfirmed sender caught",
    evidence_validity_is_100: "Every cited message ID exists in the chat",
    mandated_scenarios_pass_exactly: "Both mandated scenarios pass exactly",
  };
  $("[data-gates]").append(...Object.entries(gates).map(([k, t]) => {
    const v = R.hard_gates[k];
    const ran = typeof v === "boolean";
    return el("li", {}, el("span", {}, t, ran ? "" : el("small", { class: "hint" }, el("br"), "Not run: no challenge chats yet.")),
      el("span", { class: "stamp sm", "data-grade": !ran ? "hand_off" : v ? "act" : "refuse" }, !ran ? "Not run" : v ? "Pass" : "Fail"));
  }));
  const cm = M.confusion_matrix, labels = cm.labels, rows = cm.rows_gold_cols_pred;
  const max = Math.max(...rows.flat());
  const grid = el("div", { class: "confusion", role: "table", "aria-label": "Rows: gold grade. Columns: predicted grade." },
    el("div", { role: "row", style: "display:contents" }, el("span", { class: "h", role: "columnheader" }, "gold ↓ / predicted →"), labels.map((l) => el("span", { class: "h", role: "columnheader" }, GRADE[l].stamp))),
    rows.map((row, i) => el("div", { role: "row", style: "display:contents" }, el("span", { class: "h rh", role: "rowheader" }, GRADE[labels[i]].stamp),
      row.map((n, j) => el("span", { role: "cell", class: `cell ${i === j ? "diag" : j < i ? "over" : "under"}`, style: `--a:${n ? 0.15 + 0.4 * (n / max) : 0}` }, n)))));
  $("[data-confusion]").append(grid, el("p", { class: "legend" },
    el("span", {}, el("i", { style: "background:var(--act)" }), "correct"),
    el("span", {}, el("i", { style: "background:var(--ask)" }), "more cautious than gold"),
    el("span", {}, el("i", { style: "background:var(--refuse)" }), "less cautious than gold")));
  const limit = 300;
  $("[data-latency]").append(el("div", { class: "bars" },
    [["p50", M.latency_p50_s], ["p95", M.latency_p95_s]].map(([k, v]) => el("div", { class: "bar" }, el("span", {}, k),
      el("span", { class: "track" }, el("span", { class: "fill", style: `--w:${Math.min(100, (v / limit) * 100)}%` }), el("span", { class: "limit", title: "300 s timeout" })),
      el("span", {}, `${Math.round(v)} s`)))),
  el("p", { class: "hint" }, "Seconds per chat on the free model (one request per chat). Dashed line: the 300 s timeout."));
  const tb = $("[data-targets] tbody");
  Object.entries(R.targets).forEach(([k, t]) => tb.append(el("tr", {}, el("td", {}, k.replace(/_/g, " ")), el("td", {}, t.value.toFixed(2)),
    el("td", {}, `≥ ${t.target} `, el("span", { class: "stamp sm", "data-grade": t.met ? "act" : "refuse" }, t.met ? "Met" : "Missed")))));

  const section = $("#results");
  const run = () => {
    section.classList.add("in");
    if (REDUCE) return;
    section.querySelectorAll(".num").forEach((n) => {
      const to = +n.dataset.to, dp = +n.dataset.dp, t0 = performance.now();
      const step = (t) => {
        const k = Math.min(1, (t - t0) / 1200), e = 1 - (1 - k) ** 3;
        n.textContent = `${n.dataset.pre}${(to * e).toFixed(dp)}${n.dataset.suf}`;
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  };
  new IntersectionObserver((es, io) => { if (es.some((e) => e.isIntersecting)) { run(); io.disconnect(); } }, { threshold: 0.2 }).observe(section);
}

/* ---------- chrome: theme, smooth scroll, magnetic buttons ---------- */
function initChrome() {
  const btn = $("[data-theme-toggle]");
  const current = () => document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const label = () => btn.setAttribute("aria-label", `Switch to ${current() === "dark" ? "light" : "dark"} theme`);
  label();
  btn.addEventListener("click", () => {
    const next = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("triage-theme", next); } catch {}
    label();
  });
  if (REDUCE) return;
  if (window.Lenis && window.gsap && window.ScrollTrigger) {
    const lenis = new Lenis({ duration: 1.1 });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
    document.querySelectorAll('a[href^="#"]').forEach((a) => a.addEventListener("click", (e) => {
      const target = $(a.getAttribute("href"));
      if (!target) return;
      e.preventDefault();
      lenis.scrollTo(target, { offset: -64 });
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    }));
  }
  if (matchMedia("(hover: hover)").matches) {
    document.querySelectorAll(".magnetic").forEach((b) => {
      b.addEventListener("pointermove", (e) => {
        const r = b.getBoundingClientRect();
        b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.18}px, ${(e.clientY - r.top - r.height / 2) * 0.25}px)`;
      });
      b.addEventListener("pointerleave", () => { b.style.transform = ""; });
    });
  }
}

async function main() {
  initChrome();
  try {
    await loadData();
  } catch (e) {
    $("#main").prepend(el("p", { class: "down", role: "alert" }, `Could not load site/data: ${e.message}. Serve the site with uv run python -m triage.serve.`));
    return;
  }
  renderHero();
  initRules();
  initDemo();
  initTry();
  initResults();
  initStory();
  if (window.ScrollTrigger) addEventListener("load", () => ScrollTrigger.refresh());
}
document.addEventListener("DOMContentLoaded", main);
