/* Progressive-disclosure planning UI. Schema mechanics stay hidden by default;
   the planning surface explains why an investigation was selected and can launch it. */
(() => {
  const style = document.createElement('style');
  style.textContent = `.agent-plan{padding:22px;margin-top:0;background:#fbfaf7}.agent-plan-head{display:flex;justify-content:space-between;gap:24px;align-items:flex-start}.agent-plan-head h3{font-size:21px;margin:4px 0 5px;letter-spacing:-.02em}.agent-plan-head p{font-size:11px;color:#697873;margin:0;max-width:720px}.agent-mode{font-size:8px;text-transform:uppercase;letter-spacing:.09em;border:1px solid #bdc9c2;padding:6px 8px;color:#536760;white-space:nowrap}.agent-primary-label{font-size:8px;text-transform:uppercase;letter-spacing:.12em;font-weight:850;color:#6a7972;margin:20px 0 7px}.agent-plan-card{border:1px solid #d9ddd8;padding:17px;margin:9px 0;background:#f7f7f3;transition:border-color .15s,transform .15s}.agent-plan-card:hover{border-color:#9aaca4;transform:translateY(-1px)}.agent-plan-card.primary-plan{background:#fff;border-left:3px solid #285650}.plan-meta{display:flex;gap:10px;align-items:center;font-size:8px;text-transform:uppercase;letter-spacing:.07em;color:#77847e}.priority{font-weight:850}.priority.high{color:#285650}.priority.medium{color:#536760}.priority.low{color:#7d8984}.agent-plan-card h3{font-size:15px;margin:7px 0 4px}.plan-question{font-weight:700!important;color:#304441!important}.agent-plan-card p{font-size:10px;color:#6a7771;margin:5px 0}.plan-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:12px}.plan-steps span{border-top:1px solid #dfe3de;padding-top:7px;font-size:9px;color:#68766f}.plan-steps b{display:inline-grid;place-items:center;width:17px;height:17px;border:1px solid #c8d1cb;border-radius:50%;font-size:8px;margin-right:5px}.plan-run{margin-top:13px}.agent-plan-details{border-top:1px solid #e0e3de;margin-top:13px;padding-top:10px}.agent-plan-details summary{cursor:pointer;font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:#5e6d66}.agent-plan-details p{font-size:10px;color:#738078;max-width:800px}.agent-plan-loading,.agent-plan-error,.agent-plan-empty{display:flex;flex-direction:column;gap:5px;font-size:11px;color:#64736d}.agent-plan-error{color:#7b4a4a}.agent-plan-error small{color:#7a8781}@media(max-width:720px){.agent-plan-head{flex-direction:column}.plan-steps{grid-template-columns:1fr 1fr}.agent-mode{align-self:flex-start}}@media(max-width:560px){.plan-steps{grid-template-columns:1fr}.agent-plan-card{padding:14px}}`;
  document.head.appendChild(style);

  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    const request = args[0];
    const url = typeof request === 'string' ? request : request?.url || '';
    const method = typeof request === 'string' ? (args[1]?.method || 'GET') : (request?.method || args[1]?.method || 'GET');
    if (method.toUpperCase() === 'POST' && /\/api\/datasets\/[^/]+\/schema$/.test(url)) {
      const match = url.match(/\/api\/datasets\/([^/]+)\/schema$/);
      if (match) loadPlan(match[1]);
    }
    return response;
  };

  async function loadPlan(datasetId) {
    const host = document.querySelector('#agent-plan');
    if (!host) return;
    host.innerHTML = '<div class="agent-plan-loading"><span class="spinner"></span> The planning agent is assessing validated analytical opportunities…</div>';
    try {
      const response = await originalFetch(`/api/datasets/${encodeURIComponent(datasetId)}/plan`);
      const plan = await response.json();
      if (!response.ok) throw new Error(plan.detail || 'Planning unavailable');
      render(host, plan);
    } catch (error) {
      host.innerHTML = `<div class="agent-plan-error"><b>Planning agent unavailable.</b><span>${escapeHtml(error.message)}</span><small>The validated capability map remains available below.</small></div>`;
    }
  }

  function render(host, plan) {
    if (!plan.plans?.length) {
      host.innerHTML = '<div class="agent-plan-empty"><b>No investigation is currently feasible.</b><span>The confirmed schema and dataset-size safeguards did not establish a supported analytical objective.</span></div>';
      return;
    }
    const cards = plan.plans.map((item, index) => `
      <article class="agent-plan-card ${index === 0 ? 'primary-plan' : ''}">
        <div class="plan-meta"><span class="priority ${escapeHtml(item.priority).toLowerCase()}">${escapeHtml(item.priority)} PRIORITY</span><span>${escapeHtml(item.method)}</span></div>
        <h3>${escapeHtml(item.title)}</h3>
        <p class="plan-question">${escapeHtml(item.question)}</p>
        <p>${escapeHtml(item.agent_reason || item.reasons?.join(' ') || 'Selected from validated analytical capabilities.')}</p>
        <div class="plan-steps">${(item.steps || []).map((step, i) => `<span><b>${i + 1}</b>${escapeHtml(step)}</span>`).join('')}</div>
        <div class="plan-run"><button class="secondary agent-plan-run" data-objective="${escapeHtml(item.objective)}">Explore this investigation →</button></div>
      </article>`).join('');
    host.innerHTML = `
      <div class="agent-plan-head"><div><div class="section-kicker">ANALYTICAL PLANNER</div><h3>The workspace found useful questions before asking you to choose a model.</h3><p>Only validated objectives are supplied to the planner. The planner orders them, explains the reasoning, and hands execution to deterministic analytical tools.</p></div><span class="agent-mode">${escapeHtml((plan.mode || 'planner').replaceAll('_', ' '))}</span></div>
      <div class="agent-primary-label">Recommended investigations</div>
      ${cards}
      <details class="agent-plan-details"><summary>How the planner is constrained</summary><p>The planner cannot invent a target, alter a canonical field, or call arbitrary tools. It receives feasible candidates from the deterministic capability layer and may only rank those candidates when a local LLM is enabled.</p><p>Planning mode: <b>${escapeHtml(plan.mode || 'guardrailed')}</b></p></details>`;

    host.querySelectorAll('.agent-plan-run').forEach(button => {
      button.addEventListener('click', () => {
        const objective = button.dataset.objective;
        const target = document.querySelector(`.ml-button[data-objective="${CSS.escape(objective)}"]`);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'center' });
          target.click();
        } else {
          const status = document.querySelector('#ml-status');
          if (status) status.textContent = `The execution control for ${objective.replaceAll('_', ' ')} is not currently available.`;
        }
      });
    });
  }
})();
