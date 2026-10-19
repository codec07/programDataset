"""scikit-learn — practical single-file examples.

Install:  pip install scikit-learn pandas numpy
Run:      python sklearn_examples.py

Covers datasets, splitting, preprocessing pipelines, classification,
regression, clustering, dimensionality reduction, model selection, metrics,
and persistence. Uses small built-in or synthetic datasets so it runs offline.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn import datasets
from sklearn.cluster import DBSCAN, KMeans
from sklearn.compose import ColumnTransformer
from sklearn.datasets import make_classification, make_regression
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    cross_val_score,
    learning_curve,
    train_test_split,
)
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# 1. Datasets and splitting
# ---------------------------------------------------------------------------
def datasets_and_splitting() -> None:
    section("1. Built-in datasets and train/test splitting")

    iris = datasets.load_iris(as_frame=True)
    frame = iris.frame
    print("iris shape:", frame.shape)
    print(frame.head())
    print("\ntarget names:", iris.target_names)

    X = frame[iris.feature_names]
    y = frame["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    print("\ntrain/test sizes:", len(X_train), len(X_test))
    print("class balance (train):\n", y_train.value_counts(normalize=True).round(3))

    # Synthetic classification data with controlled difficulty
    X_syn, y_syn = make_classification(
        n_samples=500,
        n_features=8,
        n_informative=5,
        n_redundant=1,
        n_classes=2,
        flip_y=0.03,
        random_state=7,
    )
    print("\nsynthetic classification:", X_syn.shape, "positive rate:", round(float(y_syn.mean()), 3))

    # Synthetic regression data
    X_reg, y_reg = make_regression(
        n_samples=300, n_features=5, noise=12.0, bias=4.0, random_state=7
    )
    print("synthetic regression:", X_reg.shape, "target range:", round(float(y_reg.min()), 1), round(float(y_reg.max()), 1))


# ---------------------------------------------------------------------------
# 2. Preprocessing
# ---------------------------------------------------------------------------
def preprocessing() -> None:
    section("2. Scaling, encoding, imputing, and polynomial features")

    numeric = np.array([[1.0, 100.0], [2.0, 200.0], [3.0, 300.0], [4.0, 400.0]])
    scaler = StandardScaler()
    scaled = scaler.fit_transform(numeric)
    print("scaled mean:", np.round(scaled.mean(axis=0), 6))
    print("scaled std: ", np.round(scaled.std(axis=0), 6))
    print("learned mean_:", scaler.mean_)
    print("learned scale_:", scaler.scale_)

    # Categorical encoding
    colours = np.array([["red"], ["blue"], ["red"], ["green"]])
    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    encoded = encoder.fit_transform(colours)
    print("\none-hot categories:", encoder.categories_[0].tolist())
    print(encoded)
    print("feature names:", encoder.get_feature_names_out(["colour"]).tolist())

    # Label encoding for an ordinal target
    labels = np.array(["low", "medium", "high", "medium"])
    label_encoder = LabelEncoder()
    print("\nlabel encoding:", label_encoder.fit_transform(labels))
    print("classes:", label_encoder.classes_)

    # Imputation inside a pipeline (fit on train only!)
    data = pd.DataFrame(
        {
            "age": [25, np.nan, 41, 35, np.nan, 52],
            "income": [50_000, 62_000, np.nan, 71_000, 48_000, 90_000],
            "city": ["Paris", "London", "Paris", None, "Berlin", "London"],
        }
    )
    numeric_pipe = Pipeline(
        [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    categorical_pipe = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    transformer = ColumnTransformer(
        [
            ("num", numeric_pipe, ["age", "income"]),
            ("cat", categorical_pipe, ["city"]),
        ]
    )
    transformed = transformer.fit_transform(data)
    print("\nColumnTransformer output shape:", transformed.shape)

    # Polynomial features for non-linear models
    x = np.array([[1.0], [2.0], [3.0]])
    poly = PolynomialFeatures(degree=3, include_bias=False)
    print("\npolynomial features:\n", poly.fit_transform(x))
    print("feature names:", poly.get_feature_names_out(["x"]).tolist())


# ---------------------------------------------------------------------------
# 3. Classification
# ---------------------------------------------------------------------------
def classification() -> None:
    section("3. Classification models and metrics")

    iris = datasets.load_iris(as_frame=True)
    X = iris.data
    y = iris.target
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=0, stratify=y
    )

    models = {
        "logistic": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=500)
        ),
        "tree": DecisionTreeClassifier(max_depth=4, random_state=0),
        "forest": RandomForestClassifier(n_estimators=200, random_state=0),
        "boosting": GradientBoostingClassifier(random_state=0),
    }

    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        probabilities = model.predict_proba(X_test)
        accuracy = accuracy_score(y_test, predictions)
        auc = roc_auc_score(y_test, probabilities, multi_class="ovr", average="macro")
        print(f"{name:9s} accuracy={accuracy:.3f}  macro-AUC={auc:.3f}")

    # Detailed report for the best simple model
    forest = models["forest"]
    predictions = forest.predict(X_test)
    print("\nconfusion matrix:\n", confusion_matrix(y_test, predictions))
    print("\nclassification report:\n", classification_report(y_test, predictions, target_names=iris.target_names))

    # Feature importances
    importances = pd.Series(forest.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("feature importances:\n", importances.round(3))

    # A readable tree (shallow, so the text stays small)
    tree = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X_train, y_train)
    print("\nshallow tree rules:\n", export_text(tree, feature_names=list(X.columns)))


# ---------------------------------------------------------------------------
# 4. Regression
# ---------------------------------------------------------------------------
def regression() -> None:
    section("4. Regression and error metrics")

    X, y = make_regression(n_samples=400, n_features=6, noise=15.0, random_state=3)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=3)

    models = {
        "linear": LinearRegression(),
        "ridge": Ridge(alpha=2.0),
        "poly2+ridge": make_pipeline(
            PolynomialFeatures(degree=2, include_bias=False), Ridge(alpha=1.0)
        ),
    }

    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        print(
            f"{name:12s} RMSE={mean_squared_error(y_test, predictions) ** 0.5:8.2f}  "
            f"MAE={mean_absolute_error(y_test, predictions):8.2f}  "
            f"R²={r2_score(y_test, predictions):6.3f}"
        )

    best = models["ridge"]
    print("\nridge coefficients:", np.round(best.coef_, 3))
    print("ridge intercept:", round(float(best.intercept_), 3))


# ---------------------------------------------------------------------------
# 5. Clustering
# ---------------------------------------------------------------------------
def clustering() -> None:
    section("5. K-Means and DBSCAN")

    X, _ = datasets.make_blobs(
        n_samples=500, centers=4, cluster_std=1.1, random_state=11
    )

    kmeans = KMeans(n_clusters=4, n_init=10, random_state=0)
    labels = kmeans.fit_predict(X)
    print("k-means inertia:", round(float(kmeans.inertia_), 2))
    print("cluster sizes:", np.bincount(labels))
    print("silhouette:", round(float(silhouette_score(X, labels)), 3))

    # Elbow inspection without plotting
    inertias = []
    for k in range(2, 8):
        model = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
        inertias.append(round(float(model.inertia_), 1))
    print("inertia for k=2..7:", inertias)

    # DBSCAN finds arbitrary shapes and marks noise as -1
    dbscan = DBSCAN(eps=0.6, min_samples=8)
    db_labels = dbscan.fit_predict(X)
    unique = set(db_labels)
    print("\nDBSCAN clusters:", len(unique - {-1}), "noise points:", int((db_labels == -1).sum()))


# ---------------------------------------------------------------------------
# 6. Dimensionality reduction
# ---------------------------------------------------------------------------
def dimensionality_reduction() -> None:
    section("6. PCA")

    digits = datasets.load_digits()
    X = digits.data
    y = digits.target
    print("digits shape:", X.shape)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=0.90, svd_solver="full")
    X_reduced = pca.fit_transform(X_scaled)
    print("components kept for 90% variance:", pca.n_components_)
    print("explained variance ratio (first 5):", np.round(pca.explained_variance_ratio_[:5], 3))
    print("cumulative variance:", round(float(pca.explained_variance_ratio_.sum()), 3))
    print("reduced shape:", X_reduced.shape)

    # Reconstruction error with fewer components
    pca_small = PCA(n_components=10, random_state=0)
    projected = pca_small.fit_transform(X_scaled)
    reconstructed = pca_small.inverse_transform(projected)
    print("10-component reconstruction MSE:", round(float(np.mean((X_scaled - reconstructed) ** 2)), 4))


# ---------------------------------------------------------------------------
# 7. Model selection
# ---------------------------------------------------------------------------
def model_selection() -> None:
    section("7. Cross-validation, grid search, and learning curves")

    iris = datasets.load_iris(as_frame=True)
    X, y = iris.data, iris.target
    pipeline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500))

    scores = cross_val_score(pipeline, X, y, cv=5, scoring="accuracy")
    print("5-fold accuracy:", np.round(scores, 3), "mean:", round(float(scores.mean()), 3))

    param_grid = {
        "logisticregression__C": [0.01, 0.1, 1.0, 10.0],
        "logisticregression__penalty": ["l2"],
    }
    search = GridSearchCV(pipeline, param_grid, cv=5, scoring="accuracy", n_jobs=1)
    search.fit(X, y)
    print("\nbest params:", search.best_params_)
    print("best CV score:", round(float(search.best_score_), 3))

    # Learning curve: does more data help?
    sizes, train_scores, validation_scores = learning_curve(
        pipeline, X, y, cv=5, train_sizes=np.linspace(0.3, 1.0, 4), scoring="accuracy"
    )
    print("\nlearning curve")
    for size, train, validation in zip(sizes, train_scores.mean(axis=1), validation_scores.mean(axis=1)):
        print(f"  n={int(size):3d}  train={train:.3f}  validation={validation:.3f}")


# ---------------------------------------------------------------------------
# 8. Persistence
# ---------------------------------------------------------------------------
def persistence() -> None:
    section("8. Saving and loading a fitted pipeline")

    import joblib

    iris = datasets.load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, random_state=42
    )
    pipeline = make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=100, random_state=0))
    pipeline.fit(X_train, y_train)

    workdir = Path(tempfile.mkdtemp(prefix="sklearn_examples_"))
    model_path = workdir / "iris_pipeline.joblib"
    joblib.dump(pipeline, model_path)
    print("saved model:", model_path, f"({model_path.stat().st_size:,} bytes)")

    loaded = joblib.load(model_path)
    print("predictions match:", bool(np.array_equal(pipeline.predict(X_test), loaded.predict(X_test))))
    print("test accuracy:", round(float(accuracy_score(y_test, loaded.predict(X_test))), 3))


def main() -> None:
    datasets_and_splitting()
    preprocessing()
    classification()
    regression()
    clustering()
    dimensionality_reduction()
    model_selection()
    persistence()

    print("\nAll scikit-learn example sections completed.")


if __name__ == "__main__":
    main()
