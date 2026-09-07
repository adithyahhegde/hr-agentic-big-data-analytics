/* Progressive-disclosure planning UI. The main app keeps schema mechanics
   separate; this layer presents the planning agent after schema confirmation. */
(() => {
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
      host.innerHTML = `<div class="agent-plan-error"><b>Planning agent unavailable.</b><span>${escapeHtml(error.message)}</span><small>The deterministic analysis controls remain available below.</small></div>`;
    }
  }

  function render(host, plan) {
    if (!plan.plans?.length) {
      host.innerHTML = '<div class="agent-plan-empty"><b>No investigation is currently feasible.</b><span>The confirmed schema and dataset-size safeguards did not establish a supported analytical objective.</span></div>';
      return;
    }
    const primary = plan.plans[0];
    const cards = plan.plans.map((item, index) => `
      <article class="agent-plan-card ${index === 0 ? 'primary-plan' : ''}">
        <div class="plan-meta"><span class="priority ${escapeHtml(item.priority).toLowerCase()}">${escapeHtml(item.priority)} PRIORITY</span><span>${escapeHtml(item.method)}</span></div>
        <h3>${escapeHtml(item.title)}</h3>
        <p class="plan-question">${escapeHtml(item.question)}</p>
        <p>${escapeHtml(item.agent_reason || item.reasons?.join(' ') || 'Selected from validated analytical capabilities.')}</p>
        <div class="plan-steps">${(item.steps || []).map((step, i) => `<span><b>${i + 1}</b>${escapeHtml(step)}</span>`).join('')}</div>
      </article>`).join('');
    host.innerHTML = `
      <div class="agent-plan-head"><div><div class="section-kicker">AGENT / ANALYTICAL PLANNING</div><h3>Recommended investigation</h3><p>The agent selected from feasible capabilities only. It cannot invent targets or unsupported analyses.</p></div><span class="agent-mode">${escapeHtml(plan.mode.replaceAll('_', ' '))}</span></div>
      <div class="agent-primary-label">Start here</div>
      ${cards}
      <details class="agent-plan-details"><summary>Why this plan?</summary><p>The plan is grounded in the confirmed schema and deterministic feasibility gates. The execution layer still chooses and validates suitable model candidates; the planner does not bypass those safeguards.</p><p>Primary objective: <b>${escapeHtml(primary.title)}</b></p></details>`;
  }
})();
