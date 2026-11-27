"""Optional, local research ML with subject-disjoint evaluation and safe JSON models."""
from .features import extract_epoch_features
from .learning import FeatureDataset, evaluate_grouped, train_linear
from .portable import LinearModel, load_linear_model, save_linear_model
from .datasets import DatasetManifest, DatasetRecord, fetch_record

__all__ = ["FeatureDataset", "evaluate_grouped", "train_linear", "extract_epoch_features",
           "LinearModel", "load_linear_model", "save_linear_model", "DatasetManifest",
           "DatasetRecord", "fetch_record"]
