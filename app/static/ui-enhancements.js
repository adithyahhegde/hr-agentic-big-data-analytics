(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];

  const skip = document.createElement('a');
  skip.className = 'ui-skip';
  skip.href = '#main-content';
  skip.textContent = 'Skip to workspace';
  document.body.prepend(skip);

  const stack = document.createElement('div');
  stack.className = 'toast-stack';
  stack.setAttribute('aria-live', 'polite');
  stack.setAttribute('aria-atomic', 'false');
  document.body.appendChild(stack);

  const toast = (message, kind = 'info') => {
    if (!message) return;
    const item = document.createElement('div');
    item.className = 'ui-toast';
    item.dataset.kind = kind;
    item.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    item.innerHTML = `<div><strong>${kind === 'error' ? 'Needs attention' : 'Workspace update'}</strong><span></span></div><button type="button" aria-label="Dismiss notification">×</button>`;
    $('.ui-toast span', item).textContent = message;
    $('button', item).addEventListener('click', () => item.remove());
    stack.appendChild(item);
    window.setTimeout(() => item.remove(), 5200);
  };

  // Keep feedback visible even when the core workflow is busy.
  const observer = new MutationObserver(() => {
    const status = $('#status');
    if (status?.textContent.trim()) toast(status.textContent.trim(), /failed|error|unavailable/i.test(status.textContent) ? 'error' : 'info');
  });
  const status = $('#status');
  if (status) observer.observe(status, { childList: true, subtree: true, characterData: true });

  // Make drag/drop discoverable and keyboard-friendly without changing the upload contract.
  const dropzone = $('.dropzone');
  const input = $('#dataset');
  if (dropzone && input) {
    dropzone.addEventListener('keydown', event => {
      if ((event.key === 'Enter' || event.key === ' ') && event.target === dropzone) {
        event.preventDefault();
        input.click();
      }
    });
    dropzone.setAttribute('tabindex', '0');
    dropzone.setAttribute('aria-label', 'CSV dataset upload area. Press Enter to browse files or drop a CSV here.');
  }

  // Add semantic labels to dynamically generated controls and expose busy state.
  const labelControls = () => {
    $$('select[data-source]').forEach(select => {
      if (!select.getAttribute('aria-label')) select.setAttribute('aria-label', `Canonical field for ${select.dataset.source}`);
    });
    $$('.ml-button').forEach(button => button.setAttribute('aria-pressed', button.disabled ? 'true' : 'false'));
  };
  new MutationObserver(labelControls).observe(document.body, { childList: true, subtree: true });
  labelControls();

  // Use the existing navigation state to provide a compact document title cue.
  const titleByStep = ['Dataset intake','Data health','Data understanding','Explore evidence','Evidence readout'];
  const navObserver = new MutationObserver(() => {
    const active = $('.nav-step.active');
    if (active) document.title = `Workforce Intelligence · ${titleByStep[Number(active.dataset.step) - 1] || 'Workspace'}`;
  });
  navObserver.observe(document.body, { attributes: true, subtree: true, attributeFilter: ['class'] });
  navObserver.takeRecords();
  document.title = `Workforce Intelligence · ${titleByStep[0]}`;

  // Keep focus on the primary heading after workflow navigation, but only for keyboard users.
  let keyboardUser = false;
  document.addEventListener('keydown', e => { keyboardUser = e.key === 'Tab' || e.key.startsWith('Arrow'); }, true);
  document.addEventListener('click', e => {
    const stepButton = e.target.closest('.nav-step,[data-next],[data-back]');
    if (!stepButton || !keyboardUser) return;
    window.setTimeout(() => {
      const visible = $('.step-panel:not([hidden])');
      const heading = visible?.querySelector('h2');
      if (heading) {
        heading.setAttribute('tabindex', '-1');
        heading.focus({ preventScroll: true });
      }
    }, 30);
  }, true);

  window.uiEnhancements = { toast };
})();
