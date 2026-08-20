/* GNSS 文献调研 Agent — 前端逻辑（原生 JS，无构建步骤） */
"use strict";

const $ = (id) => document.getElementById(id);

const state = {
  tasks: [],
  currentId: null,
  tab: "papers",
  paperStatus: "",
  settings: {},
  sources: [],
  examples: [],
  logsCursor: 0,
  lastPapersJson: "",
};

const STATUS_LABEL = {
  running: "运行中",
  stopping: "正在停止",
  stopped: "已停止",
  completed: "已完成",
  error: "异常",
};

const STATUS_TAG = {
  running: "green",
  stopping: "amber",
  stopped: "amber",
  completed: "green",
  error: "red",
};

const PAPER_STATUS_LABEL = {
  pending: "待打分",
  relevant: "相关",
  read: "已深读",
  scored: "已排除",
  failed: "失败",
};

const SOURCE_LABEL = {
  openalex: "OpenAlex",
  arxiv: "arXiv",
  semanticscholar: "Semantic Scholar",
  crossref: "Crossref",
  upload: "📄 用户上传",
};

/* ---------------- fetch helpers ---------------- */
async function api(path, opts = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try { msg = (await resp.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return resp.json();
}

/* ---------------- init ---------------- */
async function init() {
  try {
    const health = await api("/api/health");
    const v = $("app-version");
    if (v) { v.textContent = "v" + (health.version || "?"); }
    const el = $("llm-status");
    if (health.llm_configured) {
      el.textContent = "模型已配置";
      el.className = "badge running";
    } else {
      el.textContent = "模型未配置";
      el.className = "badge off";
    }
  } catch (_) {}
  try { state.settings = await api("/api/settings"); } catch (_) {}
  try { state.sources = (await api("/api/sources")).sources; } catch (_) {}
  try { state.examples = (await api("/api/example-topics")).topics; } catch (_) {}
  renderExampleChips();
  bindEvents();
  await refresh();
  setInterval(refresh, 4000);
  setInterval(refreshDetail, 4000);
}

/* ---------------- polling ---------------- */
async function refresh() {
  try {
    const data = await api("/api/tasks");
    state.tasks = data.tasks;
  } catch (_) { return; }
  renderTaskList();
  if (!state.currentId && state.tasks.length) {
    state.currentId = state.tasks[0].id;
    state.logsCursor = 0;
  }
  if (state.currentId) renderDetail();
}

let _detailTick = 0;
async function refreshDetail() {
  if (!state.currentId) return;
  _detailTick++;
  try {
    const t = await api(`/api/tasks/${state.currentId}`);
    const idx = state.tasks.findIndex((x) => x.id === state.currentId);
    if (idx >= 0) state.tasks[idx] = t;
    if (state.tab === "papers" && _detailTick % 2 === 0) await renderPapers();
    if (state.tab === "logs") await renderLogs(true);
    renderDetail();
  } catch (_) {}
}

/* ---------------- render: task list ---------------- */
function renderTaskList() {
  $("task-count").textContent = state.tasks.length;
  const box = $("task-list");
  if (!state.tasks.length) {
    box.innerHTML = '<div class="empty" style="padding:20px 8px;font-size:12.5px">还没有任务<br>点击「新建调研」开始</div>';
    return;
  }
  box.innerHTML = state.tasks.map((t) => {
    const c = t.counters || {};
    const active = t.id === state.currentId ? "active" : "";
    const pct = t.target_count ? Math.min(100, Math.round((c.read || 0) / t.target_count * 100)) : 0;
    return `<div class="task-item ${active}" data-id="${t.id}">
      <div class="t-title">${esc(t.topic)}</div>
      <div class="t-meta">
        <span class="tag ${STATUS_TAG[t.status] || "gray"}">${STATUS_LABEL[t.status] || t.status}</span>
        <span>深读 ${c.read || 0}/${t.target_count || 100}</span>
        <span>${pct}%</span>
        <span>${fmtTime(t.created_at)}</span>
      </div>
    </div>`;
  }).join("");
  box.querySelectorAll(".task-item").forEach((el) => {
    el.addEventListener("click", () => {
      state.currentId = el.dataset.id;
      state.logsCursor = 0;
      state.lastPapersJson = "";
      renderTaskList();
      renderDetail();
      renderPapers();
    });
  });
}

/* ---------------- render: detail ---------------- */
function renderDetail() {
  const t = state.tasks.find((x) => x.id === state.currentId);
  if (!t) { $("detail").classList.add("hidden"); $("empty-hint").classList.remove("hidden"); return; }
  $("empty-hint").classList.add("hidden");
  $("detail").classList.remove("hidden");

  const c = t.counters || {};
  $("d-topic").textContent = t.topic;
  const st = $("d-status");
  st.textContent = STATUS_LABEL[t.status] || t.status;
  st.className = "badge " + (t.status || "");
  $("d-found").textContent = c.found || 0;
  $("d-relevant").textContent = c.relevant || 0;
  $("d-read").textContent = c.read || 0;
  $("d-target").textContent = t.target_count || 100;
  const pct = t.target_count ? Math.min(100, Math.round((c.read || 0) / t.target_count * 100)) : 0;
  $("d-progress").style.width = pct + "%";

  let meta = `创建于 ${fmtTime(t.created_at)}`;
  if (t.started_at) meta += ` · 开始 ${fmtTime(t.started_at)}`;
  if (t.stopped_at) meta += ` · 结束 ${fmtTime(t.stopped_at)}`;
  meta += ` · 时长上限 ${t.time_limit_hours}h · 检索轮次 ${t.rounds || 0} · 检索式 ${c.queries || 0} 个`;
  const cost = t.cost || {};
  if (cost.calls) {
    meta += ` · 💰 LLM ${cost.calls} 次调用 · ${(cost.in_tokens || 0).toLocaleString()}/${(cost.out_tokens || 0).toLocaleString()} tokens · 约 $${(cost.est_cost_usd || 0).toFixed(3)}`;
  }
  if (t.direction) meta += ` · 补充说明：${esc(t.direction)}`;
  if (t.error) meta += ` · <span class="tag red">${esc(t.error)}</span>`;
  $("d-meta").innerHTML = meta;

  const stopBtn = $("btn-stop");
  if (t.status === "running" || t.status === "stopping") {
    stopBtn.disabled = false;
    stopBtn.textContent = t.status === "stopping" ? "正在停止…" : "■ 停止调研";
  } else {
    stopBtn.disabled = true;
    stopBtn.textContent = "已结束";
  }
  $("btn-delete").disabled = (t.status === "running" || t.status === "stopping");
}

/* ---------------- render: papers ---------------- */
async function renderPapers() {
  if (!state.currentId) return;
  let url = `/api/tasks/${state.currentId}/papers?limit=500&order=created_at DESC`;
  if (state.paperStatus) url += `&status=${state.paperStatus}`;
  try {
    const data = await api(url);
    const json = JSON.stringify(data.papers.map((p) => p.id + p.status));
    if (json === state.lastPapersJson) return;
    state.lastPapersJson = json;
    const box = $("paper-list");
    if (!data.papers.length) {
      box.innerHTML = '<div class="empty" style="padding:30px">暂无论文（检索进行中…）</div>';
      return;
    }
    box.innerHTML = data.papers.map((p) => {
      const kp = p.key_points || {};
      const authors = (p.authors || []).slice(0, 3).join("、");
      const tags = [
        `<span class="tag ${p.status}">${PAPER_STATUS_LABEL[p.status] || p.status}</span>`,
        `<span class="tag gray">${SOURCE_LABEL[p.source] || p.source || "未知"}</span>`,
        p.year ? `<span class="tag gray">${p.year}</span>` : "",
        p.category ? `<span class="tag">${catLabel(p.category)}</span>` : "",
        p.relevance != null ? `<span class="tag green">相关度 ${(+p.relevance).toFixed(2)}</span>` : "",
        p.cited_by ? `<span class="tag gray">被引 ${p.cited_by}</span>` : "",
      ].filter(Boolean).join(" ");
      const link = p.doi ? `https://doi.org/${p.doi}` : (p.url || "");
      return `<div class="paper-item">
        <div class="p-title" data-expand="1">${esc(p.title)}</div>
        <div class="p-meta">${tags}${authors ? ` · ${esc(authors)}` : ""}${p.venue ? ` · ${esc(p.venue)}` : ""}</div>
        <div class="p-summary hidden">${esc(p.summary || (p.abstract || "") + (kp.relevance ? "\n\n[相关性] " + kp.relevance : ""))}
        ${kp.methods && kp.methods.length ? "\n[方法] " + esc(kp.methods.join("；")) : ""}
        ${kp.findings && kp.findings.length ? "\n[结论] " + esc(kp.findings.join("；")) : ""}</div>
        ${link ? `<div class="p-links"><a href="${esc(link)}" target="_blank" rel="noopener">${esc(link)}</a></div>` : ""}
      </div>`;
    }).join("");
    box.querySelectorAll(".p-title").forEach((el) => {
      el.addEventListener("click", () => {
        const s = el.parentElement.querySelector(".p-summary");
        s.classList.toggle("hidden");
      });
    });
  } catch (_) {}
}

function catLabel(cat) {
  const map = {
    receiver_testing: "接收机测试", high_precision: "高精度定位", integrity: "完好性",
    multipath: "多路径", ionosphere: "电离层", interference: "干扰抗干扰",
    timing: "授时", integrated_navigation: "组合导航", sbass: "星基增强",
    new_signals: "新信号", simulation: "仿真测试", other: "其他",
  };
  return map[cat] || cat;
}

/* ---------------- render: logs ---------------- */
async function renderLogs(append) {
  if (!state.currentId) return;
  try {
    const data = await api(`/api/tasks/${state.currentId}/logs?after_id=${state.logsCursor}&limit=300`);
    if (!data.logs.length) return;
    state.logsCursor = data.logs[data.logs.length - 1].id;
    const box = $("log-list");
    const html = data.logs.map((l) =>
      `<div class="log-item ${l.level}"><span class="t">${esc(l.ts.slice(11, 19))}</span><span class="m">${esc(l.message)}</span></div>`
    ).join("");
    if (append) box.insertAdjacentHTML("beforeend", html);
    else box.innerHTML = html;
    box.scrollTop = box.scrollHeight;
  } catch (_) {}
}

/* ---------------- render: report ---------------- */
let _reportCache = "";
async function renderReport(force) {
  if (!state.currentId) return;
  try {
    const data = await api(`/api/tasks/${state.currentId}/report`);
    if (!force && data.content === _reportCache) return;
    _reportCache = data.content;
    $("report-content").innerHTML = mdToHtml(data.content);
    $("report-meta").textContent =
      `报告生成于 ${new Date(data.updated_at * 1000).toLocaleString()} · 共 ${data.content.length} 字符`;
  } catch (e) {
    $("report-content").innerHTML = '<div class="empty" style="padding:30px">报告尚未生成（任务运行中会持续更新，请稍候）</div>';
    $("report-meta").textContent = "";
  }
}

/* ---------------- markdown renderer (报告子集) ---------------- */
function mdEscape(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function mdInline(s) {
  return mdEscape(s)
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
function mdToHtml(md) {
  const lines = md.split("\n");
  let html = "", inList = null, inTable = false, tableRows = [];
  const closeList = () => { if (inList) { html += inList === "ul" ? "</ul>" : "</ol>"; inList = null; } };
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) { closeList(); if (inTable) { html += buildTable(tableRows); tableRows = []; inTable = false; } continue; }
    if (line.startsWith("|")) { inTable = true; tableRows.push(line); continue; }
    if (inTable) { html += buildTable(tableRows); tableRows = []; inTable = false; }
    const h = line.match(/^(#{1,4})\s+(.*)/);
    if (h) { closeList(); const n = h[1].length; html += `<h${n}>${mdInline(h[2])}</h${n}>`; continue; }
    if (line.startsWith("> ")) { closeList(); html += `<blockquote>${mdInline(line.slice(2))}</blockquote>`; continue; }
    if (/^[-*]\s+/.test(line)) {
      if (inList !== "ul") { closeList(); html += "<ul>"; inList = "ul"; }
      html += `<li>${mdInline(line.replace(/^[-*]\s+/, ""))}</li>`; continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      if (inList !== "ol") { closeList(); html += "<ol>"; inList = "ol"; }
      html += `<li>${mdInline(line.replace(/^\d+\.\s+/, ""))}</li>`; continue;
    }
    closeList();
    html += `<p>${mdInline(line)}</p>`;
  }
  closeList();
  if (inTable) html += buildTable(tableRows);
  return html;
}
function buildTable(rows) {
  const cells = rows.map((r) => r.split("|").slice(1, -1).map((c) => c.trim()));
  if (cells.length < 2) return "";
  const head = cells[0].map((c) => `<th>${mdInline(c)}</th>`).join("");
  const body = cells.slice(2).map((r) =>
    `<tr>${r.map((c) => `<td>${mdInline(c)}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

/* ---------------- examples & settings ---------------- */
function renderExampleChips() {
  const box = $("example-chips");
  box.innerHTML = state.examples.map((e, i) =>
    `<button class="chip" data-i="${i}">${esc(e.zh)}</button>`).join("");
  box.querySelectorAll(".chip").forEach((el) => {
    el.addEventListener("click", () => {
      const e = state.examples[+el.dataset.i];
      $("t-topic").value = e.zh + "（" + e.en + "）";
    });
  });
}

function renderSourceChips() {
  const box = $("s-sources");
  // 未配置过时默认启用全部源
  if (!state.settings.sources_enabled || !state.settings.sources_enabled.length) {
    state.settings.sources_enabled = state.sources.map((s) => s.name);
  }
  const enabled = state.settings.sources_enabled;
  box.innerHTML = state.sources.map((s) =>
    `<button class="chip ${enabled.includes(s.name) ? "active" : ""}" data-name="${s.name}">${esc(s.label)}</button>`
  ).join("");
  box.querySelectorAll(".chip").forEach((el) => {
    el.addEventListener("click", () => {
      el.classList.toggle("active");
      const name = el.dataset.name;
      let enabled = state.settings.sources_enabled || [];
      enabled = enabled.includes(name) ? enabled.filter((n) => n !== name) : [...enabled, name];
      state.settings.sources_enabled = enabled;
    });
  });
}

function openSettings() {
  const s = state.settings;
  $("s-base").value = s.api_base || "";
  $("s-model").value = s.model || "";
  $("s-key").value = s.api_key || "";
  $("s-target").value = s.target_count || 100;
  $("s-hours").value = s.time_limit_hours || 24;
  $("s-years").value = s.year_back || 10;
  $("s-threshold").value = s.relevance_threshold || 0.6;
  $("s-price-in").value = s.price_in_per_m != null ? s.price_in_per_m : 0.27;
  $("s-price-out").value = s.price_out_per_m != null ? s.price_out_per_m : 1.10;
  $("s-cost-cap").value = s.max_task_cost_usd != null ? s.max_task_cost_usd : 10;
  $("s-readers").value = s.reader_pool_size != null ? s.reader_pool_size : 3;
  $("s-qc").value = (s.qc_enabled == null || s.qc_enabled === "1" || s.qc_enabled === true) ? "1" : "0";
  $("s-m-strategist").value = s.model_strategist || "";
  $("s-m-reviewer").value = s.model_reviewer || "";
  $("s-m-reader").value = s.model_reader || "";
  $("s-m-analyst").value = s.model_analyst || "";
  $("s-m-editor").value = s.model_editor || "";
  $("s-test-result").textContent = "";
  renderSourceChips();
  $("modal-settings").classList.remove("hidden");
}

function collectSettings() {
  return {
    api_base: $("s-base").value.trim(),
    model: $("s-model").value.trim(),
    api_key: $("s-key").value.trim(),
    target_count: +$("s-target").value || 100,
    time_limit_hours: +$("s-hours").value || 24,
    year_back: +$("s-years").value || 10,
    relevance_threshold: +$("s-threshold").value || 0.6,
    price_in_per_m: +$("s-price-in").value || 0,
    price_out_per_m: +$("s-price-out").value || 0,
    max_task_cost_usd: +$("s-cost-cap").value || 0,
    reader_pool_size: +$("s-readers").value || 3,
    qc_enabled: $("s-qc").value === "1",
    model_strategist: $("s-m-strategist").value.trim(),
    model_reviewer: $("s-m-reviewer").value.trim(),
    model_reader: $("s-m-reader").value.trim(),
    model_analyst: $("s-m-analyst").value.trim(),
    model_editor: $("s-m-editor").value.trim(),
    sources_enabled: state.settings.sources_enabled || [],
  };
}

/* ---------------- events ---------------- */
function bindEvents() {
  $("btn-new").addEventListener("click", () => $("modal-new").classList.remove("hidden"));
  $("btn-new-cancel").addEventListener("click", () => $("modal-new").classList.add("hidden"));
  $("btn-new-submit").addEventListener("click", createTask);
  $("btn-settings").addEventListener("click", openSettings);
  $("btn-settings-cancel").addEventListener("click", () => $("modal-settings").classList.add("hidden"));
  $("btn-settings-save").addEventListener("click", saveSettings);
  $("btn-settings-test").addEventListener("click", testSettings);
  $("btn-refresh").addEventListener("click", async () => {
    await refresh(); await renderPapers(); await renderLogs(false); await renderReport(true);
  });
  $("btn-stop").addEventListener("click", stopTask);
  $("btn-delete").addEventListener("click", deleteTask);
  $("btn-upload").addEventListener("click", () => {
    if (!state.currentId) { alert("请先选择任务"); return; }
    $("pdf-input").click();
  });
  $("pdf-input").addEventListener("change", uploadPdf);
  $("btn-copy-report").addEventListener("click", async () => {
    if (!_reportCache) return;
    try { await navigator.clipboard.writeText(_reportCache); alert("报告已复制到剪贴板"); }
    catch (_) { alert("复制失败，请手动选择复制"); }
  });
  $("btn-download-report").addEventListener("click", () => {
    if (!_reportCache || !state.currentId) return;
    const blob = new Blob([_reportCache], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `文献调研报告_${state.currentId}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  });
  document.querySelectorAll(".tabs .tab").forEach((el) => {
    el.addEventListener("click", () => {
      state.tab = el.dataset.tab;
      document.querySelectorAll(".tabs .tab").forEach((x) => x.classList.toggle("active", x === el));
      ["papers", "logs", "report"].forEach((t) => $(`tab-${t}`).classList.toggle("hidden", t !== state.tab));
      if (state.tab === "logs") renderLogs(false);
      if (state.tab === "report") renderReport(true);
      if (state.tab === "papers") renderPapers();
    });
  });
  $("paper-filters").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    state.paperStatus = chip.dataset.status;
    state.lastPapersJson = "";
    document.querySelectorAll("#paper-filters .chip").forEach((c) => c.classList.toggle("active", c === chip));
    renderPapers();
  });
  document.querySelectorAll(".modal").forEach((m) => {
    m.addEventListener("click", (e) => { if (e.target === m) m.classList.add("hidden"); });
  });
}

async function createTask() {
  const topic = $("t-topic").value.trim();
  if (!topic) { alert("请先输入调研主题"); return; }
  const body = {
    topic,
    direction: $("t-direction").value.trim(),
    target_count: +$("t-target").value || 100,
    time_limit_hours: +$("t-hours").value || 24,
    year_back: +$("t-years").value || 10,
  };
  const cap = $("t-cost-cap").value.trim();
  if (cap !== "") body.max_task_cost_usd = +cap || 0;
  try {
    const t = await api("/api/tasks", { method: "POST", body: JSON.stringify(body) });
    $("modal-new").classList.add("hidden");
    $("t-topic").value = ""; $("t-direction").value = ""; $("t-cost-cap").value = "";
    state.currentId = t.id;
    state.logsCursor = 0;
    state.lastPapersJson = "";
    await refresh();
  } catch (e) {
    alert("创建失败：" + e.message);
  }
}

async function stopTask() {
  if (!state.currentId) return;
  if (!confirm("确定停止该调研任务吗？将完成当前步骤并生成最终报告。")) return;
  try {
    await api(`/api/tasks/${state.currentId}/stop`, { method: "POST" });
  } catch (e) { alert("停止失败：" + e.message); }
}

async function uploadPdf() {
  const input = $("pdf-input");
  const file = input.files && input.files[0];
  if (!file || !state.currentId) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) { alert("仅支持 PDF 文件"); input.value = ""; return; }
  const btn = $("btn-upload");
  btn.disabled = true;
  btn.textContent = "上传中…";
  try {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch(`/api/tasks/${state.currentId}/upload`, { method: "POST", body: fd });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
    alert(`✅ 已上传并加入深读队列：${data.title || file.name}`);
    state.lastPapersJson = "";
    await renderPapers();
    await renderDetail();
  } catch (e) {
    alert("上传失败：" + e.message);
  } finally {
    input.value = "";
    btn.disabled = false;
    btn.textContent = "📄 上传论文(PDF)";
  }
}

async function deleteTask() {
  if (!state.currentId) return;
  if (!confirm("确定删除该任务吗？其论文、日志与报告将一并删除，且不可恢复。")) return;
  try {
    await api(`/api/tasks/${state.currentId}`, { method: "DELETE" });
    state.tasks = state.tasks.filter((t) => t.id !== state.currentId);
    state.currentId = state.tasks.length ? state.tasks[0].id : null;
    state.logsCursor = 0;
    state.lastPapersJson = "";
    _reportCache = "";
    renderTaskList();
    if (state.currentId) { renderDetail(); renderPapers(); }
    else { $("detail").classList.add("hidden"); $("empty-hint").classList.remove("hidden"); }
  } catch (e) { alert("删除失败：" + e.message); }
}

async function saveSettings() {
  try {
    await api("/api/settings", { method: "PUT", body: JSON.stringify(collectSettings()) });
    state.settings = await api("/api/settings");
    $("modal-settings").classList.add("hidden");
    const el = $("llm-status");
    if (state.settings.api_base && state.settings.model) {
      el.textContent = "模型已配置"; el.className = "badge running";
    }
  } catch (e) { alert("保存失败：" + e.message); }
}

async function testSettings() {
  const res = $("s-test-result");
  res.className = "test-result";
  res.textContent = "测试中…";
  try {
    const r = await api("/api/settings/test", {
      method: "POST", body: JSON.stringify(collectSettings()),
    });
    if (r.ok) { res.textContent = "✅ 连接成功：" + (r.reply || ""); res.className = "test-result ok"; }
    else { res.textContent = "❌ " + r.error; res.className = "test-result fail"; }
  } catch (e) {
    res.textContent = "❌ 请求失败：" + e.message;
    res.className = "test-result fail";
  }
}

/* ---------------- utils ---------------- */
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

init();
