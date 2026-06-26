#!/usr/bin/env python3
"""
Generate validation and presentation-readiness outputs for the SJGHC case study.

This script is intentionally separate from the notebook JSON generators so the
critical checks can be re-run in a clean environment:
- leakage and feature availability audit
- baseline, linear, random forest, and XGBoost comparison
- random and time-based split evaluation
- segment performance and high-cost capture
- data-quality summary
- local-only worst prediction review file
- SHAP waterfall/dependence figures
"""
from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
FIGS = ROOT / "figures"
DATA = ROOT / "data" / "processed" / "hcp_clean.parquet"
REPORTS.mkdir(exist_ok=True)
FIGS.mkdir(exist_ok=True)

RANDOM_STATE = 42
TARGET = "total_charge_aud"

FEATURE_COLS = [
    "LOS",
    "Age",
    "comorbidity_count",
    "procedure_count",
    "MDC_enc",
    "Sex",
    "CareType",
    "UrgencyOfAdmission",
    "SameDayStatus",
    "ModeOfSeparation",
    "adm_month",
]

FEATURE_DISPLAY = {
    "LOS": "Length of stay",
    "Age": "Age",
    "comorbidity_count": "Recorded comorbidity count",
    "procedure_count": "Recorded procedure count",
    "MDC_enc": "MDC",
    "Sex": "Sex",
    "CareType": "Care type",
    "UrgencyOfAdmission": "Admission urgency",
    "SameDayStatus": "Same-day status",
    "ModeOfSeparation": "Mode of separation",
    "adm_month": "Admission month",
}

FEATURE_GROUP = {
    "LOS": "Operational/utilisation",
    "Age": "Demographic",
    "comorbidity_count": "Clinical summary",
    "procedure_count": "Clinical summary",
    "MDC_enc": "Clinical grouping",
    "Sex": "Demographic",
    "CareType": "Administrative/clinical",
    "UrgencyOfAdmission": "Administrative",
    "SameDayStatus": "Operational/utilisation",
    "ModeOfSeparation": "Administrative/outcome",
    "adm_month": "Temporal",
}

FEATURE_AVAILABILITY = {
    "LOS": "After episode completion",
    "Age": "At admission",
    "comorbidity_count": "After episode completion",
    "procedure_count": "After episode completion",
    "MDC_enc": "After coding/final DRG grouping",
    "Sex": "At admission",
    "CareType": "At admission or during episode",
    "UrgencyOfAdmission": "At admission",
    "SameDayStatus": "After episode completion",
    "ModeOfSeparation": "After episode completion",
    "adm_month": "At admission",
}

FEATURE_RATIONALE = {
    "LOS": "Captures realised utilisation; makes this an episode-completion benchmarking model.",
    "Age": "Demographic case-mix signal available before modelling.",
    "comorbidity_count": "Summary of recorded additional diagnoses and clinical complexity.",
    "procedure_count": "Summary of recorded interventions and clinical activity.",
    "MDC_enc": "Broad final diagnostic grouping derived from DRG.",
    "Sex": "Case-mix descriptor.",
    "CareType": "Administrative/clinical care stream.",
    "UrgencyOfAdmission": "Emergency/elective status.",
    "SameDayStatus": "Separates same-day and overnight activity profiles.",
    "ModeOfSeparation": "Final episode separation status; useful for completed episode review.",
    "adm_month": "Observed month-level variation over the study period.",
}


@dataclass
class SplitData:
    name: str
    train_idx: np.ndarray
    test_idx: np.ndarray


def aud_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.clip(np.asarray(y_pred, dtype=float), 0, None)
    return {
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
        "R2": round(float(r2_score(y_true, y_pred)), 4) if len(y_true) > 1 else np.nan,
    }


def predict_aud_from_log(model, x: pd.DataFrame) -> np.ndarray:
    return np.expm1(model.predict(x)).clip(min=0)


def xgb_model(n_estimators: int = 350, early_stopping: bool = False) -> XGBRegressor:
    kwargs = {
        "n_estimators": n_estimators,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.80,
        "colsample_bytree": 0.80,
        "min_child_weight": 10,
        "gamma": 0.05,
        "reg_alpha": 0.10,
        "reg_lambda": 1.0,
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
        "verbosity": 0,
        "eval_metric": "rmse",
    }
    if early_stopping:
        kwargs["early_stopping_rounds"] = 50
    return XGBRegressor(**kwargs)


def prepare_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    df = df.copy()
    df["MDC_enc"] = LabelEncoder().fit_transform(df["MDC"].fillna("Z").astype(str))
    df["adm_month"] = df["AdmissionDate_dt"].dt.month.astype("int16")
    x = df[FEATURE_COLS].copy()
    y_aud = df[TARGET].astype(float)
    y_log = np.log1p(y_aud.clip(lower=0))
    return df, x, y_log, y_aud


def charge_columns(df: pd.DataFrame) -> list[str]:
    return [
        c
        for c in df.columns
        if c.endswith("Charge") or c.endswith("Charges") or c.endswith("Benefit")
    ]


def write_feature_and_leakage_outputs(df: pd.DataFrame) -> dict[str, object]:
    target_cols = charge_columns(df)
    feature_rows = []
    for feature in FEATURE_COLS:
        is_contaminating = any(token.lower() in feature.lower() for token in ["charge", "charges", "benefit"])
        feature_rows.append(
            {
                "feature": feature,
                "display_name": FEATURE_DISPLAY[feature],
                "feature_group": FEATURE_GROUP[feature],
                "availability": FEATURE_AVAILABILITY[feature],
                "included_in_model": True,
                "target_contamination_risk": "yes" if is_contaminating else "no",
                "rationale": FEATURE_RATIONALE[feature],
            }
        )
    pd.DataFrame(feature_rows).to_csv(REPORTS / "feature_list.csv", index=False)

    feature_set = set(FEATURE_COLS)
    target_set = set(target_cols)
    overlap = sorted(feature_set & target_set)
    leakage_rows = [
        {
            "check": "target_component_features_excluded",
            "status": "pass" if not overlap else "fail",
            "affected_columns": "; ".join(overlap),
            "detail": "No charge/benefit target component is used as a model feature."
            if not overlap
            else "Target component columns are present in the feature matrix.",
        },
        {
            "check": "feature_count_documented",
            "status": "pass" if len(FEATURE_COLS) == 11 else "review",
            "affected_columns": "; ".join(FEATURE_COLS),
            "detail": f"{len(FEATURE_COLS)} model features documented in feature_list.csv.",
        },
        {
            "check": "episode_completion_scope",
            "status": "pass",
            "affected_columns": "LOS; procedure_count; comorbidity_count; SameDayStatus; ModeOfSeparation; MDC_enc",
            "detail": "Several features are known only after completion/coding, so the model is scoped to completed episode benchmarking.",
        },
    ]
    pd.DataFrame(leakage_rows).to_csv(REPORTS / "leakage_audit.csv", index=False)

    composition = []
    for col in target_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        nonzero = s.fillna(0) != 0
        composition.append(
            {
                "charge_component": col,
                "missing_count": int(s.isna().sum()),
                "nonzero_count": int(nonzero.sum()),
                "total_aud": round(float(s.fillna(0).sum() / 100), 2),
                "median_nonzero_aud": round(float((s[nonzero] / 100).median()), 2) if nonzero.any() else 0.0,
            }
        )
    target_recalc = df[target_cols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1) / 100
    max_diff = float((target_recalc - df[TARGET]).abs().max())
    pd.DataFrame(composition).to_csv(REPORTS / "target_composition.csv", index=False)

    return {
        "target_component_columns": target_cols,
        "feature_target_overlap": overlap,
        "target_reconciliation_max_abs_diff_aud": round(max_diff, 6),
    }


def write_data_quality_output(df: pd.DataFrame) -> pd.DataFrame:
    string_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    null_like = {"", "nan", "none", "na", "<na>", "nat", "null"}
    if string_cols:
        whitespace_mask = pd.DataFrame(
            {
                c: df[c].astype(str).str.strip().str.lower().isin(null_like)
                for c in string_cols
            }
        )
        whitespace_rows = whitespace_mask.any(axis=1)
        whitespace_cells = int(whitespace_mask.to_numpy().sum())
    else:
        whitespace_rows = pd.Series(False, index=df.index)
        whitespace_cells = 0

    checks: list[dict[str, object]] = []

    def add_check(name: str, mask: pd.Series, detail: str, affected_cells: int | None = None) -> None:
        checks.append(
            {
                "check": name,
                "affected_rows": int(mask.sum()),
                "affected_pct": round(float(mask.mean() * 100), 3),
                "affected_cells": "" if affected_cells is None else affected_cells,
                "detail": detail,
            }
        )

    add_check("negative_los", df["LOS"] < 0, "LOS is negative.")
    add_check(
        "same_day_code_date_mismatch",
        ((df["SameDayStatus"] == 1) & (df["LOS"] != 0))
        | ((df["SameDayStatus"] == 2) & (df["LOS"] == 0)),
        "SameDayStatus does not match admission/separation dates as represented by LOS.",
    )
    add_check(
        "invalid_same_day_status_code",
        ~df["SameDayStatus"].isin([1, 2]),
        "SameDayStatus is outside expected codes 1=same-day, 2=overnight/multi-day.",
    )
    add_check(
        "icu_charge_without_icu_days_or_hours",
        (pd.to_numeric(df["ICU_Charge"], errors="coerce").fillna(0) > 0)
        & (pd.to_numeric(df["ICU_Days"], errors="coerce").fillna(0) <= 0)
        & (pd.to_numeric(df["ICU_Hours"], errors="coerce").fillna(0) <= 0),
        "ICU_Charge exists but ICU_Days and ICU_Hours are zero.",
    )
    add_check(
        "theatre_charge_without_theatre_minutes",
        (pd.to_numeric(df["TheatreCharge"], errors="coerce").fillna(0) > 0)
        & (pd.to_numeric(df["TheatreMinutes"], errors="coerce").fillna(0) <= 0),
        "TheatreCharge exists but TheatreMinutes is zero.",
    )
    add_check("total_charge_zero", df[TARGET].fillna(0) == 0, "Total episode charge equals zero.")
    add_check(
        "whitespace_based_missing_values",
        whitespace_rows,
        "At least one string/object field is blank after stripping whitespace.",
        affected_cells=whitespace_cells,
    )
    add_check(
        "duplicate_episode_identifier",
        df["EpisodeIdentifier"].duplicated(keep=False),
        "EpisodeIdentifier appears more than once.",
    )
    add_check("missing_target_values", df[TARGET].isna(), "Target value is missing.")

    out = pd.DataFrame(checks)
    out.to_csv(REPORTS / "data_quality_summary.csv", index=False)
    return out


def build_splits(df: pd.DataFrame) -> list[SplitData]:
    all_idx = df.index.to_numpy()
    train_idx, test_idx = train_test_split(all_idx, test_size=0.20, random_state=RANDOM_STATE)

    ordered = df.sort_values("AdmissionDate_dt").index.to_numpy()
    n_test = int(round(len(ordered) * 0.20))
    time_train, time_test = ordered[:-n_test], ordered[-n_test:]
    return [
        SplitData("random_80_20", train_idx, test_idx),
        SplitData("time_last_20_pct_by_admission_date", time_train, time_test),
    ]


def evaluate_models(x: pd.DataFrame, y_log: pd.Series, y_aud: pd.Series, splits: list[SplitData]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for split in splits:
        x_train, x_test = x.loc[split.train_idx], x.loc[split.test_idx]
        y_train_log, y_test_aud = y_log.loc[split.train_idx], y_aud.loc[split.test_idx]
        y_train_aud = y_aud.loc[split.train_idx]

        baselines = {
            "Mean baseline": float(y_train_aud.mean()),
            "Median baseline": float(y_train_aud.median()),
        }
        for name, constant in baselines.items():
            metrics = aud_metrics(y_test_aud, np.repeat(constant, len(y_test_aud)))
            rows.append({"Split": split.name, "Model": name, **metrics})

        lin = LinearRegression()
        lin.fit(x_train, y_train_log)
        rows.append(
            {
                "Split": split.name,
                "Model": "Linear Regression",
                **aud_metrics(y_test_aud, np.expm1(lin.predict(x_test)).clip(min=0)),
            }
        )

        rf = RandomForestRegressor(
            n_estimators=220,
            min_samples_leaf=8,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        rf.fit(x_train, y_train_log)
        rows.append(
            {
                "Split": split.name,
                "Model": "Random Forest",
                **aud_metrics(y_test_aud, predict_aud_from_log(rf, x_test)),
            }
        )

        xgb = xgb_model(n_estimators=350)
        xgb.fit(x_train, y_train_log)
        rows.append(
            {
                "Split": split.name,
                "Model": "XGBoost",
                **aud_metrics(y_test_aud, predict_aud_from_log(xgb, x_test)),
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "model_comparison.csv", index=False)
    return out


def fit_final_xgb(
    x: pd.DataFrame, y_log: pd.Series, y_aud: pd.Series, split: SplitData
) -> tuple[XGBRegressor, pd.DataFrame, pd.Series, np.ndarray, dict[str, object]]:
    x_train, x_test = x.loc[split.train_idx], x.loc[split.test_idx]
    y_train_log = y_log.loc[split.train_idx]
    y_test_aud = y_aud.loc[split.test_idx]

    model = xgb_model(n_estimators=350)
    model.fit(x_train, y_train_log)
    pred_aud = predict_aud_from_log(model, x_test)
    metrics = aud_metrics(y_test_aud, pred_aud)

    cv_model = xgb_model(n_estimators=220)
    kf = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(
        cv_model,
        x_train,
        y_train_log,
        cv=kf,
        scoring="neg_root_mean_squared_error",
        n_jobs=-1,
    )
    cv_rmse = -cv_scores

    positive_charge = y_test_aud.to_numpy() > 0
    mape = (
        float(
            np.mean(
                np.abs(
                    (
                        y_test_aud.to_numpy()[positive_charge]
                        - pred_aud[positive_charge]
                    )
                    / y_test_aud.to_numpy()[positive_charge]
                )
            )
            * 100
        )
        if positive_charge.any()
        else np.nan
    )

    final = {
        "log_rmse": round(
            float(np.sqrt(mean_squared_error(y_log.loc[split.test_idx], model.predict(x_test)))), 4
        ),
        "log_r2": round(float(r2_score(y_log.loc[split.test_idx], model.predict(x_test))), 4),
        "aud_rmse": metrics["RMSE"],
        "aud_mae": metrics["MAE"],
        "aud_r2": metrics["R2"],
        "mape_pct": round(mape, 2),
        "n_train": int(len(split.train_idx)),
        "n_test": int(len(split.test_idx)),
        "best_iter": int(
            (getattr(model, "best_iteration", None) + 1)
            if getattr(model, "best_iteration", None) is not None
            else model.n_estimators
        ),
        "features": FEATURE_COLS,
        "cv_rmse_mean": round(float(cv_rmse.mean()), 4),
        "cv_rmse_std": round(float(cv_rmse.std()), 4),
        "cv_rmse_scale": "log-transformed target",
    }
    return model, x_test, y_test_aud, pred_aud, final


def segment_metrics(
    df: pd.DataFrame,
    split: SplitData,
    y_test_aud: pd.Series,
    pred_aud: np.ndarray,
    train_y_aud: pd.Series,
) -> pd.DataFrame:
    test_meta = df.loc[split.test_idx].copy()
    test_meta["_actual"] = y_test_aud.to_numpy()
    test_meta["_pred"] = pred_aud

    rows: list[dict[str, object]] = []

    def add_segment(segment_type: str, segment: str, mask: pd.Series) -> None:
        sub = test_meta.loc[mask]
        if sub.empty:
            return
        metrics = aud_metrics(sub["_actual"], sub["_pred"])
        rows.append(
            {
                "segment_type": segment_type,
                "segment": segment,
                "n": int(len(sub)),
                "median_actual_charge_aud": round(float(sub["_actual"].median()), 2),
                **metrics,
            }
        )

    add_segment("stay_type", "Same-day", test_meta["SameDayStatus"] == 1)
    add_segment("stay_type", "Overnight/multi-day", test_meta["SameDayStatus"] == 2)

    low_cut = float(train_y_aud.quantile(0.50))
    high_cut = float(train_y_aud.quantile(0.90))
    add_segment("charge_band", f"Low-cost <= train median ${low_cut:,.0f}", test_meta["_actual"] <= low_cut)
    add_segment(
        "charge_band",
        f"Mid-cost train median to P90 ${low_cut:,.0f}-${high_cut:,.0f}",
        (test_meta["_actual"] > low_cut) & (test_meta["_actual"] <= high_cut),
    )
    add_segment("charge_band", f"High-cost > train P90 ${high_cut:,.0f}", test_meta["_actual"] > high_cut)

    for mdc, sub in test_meta.groupby("MDC", dropna=False):
        label = str(sub["MDC_label"].iloc[0]) if "MDC_label" in sub else ""
        add_segment("MDC", f"{mdc} - {label}", test_meta.index.isin(sub.index))

    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "segment_performance.csv", index=False)
    return out


def write_worst_predictions(
    df: pd.DataFrame,
    split: SplitData,
    y_test_aud: pd.Series,
    pred_aud: np.ndarray,
    n: int = 50,
) -> pd.DataFrame:
    out = df.loc[split.test_idx, [
        "MDC",
        "MDC_label",
        "LOS",
        "procedure_count",
        "SameDayStatus",
        "comorbidity_count",
        "Age",
        "CareType",
        "UrgencyOfAdmission",
    ]].copy()
    out.insert(0, "source_row_index", out.index)
    out["actual_charge_aud"] = y_test_aud.to_numpy()
    out["predicted_charge_aud"] = pred_aud
    out["absolute_error_aud"] = (out["actual_charge_aud"] - out["predicted_charge_aud"]).abs()
    out["signed_error_aud"] = out["predicted_charge_aud"] - out["actual_charge_aud"]
    out = out.sort_values("absolute_error_aud", ascending=False).head(n)
    for col in ["actual_charge_aud", "predicted_charge_aud", "absolute_error_aud", "signed_error_aud"]:
        out[col] = out[col].round(2)
    out.to_csv(REPORTS / "worst_predictions.csv", index=False)
    return out


def high_cost_capture(
    split: SplitData,
    y_train_aud: pd.Series,
    y_test_aud: pd.Series,
    pred_aud: np.ndarray,
) -> pd.DataFrame:
    actual_threshold = float(y_train_aud.quantile(0.90))
    pred_threshold = float(np.quantile(pred_aud, 0.90))
    actual_high = y_test_aud.to_numpy() >= actual_threshold
    predicted_high = pred_aud >= pred_threshold
    true_positive = actual_high & predicted_high
    row = {
        "split": split.name,
        "actual_high_cost_definition": "actual charge >= train P90",
        "predicted_high_cost_definition": "predicted charge >= test prediction P90",
        "actual_high_threshold_aud": round(actual_threshold, 2),
        "predicted_high_threshold_aud": round(pred_threshold, 2),
        "actual_high_n": int(actual_high.sum()),
        "predicted_high_n": int(predicted_high.sum()),
        "true_positive_n": int(true_positive.sum()),
        "top_decile_recall": round(float(true_positive.sum() / actual_high.sum()), 4) if actual_high.any() else np.nan,
        "top_decile_precision": round(float(true_positive.sum() / predicted_high.sum()), 4) if predicted_high.any() else np.nan,
    }
    out = pd.DataFrame([row])
    out.to_csv(REPORTS / "high_cost_capture.csv", index=False)
    return out


def ablation_output(
    x: pd.DataFrame,
    y_log: pd.Series,
    y_aud: pd.Series,
    split: SplitData,
) -> pd.DataFrame:
    groups = {
        "Demographics only": ["Age", "Sex"],
        "Clinical only": ["comorbidity_count", "procedure_count", "MDC_enc", "CareType", "UrgencyOfAdmission"],
        "Operational only": ["LOS", "SameDayStatus", "ModeOfSeparation", "adm_month"],
        "No LOS/procedure count": [
            "Age",
            "comorbidity_count",
            "MDC_enc",
            "Sex",
            "CareType",
            "UrgencyOfAdmission",
            "SameDayStatus",
            "ModeOfSeparation",
            "adm_month",
        ],
        "Full model": FEATURE_COLS,
    }
    rows = []
    for name, cols in groups.items():
        model = xgb_model(n_estimators=260)
        model.fit(x.loc[split.train_idx, cols], y_log.loc[split.train_idx])
        pred = predict_aud_from_log(model, x.loc[split.test_idx, cols])
        rows.append(
            {
                "feature_set": name,
                "features": "; ".join(cols),
                "n_features": len(cols),
                **aud_metrics(y_aud.loc[split.test_idx], pred),
            }
        )
    out = pd.DataFrame(rows).sort_values("RMSE")
    out.to_csv(REPORTS / "feature_ablation.csv", index=False)
    return out


def save_actual_vs_predicted(y_test_aud: pd.Series, pred_aud: np.ndarray, metrics: dict[str, object]) -> None:
    import matplotlib.ticker as mticker

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    clip_val = np.percentile(y_test_aud, 97)
    mask97 = y_test_aud.to_numpy() <= clip_val
    axes[0].scatter(
        y_test_aud.to_numpy()[mask97],
        pred_aud[mask97],
        alpha=0.25,
        s=8,
        c="#1a5276",
        linewidths=0,
    )
    axes[0].plot([0, clip_val], [0, clip_val], "r--", lw=1.8, label="Perfect prediction")
    axes[0].set_xlabel("Actual episode charge ($AUD)")
    axes[0].set_ylabel("Predicted episode charge ($AUD)")
    axes[0].set_title(f"Actual vs predicted charge\nR2 = {metrics['aud_r2']:.3f}", fontweight="bold")
    axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    axes[0].legend(fontsize=10)

    residuals = pred_aud - y_test_aud.to_numpy()
    axes[1].hist(np.clip(residuals, -5000, 5000), bins=70, color="#2980b9", edgecolor="white", linewidth=0.3)
    axes[1].axvline(0, color="red", lw=2, linestyle="--", label="Zero error")
    axes[1].axvline(residuals.mean(), color="orange", lw=1.5, linestyle="-", label=f"Mean error: ${residuals.mean():+,.0f}")
    axes[1].set_xlabel("Error (predicted - actual, $AUD)")
    axes[1].set_ylabel("Frequency")
    axes[1].set_title("Residual distribution\n(clipped to +/-$5,000)", fontweight="bold")
    axes[1].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    axes[1].legend()
    fig.suptitle(
        f"Completed Episode Charge Benchmarking | MAE=${metrics['aud_mae']:,.0f} RMSE=${metrics['aud_rmse']:,.0f}",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(FIGS / "04_actual_vs_predicted.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_shap_outputs(model: XGBRegressor, x_test: pd.DataFrame, y_test_aud: pd.Series, pred_aud: np.ndarray) -> dict[str, str]:
    display_names = [FEATURE_DISPLAY.get(c, c) for c in FEATURE_COLS]
    x_display = x_test.copy()
    x_display.columns = display_names

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(x_test)
    expected_value = explainer.expected_value
    if isinstance(expected_value, (list, np.ndarray)):
        expected_value = float(np.ravel(expected_value)[0])

    plt.figure(figsize=(10, 7))
    shap.summary_plot(shap_values, x_test.values, feature_names=display_names, max_display=11, show=False, plot_size=None)
    plt.title("SHAP summary - model use of clinical and utilisation features", fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    plt.savefig(FIGS / "04_shap_summary.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    mean_abs = np.abs(shap_values).mean(axis=0)
    imp = pd.DataFrame({"feature": display_names, "importance": mean_abs}).sort_values("importance")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(imp["feature"], imp["importance"], color="#1a5276", edgecolor="white")
    ax.set_xlabel("Mean absolute SHAP value (log target scale)")
    ax.set_title("Global feature importance (SHAP)", fontweight="bold", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGS / "04_feature_importance.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    for feature, name in [("LOS", "04_shap_dependence_los.png"), ("procedure_count", "04_shap_dependence_procedure_count.png")]:
        plt.figure(figsize=(8, 5))
        shap.dependence_plot(feature, shap_values, x_test, show=False, interaction_index=None)
        plt.title(f"SHAP dependence - {FEATURE_DISPLAY[feature]}", fontweight="bold")
        plt.tight_layout()
        plt.savefig(FIGS / name, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()

    actual = y_test_aud.to_numpy()
    abs_err = np.abs(actual - pred_aud)
    candidates = {
        "low_sameday": np.where((x_test["SameDayStatus"].to_numpy() == 1) & (actual <= np.quantile(actual, 0.30)))[0],
        "typical_mid": np.where((actual >= np.quantile(actual, 0.45)) & (actual <= np.quantile(actual, 0.55)))[0],
        "high_complex": np.where(actual >= np.quantile(actual, 0.90))[0],
    }
    files = {}
    for label, idxs in candidates.items():
        if len(idxs) == 0:
            continue
        if label == "high_complex":
            chosen = idxs[np.argmax(actual[idxs])]
        else:
            chosen = idxs[np.argmin(abs_err[idxs])]
        explanation = shap.Explanation(
            values=shap_values[chosen],
            base_values=expected_value,
            data=x_display.iloc[chosen].to_numpy(),
            feature_names=display_names,
        )
        plt.figure(figsize=(10, 6))
        shap.plots.waterfall(explanation, max_display=10, show=False)
        plt.title(
            f"SHAP waterfall - {label.replace('_', ' ')}\n"
            f"Actual \\${actual[chosen]:,.0f}, predicted \\${pred_aud[chosen]:,.0f}",
            fontweight="bold",
        )
        plt.tight_layout()
        filename = f"04_shap_waterfall_{label}.png"
        plt.savefig(FIGS / filename, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        files[label] = filename
    return files


def write_limitations() -> None:
    text = """# Limitations

- The dataset is a de-identified single HCP extract and may not generalise to other hospitals, years, or coding practices.
- The target is billed episode charge, not true economic or clinical cost.
- No external cost, outcome, or audited finance validation was available.
- Several features used by the strongest model, including LOS, same-day status, procedure count, comorbidity count, final MDC/DRG-derived grouping, and mode of separation, are known only after episode completion or final coding.
- Therefore the current model is best framed as completed episode charge benchmarking, expected charge estimation, and unusual charge review, not admission-time early warning.
- Random train/test splitting may overestimate future generalisation; a time-based split is reported separately as a more realistic sensitivity check.
- Associations in EDA and SHAP are not causal evidence.
- Charge distribution is highly right-skewed; log-transforming the target reduces the influence of extreme values but high-charge episodes remain clinically and commercially important.
- MAPE is reported only as a supporting metric because low-charge episodes can make percentage error unstable.
- Coding practices may influence diagnosis, procedure, comorbidity, and DRG-derived features.
- Row-level worst-prediction outputs are local review artifacts and should not be published in a public repository.
"""
    (REPORTS / "limitations.md").write_text(text)


def write_final_metrics(
    final_metrics: dict[str, object],
    model_comparison: pd.DataFrame,
    segment_df: pd.DataFrame,
    high_cost_df: pd.DataFrame,
    data_quality_df: pd.DataFrame,
    leakage_summary: dict[str, object],
    time_split: SplitData,
    df: pd.DataFrame,
) -> None:
    time_test_dates = df.loc[time_split.test_idx, "AdmissionDate_dt"]
    random_xgb = model_comparison.query("Split == 'random_80_20' and Model == 'XGBoost'").iloc[0].to_dict()
    time_xgb = model_comparison.query("Split == 'time_last_20_pct_by_admission_date' and Model == 'XGBoost'").iloc[0].to_dict()
    best_random = (
        model_comparison.query("Split == 'random_80_20'")
        .sort_values(["RMSE", "MAE"], ascending=True)
        .iloc[0]
        .to_dict()
    )
    best_time = (
        model_comparison.query("Split == 'time_last_20_pct_by_admission_date'")
        .sort_values(["RMSE", "MAE"], ascending=True)
        .iloc[0]
        .to_dict()
    )

    payload = {
        **final_metrics,
        "target": TARGET,
        "target_definition": "Sum of HCP charge component fields divided by 100 to convert cents to AUD.",
        "model_scope": "Completed episode charge benchmarking, expected charge estimation, and unusual charge review.",
        "primary_model": "XGBoost",
        "primary_split": "random_80_20",
        "random_xgb": random_xgb,
        "time_split_xgb": time_xgb,
        "best_random_split_model": best_random,
        "best_time_split_model": best_time,
        "model_selection_note": "Random Forest delivered the best held-out performance; XGBoost is a very close challenger used for SHAP explainability and time-split analysis.",
        "time_split_test_start": str(time_test_dates.min().date()),
        "time_split_test_end": str(time_test_dates.max().date()),
        "high_cost_capture": high_cost_df.iloc[0].to_dict(),
        "data_quality_checks_with_affected_rows": int((data_quality_df["affected_rows"] > 0).sum()),
        "feature_count": len(FEATURE_COLS),
        "leakage_summary": leakage_summary,
        "segment_rows": int(len(segment_df)),
    }
    for name in ["final_metrics.json", "model_metrics.json"]:
        with open(REPORTS / name, "w") as f:
            json.dump(payload, f, indent=2)


def main() -> None:
    df_raw = pd.read_parquet(DATA)
    df, x, y_log, y_aud = prepare_data(df_raw)

    leakage_summary = write_feature_and_leakage_outputs(df)
    data_quality_df = write_data_quality_output(df)
    splits = build_splits(df)
    model_comparison = evaluate_models(x, y_log, y_aud, splits)

    random_split = splits[0]
    model, x_test, y_test_aud, pred_aud, final_metrics = fit_final_xgb(x, y_log, y_aud, random_split)
    model.save_model(str(REPORTS / "xgb_model.json"))

    segment_df = segment_metrics(df, random_split, y_test_aud, pred_aud, y_aud.loc[random_split.train_idx])
    write_worst_predictions(df, random_split, y_test_aud, pred_aud)
    high_cost_df = high_cost_capture(random_split, y_aud.loc[random_split.train_idx], y_test_aud, pred_aud)
    ablation_output(x, y_log, y_aud, random_split)
    save_actual_vs_predicted(y_test_aud, pred_aud, final_metrics)
    shap_files = save_shap_outputs(model, x_test, y_test_aud, pred_aud)
    write_limitations()
    final_metrics["shap_waterfall_figures"] = shap_files
    write_final_metrics(
        final_metrics,
        model_comparison,
        segment_df,
        high_cost_df,
        data_quality_df,
        leakage_summary,
        splits[1],
        df,
    )

    print("Generated validation outputs:")
    for path in [
        "model_comparison.csv",
        "segment_performance.csv",
        "worst_predictions.csv",
        "data_quality_summary.csv",
        "feature_list.csv",
        "high_cost_capture.csv",
        "feature_ablation.csv",
        "leakage_audit.csv",
        "target_composition.csv",
        "limitations.md",
        "final_metrics.json",
    ]:
        print(f"  reports/{path}")
    for filename in sorted(os.listdir(FIGS)):
        if filename.startswith("04_shap_waterfall") or filename.startswith("04_shap_dependence"):
            print(f"  figures/{filename}")


if __name__ == "__main__":
    main()
