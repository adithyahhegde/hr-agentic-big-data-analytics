"""Deterministic, bounded ML execution for confirmed HR analytical tasks.

The engine trains only on confirmed mappings, uses reproducible seeds, rejects
obvious identifiers/leakage, and returns comparable evidence rather than an
opaque model choice. Unsupervised analyses return aggregate evidence only.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PreparedData:
    features: list[str]
    X: list[list[float]]
    y: list[float] | list[int]
    classification: bool


def _number(value: str) -> float | None:
    text = (value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _label(value: str) -> int | None:
    text = (value or "").strip().lower()
    if text in {"yes", "y", "true", "1", "left", "terminated", "attrition"}:
        return 1
    if text in {"no", "n", "false", "0", "stayed", "active", "retained"}:
        return 0
    return None


def _feature_sources(mappings: dict[str, str], target: str | None = None) -> list[tuple[str, str]]:
    excluded = {"employee_id", "employee_record_id", "manager_id"}
    return [(canonical, source) for source, canonical in mappings.items()
            if canonical != "unknown" and canonical != target and canonical not in excluded]


def _load_numeric(path: Path, mappings: dict[str, str], target: str, classification: bool) -> PreparedData:
    canonical_to_source = {canonical: source for source, canonical in mappings.items() if canonical != "unknown"}
    target_source = canonical_to_source.get(target)
    if not target_source:
        raise ValueError(f"Confirmed target '{target}' is not mapped.")
    feature_sources = _feature_sources(mappings, target)
    if not feature_sources:
        raise ValueError("No usable predictors remain after excluding identifiers and the target.")

    X: list[list[float]] = []
    y: list[float] | list[int] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values = [_number(row.get(source, "")) for _, source in feature_sources]
            if any(value is None for value in values):
                continue
            if classification:
                label = _label(row.get(target_source, ""))
                if label is None:
                    continue
                y.append(label)
            else:
                value = _number(row.get(target_source, ""))
                if value is None:
                    continue
                y.append(value)
            X.append([float(value) for value in values if value is not None])

    if not X:
        raise ValueError("No complete numeric training rows remain after safe missing-value filtering.")
    if len(X) < 20:
        raise ValueError("At least 20 complete rows are required for model training.")
    if classification and len(set(y)) < 2:
        raise ValueError("The classification target contains only one usable class.")
    return PreparedData([name for name, _ in feature_sources], X, y, classification)


def _load_numeric_matrix(path: Path, mappings: dict[str, str], features: list[str], max_rows: int = 100_000) -> tuple[list[str], Any]:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("ML execution requires the optional 'ml' dependencies. Install the project with the ml extra.") from exc
    selected = [(canonical, source) for source, canonical in mappings.items() if canonical in set(features)
                and canonical not in {"employee_id", "employee_record_id", "manager_id", "unknown"}]
    if len(selected) < 2:
        raise ValueError("At least two confirmed numeric predictors are required.")
    rows: list[list[float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values = [_number(row.get(source, "")) for _, source in selected]
            if any(v is None for v in values):
                continue
            rows.append([float(v) for v in values if v is not None])
            if len(rows) >= max_rows:
                break
    if len(rows) < 20:
        raise ValueError("At least 20 complete rows are required for unsupervised analysis.")
    matrix = np.asarray(rows, dtype=float)
    keep = [i for i in range(matrix.shape[1]) if len(np.unique(matrix[:, i])) > 1]
    if len(keep) < 2:
        raise ValueError("At least two non-constant predictors are required.")
    return [selected[i][0] for i in keep], matrix[:, keep]


def _classification_models(seed: int):
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    return {
        "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed),
        "random_forest": RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_leaf=3, class_weight="balanced", random_state=seed, n_jobs=-1),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15, random_state=seed),
    }


def _regression_models(seed: int):
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import Ridge
    return {
        "ridge_regression": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(n_estimators=150, max_depth=8, min_samples_leaf=3, random_state=seed, n_jobs=-1),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=120, max_leaf_nodes=15, random_state=seed),
    }


def _feature_importance(model: Any, features: list[str], X_test: Any, y_test: Any, seed: int) -> list[dict[str, Any]]:
    values = getattr(model, "feature_importances_", None)
    if values is None and hasattr(model, "coef_"):
        import numpy as np
        coef = np.asarray(model.coef_)
        values = np.mean(np.abs(coef), axis=0) if coef.ndim > 1 else np.abs(coef)
    if values is None:
        try:
            from sklearn.inspection import permutation_importance
            result = permutation_importance(model, X_test, y_test, n_repeats=3, random_state=seed, n_jobs=-1)
            values = result.importances_mean
        except Exception:
            return []
    pairs = sorted(zip(features, [float(v) for v in values]), key=lambda item: item[1], reverse=True)
    return [{"feature": name, "importance": round(value, 6)} for name, value in pairs[:10]]


def run_ml(path: Path, mappings: dict[str, str], objective: str, target: str, features: list[str], seed: int = 42) -> dict[str, Any]:
    """Train and compare bounded local candidates for one feasible supervised task."""
    try:
        import numpy as np
        from sklearn.metrics import balanced_accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, roc_auc_score
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline
    except ImportError as exc:
        raise RuntimeError("ML execution requires the optional 'ml' dependencies. Install the project with the ml extra.") from exc

    classification = objective == "attrition_classification"
    prepared = _load_numeric(path, mappings, target, classification)
    selected = [(i, name) for i, name in enumerate(prepared.features) if name in set(features)]
    if not selected:
        raise ValueError("The confirmed task does not contain usable numeric predictors.")
    indices, feature_names = zip(*selected)
    X = np.asarray([[row[i] for i in indices] for row in prepared.X], dtype=float)
    y = np.asarray(prepared.y)
    keep = [i for i, name in enumerate(feature_names) if len(np.unique(X[:, i])) > 1 and name not in {"employee_id", "employee_record_id", "manager_id"}]
    X = X[:, keep]
    feature_names = [feature_names[i] for i in keep]
    if not feature_names:
        raise ValueError("All candidate predictors are constant or identifier-like.")

    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y if classification else None)
    except ValueError as exc:
        raise ValueError(f"The dataset cannot support a reliable holdout split: {exc}") from exc
    models = _classification_models(seed) if classification else _regression_models(seed)
    results: list[dict[str, Any]] = []
    fitted: dict[str, Any] = {}
    for name, model in models.items():
        candidate = make_pipeline(StandardScaler(), model) if name in {"logistic_regression", "ridge_regression"} else model
        candidate.fit(X_train, y_train)
        pred = candidate.predict(X_test)
        metrics: dict[str, float] = {}
        if classification:
            metrics["balanced_accuracy"] = round(float(balanced_accuracy_score(y_test, pred)), 4)
            metrics["precision"] = round(float(precision_score(y_test, pred, zero_division=0)), 4)
            metrics["recall"] = round(float(__import__("sklearn.metrics", fromlist=["recall_score"]).recall_score(y_test, pred, zero_division=0)), 4)
            metrics["f1"] = round(float(f1_score(y_test, pred, zero_division=0)), 4)
            if len(set(y_test)) == 2 and hasattr(candidate, "predict_proba"):
                metrics["roc_auc"] = round(float(roc_auc_score(y_test, candidate.predict_proba(X_test)[:, 1])), 4)
            score = metrics["f1"]
        else:
            rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
            metrics["mae"] = round(float(mean_absolute_error(y_test, pred)), 4)
            metrics["rmse"] = round(rmse, 4)
            metrics["r2"] = round(float(r2_score(y_test, pred)), 4)
            score = -rmse
        fitted[name] = candidate
        results.append({"model": name, "metrics": metrics, "selection_score": round(score, 6)})
    results.sort(key=lambda item: item["selection_score"], reverse=True)
    best = results[0]
    return {
        "objective": objective, "target_field": target, "feature_fields": list(feature_names),
        "rows_used": int(len(X)), "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "models": results, "selected_model": best["model"],
        "selection_metric": "f1" if classification else "rmse",
        "explainability": {"method": "model_importance_or_permutation", "top_features": _feature_importance(fitted[best["model"]], list(feature_names), X_test, y_test, seed)},
        "safeguards": ["confirmed target only", "identifier exclusion", "constant-feature exclusion", "reproducible holdout seed", "no external model API"],
    }


def run_clustering(path: Path, mappings: dict[str, str], features: list[str], seed: int = 42) -> dict[str, Any]:
    """Compare deterministic K-Means cluster counts and return aggregate profiles."""
    try:
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("Clustering requires the optional 'ml' dependencies. Install the project with the ml extra.") from exc
    names, X = _load_numeric_matrix(path, mappings, features)
    scaled = StandardScaler().fit_transform(X)
    candidates: list[dict[str, Any]] = []
    fitted: dict[int, Any] = {}
    for k in range(2, min(6, len(X) - 1) + 1):
        model = KMeans(n_clusters=k, n_init=10, random_state=seed)
        labels = model.fit_predict(scaled)
        score = float(silhouette_score(scaled, labels)) if len(set(labels)) > 1 else -1.0
        candidates.append({"k": k, "silhouette": round(score, 4), "inertia": round(float(model.inertia_), 4)})
        fitted[k] = model
    candidates.sort(key=lambda x: x["silhouette"], reverse=True)
    best_k = candidates[0]["k"]
    labels = fitted[best_k].labels_
    profiles = []
    for cluster in range(best_k):
        mask = labels == cluster
        profiles.append({"cluster": cluster, "rows": int(mask.sum()), "share": round(float(mask.mean()), 4), "means": {name: round(float(X[mask, i].mean()), 4) for i, name in enumerate(names)}})
    return {"objective": "employee_clustering", "rows_used": int(len(X)), "feature_fields": names, "candidates": candidates, "selected_k": best_k, "cluster_profiles": profiles, "method": "standardized_kmeans", "safeguards": ["confirmed features only", "identifier exclusion", "constant-feature exclusion", "reproducible seed", "aggregate profiles only"]}


def run_anomaly_detection(path: Path, mappings: dict[str, str], features: list[str], seed: int = 42) -> dict[str, Any]:
    """Score multivariate outliers without returning employee-level identities."""
    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("Anomaly detection requires the optional 'ml' dependencies. Install the project with the ml extra.") from exc
    names, X = _load_numeric_matrix(path, mappings, features)
    scaled = StandardScaler().fit_transform(X)
    contamination = min(0.10, max(0.01, 5.0 / len(X)))
    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=seed, n_jobs=-1)
    labels = model.fit_predict(scaled)
    scores = -model.score_samples(scaled)
    threshold = float(np.quantile(scores, 1.0 - contamination))
    return {"objective": "anomaly_detection", "rows_used": int(len(X)), "feature_fields": names, "anomaly_rows": int((labels == -1).sum()), "anomaly_share": round(float((labels == -1).mean()), 4), "score_threshold": round(threshold, 6), "score_summary": {"min": round(float(scores.min()), 6), "median": round(float(np.median(scores)), 6), "max": round(float(scores.max()), 6)}, "method": "isolation_forest", "safeguards": ["confirmed features only", "identifier exclusion", "no employee identities returned", "aggregate anomaly reporting", "reproducible seed"]}
