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
    queue: source.queue.map(job => ({ ...job })),
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

  function renderMetrics() {
    const successful = state.queue.filter(x => x.state === "SUCCEEDED").length;
    const active = state.queue.filter(x => ["RUNNING","READY","RETRY_WAIT","PAUSED"].includes(x.state)).length;
    const eligible = source.providers.filter(x => x.eligibility === "ELIGIBLE").length;
    $("#global-metrics").innerHTML = `
      <div class="metric"><strong>${state.batchIntent ? state.batchIntent.semantic_asset_count : 0}</strong><span>batch semantic</span></div>
      <div class="metric"><strong>${active}</strong><span>active synthetic</span></div>
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
        <article class="card editor-card"><div class="result-head"><h2>Batch Intent</h2><span class="badge warn">NO DISPATCH</span></div>
          <div class="editor-grid"><label class="span-2">Label<input id="batch-label" value="Shopping bag ${esc(state.selectedAssetType.toLowerCase())} batch"></label><label>Quantity<input id="batch-quantity" type="number" min="1" max="1000" value="12"></label><label>Compiled blueprint<input value="${esc(plan ? plan.blueprint_id : 'Compile required')}" disabled></label></div>
          <div class="button-row"><button class="primary-btn" id="create-batch-intent" ${preview?'':'disabled'}>Create Batch Intent</button><button class="action-btn" disabled>Live Dispatch Locked</button></div>
          <p class="notice">Batch intent is local and bounded. It separates semantic asset quantity from packaging derivative count and never calls a provider.</p>
        </article>
        <article class="card"><h2>Intent Preview</h2>${state.batchIntent ? `<dl class="kv"><dt>Batch ID</dt><dd>${esc(state.batchIntent.batch_id)}</dd><dt>Semantic assets</dt><dd>${state.batchIntent.semantic_asset_count}</dd><dt>Packaging derivatives</dt><dd>${state.batchIntent.packaging_derivative_count}</dd><dt>Semantic fingerprint</dt><dd>${esc(state.batchIntent.semantic_fingerprint)}</dd><dt>Packaging fingerprint</dt><dd>${esc(state.batchIntent.packaging_fingerprint)}</dd><dt>Authority</dt><dd>${badge(state.batchIntent.dispatch_authority)}</dd></dl>` : `<p class="muted">${preview ? 'Ready to create a local batch intent.' : 'Compile a Blueprint first.'}</p>`}</article>
      </div>`;
    if ($("#create-batch-intent") && preview) $("#create-batch-intent").addEventListener('click', async () => {
      const payload = { compile_preview: preview, quantity: Number($("#batch-quantity").value), label: $("#batch-label").value.trim(), ui_constraints: state.uiConstraints };
      try { state.batchIntent = await postLocal('/api/batch-intent', payload); state.notice = 'Batch intent created locally. No provider dispatch occurred.'; } catch(error) { state.notice = `${error.code || 'ERROR'}: ${error.message || 'Batch intent rejected'}`; }
      renderBatch(); renderMetrics();
    });
  }

  function nextAction(job) { if (job.state === "RUNNING") return ["Pause", "PAUSE"]; if (job.state === "PAUSED") return ["Resume", "RESUME"]; if (job.state === "RETRY_WAIT") return ["Retry", "RETRY"]; return ["—", "NONE"]; }
  function renderQueue() {
    $("#view-queue").innerHTML = `<article class="card"><h2>Queue <span class="badge violet">SYNTHETIC</span></h2><table><thead><tr><th>Job</th><th>Provider</th><th>State</th><th>Attempt</th><th>Progress</th><th>Failure</th><th>Action</th></tr></thead><tbody>${state.queue.map((j,i) => { const [label,action]=nextAction(j); return `<tr><td><strong>${esc(j.jobId)}</strong><br><span class="muted">${esc(j.semanticAssetId)}</span></td><td>${esc(j.provider)}</td><td>${badge(j.state)}</td><td>${j.attempt}</td><td><div class="progress"><span style="width:${j.progress}%"></span></div></td><td>${esc(j.failureCode || '—')}</td><td><button class="action-btn" data-queue-index="${i}" data-action="${action}" ${action==='NONE'?'disabled':''}>${label}</button></td></tr>`; }).join("")}</tbody></table></article>`;
    $$('[data-queue-index]').forEach(button => button.addEventListener('click', () => { const job=state.queue[Number(button.dataset.queueIndex)]; if(button.dataset.action==='PAUSE')job.state='PAUSED'; if(button.dataset.action==='RESUME')job.state='RUNNING'; if(button.dataset.action==='RETRY'){job.state='READY';job.failureCode=null;job.progress=0;job.attempt+=1;} renderQueue();renderMetrics(); }));
  }
  function renderProviders() { $("#view-providers").innerHTML = `<div class="provider-grid">${source.providers.map(p => `<article class="provider-card"><header><h3>${esc(p.id.toUpperCase())}</h3>${badge(p.eligibility)}</header><dl class="kv"><dt>Transport</dt><dd>${esc(p.transport)}</dd><dt>Capacity</dt><dd>${badge(p.capacity)}</dd><dt>Policy</dt><dd>${badge(p.policy)}</dd><dt>Evidence</dt><dd>${esc(p.lastEvidence)}</dd></dl><p>${esc(p.routing)}</p></article>`).join("")}</div>`; }
  function renderOutput() { $("#view-output").innerHTML = `<div class="output-grid">${source.outputs.map(o => `<article class="card"><div class="master-preview"><div class="master-glyph"></div></div><div class="result-head"><div><span class="badge violet">${esc(o.assetType)}</span><h3>${esc(o.subject)}</h3></div><span class="badge good">SEMANTIC COUNT ${o.semanticCount}</span></div><dl class="kv"><dt>Semantic ID</dt><dd>${esc(o.semanticAssetId)}</dd><dt>Master</dt><dd>${esc(o.master.format)} · ${esc(o.master.dimensions)}</dd><dt>QA</dt><dd>${badge(o.qa)}</dd><dt>Compatibility</dt><dd>${badge(o.compatibility)}</dd></dl><div class="derivatives">${o.derivatives.map(d => `<div class="derivative"><span>${esc(d.format)} · ${esc(d.purpose)}</span><span>${esc(d.sha256)}</span></div>`).join("")}</div></article>`).join("")}</div>`; }
  function activateView(view) { state.activeView=view; $$('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view===view)); $$('[data-view-panel]').forEach(x=>x.classList.toggle('active',x.dataset.viewPanel===view)); $('#view-title').textContent=view.charAt(0).toUpperCase()+view.slice(1); }
  $$('.nav-item').forEach(button=>button.addEventListener('click',()=>activateView(button.dataset.view)));
  renderMetrics();renderBlueprint();renderBatch();renderQueue();renderProviders();renderOutput();activateView('blueprint');
})();
