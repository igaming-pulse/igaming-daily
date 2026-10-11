/**
 * iGaming 日報 Telegram 機器人（Cloudflare Workers 版，2026-10-11）
 *
 * 取代本機常駐的 scripts/telegram_bot.py：Telegram 收到訊息就主動通知這支程式（webhook），
 * 它從 GitHub 讀最新資料回覆。24 小時都在，不需要公司 Mac 開著。
 *
 * 資料來源（repo 是公開的，直接讀 raw 檔；每晚日報推上 GitHub 後就是最新）：
 *   state/inventory.json、state/<DATE>-report.json、state/<DATE>-special-report.json、
 *   state/health/<DATE>.json、state/health/credits.json、GitHub commits（判斷每天有沒有跑成功）
 *
 * 需要在 Cloudflare 後台設定的變數（Settings → Variables and Secrets）：
 *   BOT_TOKEN        Secret｜Telegram bot token（@BotFather 給的那串）
 *   WEBHOOK_SECRET   Secret｜自己產生的一串亂碼，用來確認訊息真的來自 Telegram，也當 /setup 的鑰匙
 *   ALLOWED_CHAT_ID  Text  ｜606981537（只回應這個人，其他人一律不回）
 *
 * 網址：
 *   POST /telegram                          Telegram 送訊息進來（webhook）
 *   GET  /setup?key=<WEBHOOK_SECRET>        向 Telegram 註冊 webhook＋「/」指令選單（只需開一次）
 *   GET  /unset?key=<WEBHOOK_SECRET>        取消 webhook（要改回本機機器人時用）
 *   GET  /test?key=<WEBHOOK_SECRET>&q=庫存   不經 Telegram，直接看某個指令會回什麼
 */

const REPO = "igaming-pulse/igaming-daily";
const BRANCH = "test-publish";
const RAW = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/`;
const SITE = "https://igaming-pulse.github.io/igaming-daily";
const WEEK = "一二三四五六日";
const CATS = { cat2: "🕹️ 非 Slot", cat3: "🤝 主流動態", cat4: "🇵🇭 菲律賓", cat5: "📊 市場數據" };
const NAMES = { cat1: "🎰 Slot", cat2: "🕹️ 非 Slot", cat3: "🤝 主流", cat4: "🇵🇭 菲律賓", cat5: "📊 市場數據" };
// 規則常數：與 scripts/inventory.py 相同
const SLOT_FRESH = 7, SLOT_AFTER_RELEASE = 3, OTHER_FRESH = 3, DEDUP = 3, PREVIEW_MAX = 7, WARN = 2;

const COMMANDS = [
  ["today", "今天的日報：各區標題與連結"], ["stock", "庫存：各分類數量與標題"],
  ["slot", "Slot 庫存明細（含待上線）"], ["special", "特別版：最近一期與下次檢查"],
  ["week", "本週每天收錄概況"], ["status", "系統狀態：最近執行、額度、警報"], ["help", "指令說明"],
];
const HELP = [
  "🤖 13' v 日報機器人（雲端版，24 小時都在；有沒有斜線都可以）",
  "・今天 或 /today — 今天的日報：各區標題與連結",
  "・庫存 或 /stock — 各分類庫存數量與標題",
  "・slot 或 /slot — Slot 庫存明細（含待上線）",
  "・特別版 或 /special — 最近一期與下次檢查",
  "・本週 或 /week — 本週每天收錄概況",
  "・狀態 或 /status — 最近執行、Firecrawl 額度、系統警報",
  "・說明 或 /help — 這份說明",
  "資料來自 GitHub，每晚日報推上去後就是最新。",
].join("\n");

// ───────────────────────── 日期工具（一律台北時間） ─────────────────────────
const DAY = 86400000;
function tpeToday() { return new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10); }
function d(s) { return Date.parse(String(s).slice(0, 10) + "T00:00:00Z"); }
function iso(ms) { return new Date(ms).toISOString().slice(0, 10); }
function addDays(s, n) { return iso(d(s) + n * DAY); }
function diff(a, b) { return Math.round((d(a) - d(b)) / DAY); }       // a − b（天）
function wd(s) { return WEEK[(new Date(d(s)).getUTCDay() + 6) % 7]; }
function md(s) { return `${+String(s).slice(5, 7)}/${+String(s).slice(8, 10)}`; }

// ───────────────────────── 讀 GitHub ─────────────────────────
async function raw(path) {
  const r = await fetch(RAW + encodeURI(path), { cf: { cacheTtl: 60, cacheEverything: true } });
  if (!r.ok) return null;
  return path.endsWith(".json") ? r.json() : r.text();
}
async function commits(n = 40) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/commits?sha=${BRANCH}&per_page=${n}`,
    { headers: { "User-Agent": "igaming-tg-worker", Accept: "application/vnd.github+json" }, cf: { cacheTtl: 60 } });
  return r.ok ? (await r.json()).map(c => ({ msg: c.commit.message.split("\n")[0], at: c.commit.committer.date })) : [];
}

// ───────────────────────── 庫存判斷（移植自 inventory.py） ─────────────────────────
function norm(s) { return String(s || "").toLowerCase().replace(/[^0-9a-z一-鿿|]+/g, ""); }
function keyOf(x) { return norm(x.key || `${x.title || ""}|${x.gp || ""}`); }
function deadline(x, slot) {
  const first = x.first_seen;
  if (slot) {
    const rel = x.release_date;
    if (rel && d(rel) > d(first)) return iso(Math.max(d(first) + SLOT_FRESH * DAY, d(rel) + SLOT_AFTER_RELEASE * DAY));
    return addDays(first, SLOT_FRESH);
  }
  return addDays(first, OTHER_FRESH);
}
function expired(x, today, slot) { return d(today) > d(deadline(x, slot)); }
function placeholder(x) {
  if (x.release_date) return false;
  const srcs = x.sources || [];
  const text = srcs.map(s => `${s.name || ""} ${s.published || ""}`).join(" ");
  if (!(x.tbc || /TBC/.test(text))) return false;
  const olds = text.match(/20\d\d-\d\d-\d\d/g) || [];
  return !olds.length || olds.sort()[0] < String(x.first_seen || "").slice(0, 10);
}
function snapshot(inv, today) {
  const recent = new Set((inv.history || []).filter(h => { const n = diff(today, h.date); return n >= 0 && n <= DEDUP; })
    .flatMap(h => [h.key, norm(h.title)]));
  const seen = x => recent.has(keyOf(x)) || recent.has(norm(x.title));
  const horizon = addDays(today, PREVIEW_MAX);
  const slots = (inv.slots || []).filter(x => !expired(x, today, true) && !seen(x) && !placeholder(x));
  const later = slots.filter(x => x.release_date && d(x.release_date) > d(horizon)).sort((a, b) => a.release_date.localeCompare(b.release_date));
  const ready = slots.filter(x => !later.includes(x)).sort((a, b) => (b.b || 0) - (a.b || 0) || a.first_seen.localeCompare(b.first_seen));
  const others = {};
  for (const c of Object.keys(CATS))
    others[c] = (inv.others || []).filter(x => x.cat === c && !expired(x, today, false) && !seen(x)).sort((a, b) => a.first_seen.localeCompare(b.first_seen));
  return { ready, later, others };
}
function left(x, today, slot) {
  const n = diff(deadline(x, slot), today);
  return (n <= WARN ? "⚠️ " : "") + (n === 0 ? "今天最後一天" : `剩 ${n} 天`);
}

// ───────────────────────── 各指令 ─────────────────────────
function head(today) { return `📦 13' v 庫存（公司帳號・v6.x 規則）\n查詢日：${today}（週${wd(today)}）`; }
function slotLines(today, ready, later) {
  const L = [`🎰 Slot 可用 ${ready.length} 款（B 分高→首見早）`];
  ready.forEach((x, i) => L.push(`${i + 1}. [B${x.b ?? "?"}] ${x.title} — ${x.gp || "?"}｜${md(x.first_seen)} 首見｜${left(x, today, true)}`));
  if (!ready.length) L.push("（無）");
  if (later.length) {
    L.push("", `⏳ 待上線 ${later.length} 款（上線日在 7 天以後，還不能上日報）`);
    later.forEach(x => L.push(`・[B${x.b ?? "?"}] ${x.title} — ${x.gp || "?"}｜${md(x.release_date)} 上線`));
  }
  return L;
}
async function replyStock() {
  const today = tpeToday(), inv = await raw("state/inventory.json");
  if (!inv) return "⚠️ 讀不到庫存檔，請稍後再試";
  const { ready, later, others } = snapshot(inv, today);
  const total = ready.length + Object.values(others).reduce((n, v) => n + v.length, 0);
  const L = [head(today), "", `合計可用 ${total} 則：Slot ${ready.length}${later.length ? `（另有待上線 ${later.length}）` : ""}・` +
    Object.entries(CATS).map(([c, n]) => `${n.split(" ").slice(1).join(" ")} ${others[c].length}`).join("・"), ""];
  L.push(...slotLines(today, ready, later));
  for (const [c, name] of Object.entries(CATS)) {
    L.push("", `${name} ${others[c].length} 則`);
    others[c].forEach(x => L.push(`・${x.title}｜${md(x.first_seen)} 首見｜${left(x, today, false)}`));
    if (!others[c].length) L.push("（無）");
  }
  return L.join("\n");
}
async function replySlot() {
  const today = tpeToday(), inv = await raw("state/inventory.json");
  if (!inv) return "⚠️ 讀不到庫存檔，請稍後再試";
  const { ready, later } = snapshot(inv, today);
  return [head(today), "", ...slotLines(today, ready, later)].join("\n");
}
async function replyToday() {
  const today = tpeToday(), rep = await raw(`state/${today}-report.json`);
  if (!rep) {
    const c = (await commits(10)).find(x => x.msg.startsWith("daily:"));
    return `📰 今天（${today}）的 13' v 日報還沒產出` + (c ? `\n（最近一次成功：${c.msg.replace("daily: ", "").replace(" report", "")}）` : "") +
      "\n要補跑請跟 Claude 說「補跑日報」。";
  }
  const secs = rep.sections.filter(s => s.items.length);
  const L = [`📰 今日日報 ${today}（週${wd(today)}）・13' v`, secs.map(s => `${NAMES[s.cat]} ${s.items.length}`).join("・"), ""];
  for (const s of secs) { L.push(NAMES[s.cat], ...s.items.map(it => `${String(it.no).padStart(2, "0")} ${it.title.slice(0, 60)}`), ""); }
  L.push(`🔗 ${SITE}/reports/${today}-test.html`);
  if (await raw(`state/${today}-special-report.json`)) L.push(`📦 今日特別版：${SITE}/reports/${today}-special.html`);
  return L.join("\n");
}
async function replySpecial() {
  const today = tpeToday(), inv = await raw("state/inventory.json");
  const L = ["📦 庫存釋放特別版", ""];
  const c = (await commits(60)).find(x => /^special: \d{4}-\d\d-\d\d/.test(x.msg));
  if (c) {
    const day = c.msg.match(/\d{4}-\d\d-\d\d/)[0], m = c.msg.match(/釋放 (\d+) 款/);
    L.push(`最近一期：${day}${m ? `，釋放 ${m[1]} 款` : ""}`, `🔗 ${SITE}/reports/${day}-special.html`, "");
  }
  let nxt = today; do { nxt = addDays(nxt, 1); } while (!["一", "四"].includes(wd(nxt)));
  const n = inv ? snapshot(inv, today).ready.length : 0;
  L.push(`下一次檢查：${md(nxt)}（週${wd(nxt)}）日報成功後`, `目前 Slot 可用庫存 ${n} 款（門檻 ≥5）→ ${n >= 5 ? "會發" : "不到門檻，不會發"}`);
  return L.join("\n");
}
async function replyWeek() {
  const today = tpeToday();
  const start = addDays(today, -((new Date(d(today)).getUTCDay()) % 7));      // 週日起算
  const days = [];
  for (let s = start; d(s) <= d(today); s = addDays(s, 1)) days.push(s);
  const reps = await Promise.all(days.map(s => raw(`state/${s}-report.json`)));
  const sps = await Promise.all(days.map(s => raw(`state/${s}-special-report.json`)));
  const L = [`📅 本週概況（${md(start)} 週日起）`, ""];
  days.forEach((s, i) => {
    const r = reps[i];
    if (!r) { L.push(`${md(s)} 週${wd(s)}　—`); return; }
    const c = Object.fromEntries(r.sections.map(x => [x.cat, x.items.length]));
    const tot = Object.values(c).reduce((a, b) => a + b, 0);
    L.push(`${md(s)} 週${wd(s)}　共 ${tot} 則（Slot ${c.cat1 || 0}）${sps[i] ? "　📦特別版" : ""}`);
  });
  return L.join("\n");
}
async function replyStatus() {
  const today = tpeToday();
  const L = ["🩺 系統狀態（13' v）", ""];
  const cs = await commits(40);
  const daily = cs.filter(x => x.msg.startsWith("daily:")).slice(0, 5);
  const alerts = cs.filter(x => x.msg.startsWith("alert:")).slice(0, 2);
  if (daily.length) {
    L.push("🕑 最近成功的日報");
    daily.forEach(x => L.push(`・${x.msg.match(/\d{4}-\d\d-\d\d/)[0]}　推上 GitHub：${new Date(Date.parse(x.at) + 8 * 3600000).toISOString().slice(5, 16).replace("T", " ")}`));
    L.push(daily[0].msg.includes(today) ? "✅ 今天的日報已完成" : "⚠️ 今天的日報還沒完成", "");
  }
  if (alerts.length) { L.push("🚨 最近的即時警報"); alerts.forEach(x => L.push(`・${x.msg.replace("alert: ", "")}`)); L.push(""); }
  const cr = await raw("state/health/credits.json");
  if (cr && Object.keys(cr).length) {
    const k = Object.keys(cr).sort().pop(), v = cr[k];
    const rem = typeof v === "object" ? (v.end ?? v.start) : v;
    const used = typeof v === "object" && v.start != null && v.end != null ? v.start - v.end : null;
    L.push(`💳 Firecrawl：剩 ${rem} 點（${k}）${used != null ? `，當天用 ${used} 點` : ""}；每月 14 日重置`);
  }
  const hl = (await raw(`state/health/${today}.json`)) || (await raw(`state/health/${addDays(today, -1)}.json`));
  if (hl && hl.alerts && hl.alerts.length) { L.push("⚙️ 系統警報："); hl.alerts.forEach(a => L.push(`・${a.slice(0, 80)}`)); }
  else L.push("⚙️ 系統警報：無");
  L.push("", "⏰ 每天 02:30 自動執行；週一、週四日報成功後會檢查特別版");
  return L.join("\n");
}

async function route(text) {
  let t = String(text || "").trim().toLowerCase();
  if (t.startsWith("/")) t = t.split("@")[0];
  t = t.replace(/^\/+/, "").trim();
  try {
    if (["slot", "slots", "slot 庫存", "slot庫存", "老虎機", "老虎機庫存"].includes(t)) return await replySlot();
    if (["today", "今天", "今日", "日報", "今天日報", "今日日報"].includes(t)) return await replyToday();
    if (["special", "特別版", "釋放"].includes(t)) return await replySpecial();
    if (["week", "本週", "這週", "週報"].includes(t)) return await replyWeek();
    if (["status", "狀態", "系統", "健康", "health"].includes(t)) return await replyStatus();
    if (["stock", "inventory", "庫存", "库存", "查庫存", "剩多少"].includes(t) || t.includes("庫存") || t.includes("库存")) return await replyStock();
  } catch (e) {
    return `⚠️ 查詢時出錯（${e && e.name || "Error"}），請稍後再試`;
  }
  return HELP;
}

// ───────────────────────── Telegram ─────────────────────────
async function tg(env, method, body) {
  const r = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/${method}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return r.json();
}
async function reply(env, chatId, text) {
  for (let i = 0; i < text.length; i += 4000)
    await tg(env, "sendMessage", { chat_id: chatId, text: text.slice(i, i + 4000), disable_web_page_preview: true });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const okKey = env.WEBHOOK_SECRET && url.searchParams.get("key") === env.WEBHOOK_SECRET;

    if (url.pathname === "/telegram" && request.method === "POST") {
      if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) return new Response("forbidden", { status: 403 });
      const update = await request.json().catch(() => ({}));
      const m = update.message || {};
      const chatId = String((m.chat || {}).id || "");
      if (chatId && chatId === String(env.ALLOWED_CHAT_ID || "606981537")) {
        ctx.waitUntil(route(m.text).then(t => reply(env, chatId, t)));     // 先回 200 給 Telegram，再慢慢查資料
      }
      return new Response("ok");                                           // 非白名單：直接丟棄、不回覆
    }
    if (url.pathname === "/setup") {
      if (!okKey) return new Response("key 錯誤", { status: 403 });
      const hook = await tg(env, "setWebhook", { url: `${url.origin}/telegram`, secret_token: env.WEBHOOK_SECRET, allowed_updates: ["message"] });
      const cmds = await tg(env, "setMyCommands", { commands: COMMANDS.map(([command, description]) => ({ command, description })) });
      const ok = hook.ok && cmds.ok;
      return new Response(ok ? "✓ 完成：Telegram 已改由雲端機器人回覆，指令選單也註冊好了。可以回 Telegram 打「狀態」試試。"
        : `✗ 失敗：${JSON.stringify({ hook, cmds })}`, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
    }
    if (url.pathname === "/unset") {
      if (!okKey) return new Response("key 錯誤", { status: 403 });
      const r = await tg(env, "deleteWebhook", {});
      return new Response(r.ok ? "✓ 已取消 webhook（可改回本機機器人）" : `✗ ${JSON.stringify(r)}`, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
    }
    if (url.pathname === "/test") {
      if (!okKey) return new Response("key 錯誤", { status: 403 });
      return new Response(await route(url.searchParams.get("q") || "庫存"), { headers: { "Content-Type": "text/plain; charset=utf-8" } });
    }
    return new Response("iGaming 日報機器人（雲端版）運作中", { headers: { "Content-Type": "text/plain; charset=utf-8" } });
  },
};

// 給本機測試用（Cloudflare 不會用到）
export const _test = { route, snapshot, deadline, expired, placeholder, tpeToday, addDays, diff, wd };
