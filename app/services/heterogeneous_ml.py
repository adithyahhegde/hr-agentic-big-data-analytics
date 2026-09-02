"""Local ML execution for mixed numeric/categorical HR predictors."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def _label(value: str) -> int | None:
    text = (value or "").strip().lower()
    if text in {"yes", "y", "true", "1", "left", "terminated", "attrition"}:
        return 1
    if text in {"no", "n", "false", "0", "stayed", "active", "retained"}:
        return 0
    return None


def run_heterogeneous_ml(path: Path, mappings: dict[str, str], objective: str, target: str, features: list[str], seed: int = 42) -> dict[str, Any]:
    """Train comparable local models while preserving categorical predictors."""
    try:
        import numpy as np
        import pandas as pd
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression, Ridge
        from sklearn.metrics import balanced_accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except ImportError as exc:
        raise RuntimeError("Heterogeneous ML requires the optional 'ml' dependencies. Install the project with the ml extra.") from exc

    source_for = {canonical: source for source, canonical in mappings.items() if canonical != "unknown"}
    selected = [f for f in features if f in source_for and f not in {"employee_id", "employee_record_id", "manager_id"}]
    if not selected:
        raise ValueError("No confirmed predictors are available for heterogeneous ML.")
    target_source = source_for.get(target)
    if not target_source:
        raise ValueError(f"Confirmed target '{target}' is not mapped.")

    frame = pd.read_csv(path, usecols=[source_for[f] for f in selected] + [target_source])
    frame = frame.rename(columns={source_for[f]: f for f in selected} | {target_source: target})
    classification = objective == "attrition_classification"
    if classification:
        frame[target] = frame[target].map(_label)
    else:
        frame[target] = pd.to_numeric(frame[target].astype(str).str.replace(",", "", regex=False), errors="coerce")
    frame = frame.dropna(subset=[target])
    if len(frame) < 20:
        raise ValueError("At least 20 usable rows are required for model training.")
    y = frame[target]
    if classification and y.nunique() < 2:
        raise ValueError("The classification target contains only one usable class.")
    X = frame[selected].copy()
    numeric = [c for c in selected if pd.api.types.is_numeric_dtype(X[c])]
    categorical = [c for c in selected if c not in numeric]
    for column in categorical:
        X[column] = X[column].astype("string")

    numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical_pipe = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=2))])
    preprocessor = ColumnTransformer([("numeric", numeric_pipe, numeric), ("categorical", categorical_pipe, categorical)], remainder="drop")
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y if classification else None)
    except ValueError as exc:
        raise ValueError(f"The dataset cannot support a reliable holdout split: {exc}") from exc

    if classification:
        models = {
            "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed),
            "random_forest": RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_leaf=3, class_weight="balanced", random_state=seed, n_jobs=-1),
            "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15, random_state=seed),
        }
    else:
        models = {
            "ridge_regression": Ridge(alpha=1.0),
            "random_forest": RandomForestRegressor(n_estimators=150, max_depth=8, min_samples_leaf=3, random_state=seed, n_jobs=-1),
            "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=120, max_leaf_nodes=15, random_state=seed),
        }

    results: list[dict[str, Any]] = []
    fitted: dict[str, Any] = {}
    for name, estimator in models.items():
        pipeline = Pipeline([("prepare", preprocessor), ("model", estimator)])
        try:
            pipeline.fit(X_train, y_train)
            pred = pipeline.predict(X_test)
            metrics: dict[str, float] = {}
            if classification:
                metrics["balanced_accuracy"] = round(float(balanced_accuracy_score(y_test, pred)), 4)
                metrics["precision"] = round(float(precision_score(y_test, pred, zero_division=0)), 4)
                metrics["recall"] = round(float(recall_score(y_test, pred, zero_division=0)), 4)
                metrics["f1"] = round(float(f1_score(y_test, pred, zero_division=0)), 4)
                if len(set(y_test)) == 2 and hasattr(pipeline, "predict_proba"):
                    metrics["roc_auc"] = round(float(roc_auc_score(y_test, pipeline.predict_proba(X_test)[:, 1])), 4)
                score = metrics["f1"]
            else:
                rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
                metrics["mae"] = round(float(mean_absolute_error(y_test, pred)), 4)
                metrics["rmse"] = round(rmse, 4)
                metrics["r2"] = round(float(r2_score(y_test, pred)), 4)
                score = -rmse
            fitted[name] = pipeline
            results.append({"model": name, "metrics": metrics, "selection_score": round(score, 6)})
        except Exception as exc:
            results.append({"model": name, "metrics": {}, "selection_score": float("-inf"), "status": "FAILED", "reason": str(exc)})

    valid = [r for r in results if r.get("metrics")]
    if not valid:
        raise ValueError("No candidate model could be trained on the confirmed heterogeneous schema.")
    valid.sort(key=lambda r: r["selection_score"], reverse=True)
    best = valid[0]
    top_features: list[dict[str, Any]] = []
    estimator = fitted[best["model"]].named_steps["model"]
    values = getattr(estimator, "feature_importances_", None)
    if values is None and hasattr(estimator, "coef_"):
        coef = np.asarray(estimator.coef_)
        values = np.mean(np.abs(coef), axis=0) if coef.ndim > 1 else np.abs(coef)
    if values is not None:
        transformed = fitted[best["model"]].named_steps["prepare"].get_feature_names_out()
        pairs = sorted(zip(transformed, values), key=lambda x: float(x[1]), reverse=True)[:15]
        top_features = [{"feature": str(name), "importance": round(float(value), 6)} for name, value in pairs]

    return {
        "objective": objective, "target_field": target, "feature_fields": selected,
        "numeric_features": numeric, "categorical_features": categorical,
        "rows_used": int(len(X)), "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "models": results, "selected_model": best["model"],
        "selection_metric": "f1" if classification else "rmse",
        "explainability": {"method": "encoded_model_importance", "top_features": top_features},
        "preparation": {"numeric_imputation": "median", "categorical_imputation": "most_frequent", "categorical_encoding": "one_hot", "unknown_category_policy": "ignore"},
        "safeguards": ["confirmed target only", "identifier exclusion", "constant predictors handled by model preprocessing", "reproducible holdout seed", "no external model API", "no raw records returned"],
    }
