const listEl = document.getElementById("list");
const detailEl = document.getElementById("detail");
const statsEl = document.getElementById("stats");
const filterEl = document.getElementById("filter");
const hideProcEl = document.getElementById("hideProc");
const semanticEl = document.getElementById("semantic");
let allTopics = [];
let activeId = null;

async function loadStats() {
  try {
    const c = await fetch("/api/completeness").then((r) => r.json());
    const v = await fetch("/api/validation").then((r) => r.json());
    const val = v.available
      ? `Manual review: ${v.entries_reviewed} topics, location accuracy ${v.metrics.location_accuracy_pct}%`
      : "Manual validation report not loaded";
    statsEl.innerHTML = `
      PDF pages: ${c.total_pdf_pages}<br/>
      Testimony: P${c.testimony_page_start}–P${c.testimony_page_end}<br/>
      Extracted lines: ${c.extracted_lines}<br/>
      Chunks: ${c.chunks_created}<br/>
      ${val}
    `;
  } catch (e) {
    statsEl.textContent = "Run the pipeline to generate outputs.";
  }
}

async function loadTopics() {
  const q = filterEl.value.trim();
  const procedural = hideProcEl.checked ? false : null;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (procedural === false) params.set("procedural", "false");
  const data = await fetch("/api/topics?" + params.toString()).then((r) => r.json());
  allTopics = data.topics;
  renderList();
  if (!activeId && allTopics.length > 0) {
    openTopic(allTopics[0].topic_id);
  }
}

function renderList() {
  listEl.innerHTML = allTopics
    .map(
      (t) => `
      <div class="topic ${t.topic_id === activeId ? "active" : ""}" data-id="${t.topic_id}">
        <h3>${escapeHtml(t.topic)}</h3>
        <div class="meta">P${t.start_page}:L${t.start_line} → P${t.end_page}:L${t.end_line}</div>
      </div>`
    )
    .join("");
  listEl.querySelectorAll(".topic").forEach((el) => {
    el.addEventListener("click", () => openTopic(el.dataset.id));
  });
}

async function openTopic(id) {
  activeId = id;
  renderList();
  const data = await fetch("/api/topics/" + encodeURIComponent(id)).then((r) => r.json());
  const prov = await fetch("/api/provenance/check?topic_id=" + encodeURIComponent(id)).then((r) => r.json());
  const t = data.topic;
  const related = (data.related || [])
    .map((r) => `<button type="button" class="rel" data-id="${r.topic_id}">${escapeHtml(r.topic)}</button>`)
    .join(" ");
  detailEl.innerHTML = `
    <h2>${escapeHtml(t.topic)}</h2>
    <p class="meta">${escapeHtml(t.supporting_source_reference)}</p>
    <p>Provenance: <span class="${prov.ok ? "ok" : "bad"}">${prov.ok ? "verified" : "issues"}</span>
      · ${prov.line_count} source lines · ${prov.source_ids_resolved} source IDs resolved</p>
    <h3>Supporting evidence</h3>
    <div class="evidence">${escapeHtml(t.supporting_evidence)}</div>
    <h3>Source IDs</h3>
    <p class="muted">${(t.source_ids || []).slice(0, 40).join(", ")}${(t.source_ids || []).length > 40 ? " …" : ""}</p>
    ${related ? "<h3>Related spans</h3><p>" + related + "</p>" : ""}
    <h3>Exact source testimony</h3>
    ${data.source_lines
      .map(
        (ln) => `<div class="line"><span class="sid">${ln.source_id}</span>
        <strong>${escapeHtml(ln.speaker)}</strong> ${escapeHtml(ln.text)}</div>`
      )
      .join("")}
  `;
  detailEl.querySelectorAll(".rel").forEach((b) => b.addEventListener("click", () => openTopic(b.dataset.id)));
}

async function semanticSearch() {
  const q = semanticEl.value.trim();
  if (!q) return;
  const data = await fetch("/api/search?q=" + encodeURIComponent(q)).then((r) => r.json());
  allTopics = data.results;
  renderList();
  if (allTopics[0]) openTopic(allTopics[0].topic_id);
}

function escapeHtml(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

filterEl.addEventListener("input", () => loadTopics());
hideProcEl.addEventListener("change", () => loadTopics());
document.getElementById("semanticBtn").addEventListener("click", semanticSearch);
semanticEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") semanticSearch();
});
loadStats();
loadTopics();
