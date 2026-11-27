"""Local, reproducible synthetic AI baseline laboratory."""
import json
import importlib.util

import pandas as pd
import streamlit as st

from biosignal_lab.ai import evaluate_epochs, evaluate_grouped, train_linear, train_temporal
from biosignal_lab.ai.demo import synthetic_epoch_dataset, synthetic_feature_dataset

st.set_page_config(page_title="BioSignal AI", page_icon="🧪", layout="wide")
st.title("BioSignal AI")
st.caption("Subject-disjoint research baselines · local computation · reproducible seeds")
st.info("This demonstration classifies simulated tones or spatial covariance patterns. Its scores do not measure motor imagery, disease, or any physiological task. No pretrained weights or human data are used.")

with st.sidebar:
    st.header("Synthetic experiment")
    representations = ["Spectral tone features", "Spatial covariance"]
    if importlib.util.find_spec("torch") is not None:
        representations.append("Temporal Conv1D")
    representation = st.selectbox("Representation", representations)
    models = (["lda", "logistic", "svm", "random_forest", "knn", "gradient_boosting", "qda"]
              if representation == "Spectral tone features" else ["temporal_conv1d_v1"]
              if representation == "Temporal Conv1D" else ["csp_lda", "log_euclidean"])
    model_name = st.selectbox("Classifier", models)
    n_subjects = st.slider("Simulated subjects", 3, 20, 8)
    n_trials = st.slider("Trials per subject", 4, 40, 16, 2)
    seed = int(st.number_input("Random seed", min_value=0, max_value=999999, value=42))
    max_epochs = st.slider("Maximum training epochs", 1, 50, 15) if representation == "Temporal Conv1D" else 15
    nested = st.checkbox("Nested grouped hyperparameter search", value=False,
                         help="Available for logistic regression, CSP/LDA and covariance geometry; outer test subjects never select parameters.")
    run = st.button("Run grouped evaluation", type="primary")

st.write("Every outer test subject is excluded from fitting both the scaler and classifier. Confidence intervals resample whole simulated subjects. The Python API supports validated feature datasets and explicitly licensed, checksum-pinned local caches.")
if run:
    try:
        if nested and model_name not in {"logistic", "csp_lda", "log_euclidean"}:
            st.error("Choose logistic, CSP/LDA or covariance geometry for this demonstration's nested search.")
        else:
            with st.spinner("Evaluating held-out subjects…"):
                if representation == "Spectral tone features":
                    dataset = synthetic_feature_dataset(seed, n_subjects, n_trials)
                    report = evaluate_grouped(dataset, model=model_name, seed=seed,
                                              param_grid={"logisticregression__C": [.1, 1., 10.]} if nested else None)
                    report["data_scope"] = "Synthetic 10 Hz and 20 Hz tones; no physiological generalisation claim."
                elif representation == "Spatial covariance":
                    dataset = synthetic_epoch_dataset(seed, n_subjects, n_trials)
                    parameters = ({"csptransformer__n_components": [2, 4]} if model_name == "csp_lda"
                                  else {"regularization": [.01, .1]}) if nested else None
                    report = evaluate_epochs(dataset, model=model_name, seed=seed,
                                               n_components=2, param_grid=parameters)
                    report["data_scope"] = "Synthetic spatial covariance patterns; no physiological generalisation claim."
                else:
                    dataset = synthetic_epoch_dataset(seed, n_subjects, n_trials)
                    neural_model, report = train_temporal(dataset, seed=seed, max_epochs=max_epochs, patience=3)
                    report["model"] = report["architecture"]
                    report["metrics"] = report["test_metrics"]
                    report["n_subjects"] = len(report["test_subjects"])
                    report["per_subject"] = [{**item, "n": int((dataset.subjects == item["subject"]).sum())}
                                               for item in report["test_per_subject"]]
                    report["subject_mean_accuracy"] = sum(item["metrics"]["accuracy"] for item in report["test_per_subject"]) / report["n_subjects"]
                    report["data_scope"] = "Synthetic spatial covariance patterns; subject-disjoint train/validation/test holdout. No physiological generalisation claim."
                    st.session_state["ai_neural_model"] = neural_model.to_dict()
                st.session_state["ai_report"] = report
                st.session_state["ai_linear_model"] = train_linear(dataset, model_name, seed).to_dict() if model_name in {"lda", "logistic"} else None
                if representation != "Temporal Conv1D":
                    st.session_state["ai_neural_model"] = None
    except (ValueError, ImportError, RuntimeError) as exc:
        st.error(f"Experiment could not run: {exc}")

if "ai_report" in st.session_state:
    report = st.session_state["ai_report"]
    st.subheader(f"Completed experiment: {report['model']}, seed {report['seed']}")
    st.caption("Results below describe the completed configuration; use Run to evaluate changed controls.")
    st.caption(report["data_scope"])
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
    if "subject_bootstrap_accuracy_95ci" in report:
        interval = report["subject_bootstrap_accuracy_95ci"]
        st.write(f"Subject mean accuracy: {report['subject_mean_accuracy']:.3f}; bootstrap 95% interval [{interval[0]:.3f}, {interval[1]:.3f}].")
        st.caption(report["uncertainty_note"])
    else:
        st.caption(f"Training subjects: {len(report['train_subjects'])}; validation subjects: {len(report['validation_subjects'])}; test subjects: {len(report['test_subjects'])}. A single held-out cohort does not establish a population confidence interval.")
        st.subheader("Actual training history")
        st.line_chart(pd.DataFrame(report["history"]).set_index("epoch")[["train_loss", "validation_loss"]])
        st.caption(f"Checkpoint selected by validation loss at epoch {report['best_epoch']}; test labels never select weights.")
    st.download_button("Download experiment report (JSON)",
                       json.dumps(report, indent=2, allow_nan=False),
                       file_name="synthetic-ai-report.json", mime="application/json")
    if st.session_state.get("ai_linear_model") is not None:
        st.download_button("Download affine model (safe JSON)",
                           json.dumps(st.session_state["ai_linear_model"], indent=2, allow_nan=False),
                           file_name="synthetic-linear-model.json", mime="application/json")
        st.caption("The export is fitted on all simulated epochs after evaluation. Its training fit is not an independent test score. JSON contains coefficients only; it cannot execute Python code.")
    if st.session_state.get("ai_neural_model") is not None:
        st.download_button("Download temporal model (safe JSON)",
                           json.dumps(st.session_state["ai_neural_model"], allow_nan=False),
                           file_name="synthetic-temporal-model.json", mime="application/json")
        st.caption("The temporal model uses training subjects for fitting and validation subjects for early stopping. JSON contains numeric weights for one fixed local architecture; no Python code is loaded.")
else:
    st.write("Select a classifier and run the experiment to generate actual held-out results.")
