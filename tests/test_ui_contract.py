from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "ui-enhancements.css").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "ui-enhancements.js").read_text(encoding="utf-8")


def test_workflow_has_five_accessible_steps_and_landmarks():
    for step in range(1, 6):
        assert f'id="step-{step}"' in INDEX
        assert f'data-step="{step}"' in INDEX
    assert '<main class="workspace" id="main-content">' in INDEX
    assert '<nav aria-label="Workspace steps">' in INDEX
    assert 'aria-labelledby="step-1-title"' in INDEX
    assert 'aria-labelledby="step-5-title"' in INDEX


def test_async_status_surfaces_are_live_regions():
    assert 'id="status" class="status" role="status" aria-live="polite"' in INDEX
    assert 'id="schema-status" class="status" role="status" aria-live="polite"' in INDEX
    assert 'id="ml-status" class="status" role="status" aria-live="polite"' in INDEX
    assert 'id="connection" class="connection" aria-live="polite"' in INDEX


def test_upload_contract_remains_csv_only_and_keyboard_reachable():
    assert 'type="file" accept=".csv,text/csv"' in INDEX
    assert 'for="dataset" class="file-button"' in INDEX
    assert 'dropzone.setAttribute(\'tabindex\', \'0\')' in JS
    assert 'input.click()' in JS


def test_motion_and_focus_preferences_are_defined():
    assert '@media(prefers-reduced-motion:reduce)' in CSS
    assert ':focus-visible' in CSS
    assert 'transition:none' in CSS


def test_modern_feedback_layer_is_loaded_and_safe():
    assert '<link rel="stylesheet" href="/static/ui-enhancements.css">' in INDEX
    assert '<script src="/static/ui-enhancements.js" defer></script>' in INDEX
    assert 'role',
    assert 'textContent = message' in JS
    assert 'aria-label="Dismiss notification"' in JS


def test_raw_employee_records_are_not_introduced_by_ui_layer():
    assert 'employee identities and individual anomaly records are not exposed' in INDEX
    assert 'does not receive unrestricted HR records' in INDEX
    assert 'local-first' in INDEX
