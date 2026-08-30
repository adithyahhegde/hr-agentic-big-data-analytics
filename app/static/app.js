const form = document.querySelector('#upload-form');
const status = document.querySelector('#status');
const canonicalFields = ['unknown', 'employee_id', 'department', 'job_role', 'age', 'tenure_years', 'salary', 'performance_rating', 'attrition', 'overtime'];
let latestProfile;

function optionLabel(field) { return field === 'unknown' ? 'Unknown / do not map' : field.replaceAll('_', ' '); }

function renderProfile(data) {
  document.querySelector('#summary').textContent = `${data.row_count} rows · ${data.column_count} columns · ${data.duplicate_row_count} duplicate rows`;
  const candidates = Object.values(data.mappings);
  const automatic = candidates.filter((candidate) => candidate.decision === 'AUTO_MAPPED').length;
  const unclear = candidates.filter((candidate) => candidate.decision === 'UNMAPPED').length;
  const conflicts = candidates.filter((candidate) => candidate.decision === 'NEEDS_REVIEW').length;
  document.querySelector('#mapping-summary').textContent = `${automatic} fields mapped automatically · ${unclear} left unknown · ${conflicts} conflict${conflicts === 1 ? '' : 's'}`;
  const body = document.querySelector('#rows'); body.replaceChildren();
  data.columns.forEach((column) => {
    const candidate = data.mappings[column.source_name];
    const row = document.createElement('tr');
    [column.source_name, column.inferred_type, String(column.null_count)].forEach((value) => { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); });
    const mappingCell = document.createElement('td'); const select = document.createElement('select'); select.dataset.source = column.source_name; select.setAttribute('aria-label', `Mapping for ${column.source_name}`);
    canonicalFields.forEach((field) => { const option = document.createElement('option'); option.value = field; option.textContent = optionLabel(field); option.selected = field === candidate.canonical_field; select.append(option); });
    mappingCell.append(select); row.append(mappingCell);
    const evidenceCell = document.createElement('td'); evidenceCell.textContent = `${candidate.decision}: ${candidate.evidence.join(', ')}`; row.append(evidenceCell); body.append(row);
  });
  const issues = document.querySelector('#issues'); issues.replaceChildren();
  (data.issues.length ? data.issues : [{severity: 'INFO', message: 'No profile warnings.'}]).forEach((issue) => { const item = document.createElement('li'); item.textContent = `${issue.severity}: ${issue.message}`; issues.append(item); });
}

form.addEventListener('submit', async (event) => {
  event.preventDefault(); status.textContent = 'Validating and profiling the selected file…';
  const response = await fetch('/api/datasets/profile', { method: 'POST', body: new FormData(form) });
  const result = document.querySelector('#result');
  if (!response.ok) { const body = await response.json(); status.textContent = body.detail || 'The file could not be processed.'; result.hidden = true; return; }
  latestProfile = await response.json(); status.textContent = 'Profile completed. You can continue with safe mappings or review them.'; result.hidden = false; document.querySelector('#capabilities').hidden = true; document.querySelector('#mapping-review').open = false; renderProfile(latestProfile);
});

async function submitMappings(mappings) {
  if (!latestProfile) return;
  const schemaStatus = document.querySelector('#schema-status'); schemaStatus.textContent = 'Checking confirmed mappings…';
  const response = await fetch(`/api/datasets/${latestProfile.dataset_id}/schema`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({mappings}) });
  const data = await response.json();
  if (!response.ok) { schemaStatus.textContent = data.detail || 'The mappings need review.'; return; }
  schemaStatus.textContent = 'Mappings confirmed for this temporary session.'; document.querySelector('#capabilities').hidden = false;
  const list = document.querySelector('#capability-list'); list.replaceChildren(); data.capabilities.forEach((capability) => { const item = document.createElement('li'); item.textContent = `${capability.objective}: ${capability.status} — ${capability.reasons.join(' ')}`; list.append(item); });
}

document.querySelector('#continue-mappings').addEventListener('click', () => {
  if (!latestProfile) return;
  submitMappings(Object.fromEntries(Object.entries(latestProfile.mappings).map(([source, candidate]) => [source, candidate.canonical_field])));
});

document.querySelector('#review-mappings').addEventListener('click', () => { document.querySelector('#mapping-review').open = true; document.querySelector('#mapping-review').scrollIntoView({behavior: 'smooth'}); });

document.querySelector('#accept-mappings').addEventListener('click', () => {
  submitMappings(Object.fromEntries([...document.querySelectorAll('#rows select')].map((select) => [select.dataset.source, select.value])));
});
