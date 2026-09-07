"""Bounded local AutoML execution for confirmed heterogeneous HR schemas.

AutoML is optional. The agent chooses an analytical objective, while this
module searches a constrained set of tabular learners and hyperparameters.
Raw HR records never leave this execution boundary or appear in the result.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _label(value: str) -> int | None:
    text = (value or "").strip().lower()
    if text in {"yes", "y", "true", "1", "left", "terminated", "attrition"}:
        return 1
    if text in {"no", "n", "false", "0", "stayed", "active", "retained"}:
        return 0
    return None


def run_automl(
    path: Path,
    mappings: dict[str, str],
    objective: str,
    target: str,
    features: list[str],
    seed: int = 42,
    time_budget: int = 30,
) -> dict[str, Any]:
    """Search bounded tabular model families and evaluate the winner on a holdout set."""
    try:
        import numpy as np
        import pandas as pd
        from flaml import AutoML
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import OneHotEncoder
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline
        from sklearn.metrics import (
            balanced_accuracy_score,
            f1_score,
            mean_absolute_error,
            mean_squared_error,
            precision_score,
            r2_score,
            recall_score,
            roc_auc_score,
        )
    except ImportError as exc:
        raise RuntimeError("AutoML requires the optional 'automl' dependencies. Install the project with the automl extra.") from exc

    if time_budget < 1 or time_budget > 600:
        raise ValueError("AutoML time_budget must be between 1 and 600 seconds.")
    source_for = {canonical: source for source, canonical in mappings.items() if canonical != "unknown"}
    selected = [field for field in features if field in source_for and field not in {"employee_id", "employee_record_id", "manager_id"}]
    if not selected:
        raise ValueError("No confirmed predictors are available for AutoML.")
    target_source = source_for.get(target)
    if not target_source:
        raise ValueError(f"Confirmed target '{target}' is not mapped.")

    frame = pd.read_csv(path, usecols=[source_for[field] for field in selected] + [target_source])
    frame = frame.rename(columns={source_for[field]: field for field in selected} | {target_source: target})
    classification = objective == "attrition_classification"
    if classification:
        frame[target] = frame[target].map(_label)
    else:
        frame[target] = pd.to_numeric(frame[target].astype(str).str.replace(",", "", regex=False), errors="coerce")
    frame = frame.dropna(subset=[target])
    if len(frame) < 20:
        raise ValueError("At least 20 usable rows are required for AutoML.")
    y = frame[target]
    if classification and y.nunique() < 2:
        raise ValueError("The classification target contains only one usable class.")

    X = frame[selected].copy()
    numeric = [field for field in selected if pd.api.types.is_numeric_dtype(X[field])]
    categorical = [field for field in selected if field not in numeric]
    for field in categorical:
        X[field] = X[field].astype("string")

    numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=2, max_categories=100)),
    ])
    preprocessor = ColumnTransformer([
        ("numeric", numeric_pipe, numeric),
        ("categorical", categorical_pipe, categorical),
    ], remainder="drop")

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=seed,
            stratify=y if classification else None,
        )
    except ValueError as exc:
        raise ValueError(f"The dataset cannot support a reliable AutoML holdout split: {exc}") from exc

    X_train_ready = preprocessor.fit_transform(X_train)
    X_test_ready = preprocessor.transform(X_test)
    automl = AutoML()
    task = "classification" if classification else "regression"
    metric = "f1" if classification else "rmse"
    # Keep the search reproducible and bounded. These learners cover linear/tree
    # families without pulling optional GPU/deep-learning stacks into the app.
    estimator_list = ["rf", "extra_tree", "histgb", "lrl2"] if classification else ["rf", "extra_tree", "histgb"]
    automl.fit(
        X_train=X_train_ready,
        y_train=y_train,
        task=task,
        metric=metric,
        time_budget=time_budget,
        estimator_list=estimator_list,
        seed=seed,
        verbose=0,
        retrain_full=True,
    )

    pred = automl.predict(X_test_ready)
    metrics: dict[str, float] = {}
    if classification:
        metrics["balanced_accuracy"] = round(float(balanced_accuracy_score(y_test, pred)), 4)
        metrics["precision"] = round(float(precision_score(y_test, pred, zero_division=0)), 4)
        metrics["recall"] = round(float(recall_score(y_test, pred, zero_division=0)), 4)
        metrics["f1"] = round(float(f1_score(y_test, pred, zero_division=0)), 4)
        if len(set(y_test)) == 2:
            try:
                probabilities = automl.predict_proba(X_test_ready)[:, 1]
                metrics["roc_auc"] = round(float(roc_auc_score(y_test, probabilities)), 4)
            except (AttributeError, ValueError, IndexError):
                pass
    else:
        rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
        metrics["mae"] = round(float(mean_absolute_error(y_test, pred)), 4)
        metrics["rmse"] = round(rmse, 4)
        metrics["r2"] = round(float(r2_score(y_test, pred)), 4)

    return {
        "objective": objective,
        "target_field": target,
        "feature_fields": selected,
        "numeric_features": numeric,
        "categorical_features": categorical,
        "rows_used": int(len(X)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "selected_model": str(automl.best_estimator),
        "metrics": metrics,
        "selection_metric": metric,
        "search": {
            "engine": "FLAML",
            "time_budget_seconds": time_budget,
            "estimators": estimator_list,
            "best_config": {str(k): v for k, v in automl.best_config.items()},
            "best_loss": float(automl.best_loss),
        },
        "preparation": {
            "numeric_imputation": "median",
            "categorical_imputation": "most_frequent",
            "categorical_encoding": "one_hot",
            "unknown_category_policy": "ignore",
            "max_categories_per_field": 100,
        },
        "safeguards": [
            "confirmed target only",
            "identifier exclusion",
            "bounded categorical encoding",
            "reproducible holdout seed",
            "bounded AutoML time budget",
            "no external model API",
            "no raw records returned",
        ],
    }
