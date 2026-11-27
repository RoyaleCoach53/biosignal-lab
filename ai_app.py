"""Local, reproducible synthetic AI baseline laboratory."""
import json

import pandas as pd
import streamlit as st

from biosignal_lab.ai import evaluate_grouped, train_linear
from biosignal_lab.ai.demo import synthetic_feature_dataset

st.set_page_config(page_title="BioSignal AI", page_icon="🧪", layout="wide")
st.title("BioSignal AI")
st.caption("Subject-disjoint research baselines · local computation · reproducible seeds")
st.info("This demonstration classifies simulated 10 Hz versus 20 Hz tones. Its scores do not measure motor imagery, disease, or any physiological task. No pretrained weights or human data are used.")

with st.sidebar:
    st.header("Synthetic experiment")
    model_name = st.selectbox("Classifier", ["lda", "logistic", "svm", "random_forest",
                                             "knn", "gradient_boosting", "qda"])
    n_subjects = st.slider("Simulated subjects", 3, 20, 8)
    n_trials = st.slider("Trials per subject", 4, 40, 16, 2)
    seed = int(st.number_input("Random seed", min_value=0, max_value=999999, value=42))
    nested = st.checkbox("Nested grouped hyperparameter search", value=False,
                         help="Available for logistic regression; outer test subjects never select parameters.")
    run = st.button("Run grouped evaluation", type="primary")

st.write("Every outer test subject is excluded from fitting both the scaler and classifier. Confidence intervals resample whole simulated subjects. The Python API supports validated feature datasets and explicitly licensed, checksum-pinned local caches.")
if run:
    try:
        if nested and model_name != "logistic":
            st.error("Choose logistic regression for this demonstration's nested search.")
        else:
            with st.spinner("Evaluating held-out subjects…"):
                dataset = synthetic_feature_dataset(seed, n_subjects, n_trials)
                report = evaluate_grouped(dataset, model=model_name, seed=seed,
                                          param_grid={"logisticregression__C": [.1, 1., 10.]} if nested else None)
                report["data_scope"] = "Synthetic 10 Hz and 20 Hz tones; no physiological generalisation claim."
                st.session_state["ai_report"] = report
                st.session_state["ai_linear_model"] = train_linear(dataset, model_name, seed).to_dict() if model_name in {"lda", "logistic"} else None
    except (ValueError, ImportError, RuntimeError) as exc:
        st.error(f"Experiment could not run: {exc}")

if "ai_report" in st.session_state:
    report = st.session_state["ai_report"]
    st.subheader(f"Completed experiment: {report['model']}, seed {report['seed']}")
    st.caption("Results below describe the completed configuration; use Run to evaluate changed controls.")
    cols = st.columns(4)
    cols[0].metric("Held-out accuracy", f"{report['metrics']['accuracy']:.3f}")
    cols[1].metric("Balanced accuracy", f"{report['metrics']['balanced_accuracy']:.3f}")
    cols[2].metric("Macro F1", f"{report['metrics']['macro_f1']:.3f}")
    cols[3].metric("Held-out subjects", report["n_subjects"])
    st.subheader("Out-of-fold confusion matrix")
    st.dataframe(pd.DataFrame(report["metrics"]["confusion_matrix"],
                             index=report["classes"], columns=report["classes"]), width="stretch")
    st.caption("Rows are true labels; columns are predicted labels.")
    st.subheader("Per-subject results")
    st.dataframe(pd.DataFrame([{"subject": item["subject"], "epochs": item["n"],
                               "accuracy": item["metrics"]["accuracy"],
                               "macro_f1": item["metrics"]["macro_f1"]} for item in report["per_subject"]]), width="stretch")
    interval = report["subject_bootstrap_accuracy_95ci"]
    st.write(f"Subject mean accuracy: {report['subject_mean_accuracy']:.3f}; bootstrap 95% interval [{interval[0]:.3f}, {interval[1]:.3f}].")
    st.caption(report["uncertainty_note"])
    st.download_button("Download experiment report (JSON)",
                       json.dumps(report, indent=2, allow_nan=False),
                       file_name="synthetic-ai-report.json", mime="application/json")
    if st.session_state.get("ai_linear_model") is not None:
        st.download_button("Download affine model (safe JSON)",
                           json.dumps(st.session_state["ai_linear_model"], indent=2, allow_nan=False),
                           file_name="synthetic-linear-model.json", mime="application/json")
        st.caption("The export is fitted on all simulated epochs after evaluation. Its training fit is not an independent test score. JSON contains coefficients only; it cannot execute Python code.")
else:
    st.write("Select a classifier and run the experiment to generate actual held-out results.")
