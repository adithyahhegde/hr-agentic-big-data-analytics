(() => {
  const root = document.querySelector('#ml-actions');
  if (!root) return;

  const names = {
    attrition_classification: 'Run bounded AutoML',
    salary_regression: 'Run bounded AutoML',
  };

  function addButtons() {
    root.querySelectorAll('[data-objective]').forEach((source) => {
      const objective = source.dataset.objective;
      if (!names[objective] || root.querySelector(`[data-automl="${objective}"]`)) return;
      const button = document.createElement('button');
      button.className = 'secondary ml-button automl-button';
      button.dataset.automl = objective;
      button.textContent = `${names[objective]} · ${objective === 'attrition_classification' ? 'classification' : 'regression'} →`;
      button.addEventListener('click', () => run(objective, button));
      root.appendChild(button);
    });
  }

  async function run(objective, button) {
    button.disabled = true;
    button.textContent = 'AutoML searching…';
    const status = document.querySelector('#ml-status');
    if (status) status.textContent = 'Searching a bounded model space and evaluating the selected model on held-out evidence…';
    try {
      const result = await json(`/api/datasets/${latestProfile.dataset_id}/ml/${objective}/automl`, {method: 'POST'});
      mlResults[`automl:${objective}`] = result;
      const host = document.querySelector('#ml-results');
      const existing = document.querySelector(`[data-automl-result="${objective}"]`);
      if (existing) existing.remove();
      const block = document.createElement('div');
      block.className = 'model-block';
      block.dataset.automlResult = objective;
      const metrics = Object.entries(result.metrics || {}).map(([k, v]) => `<span class="feature-chip">${esc(k.replaceAll('_', ' '))}: ${esc(v)}</span>`).join('');
      block.innerHTML = `<h4>Bounded AutoML <small>${esc(result.selected_model)} · ${Number(result.rows_used).toLocaleString()} usable rows · ${Number(result.search?.time_budget_seconds || 0)}s budget</small></h4><div class="feature-list">${metrics}</div><p class="muted">Search space: ${esc((result.search?.estimators || []).join(', '))}. This is predictive evidence, not causal evidence or an automated employment decision.</p>`;
      host?.appendChild(block);
      if (status) status.textContent = `${result.selected_model} selected by bounded AutoML.`;
    } catch (error) {
      if (status) status.textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = `${names[objective]} · ${objective === 'attrition_classification' ? 'classification' : 'regression'} →`;
    }
  }

  const observer = new MutationObserver(addButtons);
  observer.observe(root, {childList: true, subtree: true});
  addButtons();
})();
