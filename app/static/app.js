const form = document.querySelector('#upload-form');
const status = document.querySelector('#status');
const canonicalFields = ['unknown', 'employee_id', 'department', 'job_role', 'age', 'tenure_years', 'salary', 'performance_rating', 'attrition', 'overtime'];
let latestProfile;

function optionLabel(field) { return field === 'unknown' ? 'Unknown / do not map' : field.replaceAll('_', ' '); }

function createMetricCard(label, value, subtext = '') {
  const card = document.createElement('div');
  card.className = 'metric-card';
  const valElem = document.createElement('div');
  valElem.className = 'metric-value';
  valElem.textContent = value;
  const lblElem = document.createElement('div');
  lblElem.className = 'metric-label';
  lblElem.textContent = label;
  card.append(valElem, lblElem);
  if (subtext) {
    const subElem = document.createElement('div');
    subElem.className = 'metric-subtext';
    subElem.textContent = subtext;
    card.append(subElem);
  }
  return card;
}

function renderProfile(data) {
  const summary = document.querySelector('#summary');
  summary.replaceChildren(
    createMetricCard('Total Rows', data.row_count.toLocaleString()),
    createMetricCard('Columns', data.column_count.toLocaleString()),
    createMetricCard('Duplicate Rows', data.duplicate_row_count.toLocaleString(), `${((data.duplicate_row_count / (data.row_count || 1)) * 100).toFixed(1)}% of rows`)
  );

  if (data.data_quality) {
    const dq = data.data_quality;
    const dqMetrics = document.querySelector('#dq-metrics');
    dqMetrics.replaceChildren(
      createMetricCard('Health Score', `${dq.health_score} / 100`, dq.health_score >= 80 ? 'Good quality' : dq.health_score >= 50 ? 'Moderate quality' : 'Requires attention'),
      createMetricCard('Completeness', `${(dq.metrics.completeness_rate * 100).toFixed(1)}%`, `${dq.metrics.missing_cells.toLocaleString()} missing cells`),
      createMetricCard('Clean Rows', `${(dq.metrics.clean_row_rate * 100).toFixed(1)}%`, `${dq.metrics.clean_row_count.toLocaleString()} fully populated`),
      createMetricCard('Constant Columns', String(dq.metrics.constant_column_count), dq.metrics.constant_column_count > 0 ? 'Zero/near-zero variance' : 'No degenerate columns')
    );

    document.querySelector('#dq-rule-count').textContent = String(dq.rules.length);
    const rulesBody = document.querySelector('#dq-rules-rows');
    rulesBody.replaceChildren();
    dq.rules.forEach((rule) => {
      const row = document.createElement('tr');
      const nameCell = document.createElement('td');
      nameCell.textContent = rule.rule_name.replaceAll('_', ' ');
      const catCell = document.createElement('td');
      catCell.textContent = rule.category;
      const statusCell = document.createElement('td');
      statusCell.textContent = `${rule.status} (${rule.severity})`;
      statusCell.className = `rule-status-${rule.status.toLowerCase()}`;
      const msgCell = document.createElement('td');
      msgCell.textContent = rule.message;
      row.append(nameCell, catCell, statusCell, msgCell);
      rulesBody.append(row);
    });
  }

  const candidates = Object.values(data.mappings);
  const automatic = candidates.filter((candidate) => candidate.decision === 'AUTO_MAPPED').length;
  const unclear = candidates.filter((candidate) => candidate.decision === 'UNMAPPED').length;
  const conflicts = candidates.filter((candidate) => candidate.decision === 'NEEDS_REVIEW').length;
  document.querySelector('#mapping-summary').textContent = `${automatic} fields mapped automatically · ${unclear} left unknown · ${conflicts} conflict${conflicts === 1 ? '' : 's'}`;

  const body = document.querySelector('#rows');
  body.replaceChildren();
  data.columns.forEach((column) => {
    const candidate = data.mappings[column.source_name];
    const row = document.createElement('tr');

    let statSummary = column.sample_values.slice(0, 3).join(', ');
    if (column.numeric_stats) {
      statSummary = `min: ${column.numeric_stats.min}, max: ${column.numeric_stats.max}, mean: ${column.numeric_stats.mean}`;
    }

    const missingStr = `${(column.missing_percentage * 100).toFixed(1)}% (${column.null_count})`;

    [column.source_name, column.inferred_type, missingStr, statSummary].forEach((value) => {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.append(cell);
    });

    const mappingCell = document.createElement('td');
    const select = document.createElement('select');
    select.dataset.source = column.source_name;
    select.setAttribute('aria-label', `Mapping for ${column.source_name}`);
    canonicalFields.forEach((field) => {
      const option = document.createElement('option');
      option.value = field;
      option.textContent = optionLabel(field);
      option.selected = field === candidate.canonical_field;
      select.append(option);
    });
    mappingCell.append(select);
    row.append(mappingCell);

    const evidenceCell = document.createElement('td');
    evidenceCell.textContent = `${candidate.decision}: ${candidate.evidence.join(', ')}`;
    row.append(evidenceCell);
    body.append(row);
  });

  const issues = document.querySelector('#issues');
  issues.replaceChildren();
  (data.issues.length ? data.issues : [{severity: 'INFO', message: 'No profile warnings.'}]).forEach((issue) => {
    const item = document.createElement('li');
    item.textContent = `${issue.severity}: ${issue.message}`;
    issues.append(item);
  });
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  status.textContent = 'Validating and profiling the selected file…';
  const response = await fetch('/api/datasets/profile', { method: 'POST', body: new FormData(form) });
  const result = document.querySelector('#result');
  if (!response.ok) {
    const body = await response.json();
    status.textContent = body.detail || 'The file could not be processed.';
    result.hidden = true;
    return;
  }
  latestProfile = await response.json();
  status.textContent = 'Profile completed. You can continue with safe mappings or review them.';
  result.hidden = false;
  document.querySelector('#capabilities').hidden = true;
  document.querySelector('#mapping-review').open = false;
  renderProfile(latestProfile);
});

async function submitMappings(mappings) {
  if (!latestProfile) return;
  const schemaStatus = document.querySelector('#schema-status');
  schemaStatus.textContent = 'Checking confirmed mappings…';
  const response = await fetch(`/api/datasets/${latestProfile.dataset_id}/schema`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mappings})
  });
  const data = await response.json();
  if (!response.ok) {
    schemaStatus.textContent = data.detail || 'The mappings need review.';
    return;
  }
  schemaStatus.textContent = 'Mappings confirmed for this temporary session.';
  document.querySelector('#capabilities').hidden = false;
  const list = document.querySelector('#capability-list');
  list.replaceChildren();
  data.capabilities.forEach((capability) => {
    const item = document.createElement('li');
    item.textContent = `${capability.objective}: ${capability.status} — ${capability.reasons.join(' ')}`;
    list.append(item);
  });
}

document.querySelector('#continue-mappings').addEventListener('click', () => {
  if (!latestProfile) return;
  submitMappings(Object.fromEntries(Object.entries(latestProfile.mappings).map(([source, candidate]) => [source, candidate.canonical_field])));
});

document.querySelector('#review-mappings').addEventListener('click', () => {
  document.querySelector('#mapping-review').open = true;
  document.querySelector('#mapping-review').scrollIntoView({behavior: 'smooth'});
});

document.querySelector('#accept-mappings').addEventListener('click', () => {
  submitMappings(Object.fromEntries([...document.querySelectorAll('#rows select')].map((select) => [select.dataset.source, select.value])));
});

