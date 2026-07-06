from pathlib import Path
from PySide6.QtCore import QRunnable, Signal, QObject, Slot

from models import BatchItem
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BatchSignals(QObject):
    """Signals emitted by :class:`BatchWorker`."""

    item_started = Signal(int)            # index
    item_progress = Signal(int, float)    # index, progress 0-1
    item_complete = Signal(int, object)   # index, CompressionResult
    item_error = Signal(int, str)         # index, error message
    all_complete = Signal()               # all items processed
    total_progress = Signal(float)        # overall progress 0-1


class BatchWorker(QRunnable):
    """Process multiple images sequentially in a single background thread.

    For each file the worker performs analysis and compression, emitting
    per-item progress as well as an aggregate ``total_progress`` signal
    so the UI can show both individual and overall completion.

    When *settings.smart_mode* is enabled, recommended compression
    parameters from the analysis result are applied automatically.

    Usage::

        worker = BatchWorker(
            filepaths=[Path("a.jpg"), Path("b.png")],
            settings=settings,
            output_dir=Path("output/"),
        )
        worker.signals.item_complete.connect(on_item_done)
        worker.signals.total_progress.connect(on_total_progress)
        worker.signals.all_complete.connect(on_all_done)
        worker.signals.error.connect(on_error)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        filepaths: list[Path],
        settings,
        output_dir: Path | None = None,
    ):
        super().__init__()
        self.filepaths = filepaths
        self.settings = settings
        self.output_dir = output_dir
        self.signals = BatchSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        """Analyse and compress every file, emitting per-item signals."""
        try:
            from core.analyzer import ImageAnalyzer
            from core.compressor import ImageCompressor

            analyzer = ImageAnalyzer()
            compressor = ImageCompressor()
            total = len(self.filepaths)

            logger.info("Batch processing started – %d file(s)", total)

            for i, filepath in enumerate(self.filepaths):
                try:
                    self.signals.item_started.emit(i)
                    logger.debug("[%d/%d] Processing %s", i + 1, total, filepath)

                    # --- Analyse ---
                    image_info = analyzer.get_image_info(filepath)
                    analysis = analyzer.analyze(image_info)
                    self.signals.item_progress.emit(i, 0.3)

                    # --- Smart-mode overrides ---
                    settings = self.settings
                    if settings.smart_mode:
                        settings.compression_percent = analysis.recommended_compression
                        settings.quality_percent = analysis.recommended_quality
                        settings.output_format = analysis.recommended_format

                    # --- Compress ---
                    result = compressor.compress(image_info, settings, self.output_dir)
                    self.signals.item_progress.emit(i, 1.0)
                    self.signals.item_complete.emit(i, result)
                    logger.debug(
                        "[%d/%d] Done – %s → %s",
                        i + 1,
                        total,
                        filepath,
                        result.output_path,
                    )

                except Exception as item_err:
                    logger.warning(
                        "[%d/%d] Error processing %s: %s",
                        i + 1,
                        total,
                        filepath,
                        item_err,
                    )
                    self.signals.item_error.emit(i, str(item_err))

                # Report aggregate progress regardless of per-item success
                self.signals.total_progress.emit((i + 1) / total)

            self.signals.all_complete.emit()
            logger.info("Batch processing finished – %d file(s)", total)

        except Exception as e:
            logger.error("Batch processing aborted: %s", e)
            self.signals.error.emit(str(e))