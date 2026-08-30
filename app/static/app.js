const form = document.querySelector('#upload-form');
const status = document.querySelector('#status');
let latestProfile;
form.addEventListener('submit', async (event) => {
  event.preventDefault(); status.textContent = 'Validating and profiling the selected file…';
  const response = await fetch('/api/datasets/profile', { method: 'POST', body: new FormData(form) });
  const result = document.querySelector('#result');
  if (!response.ok) { const body = await response.json(); status.textContent = body.detail || 'The file could not be processed.'; result.hidden = true; return; }
  const data = await response.json(); latestProfile = data; status.textContent = 'Profile completed.'; result.hidden = false;
  document.querySelector('#summary').textContent = `${data.row_count} rows · ${data.column_count} columns · ${data.duplicate_row_count} duplicate rows`;
  document.querySelector('#rows').innerHTML = data.columns.map(c => { const m = data.mappings[c.source_name]; return `<tr><td>${c.source_name}</td><td>${c.inferred_type}</td><td>${c.null_count}</td><td>${m.canonical_field} (${Math.round(m.confidence * 100)}%)</td><td>${m.decision}</td></tr>`; }).join('');
  document.querySelector('#issues').innerHTML = data.issues.length ? data.issues.map(i => `<li>${i.severity}: ${i.message}</li>`).join('') : '<li>No profile warnings.</li>';
});

document.querySelector('#accept-mappings').addEventListener('click', async () => {
  if (!latestProfile) return;
  const schemaStatus = document.querySelector('#schema-status');
  schemaStatus.textContent = 'Checking accepted mappings…';
  const mappings = Object.fromEntries(Object.entries(latestProfile.mappings).map(([source, candidate]) => [source, candidate.canonical_field]));
  const response = await fetch(`/api/datasets/${latestProfile.dataset_id}/schema`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({mappings}) });
  const data = await response.json();
  if (!response.ok) { schemaStatus.textContent = data.detail || 'The mappings need review.'; return; }
  schemaStatus.textContent = 'Mappings accepted for this temporary session.';
  document.querySelector('#capabilities').hidden = false;
  document.querySelector('#capability-list').innerHTML = data.capabilities.map(c => `<li><strong>${c.objective}</strong>: ${c.status} — ${c.reasons.join(' ')}</li>`).join('');
});
