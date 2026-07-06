from pathlib import Path
from PySide6.QtCore import QRunnable, Signal, Slot, QObject

from utils.logger import setup_logger

logger = setup_logger(__name__)


class AnalysisSignals(QObject):
    """Signals for analysis worker."""

    info_ready = Signal(object)         # ImageInfo
    analysis_complete = Signal(object)  # AnalysisResult
    error = Signal(str)                 # error message


class AnalysisWorker(QRunnable):
    """Background worker for image analysis.

    Runs get_image_info() and analyze() in a background thread via
    QThreadPool so the UI never freezes. Emits intermediate and final
    results through the attached ``signals`` object.

    Usage::

        worker = AnalysisWorker(Path("photo.jpg"))
        worker.signals.info_ready.connect(on_info)
        worker.signals.analysis_complete.connect(on_analysis)
        worker.signals.error.connect(on_error)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, filepath: Path):
        super().__init__()
        self.filepath = filepath
        self.signals = AnalysisSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        """Execute analysis in background. Emit signals on completion/error."""
        try:
            from core.analyzer import ImageAnalyzer

            logger.info("Starting analysis for %s", self.filepath)
            analyzer = ImageAnalyzer()

            # Step 1: Get image info
            image_info = analyzer.get_image_info(self.filepath)
            self.signals.info_ready.emit(image_info)
            logger.debug("Image info ready for %s", self.filepath)

            # Step 2: Full analysis
            analysis = analyzer.analyze(image_info)
            self.signals.analysis_complete.emit(analysis)
            logger.info("Analysis complete for %s", self.filepath)

        except Exception as e:
            logger.error("Analysis failed for %s: %s", self.filepath, e)
            self.signals.error.emit(str(e))