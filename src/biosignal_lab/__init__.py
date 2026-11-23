"""BioSignal Lab: research-only signal-quality and spectral processing."""
from .models import Recording, AnalysisConfig, AnalysisResults
from .pipeline import analyze

from ._version import __version__
__all__ = ["Recording", "AnalysisConfig", "AnalysisResults", "analyze"]
