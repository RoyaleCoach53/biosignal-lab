"""Synthetic separable oscillations, not a physiological classification dataset."""
import numpy as np

from .features import extract_epoch_features
from .learning import FeatureDataset


def synthetic_feature_dataset(seed=42, n_subjects=8, trials_per_subject=16):
    if not isinstance(n_subjects, int) or not 3 <= n_subjects <= 100:
        raise ValueError("Use 3..100 simulated subjects")
    if not isinstance(trials_per_subject, int) or not 4 <= trials_per_subject <= 100:
        raise ValueError("Use 4..100 trials per simulated subject")
    rng = np.random.default_rng(seed)
    time = np.arange(500) / 250
    epochs, labels, subjects = [], [], []
    for subject in range(n_subjects):
        gain = rng.uniform(.7, 1.3)
        for trial in range(trials_per_subject):
            label = trial % 2
            frequency = 10 if label == 0 else 20
            signal = gain * 10 * np.sin(2 * np.pi * frequency * time + rng.uniform(0, 2 * np.pi))
            epochs.append(signal[None, :] + rng.normal(0, 4, size=(1, len(time))))
            labels.append("10Hz" if label == 0 else "20Hz")
            subjects.append(f"synthetic_{subject:03d}")
    features, names = extract_epoch_features(np.array(epochs), 250)
    return FeatureDataset(features, np.array(labels), np.array(subjects), names,
                          {"generator": "synthetic_feature_dataset", "seed": seed,
                           "sampling_frequency_hz": 250, "epoch_duration_s": 2,
                           "amplitude_unit": "arbitrary", "frequencies_hz": [10, 20],
                           "feature_extraction": "extract_epoch_features:eeg",
                           "scope": "Synthetic oscillations only; no physiological task"})
