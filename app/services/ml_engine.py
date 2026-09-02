"""Deterministic, bounded ML execution for confirmed HR analytical tasks.

The engine intentionally trains only on confirmed numeric feature mappings. It
never invents targets, uses reproducible splits/seeds, rejects obvious leakage,
and returns comparable evidence rather than a single opaque model choice.
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
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _label(value: str) -> int | None:
    text = (value or "").strip().lower()
    if text in {"yes", "y", "true", "1", "left", "terminated", "attrition"}:
        return 1
    if text in {"no", "n", "false", "0", "stayed", "active", "retained"}:
        return 0
    return None


def _load_numeric(path: Path, mappings: dict[str, str], target: str, classification: bool) -> PreparedData:
    canonical_to_source = {canonical: source for source, canonical in mappings.items() if canonical != "unknown"}
    target_source = canonical_to_source.get(target)
    if not target_source:
        raise ValueError(f"Confirmed target '{target}' is not mapped.")
    feature_sources = [
        (canonical, source) for canonical, source in canonical_to_source.items()
        if canonical != target and canonical not in {"employee_id", "employee_record_id", "manager_id"}
    ]
    if not feature_sources:
        raise ValueError("No usable predictors remain after excluding identifiers and the target.")

    X: list[list[float]] = []
    y: list[float] | list[int] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values: list[float] = []
            valid = True
            for _, source in feature_sources:
                value = _number(row.get(source, ""))
                if value is None:
                    valid = False
                    break
                values.append(value)
            if not valid:
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
            X.append(values)

    if not X:
        raise ValueError("No complete numeric training rows remain after safe missing-value filtering.")
    if len(X) < 20:
        raise ValueError("At least 20 complete rows are required for model training.")
    if classification and len(set(y)) < 2:
        raise ValueError("The classification target contains only one usable class.")
    return PreparedData([name for name, _ in feature_sources], X, y, classification)


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
    """Train and compare bounded local candidates for one feasible task."""
    try:
        import numpy as np
        from sklearn.metrics import (balanced_accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, roc_auc_score)
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

    # Remove constant predictors and obvious identifier-like fields.
    keep = [i for i, name in enumerate(feature_names) if len(np.unique(X[:, i])) > 1 and name not in {"employee_id", "employee_record_id", "manager_id"}]
    X = X[:, keep]
    feature_names = [feature_names[i] for i in keep]
    if not feature_names:
        raise ValueError("All candidate predictors are constant or identifier-like.")

    stratify = y if classification else None
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=stratify)
    except ValueError as exc:
        raise ValueError(f"The dataset cannot support a reliable holdout split: {exc}") from exc

    if classification:
        models = _classification_models(seed)
    else:
        models = _regression_models(seed)

    results: list[dict[str, Any]] = []
    fitted: dict[str, Any] = {}
    for name, model in models.items():
        candidate = make_pipeline(StandardScaler(), model) if name == "logistic_regression" or name == "ridge_regression" else model
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
    importance = _feature_importance(fitted[best["model"]], list(feature_names), X_test, y_test, seed)
    return {
        "objective": objective,
        "target_field": target,
        "feature_fields": list(feature_names),
        "rows_used": int(len(X)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "models": results,
        "selected_model": best["model"],
        "selection_metric": "f1" if classification else "rmse",
        "explainability": {"method": "model_importance_or_permutation", "top_features": importance},
        "safeguards": ["confirmed target only", "identifier exclusion", "constant-feature exclusion", "reproducible holdout seed", "no external model API"],
    }
