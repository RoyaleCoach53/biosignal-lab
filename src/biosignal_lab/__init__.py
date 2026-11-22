"""BioSignal Lab: research-only signal-quality and spectral processing."""
from .models import Recording, AnalysisConfig, AnalysisResults
from .pipeline import analyze

__version__ = "0.2.0"
__all__ = ["Recording", "AnalysisConfig", "AnalysisResults", "analyze"]
