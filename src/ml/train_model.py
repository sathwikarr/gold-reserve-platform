"""
ML Model Training — V4 Machine Learning Model
Trains two models from scratch using NumPy only (no sklearn/XGBoost dependency):

Model 1: Logistic Regression (gradient descent)
  - Binary cross-entropy loss
  - L2 regularization
  - Standardized features
  - Convergence tracked via loss curve

Model 2: Gradient Boosting Classifier (numpy implementation)
  - Builds an ensemble of shallow decision stumps
  - Each stump fits residuals from previous ensemble
  - Equivalent conceptually to XGBoost with max_depth=1
  - More robust to feature scale differences than logistic regression

Both models output:
  - Accuracy, Precision, Recall, F1 on test set
  - Feature importance / coefficients
  - Probability scores per country-year (for prediction in predict.py)

Input:  data/curated/ml_features.csv
Output: data/curated/ml_predictions.csv
        data/curated/ml_feature_importance.csv
        docs/ml_confusion_matrix.png
        docs/ml_feature_importance.png
        docs/ml_roc_curves.png
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import logging
from pathlib import Path

CURATED_DIR = Path(__file__).resolve().parents[2] / "data" / "curated"
DOCS_DIR    = Path(__file__).resolve().parents[2] / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── Feature columns (must match prepare_features.py) ─────────────────────────
FEATURE_COLS = [
    "gold_share_pct", "accumulation_streak", "gold_yoy_change_pct",
    "gold_share_yoy_change", "gold_share_vs_world", "country_share_of_world_gold_pct",
    "usd_share_drawdown_pct", "usd_share_yoy_change", "accumulating_during_usd_decline",
    "sanctions_score", "geo_risk_score", "un_alignment_score",
    "global_usd_negative_pct", "global_usd_positive_pct", "world_gold_share_pct",
]
TARGET_COL = "will_accumulate_next_year"


# ── Logistic Regression ───────────────────────────────────────────────────────

class LogisticRegression:
    """Binary logistic regression trained via gradient descent with L2 regularization."""

    def __init__(self, lr=0.01, epochs=2000, lambda_=0.01):
        self.lr      = lr
        self.epochs  = epochs
        self.lambda_ = lambda_
        self.weights = None
        self.bias    = None
        self.losses  = []

    @staticmethod
    def _sigmoid(z):
        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))

    def fit(self, X: np.ndarray, y: np.ndarray):
        n, p = X.shape
        self.weights = np.zeros(p)
        self.bias    = 0.0

        # Class weights to handle imbalance
        n1 = y.sum()
        n0 = n - n1
        w1 = n / (2 * n1) if n1 > 0 else 1.0
        w0 = n / (2 * n0) if n0 > 0 else 1.0
        sample_weights = np.where(y == 1, w1, w0)

        for epoch in range(self.epochs):
            z    = X @ self.weights + self.bias
            pred = self._sigmoid(z)
            err  = (pred - y) * sample_weights

            # Gradients
            dw = (1/n) * X.T @ err + self.lambda_ * self.weights
            db = (1/n) * np.sum(err)

            self.weights -= self.lr * dw
            self.bias    -= self.lr * db

            # Weighted log loss
            eps  = 1e-15
            loss = -(1/n) * np.sum(sample_weights * (y * np.log(pred + eps) + (1 - y) * np.log(1 - pred + eps)))
            self.losses.append(loss)

        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._sigmoid(X @ self.weights + self.bias)

    def predict(self, X: np.ndarray, threshold=0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)


# ── Gradient Boosting (decision stumps) ──────────────────────────────────────

class DecisionStump:
    """Single-feature threshold classifier — the base learner for gradient boosting."""

    def __init__(self):
        self.feature_idx = None
        self.threshold   = None
        self.left_val    = None
        self.right_val   = None

    def fit(self, X: np.ndarray, residuals: np.ndarray):
        n, p = X.shape
        best_loss = np.inf

        for j in range(p):
            col    = X[:, j]
            thresholds = np.percentile(col, [20, 40, 60, 80])

            for thresh in thresholds:
                left_mask  = col <= thresh
                right_mask = ~left_mask

                if left_mask.sum() < 5 or right_mask.sum() < 5:
                    continue

                left_pred  = residuals[left_mask].mean()
                right_pred = residuals[right_mask].mean()

                pred = np.where(left_mask, left_pred, right_pred)
                loss = np.mean((residuals - pred) ** 2)

                if loss < best_loss:
                    best_loss        = loss
                    self.feature_idx = j
                    self.threshold   = thresh
                    self.left_val    = left_pred
                    self.right_val   = right_pred

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        col = X[:, self.feature_idx]
        return np.where(col <= self.threshold, self.left_val, self.right_val)


class GradientBoostingClassifier:
    """
    Gradient boosting with decision stumps.
    Uses log-loss / logistic regression objective.
    """

    def __init__(self, n_estimators=100, lr=0.1):
        self.n_estimators  = n_estimators
        self.lr            = lr
        self.stumps        = []
        self.initial_pred  = None
        self.feature_importance_ = None

    @staticmethod
    def _sigmoid(z):
        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))

    def fit(self, X: np.ndarray, y: np.ndarray):
        # Initialize with log-odds but bias toward balanced prediction
        # Use 0.5 as init to avoid always predicting majority class
        self.initial_pred = 0.0
        F = np.full(len(y), self.initial_pred)

        # Class weights for balanced learning
        n  = len(y)
        n1 = y.sum()
        n0 = n - n1
        w1 = n / (2 * n1) if n1 > 0 else 1.0
        w0 = n / (2 * n0) if n0 > 0 else 1.0
        sample_weights = np.where(y == 1, w1, w0)

        feat_scores = np.zeros(X.shape[1])

        for _ in range(self.n_estimators):
            # Weighted negative gradient of log-loss
            residuals = sample_weights * (y - self._sigmoid(F))

            stump = DecisionStump()
            stump.fit(X, residuals)
            update = stump.predict(X)

            F += self.lr * update
            self.stumps.append(stump)

            if stump.feature_idx is not None:
                feat_scores[stump.feature_idx] += abs(update).mean()

        # Normalize feature importance
        total = feat_scores.sum()
        self.feature_importance_ = feat_scores / total if total > 0 else feat_scores
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        F = np.full(len(X), self.initial_pred)
        for stump in self.stumps:
            F += self.lr * stump.predict(X)
        return self._sigmoid(F)

    def predict(self, X: np.ndarray, threshold=0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)


# ── Evaluation metrics ────────────────────────────────────────────────────────

def evaluate(y_true, y_pred, y_prob, name):
    tp = ((y_pred == 1) & (y_true == 1)).sum()
    tn = ((y_pred == 0) & (y_true == 0)).sum()
    fp = ((y_pred == 1) & (y_true == 0)).sum()
    fn = ((y_pred == 0) & (y_true == 1)).sum()

    acc  = (tp + tn) / len(y_true)
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec  = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0

    # AUC-ROC — iterate thresholds high→low so FPR increases monotonically
    thresholds = np.linspace(1, 0, 100)
    tprs, fprs = [], []
    for t in thresholds:
        p = (y_prob >= t).astype(int)
        tpr = ((p == 1) & (y_true == 1)).sum() / max((y_true == 1).sum(), 1)
        fpr = ((p == 1) & (y_true == 0)).sum() / max((y_true == 0).sum(), 1)
        tprs.append(tpr)
        fprs.append(fpr)
    auc = float(np.trapezoid(tprs, fprs))

    log.info(f"\n{name} Results:")
    log.info(f"  Accuracy  : {acc:.4f}")
    log.info(f"  Precision : {prec:.4f}")
    log.info(f"  Recall    : {rec:.4f}")
    log.info(f"  F1        : {f1:.4f}")
    log.info(f"  AUC-ROC   : {auc:.4f}")
    log.info(f"  Confusion : TP={tp} TN={tn} FP={fp} FN={fn}")

    return {"model": name, "accuracy": round(acc,4), "precision": round(prec,4),
            "recall": round(rec,4), "f1": round(f1,4), "auc_roc": round(auc,4),
            "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
            "tprs": tprs, "fprs": fprs}


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_feature_importance(lr_coefs, gb_importance, feature_names):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Feature Importance — V4 ML Model", fontsize=14, fontweight="bold")

    # LR coefficients
    ax = axes[0]
    sorted_idx = np.argsort(np.abs(lr_coefs))
    colors = ["#C0392B" if c < 0 else "#1F3A6E" for c in lr_coefs[sorted_idx]]
    ax.barh(np.array(feature_names)[sorted_idx], lr_coefs[sorted_idx], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Logistic Regression Coefficients")
    ax.set_xlabel("Coefficient Value")

    # GB importance
    ax = axes[1]
    sorted_idx = np.argsort(gb_importance)
    ax.barh(np.array(feature_names)[sorted_idx], gb_importance[sorted_idx], color="#B8860B")
    ax.set_title("Gradient Boosting Feature Importance")
    ax.set_xlabel("Relative Importance")

    plt.tight_layout()
    path = DOCS_DIR / "ml_feature_importance.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Saved → {path}")


def plot_roc_curves(results):
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = {"Logistic Regression": "#1F3A6E", "Gradient Boosting": "#B8860B"}
    for r in results:
        ax.plot(r["fprs"], r["tprs"], label=f"{r['model']} (AUC={r['auc_roc']:.3f})",
                color=colors.get(r["model"], "gray"), linewidth=2)
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Random (AUC=0.5)")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves — Gold Accumulation Prediction")
    ax.legend()
    ax.grid(alpha=0.3)
    path = DOCS_DIR / "ml_roc_curves.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Saved → {path}")


def plot_confusion_matrices(results):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle("Confusion Matrices — Test Set (2020–latest)", fontsize=13, fontweight="bold")
    for ax, r in zip(axes, results):
        cm = np.array([[r["tn"], r["fp"]], [r["fn"], r["tp"]]])
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred: No", "Pred: Yes"])
        ax.set_yticklabels(["Actual: No", "Actual: Yes"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        fontsize=14, color="white" if cm[i, j] > cm.max()/2 else "black")
        ax.set_title(r["model"])
    plt.tight_layout()
    path = DOCS_DIR / "ml_confusion_matrix.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"Saved → {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    log.info("=" * 60)
    log.info("ML Model Training — V4")
    log.info("=" * 60)

    df = pd.read_csv(CURATED_DIR / "ml_features.csv")

    train = df[df["year"] <= 2019]
    test  = df[df["year"] >= 2020]

    X_train = train[FEATURE_COLS].values
    y_train = train[TARGET_COL].values
    X_test  = test[FEATURE_COLS].values
    y_test  = test[TARGET_COL].values

    log.info(f"Train: {X_train.shape} | Test: {X_test.shape}")

    # Standardize features — handle NaN and zero variance
    mean = np.nanmean(X_train, axis=0)
    std  = np.nanstd(X_train, axis=0)
    std[std == 0] = 1  # avoid division by zero

    def standardize(X, mean, std):
        Xs = (X - mean) / std
        Xs = np.nan_to_num(Xs, nan=0.0, posinf=0.0, neginf=0.0)
        return Xs

    X_train_s = standardize(X_train, mean, std)
    X_test_s  = standardize(X_test, mean, std)

    # ── Model 1: Logistic Regression ──────────────────────────────────────────
    log.info("\nTraining Logistic Regression...")
    lr_model = LogisticRegression(lr=0.05, epochs=3000, lambda_=0.01)
    lr_model.fit(X_train_s, y_train)

    lr_train_prob = lr_model.predict_proba(X_train_s)
    lr_test_prob  = lr_model.predict_proba(X_test_s)
    lr_test_pred  = lr_model.predict(X_test_s)

    lr_results = evaluate(y_test, lr_test_pred, lr_test_prob, "Logistic Regression")

    # ── Model 2: Gradient Boosting ────────────────────────────────────────────
    log.info("\nTraining Gradient Boosting...")
    gb_model = GradientBoostingClassifier(n_estimators=150, lr=0.08)
    gb_model.fit(X_train, y_train)

    gb_test_prob = gb_model.predict_proba(X_test)
    gb_test_pred = gb_model.predict(X_test)

    gb_results = evaluate(y_test, gb_test_pred, gb_test_prob, "Gradient Boosting")

    # ── Ensemble: average probabilities ──────────────────────────────────────
    log.info("\nEnsemble (average of both models):")
    ensemble_prob = (lr_test_prob + gb_test_prob) / 2
    ensemble_pred = (ensemble_prob >= 0.5).astype(int)
    ens_results = evaluate(y_test, ensemble_pred, ensemble_prob, "Ensemble")

    # ── Save predictions on full dataset ─────────────────────────────────────
    # Re-score entire dataset for prediction output
    X_all   = df[FEATURE_COLS].values
    X_all_s = standardize(X_all, mean, std)

    df["lr_prob"]       = lr_model.predict_proba(X_all_s).round(4)
    df["gb_prob"]       = gb_model.predict_proba(X_all).round(4)
    df["ensemble_prob"] = ((df["lr_prob"] + df["gb_prob"]) / 2).round(4)

    pred_path = CURATED_DIR / "ml_predictions.csv"
    df.to_csv(pred_path, index=False)
    log.info(f"\nSaved predictions → {pred_path}")

    # ── Feature importance ────────────────────────────────────────────────────
    # LR: use standardized coefficients (magnitude = importance)
    lr_coefs_std = lr_model.weights  # already standardized

    feat_imp = pd.DataFrame({
        "feature":        FEATURE_COLS,
        "lr_coefficient": lr_coefs_std.round(4),
        "gb_importance":  gb_model.feature_importance_.round(4),
    }).sort_values("gb_importance", ascending=False)

    feat_imp_path = CURATED_DIR / "ml_feature_importance.csv"
    feat_imp.to_csv(feat_imp_path, index=False)
    log.info(f"Saved feature importance → {feat_imp_path}")
    log.info(f"\nTop 10 features (Gradient Boosting):\n{feat_imp.head(10).to_string(index=False)}")

    # ── Model comparison ──────────────────────────────────────────────────────
    metrics = pd.DataFrame([
        {k: v for k, v in r.items() if k not in ("tprs", "fprs")}
        for r in [lr_results, gb_results, ens_results]
    ])
    log.info(f"\nModel Comparison:\n{metrics[['model','accuracy','precision','recall','f1','auc_roc']].to_string(index=False)}")
    metrics.to_csv(CURATED_DIR / "ml_model_metrics.csv", index=False)

    # ── Plots ─────────────────────────────────────────────────────────────────
    plot_feature_importance(lr_coefs_std, gb_model.feature_importance_, FEATURE_COLS)
    plot_roc_curves([lr_results, gb_results])
    plot_confusion_matrices([lr_results, gb_results])

    return lr_model, gb_model, mean, std, metrics, feat_imp


if __name__ == "__main__":
    run()
