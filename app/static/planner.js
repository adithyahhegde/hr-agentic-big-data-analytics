/* Progressive-disclosure planning UI. The main app keeps schema mechanics
   separate; this layer presents the planning agent after schema confirmation. */
(() => {
  const style = document.createElement('style');
  style.textContent = `.schema-details{padding:0;overflow:hidden}.schema-details summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;gap:15px;align-items:center;padding:16px 18px;font-size:12px}.schema-details summary::-webkit-details-marker{display:none}.schema-details summary span{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#74818b}.schema-details[open] summary{border-bottom:1px solid #e2e6ea}.agent-plan{padding:20px;margin-top:0}.agent-plan-head{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}.agent-plan-head h3{font-size:18px;margin:5px 0}.agent-plan-head p{font-size:11px;color:#697782;margin:0;max-width:650px}.agent-mode{font-size:9px;text-transform:uppercase;letter-spacing:.08em;border:1px solid #cbd3d9;padding:6px 8px;color:#61707b;white-space:nowrap}.agent-primary-label{font-size:9px;text-transform:uppercase;letter-spacing:.1em;font-weight:800;color:#64737e;margin:18px 0 7px}.agent-plan-card{border:1px solid #d9dfe4;padding:15px;margin:8px 0;background:#fafbfb}.agent-plan-card.primary-plan{border-left:3px solid #263641;background:#fff}.plan-meta{display:flex;gap:10px;align-items:center;font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:#78858f}.priority{font-weight:800}.priority.high{color:#263641}.priority.medium{color:#536371}.priority.low{color:#7c8993}.agent-plan-card h3{font-size:14px;margin:7px 0 4px}.plan-question{font-weight:650!important;color:#33434e!important}.agent-plan-card p{font-size:11px;color:#697782;margin:5px 0}.plan-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:11px}.plan-steps span{border-top:1px solid #dfe4e8;padding-top:7px;font-size:10px;color:#65737e}.plan-steps b{display:inline-grid;place-items:center;width:17px;height:17px;border:1px solid #cbd3d9;border-radius:50%;font-size:8px;margin-right:5px}.agent-plan-details{border-top:1px solid #e2e6ea;margin-top:12px;padding-top:10px}.agent-plan-details summary{cursor:pointer;font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:#5e6d78}.agent-plan-details p{font-size:10px;color:#73808a;max-width:800px}.agent-plan-loading,.agent-plan-error,.agent-plan-empty{display:flex;flex-direction:column;gap:5px;font-size:11px;color:#64727d}.agent-plan-error{color:#7b4a4a}.agent-plan-error small{color:#7a8791}.spinner{display:inline-block;width:12px;height:12px;border:2px solid #d0d7dc;border-top-color:#263641;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:7px}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:720px){.agent-plan-head{flex-direction:column}.plan-steps{grid-template-columns:1fr 1fr}.agent-mode{align-self:flex-start}}@media(max-width:560px){.plan-steps{grid-template-columns:1fr}}`;
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
