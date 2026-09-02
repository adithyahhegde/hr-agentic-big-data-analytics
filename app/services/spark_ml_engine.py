"""Distributed ML execution for workloads routed to Spark.

The service deliberately keeps raw rows inside Spark. API results contain only
aggregate metrics, model metadata, and grouped feature evidence.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _spark():
    try:
        from pyspark.sql import SparkSession
        from pyspark.ml import Pipeline
        from pyspark.ml.classification import GBTClassifier, LogisticRegression, RandomForestClassifier
        from pyspark.ml.regression import GBTRegressor, LinearRegression, RandomForestRegressor
        from pyspark.ml.feature import OneHotEncoder, StandardScaler, StringIndexer, VectorAssembler
        from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator, RegressionEvaluator
        from pyspark.ml.clustering import KMeans
        from pyspark.sql import functions as F
    except ImportError as exc:
        raise RuntimeError("Spark ML execution requires the optional 'bigdata' dependencies. Install the project with the bigdata extra.") from exc
    spark = SparkSession.builder.appName("hr-agentic-analytics").getOrCreate()
    return spark, (Pipeline, GBTClassifier, LogisticRegression, RandomForestClassifier, GBTRegressor, LinearRegression, RandomForestRegressor, OneHotEncoder, StandardScaler, StringIndexer, VectorAssembler, BinaryClassificationEvaluator, MulticlassClassificationEvaluator, RegressionEvaluator, KMeans, F)


def _load(path: Path, mappings: dict[str, str], target: str | None = None):
    spark, _ = _spark()
    df = spark.read.option("header", True).option("inferSchema", True).csv(str(path))
    canonical = {source: field for source, field in mappings.items() if field != "unknown"}
    rename = {}
    for source, field in canonical.items():
        if source in df.columns:
            safe = f"c_{field}"
            if safe not in df.columns:
                rename[source] = safe
    for source, safe in rename.items():
        df = df.withColumnRenamed(source, safe)
    usable = {field: f"c_{field}" for field in set(canonical.values()) if f"c_{field}" in df.columns and field not in {"employee_id", "employee_record_id", "manager_id", "unknown"}}
    if target and target not in usable:
        raise ValueError(f"Confirmed target '{target}' is not available in the Spark dataframe.")
    return df, usable


def _feature_columns(df, usable: dict[str, str], features: list[str], target: str):
    selected = [f for f in features if f in usable and f != target]
    if not selected:
        raise ValueError("No usable confirmed predictors remain for Spark ML.")
    numeric, categorical = [], []
    for field in selected:
        dtype = dict(df.dtypes).get(usable[field])
        if dtype in {"int", "bigint", "double", "float", "smallint", "tinyint", "long", "decimal"}:
            numeric.append(field)
        else:
            categorical.append(field)
    return numeric, categorical


def _classification(path: Path, mappings: dict[str, str], objective: str, target: str, features: list[str], seed: int) -> dict[str, Any]:
    spark, deps = _spark()
    (Pipeline, GBTClassifier, LogisticRegression, RandomForestClassifier, _, _, _, OneHotEncoder, StandardScaler, StringIndexer, VectorAssembler, BinaryClassificationEvaluator, MulticlassClassificationEvaluator, _, _, F) = deps
    df, usable = _load(path, mappings, target)
    numeric, categorical = _feature_columns(df, usable, features, target)
    label_source = usable[target]
    df = df.withColumn("__label", F.when(F.lower(F.trim(F.col(label_source).cast("string"))).isin("yes", "y", "true", "1", "left", "terminated", "attrition"), F.lit(1.0)).when(F.lower(F.trim(F.col(label_source).cast("string"))).isin("no", "n", "false", "0", "stayed", "active", "retained"), F.lit(0.0)).otherwise(F.col(label_source).cast("double")))
    df = df.dropna(subset=["__label"])
    for field in numeric:
        df = df.withColumn(usable[field], F.col(usable[field]).cast("double"))
    stages = []
    cat_indexed, cat_encoded = [], []
    for field in categorical:
        idx, enc = f"__{field}_idx", f"__{field}_enc"
        stages.append(StringIndexer(inputCol=usable[field], outputCol=idx, handleInvalid="keep"))
        stages.append(OneHotEncoder(inputCol=idx, outputCol=enc, handleInvalid="keep"))
        cat_encoded.append(enc)
    inputs = [usable[f] for f in numeric] + cat_encoded
    if not inputs:
        raise ValueError("No usable predictors remain after schema validation.")
    stages.append(VectorAssembler(inputCols=inputs, outputCol="__features", handleInvalid="keep"))
    train, test = df.randomSplit([0.8, 0.2], seed=seed)
    if train.limit(20).count() < 20 or test.limit(2).count() == 0:
        raise ValueError("Spark holdout split is too small for reliable evaluation.")
    models = {
        "logistic_regression": LogisticRegression(featuresCol="__features", labelCol="__label", maxIter=100, regParam=0.05),
        "random_forest": RandomForestClassifier(featuresCol="__features", labelCol="__label", numTrees=150, maxDepth=8, seed=seed),
        "gbt_classifier": GBTClassifier(featuresCol="__features", labelCol="__label", maxIter=100, maxDepth=6, seed=seed),
    }
    results = []
    fitted = {}
    for name, model in models.items():
        pipeline = Pipeline(stages=stages + [model])
        fitted_model = pipeline.fit(train)
        pred = fitted_model.transform(test).cache()
        evaluator = MulticlassClassificationEvaluator(labelCol="__label", predictionCol="prediction")
        f1 = float(evaluator.evaluate(pred, {evaluator.metricName: "f1"}))
        precision = float(evaluator.evaluate(pred, {evaluator.metricName: "weightedPrecision"}))
        recall = float(evaluator.evaluate(pred, {evaluator.metricName: "weightedRecall"}))
        auc = float(BinaryClassificationEvaluator(labelCol="__label", rawPredictionCol="rawPrediction", metricName="areaUnderROC").evaluate(pred))
        pred.unpersist()
        results.append({"model": name, "metrics": {"f1": round(f1, 4), "precision": round(precision, 4), "recall": round(recall, 4), "roc_auc": round(auc, 4)}, "selection_score": round(f1, 6)})
        fitted[name] = fitted_model
    results.sort(key=lambda x: x["selection_score"], reverse=True)
    best = results[0]
    return {"objective": objective, "target_field": target, "feature_fields": numeric + categorical, "rows_used": int(df.count()), "models": results, "selected_model": best["model"], "selection_metric": "f1", "explainability": {"method": "spark_model_feature_metadata", "top_features": [{"feature": f, "importance": None} for f in (numeric + categorical)[:10]], "note": "Distributed categorical encoding is included; exact grouped importance is exposed only when the fitted estimator provides stable feature attribution."}, "execution": {"engine": "SPARK", "distributed": True, "raw_rows_returned": False}, "safeguards": ["confirmed target only", "identifier exclusion", "categorical encoding with invalid-value handling", "distributed holdout evaluation", "reproducible seed", "aggregate results only"]}


def _regression(path: Path, mappings: dict[str, str], objective: str, target: str, features: list[str], seed: int) -> dict[str, Any]:
    spark, deps = _spark()
    (Pipeline, _, _, _, GBTRegressor, LinearRegression, RandomForestRegressor, OneHotEncoder, StandardScaler, StringIndexer, VectorAssembler, _, _, RegressionEvaluator, _, F) = deps
    df, usable = _load(path, mappings, target)
    numeric, categorical = _feature_columns(df, usable, features, target)
    df = df.withColumn("__label", F.col(usable[target]).cast("double")).dropna(subset=["__label"])
    for field in numeric:
        df = df.withColumn(usable[field], F.col(usable[field]).cast("double"))
    stages, cat_encoded = [], []
    for field in categorical:
        idx, enc = f"__{field}_idx", f"__{field}_enc"
        stages.append(StringIndexer(inputCol=usable[field], outputCol=idx, handleInvalid="keep"))
        stages.append(OneHotEncoder(inputCol=idx, outputCol=enc, handleInvalid="keep"))
        cat_encoded.append(enc)
    inputs = [usable[f] for f in numeric] + cat_encoded
    if not inputs:
        raise ValueError("No usable predictors remain after schema validation.")
    stages.append(VectorAssembler(inputCols=inputs, outputCol="__features", handleInvalid="keep"))
    train, test = df.randomSplit([0.8, 0.2], seed=seed)
    if train.limit(20).count() < 20 or test.limit(2).count() == 0:
        raise ValueError("Spark holdout split is too small for reliable evaluation.")
    models = {"linear_regression": LinearRegression(featuresCol="__features", labelCol="__label", regParam=0.1), "random_forest": RandomForestRegressor(featuresCol="__features", labelCol="__label", numTrees=150, maxDepth=8, seed=seed), "gbt_regressor": GBTRegressor(featuresCol="__features", labelCol="__label", maxIter=100, maxDepth=6, seed=seed)}
    results = []
    for name, model in models.items():
        fitted = Pipeline(stages=stages + [model]).fit(train)
        pred = fitted.transform(test).cache()
        rmse = float(RegressionEvaluator(labelCol="__label", predictionCol="prediction", metricName="rmse").evaluate(pred))
        mae = float(RegressionEvaluator(labelCol="__label", predictionCol="prediction", metricName="mae").evaluate(pred))
        r2 = float(RegressionEvaluator(labelCol="__label", predictionCol="prediction", metricName="r2").evaluate(pred))
        pred.unpersist()
        results.append({"model": name, "metrics": {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4)}, "selection_score": round(-rmse, 6)})
    results.sort(key=lambda x: x["selection_score"], reverse=True)
    best = results[0]
    return {"objective": objective, "target_field": target, "feature_fields": numeric + categorical, "rows_used": int(df.count()), "models": results, "selected_model": best["model"], "selection_metric": "rmse", "explainability": {"method": "spark_model_feature_metadata", "top_features": [{"feature": f, "importance": None} for f in (numeric + categorical)[:10]], "note": "Distributed categorical encoding is included; exact grouped importance is exposed only when the fitted estimator provides stable feature attribution."}, "execution": {"engine": "SPARK", "distributed": True, "raw_rows_returned": False}, "safeguards": ["confirmed target only", "identifier exclusion", "categorical encoding with invalid-value handling", "distributed holdout evaluation", "reproducible seed", "aggregate results only"]}


def run_spark_ml(path: Path, mappings: dict[str, str], objective: str, target: str, features: list[str], seed: int = 42) -> dict[str, Any]:
    if objective == "attrition_classification":
        return _classification(path, mappings, objective, target, features, seed)
    if objective == "salary_regression":
        return _regression(path, mappings, objective, target, features, seed)
    raise ValueError("Spark supervised ML currently supports attrition classification and salary regression.")


def run_spark_clustering(path: Path, mappings: dict[str, str], features: list[str], seed: int = 42) -> dict[str, Any]:
    spark, deps = _spark()
    (_, _, _, _, _, _, _, _, _, _, VectorAssembler, _, _, _, KMeans, F) = deps
    df, usable = _load(path, mappings)
    numeric = []
    for field in features:
        if field in usable and dict(df.dtypes).get(usable[field]) in {"int", "bigint", "double", "float", "smallint", "tinyint", "long", "decimal"}:
            numeric.append(field)
    if len(numeric) < 2:
        raise ValueError("At least two numeric predictors are required for distributed clustering.")
    for field in numeric:
        df = df.withColumn(usable[field], F.col(usable[field]).cast("double"))
    df = df.dropna(subset=[usable[f] for f in numeric])
    vec = VectorAssembler(inputCols=[usable[f] for f in numeric], outputCol="__features")
    data = vec.transform(df).select("__features").cache()
    if data.limit(20).count() < 20:
        raise ValueError("At least 20 complete rows are required for clustering.")
    best, best_score = None, float("-inf")
    for k in range(2, 7):
        model = KMeans(k=k, seed=seed, featuresCol="__features", predictionCol="__cluster").fit(data)
        score = float(model.summary.trainingCost) * -1.0
        if score > best_score:
            best, best_score = k, score
    model = KMeans(k=best, seed=seed, featuresCol="__features", predictionCol="__cluster").fit(data)
    labels = model.transform(data)
    counts = {int(r["__cluster"]): int(r["count"]) for r in labels.groupBy("__cluster").count().collect()}
    total = sum(counts.values())
    data.unpersist()
    return {"objective": "employee_clustering", "rows_used": total, "feature_fields": numeric, "selected_k": best, "cluster_profiles": [{"cluster": k, "rows": v, "share": round(v / total, 4)} for k, v in sorted(counts.items())], "method": "spark_kmeans", "execution": {"engine": "SPARK", "distributed": True, "raw_rows_returned": False}, "safeguards": ["confirmed features only", "identifier exclusion", "distributed feature assembly", "aggregate cluster profiles only", "reproducible seed"]}
