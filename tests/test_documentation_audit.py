from pathlib import Path

from scripts.documentation_audit import audit


ROOT = Path(__file__).resolve().parents[1]


def test_documentation_audit_passes_for_repository_root():
    assert audit(ROOT) == []


def test_documentation_audit_rejects_missing_evaluation_commit_provenance(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "A successful CI evaluation run on 2026-09-09\n"
        "External Spark target-cluster scalability has not yet been measured.\n"
        "application-level API-key identities scope\n",
        encoding="utf-8",
    )
    implementation = """# Implementation Plan\n\n## Definition of done\n\n## Current status\n\n[x] Reproducible local scalability measurements at 100, 1,000, and 10,000 rows\n[x] Comparative schema-mapping evaluation against baseline methods, with CI evidence recorded.\n[x] Executable objective-feasibility evaluation against explicit fixture-contract labels and a weak baseline, with CI evidence recorded.\n[x] Executable bounded planner-to-synthesis reliability/abstention evaluation, with CI evidence recorded.\n[x] SHAP smoke evaluation contract and CI smoke execution for optional local explainability.\n[ ] External Spark target-cluster scalability validation.\n[x] Documentation consistency audit after final feature freeze.\n"""
    (tmp_path / "docs" / "IMPLEMENTATION.md").write_text(implementation, encoding="utf-8")
    (tmp_path / "docs" / "EVALUATION_PLAN.md").write_text("", encoding="utf-8")
    (tmp_path / "docs" / "EVALUATION_RESULTS.md").write_text(
        "GitHub Actions run `34212312393` (Ephemeral Spark Validation) completed successfully\n"
        "External Spark scalability remains unverified\n"
        "do not establish generalization to real-world heterogeneous HR schemas\n",
        encoding="utf-8",
    )

    errors = audit(tmp_path)
    assert any("missing evaluation commit identifier" in error for error in errors)


def test_documentation_audit_rejects_malformed_evaluation_commit_provenance(tmp_path):
    (tmp_path / "docs").mkdir()
    for relative, content in {
        "README.md": "A successful CI evaluation run on 2026-09-09\nExternal Spark target-cluster scalability has not yet been measured.\napplication-level API-key identities scope",
        "docs/IMPLEMENTATION.md": "## Definition of done\n## Current status\n[x] Reproducible local scalability measurements at 100, 1,000, and 10,000 rows\n[x] Comparative schema-mapping evaluation against baseline methods, with CI evidence recorded.\n[x] Executable objective-feasibility evaluation against explicit fixture-contract labels and a weak baseline, with CI evidence recorded.\n[x] Executable bounded planner-to-synthesis reliability/abstention evaluation, with CI evidence recorded.\n[x] SHAP smoke evaluation contract and CI smoke execution for optional local explainability.\n[ ] External Spark target-cluster scalability validation.\n[x] Documentation consistency audit after final feature freeze.",
        "docs/EVALUATION_PLAN.md": "",
        "docs/EVALUATION_RESULTS.md": "GitHub Actions run `34212312393` (Ephemeral Spark Validation) completed successfully for commit `not-a-sha`\nExternal Spark scalability remains unverified\ndo not establish generalization to real-world heterogeneous HR schemas",
    }.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    errors = audit(tmp_path)
    assert any("evaluation commit identifier must be a 40-character lowercase SHA" in error for error in errors)
