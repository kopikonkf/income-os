(() => {
  "use strict";
  const source = window.FactoryConsoleSyntheticData;
  const state = { activeView: "blueprint", queue: source.queue.map(job => ({ ...job })), notice: "Synthetic controls do not dispatch live work." };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const badgeTone = value => {
    const good = ["VALID","PASS","COMPATIBLE","AVAILABLE","ELIGIBLE","SUCCEEDED","RUNNING","READY","ALLOWED_EVIDENCED"];
    const warn = ["CONSTRAINED","RETRY_WAIT","PAUSED","UNKNOWN","DEFERRED_OPTIONAL"];
    const bad = ["FAILED","BLOCKED","UNAVAILABLE","POLICY_BLOCKED","AUTH_REQUIRED","INCOMPATIBLE"];
    if (good.includes(value)) return "good";
    if (warn.includes(value)) return "warn";
    if (bad.includes(value)) return "bad";
    return "violet";
  };
  const badge = value => `<span class="badge ${badgeTone(value)}">${value}</span>`;

  function renderMetrics() {
    const successful = state.queue.filter(x => x.state === "SUCCEEDED").length;
    const active = state.queue.filter(x => ["RUNNING","READY","RETRY_WAIT","PAUSED"].includes(x.state)).length;
    const eligible = source.providers.filter(x => x.eligibility === "ELIGIBLE").length;
    $("#global-metrics").innerHTML = `
      <div class="metric"><strong>${source.batch.semanticCount}</strong><span>semantic target</span></div>
      <div class="metric"><strong>${active}</strong><span>active jobs</span></div>
      <div class="metric"><strong>${successful}</strong><span>succeeded</span></div>
      <div class="metric"><strong>${eligible}</strong><span>eligible providers</span></div>`;
  }

  function renderBlueprint() {
    const b = source.blueprint;
    $("#view-blueprint").innerHTML = `
      <div class="grid two">
        <article class="card">
          <h2>Semantic Blueprint</h2>
          <dl class="kv">
            <dt>Blueprint</dt><dd>${b.blueprintId}</dd>
            <dt>Semantic asset</dt><dd>${b.semanticAssetId}</dd>
            <dt>Use case</dt><dd>${b.commercialUseCase}</dd>
            <dt>Subject</dt><dd>${b.subject}</dd>
            <dt>Compile</dt><dd>${badge(b.compileState)}</dd>
          </dl>
        </article>
        <article class="card">
          <h2>Native production plan</h2>
          <dl class="kv">
            <dt>Asset type</dt><dd>${b.assetType}</dd>
            <dt>Producer</dt><dd>${b.producer}</dd>
            <dt>Representation</dt><dd>${b.nativeRepresentation}</dd>
            <dt>Master</dt><dd>${b.master}</dd>
            <dt>Delivery</dt><dd>${b.delivery.join(" · ")}</dd>
          </dl>
        </article>
      </div>
      <article class="card" style="margin-top:16px">
        <h2>Asset Type Registry</h2>
        <div class="asset-types">${source.assetTypes.map(x => `<div class="asset-type ${x.id===b.assetType?'active':''}"><strong>${x.id}</strong><span>${x.family} · ${x.producer}</span></div>`).join("")}</div>
      </article>
      <article class="card" style="margin-top:16px">
        <h2>Production constraints</h2>
        <div class="control-row">
          <div class="control"><label>Style preset</label><strong>${b.stylePreset}</strong></div>
          <div class="control"><label>Consistency</label><strong>${b.consistency}</strong></div>
          <div class="control"><label>Background</label><strong>${b.background}</strong></div>
        </div>
        <p class="notice" style="margin-top:14px">Preset, resolution and packaging changes are controls on production/package output. They do not mint a new semantic asset ID.</p>
      </article>`;
  }

  function renderBatch() {
    const b = source.batch;
    $("#view-batch").innerHTML = `
      <div class="grid two">
        <article class="card">
          <h2>Batch Intent</h2>
          <dl class="kv">
            <dt>Batch</dt><dd>${b.batchId}</dd><dt>Label</dt><dd>${b.label}</dd>
            <dt>Blueprint</dt><dd>${b.blueprintId}</dd><dt>Quantity</dt><dd>${b.quantity}</dd>
            <dt>Consistency</dt><dd>${b.consistencyPreset}</dd><dt>Authority</dt><dd>${badge(b.dispatchAuthority)}</dd>
          </dl>
        </article>
        <article class="card">
          <h2>Count truth</h2>
          <div class="count-split"><div class="count-box"><strong>${b.semanticCount}</strong><span>semantic assets</span></div><div class="count-box"><strong>${b.packagingDerivativeCount}</strong><span>packaging derivatives</span></div></div>
          <p class="notice" style="margin-top:14px">Derivatives are delivery representations, not additional commercial inventory.</p>
        </article>
      </div>
      <article class="card" style="margin-top:16px">
        <h2>Prototype actions</h2>
        <p class="muted">${state.notice}</p>
        <button class="action-btn" id="simulate-preview">Simulate queue preview</button>
        <button class="action-btn" disabled title="Live dispatch is not available in FA-C004">Live dispatch locked</button>
      </article>`;
    $("#simulate-preview").addEventListener("click", () => {
      state.notice = "SIMULATED: batch intent validated locally; no network or provider action occurred.";
      renderBatch();
    });
  }

  function nextAction(job) {
    if (job.state === "RUNNING") return ["Pause", "PAUSE"];
    if (job.state === "PAUSED") return ["Resume", "RESUME"];
    if (job.state === "RETRY_WAIT") return ["Retry", "RETRY"];
    return ["—", "NONE"];
  }

  function renderQueue() {
    $("#view-queue").innerHTML = `
      <article class="card">
        <h2>Queue <span class="badge violet">SIMULATED CONTROLS</span></h2>
        <table><thead><tr><th>Job</th><th>Provider</th><th>State</th><th>Attempt</th><th>Progress</th><th>Failure</th><th>Action</th></tr></thead>
        <tbody>${state.queue.map((j,i) => { const [label,action]=nextAction(j); return `<tr><td><strong>${j.jobId}</strong><br><span class="muted">${j.semanticAssetId}</span></td><td>${j.provider}</td><td>${badge(j.state)}</td><td>${j.attempt}</td><td><div class="progress"><span style="width:${j.progress}%"></span></div></td><td>${j.failureCode || '—'}</td><td><button class="action-btn" data-queue-index="${i}" data-action="${action}" ${action==='NONE'?'disabled':''}>${label}</button></td></tr>`; }).join("")}</tbody></table>
      </article>`;
    $$('[data-queue-index]').forEach(button => button.addEventListener('click', () => {
      const job = state.queue[Number(button.dataset.queueIndex)];
      if (button.dataset.action === 'PAUSE') job.state = 'PAUSED';
      if (button.dataset.action === 'RESUME') job.state = 'RUNNING';
      if (button.dataset.action === 'RETRY') { job.state = 'READY'; job.failureCode = null; job.progress = 0; job.attempt += 1; }
      renderQueue(); renderMetrics();
    }));
  }

  function renderProviders() {
    $("#view-providers").innerHTML = `<div class="provider-grid">${source.providers.map(p => `
      <article class="provider-card">
        <header><h3>${p.id.toUpperCase()}</h3>${badge(p.eligibility)}</header>
        <dl class="kv"><dt>Transport</dt><dd>${p.transport}</dd><dt>Capacity</dt><dd>${badge(p.capacity)}</dd><dt>Policy</dt><dd>${badge(p.policy)}</dd><dt>Evidence</dt><dd>${p.lastEvidence}</dd></dl>
        <p>${p.routing}</p>
      </article>`).join("")}</div>`;
  }

  function renderOutput() {
    $("#view-output").innerHTML = `<div class="output-grid">${source.outputs.map(o => `
      <article class="card">
        <div class="master-preview"><div class="master-glyph" aria-label="synthetic shopping bag preview"></div></div>
        <div style="display:flex;justify-content:space-between;gap:12px"><div><span class="badge violet">${o.assetType}</span><h3 style="margin-top:9px">${o.subject}</h3></div><span class="badge good">SEMANTIC COUNT ${o.semanticCount}</span></div>
        <dl class="kv"><dt>Semantic ID</dt><dd>${o.semanticAssetId}</dd><dt>Provider</dt><dd>${o.provider}</dd><dt>Master</dt><dd>${o.master.format} · ${o.master.dimensions}</dd><dt>Master hash</dt><dd>${o.master.sha256}</dd><dt>QA</dt><dd>${badge(o.qa)}</dd><dt>Compatibility</dt><dd>${badge(o.compatibility)}</dd></dl>
        <div class="derivatives">${o.derivatives.map(d => `<div class="derivative"><span>${d.format} · ${d.purpose}</span><span>${d.sha256}</span></div>`).join("")}</div>
      </article>`).join("")}</div>`;
  }

  function activateView(view) {
    state.activeView = view;
    $$('.nav-item').forEach(x => x.classList.toggle('active', x.dataset.view === view));
    $$('[data-view-panel]').forEach(x => x.classList.toggle('active', x.dataset.viewPanel === view));
    $('#view-title').textContent = view.charAt(0).toUpperCase() + view.slice(1);
  }

  $$('.nav-item').forEach(button => button.addEventListener('click', () => activateView(button.dataset.view)));
  renderMetrics(); renderBlueprint(); renderBatch(); renderQueue(); renderProviders(); renderOutput(); activateView('blueprint');
})();
