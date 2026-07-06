class DarkTheme:
    """Monochrome minimalist dark theme for Compresso."""

    # ── Color palette: pure grayscale ──
    BG_PRIMARY = "#111111"       # Deepest background
    BG_SECONDARY = "#171717"     # Slightly lighter
    BG_CARD = "#1c1c1c"          # Card background
    BG_HOVER = "#242424"         # Hover state
    BG_ACTIVE = "#2a2a2a"        # Active/pressed
    BG_INPUT = "#141414"         # Input fields

    TEXT_PRIMARY = "#e5e5e5"     # Main text (near-white)
    TEXT_SECONDARY = "#888888"   # Secondary text
    TEXT_MUTED = "#555555"       # Muted text
    TEXT_ACCENT = "#ffffff"      # Accent text (pure white for emphasis)

    ACCENT = "#ffffff"           # Primary accent (white)
    ACCENT_HOVER = "#f0f0f0"     # Accent hover
    ACCENT_PRESSED = "#d0d0d0"   # Accent pressed
    ACCENT_GRADIENT_START = "#ffffff"
    ACCENT_GRADIENT_END = "#cccccc"

    SUCCESS = "#a0a0a0"          # Gray (replaces green)
    WARNING = "#909090"          # Gray (replaces orange)
    ERROR = "#808080"            # Gray (replaces red)
    INFO = "#b0b0b0"             # Gray (replaces blue)

    BORDER = "#2a2a2a"           # Border color
    BORDER_LIGHT = "#333333"     # Lighter border
    BORDER_FOCUS = "#555555"     # Focus border

    SHADOW = "rgba(0, 0, 0, 0.4)"
    GLASS_BG = "#1c1c1c"        # Solid (no glassmorphism)

    RADIUS_SM = "4px"
    RADIUS_MD = "6px"
    RADIUS_LG = "8px"
    RADIUS_XL = "12px"

    FONT_FAMILY = "'Inter', 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif"
    FONT_SIZE_SM = "11px"
    FONT_SIZE_MD = "13px"
    FONT_SIZE_LG = "14px"
    FONT_SIZE_XL = "16px"
    FONT_SIZE_TITLE = "20px"
    FONT_SIZE_HUGE = "28px"

    TRANSITION_FAST = "150ms"
    TRANSITION_NORMAL = "250ms"
    TRANSITION_SLOW = "400ms"

    @classmethod
    def apply(cls, app) -> None:
        """Apply the dark theme to a QApplication."""
        app.setStyleSheet(cls.get_full_stylesheet())

    @classmethod
    def get_full_stylesheet(cls) -> str:
        """Return the complete QSS stylesheet."""
        return "\n".join([
            cls._global_styles(),
            cls._qpushbutton_styles(),
            cls._qslider_styles(),
            cls._qprogressbar_styles(),
            cls._qlabel_styles(),
            cls._qframe_card_styles(),
            cls._qlineedit_styles(),
            cls._qcombobox_styles(),
            cls._qscrollarea_styles(),
            cls._qtooltip_styles(),
            cls._custom_widget_styles(),
        ])

    # ------------------------------------------------------------------ #
    #  Global
    # ------------------------------------------------------------------ #
    @classmethod
    def _global_styles(cls) -> str:
        return f"""
        QWidget {{
            font-family: {cls.FONT_FAMILY};
            font-size: {cls.FONT_SIZE_MD};
            color: {cls.TEXT_PRIMARY};
            background-color: transparent;
        }}
        QMainWindow {{
            background-color: {cls.BG_PRIMARY};
        }}
        QDialog {{
            background-color: {cls.BG_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_LG};
        }}
        """

    # ------------------------------------------------------------------ #
    #  QPushButton
    # ------------------------------------------------------------------ #
    @classmethod
    def _qpushbutton_styles(cls) -> str:
        return f"""
        /* ── Base button ── */
        QPushButton {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            padding: 8px 20px;
            min-height: 22px;
            font-family: {cls.FONT_FAMILY};
            font-size: {cls.FONT_SIZE_MD};
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {cls.BG_HOVER};
            border-color: {cls.BORDER_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {cls.BG_ACTIVE};
            border-color: {cls.TEXT_MUTED};
        }}
        QPushButton:disabled {{
            background-color: {cls.BG_SECONDARY};
            color: {cls.TEXT_MUTED};
            border-color: {cls.BORDER};
        }}
        QPushButton:focus {{
            border-color: {cls.BORDER_FOCUS};
            outline: none;
        }}

        /* ── Primary button (white, monochrome) ── */
        QPushButton#primaryBtn {{
            background-color: {cls.TEXT_PRIMARY};
            color: {cls.BG_PRIMARY};
            border: none;
            border-radius: {cls.RADIUS_MD};
            padding: 9px 24px;
            min-height: 22px;
            font-weight: 600;
            font-size: {cls.FONT_SIZE_MD};
        }}
        QPushButton#primaryBtn:hover {{
            background-color: {cls.ACCENT_HOVER};
        }}
        QPushButton#primaryBtn:pressed {{
            background-color: {cls.ACCENT_PRESSED};
        }}
        QPushButton#primaryBtn:disabled {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_MUTED};
        }}
        QPushButton#primaryBtn:focus {{
            border: 1px solid {cls.TEXT_MUTED};
        }}

        /* ── Secondary button (bordered) ── */
        QPushButton#secondaryBtn {{
            background-color: transparent;
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_MD};
            padding: 8px 20px;
            min-height: 22px;
            font-weight: 500;
        }}
        QPushButton#secondaryBtn:hover {{
            background-color: {cls.BG_HOVER};
            border-color: {cls.TEXT_MUTED};
            color: {cls.TEXT_PRIMARY};
        }}
        QPushButton#secondaryBtn:pressed {{
            background-color: {cls.BG_ACTIVE};
            border-color: {cls.TEXT_SECONDARY};
        }}
        QPushButton#secondaryBtn:disabled {{
            background-color: transparent;
            color: {cls.TEXT_MUTED};
            border-color: {cls.BORDER};
        }}

        /* ── Danger button ── */
        QPushButton#dangerBtn {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_MD};
            padding: 8px 20px;
            min-height: 22px;
            font-weight: 600;
        }}
        QPushButton#dangerBtn:hover {{
            background-color: {cls.TEXT_MUTED};
        }}
        QPushButton#dangerBtn:pressed {{
            background-color: {cls.BORDER_LIGHT};
        }}
        QPushButton#dangerBtn:disabled {{
            background-color: {cls.BG_SECONDARY};
            color: {cls.TEXT_MUTED};
        }}

        /* ── Small / icon button ── */
        QPushButton#iconBtn, QPushButton#smallBtn {{
            background-color: transparent;
            color: {cls.TEXT_SECONDARY};
            border: 1px solid transparent;
            border-radius: {cls.RADIUS_SM};
            padding: 5px 10px;
            min-height: 16px;
            min-width: 16px;
            font-size: {cls.FONT_SIZE_SM};
        }}
        QPushButton#iconBtn:hover, QPushButton#smallBtn:hover {{
            background-color: {cls.BG_HOVER};
            color: {cls.TEXT_PRIMARY};
            border-color: {cls.BORDER_LIGHT};
        }}
        QPushButton#iconBtn:pressed, QPushButton#smallBtn:pressed {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
        }}
        QPushButton#iconBtn:disabled, QPushButton#smallBtn:disabled {{
            color: {cls.TEXT_MUTED};
        }}
        """

    # ------------------------------------------------------------------ #
    #  QSlider
    # ------------------------------------------------------------------ #
    @classmethod
    def _qslider_styles(cls) -> str:
        return f"""
        /* ── Horizontal groove ── */
        QSlider::groove:horizontal {{
            border: none;
            height: 3px;
            background: {cls.BORDER};
            border-radius: 1px;
        }}
        QSlider::handle:horizontal {{
            background: {cls.TEXT_PRIMARY};
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
            border: none;
        }}
        QSlider::handle:horizontal:hover {{
            background: {cls.ACCENT_HOVER};
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:pressed {{
            background: {cls.TEXT_SECONDARY};
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}
        QSlider::sub-page:horizontal {{
            background: {cls.TEXT_PRIMARY};
            border-radius: 1px;
        }}
        QSlider::add-page:horizontal {{
            background: {cls.BORDER};
            border-radius: 1px;
        }}

        /* ── Vertical groove ── */
        QSlider::groove:vertical {{
            border: none;
            width: 3px;
            background: {cls.BORDER};
            border-radius: 1px;
        }}
        QSlider::handle:vertical {{
            background: {cls.TEXT_PRIMARY};
            width: 14px;
            height: 14px;
            margin: 0 -5px;
            border-radius: 7px;
            border: none;
        }}
        QSlider::handle:vertical:hover {{
            background: {cls.ACCENT_HOVER};
            width: 16px;
            height: 16px;
            margin: 0 -6px;
            border-radius: 8px;
        }}
        QSlider::handle:vertical:pressed {{
            background: {cls.TEXT_SECONDARY};
            width: 16px;
            height: 16px;
            margin: 0 -6px;
            border-radius: 8px;
        }}
        QSlider::sub-page:vertical {{
            background: {cls.TEXT_PRIMARY};
            border-radius: 1px;
        }}
        QSlider::add-page:vertical {{
            background: {cls.BORDER};
            border-radius: 1px;
        }}

        /* Disabled slider */
        QSlider:disabled {{
            opacity: 0.4;
        }}
        QSlider:disabled::groove:horizontal,
        QSlider:disabled::groove:vertical {{
            background: {cls.BG_CARD};
        }}
        QSlider:disabled::handle:horizontal,
        QSlider:disabled::handle:vertical {{
            background: {cls.TEXT_MUTED};
        }}
        """

    # ------------------------------------------------------------------ #
    #  QProgressBar
    # ------------------------------------------------------------------ #
    @classmethod
    def _qprogressbar_styles(cls) -> str:
        return f"""
        QProgressBar {{
            border: 1px solid {cls.BORDER};
            border-radius: 2px;
            background-color: {cls.BG_INPUT};
            min-height: 6px;
            max-height: 8px;
            text-align: center;
            color: {cls.TEXT_PRIMARY};
            font-size: {cls.FONT_SIZE_SM};
            font-weight: 600;
        }}
        QProgressBar::chunk {{
            background-color: {cls.TEXT_PRIMARY};
            border-radius: 1px;
        }}

        /* ── Success variant ── */
        QProgressBar#successBar::chunk {{
            background-color: {cls.TEXT_SECONDARY};
        }}

        /* ── Warning variant ── */
        QProgressBar#warningBar::chunk {{
            background-color: {cls.TEXT_MUTED};
        }}

        /* ── Error variant ── */
        QProgressBar#errorBar::chunk {{
            background-color: {cls.BORDER_LIGHT};
        }}

        /* Indeterminate */
        QProgressBar:indeterminate {{
            border: 1px solid {cls.BORDER};
            border-radius: 2px;
            background-color: {cls.BG_INPUT};
        }}
        QProgressBar:indeterminate::chunk {{
            background-color: {cls.TEXT_PRIMARY};
            border-radius: 1px;
            width: 40px;
        }}
        """

    # ------------------------------------------------------------------ #
    #  QLabel
    # ------------------------------------------------------------------ #
    @classmethod
    def _qlabel_styles(cls) -> str:
        return f"""
        /* ── Title label ── */
        QLabel#titleLabel {{
            font-size: {cls.FONT_SIZE_TITLE};
            font-weight: 700;
            color: {cls.TEXT_PRIMARY};
            background: transparent;
            padding: 0px;
            letter-spacing: -0.02em;
        }}

        /* ── Subtitle label ── */
        QLabel#subtitleLabel {{
            font-size: {cls.FONT_SIZE_LG};
            font-weight: 500;
            color: {cls.TEXT_SECONDARY};
            background: transparent;
        }}

        /* ── Value / metric label (large number) ── */
        QLabel#valueLabel {{
            font-size: {cls.FONT_SIZE_XL};
            font-weight: 700;
            color: {cls.TEXT_PRIMARY};
            background: transparent;
        }}

        /* ── Stat label ── */
        QLabel#statLabel {{
            font-size: {cls.FONT_SIZE_LG};
            font-weight: 600;
            color: {cls.TEXT_PRIMARY};
            background: transparent;
        }}

        /* ── Muted / hint label ── */
        QLabel#mutedLabel {{
            font-size: {cls.FONT_SIZE_SM};
            color: {cls.TEXT_MUTED};
            background: transparent;
        }}

        /* ── Success label ── */
        QLabel#successLabel {{
            color: {cls.TEXT_SECONDARY};
            font-weight: 600;
            background: transparent;
        }}

        /* ── Error label ── */
        QLabel#errorLabel {{
            color: {cls.TEXT_SECONDARY};
            font-weight: 600;
            background: transparent;
        }}

        /* ── Warning label ── */
        QLabel#warningLabel {{
            color: {cls.TEXT_MUTED};
            font-weight: 600;
            background: transparent;
        }}

        /* ── Accent label ── */
        QLabel#accentLabel {{
            color: {cls.TEXT_PRIMARY};
            font-weight: 600;
            background: transparent;
        }}

        /* ── Logo / brand label ── */
        QLabel#logoLabel {{
            font-size: {cls.FONT_SIZE_HUGE};
            font-weight: 800;
            color: {cls.TEXT_PRIMARY};
            background: transparent;
            letter-spacing: -0.03em;
        }}

        /* ── Link-styled label ── */
        QLabel#linkLabel {{
            color: {cls.TEXT_SECONDARY};
            background: transparent;
            text-decoration: underline;
            cursor: pointer;
        }}
        QLabel#linkLabel:hover {{
            color: {cls.TEXT_PRIMARY};
        }}
        """

    # ------------------------------------------------------------------ #
    #  QFrame (card)
    # ------------------------------------------------------------------ #
    @classmethod
    def _qframe_card_styles(cls) -> str:
        return f"""
        /* ── Card ── */
        QFrame#card {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_LG};
            padding: 0px;
        }}
        QFrame#card:hover {{
            border-color: {cls.BORDER_LIGHT};
        }}

        /* ── Card title bar ── */
        QFrame#cardTitle {{
            background-color: transparent;
            border: none;
            border-bottom: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_LG} {cls.RADIUS_LG} 0px 0px;
            padding: 12px 16px 10px 16px;
        }}

        /* ── Card body ── */
        QFrame#cardBody {{
            background-color: transparent;
            border: none;
            padding: 14px 16px;
        }}

        /* ── Separator / divider line ── */
        QFrame#separator, QFrame#divider {{
            background-color: {cls.BORDER};
            border: none;
            max-height: 1px;
            min-height: 1px;
        }}

        /* ── Group box card ── */
        QGroupBox {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_LG};
            margin-top: 12px;
            padding: 16px 14px 14px 14px;
            font-weight: 600;
            color: {cls.TEXT_SECONDARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 6px;
            color: {cls.TEXT_SECONDARY};
        }}

        /* ── Sidebar frame ── */
        QFrame#sidebar {{
            background-color: {cls.BG_SECONDARY};
            border-right: 1px solid {cls.BORDER};
        }}

        /* ── Toolbar / header bar frame ── */
        QFrame#headerBar {{
            background-color: {cls.BG_SECONDARY};
            border-bottom: 1px solid {cls.BORDER};
        }}

        /* ── Status bar frame ── */
        QFrame#statusBar {{
            background-color: {cls.BG_SECONDARY};
            border-top: 1px solid {cls.BORDER};
        }}
        """

    # ------------------------------------------------------------------ #
    #  QLineEdit
    # ------------------------------------------------------------------ #
    @classmethod
    def _qlineedit_styles(cls) -> str:
        return f"""
        QLineEdit {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            padding: 7px 12px;
            min-height: 20px;
            selection-background-color: {cls.TEXT_MUTED};
            selection-color: {cls.TEXT_PRIMARY};
        }}
        QLineEdit:hover {{
            border-color: {cls.BORDER_LIGHT};
        }}
        QLineEdit:focus {{
            border-color: {cls.BORDER_FOCUS};
            border-width: 1px;
            padding: 7px 12px;
        }}
        QLineEdit:disabled {{
            background-color: {cls.BG_SECONDARY};
            color: {cls.TEXT_MUTED};
            border-color: {cls.BORDER};
        }}
        QLineEdit:read-only {{
            background-color: {cls.BG_SECONDARY};
            color: {cls.TEXT_SECONDARY};
        }}

        QLineEdit::placeholder {{
            color: {cls.TEXT_MUTED};
        }}

        QLineEdit#searchInput {{
            border-radius: {cls.RADIUS_XL};
            padding-left: 32px;
            font-size: {cls.FONT_SIZE_MD};
        }}
        """

    # ------------------------------------------------------------------ #
    #  QComboBox
    # ------------------------------------------------------------------ #
    @classmethod
    def _qcombobox_styles(cls) -> str:
        return f"""
        QComboBox {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            padding: 7px 36px 7px 12px;
            min-height: 20px;
            font-size: {cls.FONT_SIZE_MD};
        }}
        QComboBox:hover {{
            border-color: {cls.BORDER_LIGHT};
        }}
        QComboBox:focus {{
            border-color: {cls.BORDER_FOCUS};
        }}
        QComboBox:disabled {{
            background-color: {cls.BG_SECONDARY};
            color: {cls.TEXT_MUTED};
            border-color: {cls.BORDER};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid {cls.BORDER};
            border-top-right-radius: {cls.RADIUS_MD};
            border-bottom-right-radius: {cls.RADIUS_MD};
            background: transparent;
        }}
        QComboBox::down-arrow {{
            width: 10px;
            height: 10px;
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {cls.TEXT_MUTED};
            margin-right: 8px;
        }}
        QComboBox:hover::down-arrow {{
            border-top-color: {cls.TEXT_PRIMARY};
        }}
        QComboBox QAbstractItemView {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            selection-background-color: {cls.BG_ACTIVE};
            selection-color: {cls.TEXT_PRIMARY};
            outline: none;
            padding: 4px 0px;
        }}
        QComboBox QAbstractItemView::item {{
            height: 30px;
            padding: 4px 12px;
            min-width: 120px;
            border-radius: {cls.RADIUS_SM};
            margin: 1px 4px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {cls.BG_HOVER};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
        }}
        """

    # ------------------------------------------------------------------ #
    #  QScrollArea / QScrollBar
    # ------------------------------------------------------------------ #
    @classmethod
    def _qscrollarea_styles(cls) -> str:
        return f"""
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}

        /* ── Vertical scrollbar ── */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 6px;
            margin: 0px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical {{
            background: {cls.BORDER_LIGHT};
            min-height: 30px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {cls.TEXT_MUTED};
        }}
        QScrollBar::handle:vertical:pressed {{
            background: {cls.TEXT_SECONDARY};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
            background: none;
        }}
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: none;
        }}

        /* ── Horizontal scrollbar ── */
        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 6px;
            margin: 0px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal {{
            background: {cls.BORDER_LIGHT};
            min-width: 30px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {cls.TEXT_MUTED};
        }}
        QScrollBar::handle:horizontal:pressed {{
            background: {cls.TEXT_SECONDARY};
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
            background: none;
        }}
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {{
            background: none;
        }}
        """

    # ------------------------------------------------------------------ #
    #  QToolTip
    # ------------------------------------------------------------------ #
    @classmethod
    def _qtooltip_styles(cls) -> str:
        return f"""
        QToolTip {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_SM};
            padding: 6px 10px;
            font-family: {cls.FONT_FAMILY};
            font-size: {cls.FONT_SIZE_SM};
            font-weight: 400;
        }}
        """

    # ------------------------------------------------------------------ #
    #  Custom widgets
    # ------------------------------------------------------------------ #
    @classmethod
    def _custom_widget_styles(cls) -> str:
        return f"""
        /* ── DropZone ── */
        #dropZone {{
            border: 1px dashed {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_LG};
            background-color: {cls.BG_SECONDARY};
            min-height: 160px;
        }}
        #dropZone:hover, #dropZone[dragActive="true"] {{
            border-color: {cls.TEXT_MUTED};
            background-color: {cls.BG_CARD};
        }}
        #dropZone:hover, #dropZone.dragging {{
            border-color: {cls.TEXT_MUTED};
            background-color: {cls.BG_CARD};
        }}

        /* ── ComparisonSlider ── */
        #comparisonSlider {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
        }}

        /* ── Quality gauge ── */
        #qualityGauge {{
            background-color: transparent;
        }}

        /* ── Status pill ── */
        #statusPill {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER};
            border-radius: 10px;
            padding: 3px 10px;
            font-size: {cls.FONT_SIZE_SM};
            color: {cls.TEXT_SECONDARY};
        }}

        /* ── Tab bar ── */
        QTabWidget::pane {{
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            background-color: {cls.BG_PRIMARY};
            top: -1px;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {cls.TEXT_MUTED};
            border: none;
            border-bottom: 1px solid transparent;
            padding: 8px 18px;
            margin-right: 2px;
            font-size: {cls.FONT_SIZE_MD};
            font-weight: 500;
            border-top-left-radius: {cls.RADIUS_SM};
            border-top-right-radius: {cls.RADIUS_SM};
        }}
        QTabBar::tab:hover {{
            color: {cls.TEXT_SECONDARY};
            background-color: {cls.BG_HOVER};
        }}
        QTabBar::tab:selected {{
            color: {cls.TEXT_PRIMARY};
            border-bottom: 1px solid {cls.TEXT_PRIMARY};
            background-color: {cls.BG_PRIMARY};
        }}

        /* ── QCheckBox ── */
        QCheckBox {{
            color: {cls.TEXT_PRIMARY};
            spacing: 8px;
            font-size: {cls.FONT_SIZE_MD};
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: 3px;
            background-color: {cls.BG_INPUT};
        }}
        QCheckBox::indicator:hover {{
            border-color: {cls.TEXT_MUTED};
        }}
        QCheckBox::indicator:checked {{
            background-color: {cls.TEXT_PRIMARY};
            border-color: {cls.TEXT_PRIMARY};
            image: none;
        }}
        QCheckBox::indicator:disabled {{
            border-color: {cls.BORDER};
            background-color: {cls.BG_SECONDARY};
        }}

        /* ── QRadioButton ── */
        QRadioButton {{
            color: {cls.TEXT_PRIMARY};
            spacing: 8px;
            font-size: {cls.FONT_SIZE_MD};
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {cls.BORDER_LIGHT};
            border-radius: 8px;
            background-color: {cls.BG_INPUT};
        }}
        QRadioButton::indicator:hover {{
            border-color: {cls.TEXT_MUTED};
        }}
        QRadioButton::indicator:checked {{
            border-color: {cls.TEXT_PRIMARY};
            background-color: {cls.BG_INPUT};
            border-width: 3px;
        }}
        QRadioButton::indicator:disabled {{
            border-color: {cls.BORDER};
            background-color: {cls.BG_SECONDARY};
        }}

        /* ── QSpinBox / QDoubleSpinBox ── */
        QSpinBox, QDoubleSpinBox {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            padding: 6px 10px;
            min-height: 20px;
            font-size: {cls.FONT_SIZE_MD};
        }}
        QSpinBox:hover, QDoubleSpinBox:hover {{
            border-color: {cls.BORDER_LIGHT};
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {cls.BORDER_FOCUS};
        }}
        QSpinBox:disabled, QDoubleSpinBox:disabled {{
            background-color: {cls.BG_SECONDARY};
            color: {cls.TEXT_MUTED};
            border-color: {cls.BORDER};
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background: transparent;
            border: none;
            width: 20px;
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid {cls.TEXT_MUTED};
            width: 8px;
            height: 5px;
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {cls.TEXT_MUTED};
            width: 8px;
            height: 5px;
        }}

        /* ── QListWidget ── */
        QListWidget {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            outline: none;
            padding: 4px;
        }}
        QListWidget::item {{
            padding: 8px 10px;
            border-radius: {cls.RADIUS_SM};
            margin: 1px 2px;
        }}
        QListWidget::item:hover {{
            background-color: {cls.BG_HOVER};
        }}
        QListWidget::item:selected {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
        }}
        QListWidget::item:disabled {{
            color: {cls.TEXT_MUTED};
        }}

        /* ── QTreeWidget ── */
        QTreeWidget, QTreeView {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            outline: none;
            show-decoration-selected: 1;
        }}
        QTreeWidget::item, QTreeView::item {{
            padding: 6px 8px;
            border-radius: {cls.RADIUS_SM};
            margin: 1px 2px;
        }}
        QTreeWidget::item:hover, QTreeView::item:hover {{
            background-color: {cls.BG_HOVER};
        }}
        QTreeWidget::item:selected, QTreeView::item:selected {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
        }}
        QHeaderView::section {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_MUTED};
            border: none;
            border-bottom: 1px solid {cls.BORDER};
            padding: 8px 12px;
            font-weight: 600;
            font-size: {cls.FONT_SIZE_SM};
        }}

        /* ── QTableWidget ── */
        QTableWidget {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            gridline-color: {cls.BORDER};
            outline: none;
        }}
        QTableWidget::item {{
            padding: 6px 10px;
        }}
        QTableWidget::item:hover {{
            background-color: {cls.BG_HOVER};
        }}
        QTableWidget::item:selected {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
        }}

        /* ── QSplitter ── */
        QSplitter::handle {{
            background-color: {cls.BORDER};
        }}
        QSplitter::handle:hover {{
            background-color: {cls.TEXT_MUTED};
        }}
        QSplitter::handle:horizontal {{
            width: 1px;
        }}
        QSplitter::handle:vertical {{
            height: 1px;
        }}

        /* ── QMenuBar ── */
        QMenuBar {{
            background-color: {cls.BG_SECONDARY};
            color: {cls.TEXT_SECONDARY};
            border-bottom: 1px solid {cls.BORDER};
            padding: 2px 4px;
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 6px 12px;
            border-radius: {cls.RADIUS_SM};
        }}
        QMenuBar::item:hover {{
            background-color: {cls.BG_HOVER};
            color: {cls.TEXT_PRIMARY};
        }}
        QMenuBar::item:selected {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
        }}

        /* ── QMenu ── */
        QMenu {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: {cls.RADIUS_MD};
            padding: 4px 0px;
        }}
        QMenu::item {{
            padding: 7px 28px 7px 14px;
            margin: 1px 4px;
            border-radius: {cls.RADIUS_SM};
        }}
        QMenu::item:hover {{
            background-color: {cls.BG_HOVER};
        }}
        QMenu::item:selected {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
        }}
        QMenu::item:disabled {{
            color: {cls.TEXT_MUTED};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {cls.BORDER};
            margin: 4px 10px;
        }}

        /* ── QStatusBar ── */
        QStatusBar {{
            background-color: {cls.BG_SECONDARY};
            color: {cls.TEXT_MUTED};
            border-top: 1px solid {cls.BORDER};
            padding: 2px 8px;
            font-size: {cls.FONT_SIZE_SM};
        }}

        /* ── QDockWidget ── */
        QDockWidget {{
            color: {cls.TEXT_PRIMARY};
            titlebar-close-icon: none;
        }}
        QDockWidget::title {{
            background-color: {cls.BG_SECONDARY};
            border-bottom: 1px solid {cls.BORDER};
            padding: 8px 12px;
            font-weight: 600;
        }}

        /* ── QToolButton ── */
        QToolButton {{
            background-color: transparent;
            color: {cls.TEXT_MUTED};
            border: none;
            border-radius: {cls.RADIUS_SM};
            padding: 6px 10px;
        }}
        QToolButton:hover {{
            background-color: {cls.BG_HOVER};
            color: {cls.TEXT_PRIMARY};
        }}
        QToolButton:pressed {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
        }}
        QToolButton:disabled {{
            color: {cls.TEXT_MUTED};
        }}
        QToolButton:checked {{
            background-color: {cls.BG_ACTIVE};
            color: {cls.TEXT_PRIMARY};
            border-bottom: 1px solid {cls.TEXT_PRIMARY};
        }}
        """

    # ------------------------------------------------------------------ #
    #  Convenience: dropzone only
    # ------------------------------------------------------------------ #
    @classmethod
    def get_dropzone_style(cls) -> str:
        return f"""
        #dropZone {{
            border: 1px dashed {cls.BORDER_LIGHT};
            border-radius: {cls.RADIUS_LG};
            background-color: {cls.BG_SECONDARY};
            min-height: 160px;
        }}
        #dropZone:hover, #dropZone.dragging {{
            border-color: {cls.TEXT_MUTED};
            background-color: {cls.BG_CARD};
        }}
        """