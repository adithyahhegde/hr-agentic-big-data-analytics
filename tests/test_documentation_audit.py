from pathlib import Path

from scripts.documentation_audit import audit


def test_documentation_audit_passes_for_repository_root():
    root = Path(__file__).resolve().parents[1]
    assert audit(root) == []


def test_documentation_audit_rejects_stale_status_marker(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "A successful CI evaluation run on 2026-09-08\n"
        "External Spark target-cluster scalability has not yet been measured.\n"
        "application-level API-key identity\n",
        encoding="utf-8",
    )
    implementation = """# Implementation Plan\n\n## Definition of done\n\n## Current status\n\n[x] Reproducible local scalability measurements at 100, 1,000, and 10,000 rows\n[x] Comparative schema-mapping evaluation against baseline methods, with CI evidence recorded.\n[x] Executable objective-feasibility evaluation against explicit fixture-contract labels and a weak baseline, with CI evidence recorded.\n[x] Executable bounded planner-to-synthesis reliability/abstention evaluation, with CI evidence recorded.\n[x] SHAP smoke evaluation contract and CI smoke execution for optional local explainability.\n[ ] External Spark target-cluster scalability validation.\n[ ] Documentation consistency audit after final feature freeze.\n"""
    (tmp_path / "docs" / "IMPLEMENTATION.md").write_text(implementation, encoding="utf-8")
    (tmp_path / "docs" / "EVALUATION_PLAN.md").write_text("", encoding="utf-8")
    (tmp_path / "docs" / "EVALUATION_RESULTS.md").write_text(
        "GitHub Actions run `34212312393`\n"
        "External Spark scalability remains unverified\n"
        "do not establish generalization to real-world heterogeneous HR schemas\n",
        encoding="utf-8",
    )

    errors = audit(tmp_path)
    assert any("stale status marker" in error for error in errors)
