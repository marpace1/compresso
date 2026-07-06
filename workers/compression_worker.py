from pathlib import Path
from PySide6.QtCore import QRunnable, Signal, QObject, Slot

from utils.logger import setup_logger

logger = setup_logger(__name__)


class CompressionSignals(QObject):
    """Signals for compression worker."""

    started = Signal()
    progress = Signal(float)            # 0-1 progress
    prediction_ready = Signal(object)   # CompressionPrediction
    complete = Signal(object)           # CompressionResult
    error = Signal(str)


class CompressionWorker(QRunnable):
    """Background worker for image compression.

    Optionally runs a compression-prediction pass before the actual
    compression so the UI can show an estimated result first. All work
    happens off the main thread via QThreadPool.

    Usage::

        worker = CompressionWorker(
            image_info, analysis, settings,
            output_dir=Path("output/"),
            run_prediction=True,
        )
        worker.signals.progress.connect(on_progress)
        worker.signals.prediction_ready.connect(on_prediction)
        worker.signals.complete.connect(on_done)
        worker.signals.error.connect(on_error)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        image_info,
        analysis,
        settings,
        output_dir: Path | None = None,
        run_prediction: bool = False,
    ):
        super().__init__()
        self.image_info = image_info
        self.analysis = analysis
        self.settings = settings
        self.output_dir = output_dir
        self.run_prediction = run_prediction
        self.signals = CompressionSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        """Execute compression (and optional prediction) in background."""
        try:
            self.signals.started.emit()
            self.signals.progress.emit(0.05)
            logger.info("Compression started for %s", self.image_info.filepath)

            # --- Optional prediction pass ---
            if self.run_prediction:
                from core.predictor import CompressionPredictor

                predictor = CompressionPredictor()
                prediction = predictor.predict(
                    self.image_info, self.analysis, self.settings
                )
                self.signals.prediction_ready.emit(prediction)
                logger.debug("Prediction emitted for %s", self.image_info.filepath)

            self.signals.progress.emit(0.3)

            # --- Compression ---
            from core.compressor import ImageCompressor

            compressor = ImageCompressor()
            self.signals.progress.emit(0.5)

            result = compressor.compress(
                self.image_info, self.settings, self.output_dir
            )

            self.signals.progress.emit(1.0)
            self.signals.complete.emit(result)
            logger.info(
                "Compression complete for %s – saved to %s",
                self.image_info.filepath,
                result.output_path,
            )

        except Exception as e:
            logger.error("Compression failed for %s: %s", self.image_info.filepath, e)
            self.signals.error.emit(str(e))


class TargetSizeWorker(QRunnable):
    """Background worker for target-size binary-search compression."""

    def __init__(self, image_info, target_bytes: int, fmt: str, remove_metadata: bool = False):
        super().__init__()
        self.image_info = image_info
        self.target_bytes = target_bytes
        self.fmt = fmt
        self.remove_metadata = remove_metadata
        self.signals = CompressionSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            self.signals.started.emit()
            from core.compressor import ImageCompressor
            compressor = ImageCompressor()
            result = compressor.compress_to_target_size(
                self.image_info, self.target_bytes, self.fmt, self.remove_metadata
            )
            self.signals.complete.emit(result)
        except Exception as e:
            logger.error("Target-size compression failed: %s", e)
            self.signals.error.emit(str(e))