(() => {
  "use strict";
  const source = window.FactoryConsoleSyntheticData;
  const templates = window.FactoryBlueprintTemplates;
  const clone = value => JSON.parse(JSON.stringify(value));
  const state = {
    activeView: "blueprint",
    selectedAssetType: "ISOLATED_OBJECT",
    draft: clone(templates.ISOLATED_OBJECT),
    uiConstraints: { style_preset: "Clean Commerce Object v1", consistency_preset: "white-object-lighting-v1", background: "transparent" },
    compilePreview: null,
    compileError: null,
    batchIntent: null,
    queueEvents: [],
    queueError: null,
    providerDashboard: null,
    providerError: null,
    outputGallery: null,
    outputError: null,
    syntheticE2E: null,
    syntheticE2EError: null,
    notice: "Compile a Blueprint v2 before creating a batch intent."
  };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch]));
  const badgeTone = value => {
    const good = ["VALID","PASS","COMPATIBLE","AVAILABLE","ELIGIBLE","SUCCEEDED","RUNNING","READY","ALLOWED_EVIDENCED"];
    const warn = ["CONSTRAINED","RETRY_WAIT","PAUSED","UNKNOWN","DEFERRED_OPTIONAL","SIMULATED_ONLY"];
    const bad = ["FAILED","BLOCKED","UNAVAILABLE","POLICY_BLOCKED","AUTH_REQUIRED","INCOMPATIBLE","INVALID"];
    if (good.includes(value)) return "good";
    if (warn.includes(value)) return "warn";
    if (bad.includes(value)) return "bad";
    return "violet";
  };
  const badge = value => `<span class="badge ${badgeTone(value)}">${esc(value)}</span>`;

  async function postLocal(path, payload) {
    const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const value = await response.json();
    if (!response.ok) throw value;
    return value;
  }
  async function getLocal(path) {
    const response = await fetch(path, { headers: { "Accept": "application/json" } });
    const value = await response.json();
    if (!response.ok) throw value;
    return value;
  }

  function renderMetrics() {
    const successful = state.queueEvents.filter(x => x.state === "SUCCEEDED").length;
    const active = state.queueEvents.filter(x => ["RUNNING","READY","RETRY_WAIT","PAUSED"].includes(x.state)).length;
    const eligible = state.providerDashboard ? state.providerDashboard.providers.filter(x => x.eligibility === "ELIGIBLE").length : 0;
    $("#global-metrics").innerHTML = `
      <div class="metric"><strong>${state.batchIntent ? state.batchIntent.semantic_asset_count : 0}</strong><span>batch semantic</span></div>
      <div class="metric"><strong>${active}</strong><span>core queue active</span></div>
      <div class="metric"><strong>${successful}</strong><span>succeeded</span></div>
      <div class="metric"><strong>${eligible}</strong><span>eligible providers</span></div>`;
  }

  function derivativeRows() {
    return state.draft.derivatives.map((d, index) => `
      <div class="editor-row derivative-editor">
        <input data-derivative-id="${index}" value="${esc(d.derivative_id)}" aria-label="Derivative id ${index}">
        <select data-derivative-purpose="${index}" aria-label="Derivative purpose ${index}">${["MARKETPLACE_DELIVERY","PREVIEW","THUMBNAIL","COMPATIBILITY_EXPORT"].map(x => `<option ${x===d.purpose?'selected':''}>${x}</option>`).join("")}</select>
        <select data-derivative-format="${index}" aria-label="Derivative format ${index}">${["PNG","JPEG","WEBP","TIFF","PDF","SVG","EPS","MP4","MOV"].map(x => `<option ${x===d.format?'selected':''}>${x}</option>`).join("")}</select>
      </div>`).join("");
  }

  function masterControls() {
    const m = state.draft.master_spec;
    const raster = state.draft.native_representation === "RASTER_PIXELS";
    const motion = state.draft.native_representation === "TIMED_FRAMES";
    return `
      <div class="editor-row">
        <label>Master format<select id="master-format">${["PNG","JPEG","TIFF","SVG","EPS","MP4","MOV"].map(x => `<option ${x===m.format?'selected':''}>${x}</option>`).join("")}</select></label>
        ${raster ? `<label>Width<input id="master-width" type="number" min="1" value="${m.width_px || 4096}"></label><label>Height<input id="master-height" type="number" min="1" value="${m.height_px || 4096}"></label>` : ''}
        ${motion ? `<label>Duration<input id="master-duration" type="number" min="0.1" step="0.1" value="${m.duration_seconds || 6}"></label><label>FPS<input id="master-fps" type="number" min="1" value="${m.fps || 30}"></label>` : ''}
      </div>`;
  }

  function collectEditor() {
    const b = clone(state.draft);
    b.semantic_identity.commercial_use_case = $("#commercial-use-case").value.trim();
    b.semantic_identity.subject = $("#subject").value.trim();
    b.master_spec.format = $("#master-format").value;
    if ($("#master-width")) b.master_spec.width_px = Number($("#master-width").value);
    if ($("#master-height")) b.master_spec.height_px = Number($("#master-height").value);
    if ($("#master-duration")) b.master_spec.duration_seconds = Number($("#master-duration").value);
    if ($("#master-fps")) b.master_spec.fps = Number($("#master-fps").value);
    b.derivatives = b.derivatives.map((d,i) => ({ ...d, derivative_id: $(`[data-derivative-id="${i}"]`).value.trim(), purpose: $(`[data-derivative-purpose="${i}"]`).value, format: $(`[data-derivative-format="${i}"]`).value, semantic_identity_effect: "NONE" }));
    state.uiConstraints = { style_preset: $("#style-preset").value.trim(), consistency_preset: $("#consistency-preset").value.trim(), background: $("#background").value.trim() };
    return b;
  }

  function compilePanel() {
    if (state.compileError) return `<div class="compile-result invalid"><strong>Compile rejected</strong><code>${esc(state.compileError.code)}</code><p>${esc(state.compileError.message || '')}</p></div>`;
    if (!state.compilePreview) return `<div class="compile-result"><strong>Not compiled</strong><p>Run canonical Blueprint v2 compile preview. No provider dispatch occurs.</p></div>`;
    const p = state.compilePreview.plan;
    return `<div class="compile-result valid"><div class="result-head"><strong>Canonical compile PASS</strong>${badge('VALID')}</div>
      <dl class="kv"><dt>Blueprint SHA</dt><dd>${esc(p.blueprint_sha256)}</dd><dt>Semantic fingerprint</dt><dd>${esc(state.compilePreview.semantic_fingerprint)}</dd><dt>Packaging fingerprint</dt><dd>${esc(state.compilePreview.packaging_fingerprint)}</dd><dt>Producer</dt><dd>${esc(p.producer.class)} / ${esc(p.producer.recipe_id)}</dd><dt>Master</dt><dd>${esc(p.master.format)}</dd><dt>Recipes</dt><dd>${p.derivatives.map(d => esc(d.recipe_id)).join(' · ')}</dd><dt>Registry/Profile</dt><dd>${esc(p.asset_type_registry_revision)} / ${esc(p.marketplace_delivery_profile_revision)}</dd><dt>Dispatch</dt><dd>${badge('SIMULATED_ONLY')}</dd></dl></div>`;
  }

  function renderBlueprint() {
    const b = state.draft;
    $("#view-blueprint").innerHTML = `
      <div class="grid two">
        <article class="card editor-card">
          <div class="result-head"><h2>Blueprint v2 Editor</h2><span class="badge violet">CANONICAL COMPILER</span></div>
          <div class="asset-types">${Object.keys(templates).map(type => `<button class="asset-type ${type===state.selectedAssetType?'active':''}" data-asset-type="${type}"><strong>${type}</strong><span>${templates[type].native_representation} · ${templates[type].producer_class}</span></button>`).join("")}</div>
          <div class="editor-grid" style="margin-top:16px">
            <label>Blueprint ID<input value="${esc(b.blueprint_id)}" disabled></label>
            <label>Semantic Asset ID<input value="${esc(b.semantic_identity.semantic_asset_id)}" disabled></label>
            <label class="span-2">Commercial use case<input id="commercial-use-case" value="${esc(b.semantic_identity.commercial_use_case)}"></label>
            <label class="span-2">Subject<input id="subject" value="${esc(b.semantic_identity.subject)}"></label>
          </div>
          <h3 style="margin-top:18px">Master</h3>${masterControls()}
          <h3 style="margin-top:18px">Delivery recipes</h3>${derivativeRows()}
          <h3 style="margin-top:18px">UI / batch constraints</h3>
          <div class="editor-row"><label>Style preset<input id="style-preset" value="${esc(state.uiConstraints.style_preset)}"></label><label>Consistency<input id="consistency-preset" value="${esc(state.uiConstraints.consistency_preset)}"></label><label>Background<input id="background" value="${esc(state.uiConstraints.background)}"></label></div>
          <div class="button-row"><button class="primary-btn" id="compile-blueprint">Compile Blueprint</button><button class="action-btn" id="reset-blueprint">Reset mode fixture</button></div>
          <p class="notice">Asset-type changes load a distinct canonical semantic fixture. Master format, resolution, delivery format, style and consistency are packaging/production controls and do not auto-mint a semantic ID.</p>
        </article>
        <article class="card"><h2>Compile Preview</h2>${compilePanel()}</article>
      </div>`;
    $$('[data-asset-type]').forEach(btn => btn.addEventListener('click', () => {
      state.selectedAssetType = btn.dataset.assetType;
      state.draft = clone(templates[state.selectedAssetType]);
      state.compilePreview = null; state.compileError = null; state.batchIntent = null;
      renderBlueprint(); renderBatch(); renderMetrics();
    }));
    $("#reset-blueprint").addEventListener('click', () => { state.draft = clone(templates[state.selectedAssetType]); state.compilePreview=null; state.compileError=null; state.batchIntent=null; renderBlueprint(); renderBatch(); renderMetrics(); });
    $("#compile-blueprint").addEventListener('click', async () => {
      const button = $("#compile-blueprint"); button.disabled = true; button.textContent = 'Compiling…';
      try {
        state.draft = collectEditor();
        state.compilePreview = await postLocal('/api/compile', { blueprint: state.draft, ui_constraints: state.uiConstraints });
        state.compileError = null; state.batchIntent = null;
      } catch (error) { state.compilePreview = null; state.compileError = error; state.batchIntent = null; }
      renderBlueprint(); renderBatch(); renderMetrics();
    });
  }

  function renderBatch() {
    const preview = state.compilePreview;
    const plan = preview && preview.plan;
    $("#view-batch").innerHTML = `
      <div class="grid two">
        <article class="card editor-card"><div class="result-head"><h2>Batch Intent</h2><span class="badge warn">CORE QUEUE ONLY</span></div>
          <div class="editor-grid"><label class="span-2">Label<input id="batch-label" value="Shopping bag ${esc(state.selectedAssetType.toLowerCase())} batch"></label><label>Quantity<input id="batch-quantity" type="number" min="1" max="1000" value="12"></label><label>Compiled blueprint<input value="${esc(plan ? plan.blueprint_id : 'Compile required')}" disabled></label></div>
          <div class="button-row"><button class="primary-btn" id="create-batch-intent" ${preview?'':'disabled'}>Create Batch Intent</button><button class="action-btn" id="queue-local-batch" ${state.batchIntent?'':'disabled'}>Queue Local Batch</button><button class="action-btn" disabled>Provider Dispatch Locked</button></div>
          <p class="notice">Queue Local Batch creates governed FA-105 jobs only. START owns a queue job; it does not call a provider in FA-C006.</p>
        </article>
        <article class="card"><h2>Intent Preview</h2>${state.batchIntent ? `<dl class="kv"><dt>Batch ID</dt><dd>${esc(state.batchIntent.batch_id)}</dd><dt>Semantic assets</dt><dd>${state.batchIntent.semantic_asset_count}</dd><dt>Packaging derivatives</dt><dd>${state.batchIntent.packaging_derivative_count}</dd><dt>Semantic fingerprint</dt><dd>${esc(state.batchIntent.semantic_fingerprint)}</dd><dt>Packaging fingerprint</dt><dd>${esc(state.batchIntent.packaging_fingerprint)}</dd><dt>Authority</dt><dd>${badge(state.batchIntent.dispatch_authority)}</dd></dl>` : `<p class="muted">${preview ? 'Ready to create a local batch intent.' : 'Compile a Blueprint first.'}</p>`}<p class="muted">${esc(state.notice)}</p></article>
      </div>`;
    if ($("#create-batch-intent") && preview) $("#create-batch-intent").addEventListener('click', async () => {
      const payload = { compile_preview: preview, quantity: Number($("#batch-quantity").value), label: $("#batch-label").value.trim(), ui_constraints: state.uiConstraints };
      try { state.batchIntent = await postLocal('/api/batch-intent', payload); state.notice = 'Batch intent created. Queue submission is available; provider dispatch remains locked.'; } catch(error) { state.notice = `${error.code || 'ERROR'}: ${error.message || 'Batch intent rejected'}`; }
      renderBatch(); renderMetrics();
    });
    if ($("#queue-local-batch") && state.batchIntent) $("#queue-local-batch").addEventListener('click', async () => {
      try { const result = await postLocal('/api/queue/submit', { batch_intent: state.batchIntent }); state.notice = `${result.created_or_reused} governed jobs created/reused. Provider dispatch: ${result.provider_dispatch_performed}.`; await refreshQueue(); activateView('queue'); }
      catch(error) { state.notice = `${error.code || 'ERROR'}: ${error.message || 'Queue submit rejected'}`; renderBatch(); }
    });
  }

  function actionsFor(job) {
    if (job.state === "READY") return [["Start","START"],["Cancel","CANCEL"]];
    if (job.state === "RUNNING") return [["Pause","PAUSE"],["Cancel","CANCEL"]];
    if (job.state === "PAUSED") return [["Resume","RESUME"],["Cancel","CANCEL"]];
    if (job.state === "RETRY_WAIT") return [["Retry","RETRY"],["Cancel","CANCEL"]];
    return [];
  }
  async function refreshQueue() {
    try { const value = await getLocal('/api/queue/jobs'); state.queueEvents = value.events; state.queueError = null; }
    catch(error) { state.queueError = `${error.code || 'ERROR'}: ${error.message || 'Queue unavailable'}`; }
    renderQueue(); renderMetrics();
  }
  async function queueAction(jobId, action) {
    const command = { schema:'die.factory-asset.console-api.v1', kind:'CONTROL_COMMAND', command_id:`FCCMD-${Date.now()}-${action}`, job_id:jobId, action };
    try { await postLocal('/api/queue/action', command); state.queueError = null; }
    catch(error) { state.queueError = `${error.code || 'ERROR'}: ${error.message || 'Control rejected'}`; }
    await refreshQueue();
  }
  async function runSyntheticE2E() {
    state.syntheticE2EError = null;
    try { state.syntheticE2E = await postLocal('/api/synthetic/e2e', { schema:'die.factory-asset.console-synthetic-e2e-request.v1' }); }
    catch(error) { state.syntheticE2E = null; state.syntheticE2EError = `${error.code || 'ERROR'}: ${error.message || 'Synthetic E2E failed'}`; }
    renderQueue();
  }
  function renderQueue() {
    const rows = state.queueEvents;
    const e2e=state.syntheticE2E;
    $("#view-queue").innerHTML = `
      <article class="card" style="margin-bottom:16px"><div class="result-head"><div><h2>Console → Factory Core Synthetic E2E</h2><p class="muted">Queue · routing/capacity · retry · crash recovery · output ingestion</p></div>${e2e ? badge(e2e.result) : badge('READY')}</div>
        <div class="button-row"><button class="primary-btn" id="run-synthetic-e2e">Run Synthetic E2E</button><button class="action-btn" disabled>Live Provider Calls Locked</button></div>
        ${state.syntheticE2EError ? `<p class="notice">${esc(state.syntheticE2EError)}</p>` : ''}
        ${e2e ? `<dl class="kv" style="margin-top:14px"><dt>Selected route</dt><dd>${esc(e2e.routing.selected_profile_id)} / ${esc(e2e.routing.selected_provider_id)}</dd><dt>Capacity</dt><dd>Qwen ${badge(e2e.routing.qwen_capacity)} · ChatGPT ${badge(e2e.routing.chatgpt_capacity)}</dd><dt>Retry flow</dt><dd>${badge(e2e.queue.retry_state)} → ${badge(e2e.queue.final_state)} · retries ${e2e.queue.retries}</dd><dt>Crash recovery</dt><dd>${badge(e2e.crash_recovery.state_after_restore)} · recovery ${e2e.crash_recovery.recovery_count}</dd><dt>Output SHA</dt><dd>${esc(e2e.output.master_sha256)}</dd><dt>Ingestion</dt><dd>${e2e.output.ingestion_attempt_count} attempts / ${e2e.output.unique_blob_count} blob · canonical=${e2e.output.canonical_truth}</dd><dt>Secret guard</dt><dd>${badge(e2e.secret_observability_blocked ? 'PASS':'FAIL')}</dd><dt>Zero false success</dt><dd>${badge(e2e.zero_false_success ? 'PASS':'FAIL')}</dd><dt>Provider calls</dt><dd>${e2e.provider_calls_performed ? badge('INVALID'):badge('NONE')}</dd></dl>` : `<p class="notice" style="margin-top:14px">This test is fully synthetic and ephemeral. It exercises Factory Core contracts without provider/browser/network generation.</p>`}
      </article>
      <article class="card"><div class="result-head"><h2>Factory Core Queue</h2><div><span class="badge good">FA-105 GOVERNED</span> <span class="badge warn">NO PROVIDER DISPATCH</span></div></div>
      ${state.queueError ? `<p class="notice">${esc(state.queueError)}</p>` : ''}
      <table><thead><tr><th>Job</th><th>Semantic / Blueprint</th><th>State</th><th>Attempts</th><th>Retries</th><th>Recovery</th><th>Failure</th><th>Controls</th></tr></thead><tbody>${rows.map(j => `<tr><td><strong>${esc(j.job_id)}</strong><br><span class="muted">${esc(j.label)}</span></td><td>${esc(j.semantic_asset_id)}<br><span class="muted">${esc(j.blueprint_id)}</span></td><td>${badge(j.state)}</td><td>${j.attempts}</td><td>${j.retries}/2</td><td>${j.recovery_count}</td><td>${esc(j.failure_code || '—')}</td><td>${actionsFor(j).map(([label,action]) => `<button class="action-btn queue-control" data-job-id="${esc(j.job_id)}" data-core-action="${action}">${label}</button>`).join(' ') || '—'}</td></tr>`).join("")}</tbody></table>
      <p class="notice" style="margin-top:14px">START acquires local queue ownership only. Provider routing/dispatch is intentionally not invoked by governed queue controls.</p></article>`;
    $$('.queue-control').forEach(button => button.addEventListener('click', () => queueAction(button.dataset.jobId, button.dataset.coreAction)));
    if ($('#run-synthetic-e2e')) $('#run-synthetic-e2e').addEventListener('click', runSyntheticE2E);
  }

  async function refreshProviders() {
    try { state.providerDashboard = await getLocal('/api/providers'); state.providerError = null; }
    catch(error) { state.providerError = `${error.code || 'ERROR'}: ${error.message || 'Provider dashboard unavailable'}`; }
    renderProviders(); renderMetrics();
  }
  function renderProviders() {
    const d = state.providerDashboard;
    const rows = d ? d.providers : [];
    $("#view-providers").innerHTML = `
      <article class="card" style="margin-bottom:16px"><div class="result-head"><div><h2>Provider Health / Capacity / Routing</h2><p class="muted">Core policy + capacity ledger + deterministic router</p></div>${d ? badge(d.evidence_mode) : badge('UNKNOWN')}</div>
        ${state.providerError ? `<p class="notice">${esc(state.providerError)}</p>` : ''}
        ${d ? `<dl class="kv"><dt>Evidence mode</dt><dd>${esc(d.evidence_mode)}</dd><dt>Observed at</dt><dd>${esc(d.observed_at)}</dd><dt>Route sample</dt><dd>${esc(d.route_asset_type)}</dd><dt>Selected profile</dt><dd>${esc(d.selected_profile_id || 'NONE')}</dd><dt>Guessed quota</dt><dd>${d.guessed_quota_present ? badge('INVALID') : badge('NONE')}</dd><dt>Provider dispatch</dt><dd>${d.provider_dispatch_performed ? badge('INVALID') : badge('LOCKED')}</dd></dl>` : '<p class="muted">Loading normalized provider state…</p>'}
        <p class="notice">Capacity shown here is deterministic observed fixture evidence, not live quota polling. Optional/deferred Grok cannot block healthy eligible routes.</p>
      </article>
      <div class="provider-grid">${rows.map(p => `<article class="provider-card"><header><h3>${esc(p.provider_id.toUpperCase())}</h3>${badge(p.eligibility)}</header><dl class="kv"><dt>Profile</dt><dd>${esc(p.profile_id)}</dd><dt>Health</dt><dd>${badge(p.health)}</dd><dt>Transport</dt><dd>${esc(p.transport)}</dd><dt>Capacity</dt><dd>${badge(p.capacity)}</dd><dt>Policy</dt><dd>${badge(p.policy)}</dd><dt>Evidence</dt><dd>${esc(p.last_evidence || 'UNKNOWN')}</dd><dt>Retry after</dt><dd>${p.retry_after_seconds == null ? '—' : esc(p.retry_after_seconds + 's')}</dd></dl><p>${esc(p.routing_reason)}</p></article>`).join("")}</div>`;
  }
  async function refreshOutputs() {
    try { state.outputGallery = await getLocal('/api/outputs'); state.outputError = null; }
    catch(error) { state.outputError = `${error.code || 'ERROR'}: ${error.message || 'Output gallery unavailable'}`; }
    renderOutput(); renderMetrics();
  }
  function renderOutput() {
    const d=state.outputGallery;
    const rows=d ? d.assets : [];
    $("#view-output").innerHTML = `
      <article class="card" style="margin-bottom:16px"><div class="result-head"><div><h2>Output / Lineage / QA</h2><p class="muted">Actual FA-029 five-master canary evidence + FA-106 ingestion staging</p></div>${d ? badge(d.evidence_mode) : badge('UNKNOWN')}</div>
        ${state.outputError ? `<p class="notice">${esc(state.outputError)}</p>` : ''}
        ${d ? `<div class="count-split"><div class="count-box"><strong>${d.semantic_asset_count}</strong><span>semantic assets</span></div><div class="count-box"><strong>${d.derivative_count}</strong><span>packaging derivatives</span></div></div><p class="notice" style="margin-top:14px">State Manager: ${esc(d.state_manager_status)} · canonical truth=${d.canonical_truth}. Derivatives never increase semantic asset count.</p>` : '<p class="muted">Loading output evidence…</p>'}
      </article>
      <div class="output-grid">${rows.map(o => `<article class="card"><div class="master-preview"><div class="master-glyph"></div></div><div class="result-head"><div><span class="badge violet">${esc(o.task_id)}</span><h3>${esc(o.seed_id)}</h3></div><span class="badge good">SEMANTIC COUNT ${o.semantic_count}</span></div>
        <dl class="kv"><dt>Semantic ID</dt><dd>${esc(o.semantic_asset_id)}</dd><dt>Blueprint</dt><dd>${esc(o.blueprint_id)}</dd><dt>Master</dt><dd>${esc(o.master.format)} · ${esc(o.master.dimensions.join('×'))}</dd><dt>Master SHA</dt><dd>${esc(o.master.sha256)}</dd><dt>Immutable</dt><dd>${badge(o.master.immutable ? 'PASS' : 'FAIL')}</dd><dt>Ingestion</dt><dd>${badge(o.master.ingestion_state)}</dd><dt>Package files</dt><dd>${o.package.unique_file_count}/${o.package.manifest_entry_count}</dd></dl>
        <div class="derivatives">${o.derivatives.map(x => `<div class="derivative" style="display:block"><div style="display:flex;justify-content:space-between;gap:10px"><span><strong>${esc(x.format)}</strong> · ${esc(x.purpose)}</span><span>${badge(x.qa_state)} ${badge(x.compatibility_state)}</span></div><div class="muted" style="margin-top:4px">${esc(x.recipe_id)} · ${esc(x.dimensions.join('×'))}</div><div class="muted" style="margin-top:3px;overflow-wrap:anywhere">${esc(x.sha256)}</div></div>`).join('')}</div>
        <details style="margin-top:12px"><summary>Lineage</summary><dl class="kv" style="margin-top:10px"><dt>Linux master</dt><dd>${esc(o.lineage.linux_master_path)}</dd><dt>Inventory</dt><dd>${esc(o.lineage.inventory_receipt)}</dd><dt>Canary</dt><dd>${esc(o.lineage.canary_receipt)}</dd><dt>Ingestion</dt><dd>${esc(o.lineage.ingestion_receipt)}</dd></dl></details>
      </article>`).join('')}</div>`;
  }

  function activateView(view) { state.activeView=view; $$('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view===view)); $$('[data-view-panel]').forEach(x=>x.classList.toggle('active',x.dataset.viewPanel===view)); $('#view-title').textContent=view.charAt(0).toUpperCase()+view.slice(1); if(view==='queue') refreshQueue(); if(view==='providers') refreshProviders(); if(view==='output') refreshOutputs(); }
  $$('.nav-item').forEach(button=>button.addEventListener('click',()=>activateView(button.dataset.view)));
  renderMetrics();renderBlueprint();renderBatch();renderQueue();renderProviders();renderOutput();activateView('blueprint');refreshQueue();refreshProviders();refreshOutputs();
})();
