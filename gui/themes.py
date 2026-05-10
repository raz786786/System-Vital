"""
QSS Themes for SYSTEM VITAL PySide6 UI
"""

DARK_COLORS = {
    "bg_main": "#0f1117",
    "bg_sidebar": "#1a1d27",
    "bg_card": "#1e2130",
    "border_light": "#2d3150",
    "border_hover": "#3f4468",
    "text_main": "#e8eaf6",
    "text_muted": "#8b90b8",
    "text_darker": "#555a7a",
    "accent": "#3b82f6",
    "accent_hover": "#2563eb",
    "btn_bg": "#2d3150",
    "input_bg": "#1a1d27",
    "badge_sys_bg": "#1a2e1f",
    "badge_health_bg": "#1a2540"
}

LIGHT_COLORS = {
    "bg_main": "#f8fafc",
    "bg_sidebar": "#ffffff",
    "bg_card": "#ffffff",
    "border_light": "#e2e8f0",
    "border_hover": "#cbd5e1",
    "text_main": "#1e293b",
    "text_muted": "#64748b",
    "text_darker": "#94a3b8",
    "accent": "#3b82f6",
    "accent_hover": "#2563eb",
    "btn_bg": "#f1f5f9",
    "input_bg": "#f8fafc",
    "badge_sys_bg": "#dcfce7",
    "badge_health_bg": "#dbeafe"
}


def generate_qss(colors: dict) -> str:
    return f"""
    * {{
        font-family: "Segoe UI", "Inter", sans-serif;
        color: {colors["text_main"]};
    }}

    QMainWindow {{
        background-color: {colors["bg_main"]};
    }}

    /* Dialogs & Message Boxes */
    QMessageBox {{
        background-color: {colors["bg_card"]};
        color: {colors["text_main"]};
    }}
    QMessageBox QLabel {{
        color: {colors["text_main"]};
        font-size: 13px;
        padding: 8px;
        background: transparent;
    }}
    QMessageBox QPushButton {{
        background-color: {colors["accent"]};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 24px;
        font-weight: bold;
        min-width: 80px;
    }}
    QMessageBox QPushButton:hover {{
        background-color: {colors["accent_hover"]};
    }}
    QDialog {{
        background-color: {colors["bg_card"]};
        color: {colors["text_main"]};
    }}
    QToolTip {{
        background-color: {colors["bg_card"]};
        color: {colors["text_main"]};
        border: 1px solid {colors["border_light"]};
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 12px;
    }}
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}

    /* Sidebar & Topbar */
    #Sidebar, #Topbar {{
        background-color: {colors["bg_sidebar"]};
        border: none;
    }}
    #Sidebar {{ border-right: 1px solid {colors["border_light"]}; }}
    #Topbar {{ border-bottom: 1px solid {colors["border_light"]}; }}

    /* Cards */
    QFrame.CardFrame {{
        background-color: {colors["bg_card"]};
        border: 1px solid {colors["border_light"]};
        border-radius: 12px;
    }}

    QFrame.SegmentFrame {{
        background-color: transparent;
        border: 1px solid {colors["border_light"]};
        border-radius: 10px;
    }}

    /* Buttons */
    QPushButton {{
        background-color: {colors["btn_bg"]};
        color: {colors["text_main"]};
        border: 1px solid {colors["border_hover"]};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {colors["border_hover"]};
    }}
    QPushButton:pressed {{
        background-color: {colors["border_light"]};
    }}

    QPushButton.PrimaryButton {{
        background-color: {colors["accent"]};
        border: none;
        color: white;
    }}
    QPushButton.PrimaryButton:hover {{
        background-color: {colors["accent_hover"]};
    }}

    QPushButton.SegmentBtn {{
        background-color: transparent;
        color: {colors["text_muted"]};
        border: none;
        border-radius: 6px;
    }}
    QPushButton.SegmentBtn:checked {{
        background-color: {colors["accent"]};
        color: white;
    }}

    QPushButton.NavButton {{
        background-color: transparent;
        border: none;
        color: {colors["text_muted"]};
        text-align: left;
        padding-left: 12px;
    }}
    QPushButton.NavButton:hover {{
        background-color: {colors["btn_bg"]};
        border-radius: 8px;
    }}
    QPushButton.NavButton:checked {{
        background-color: {colors["accent"]};
        color: white;
        border-radius: 8px;
    }}

    /* Typography */
    QLabel {{ background: transparent; }}
    QLabel.Title {{ font-size: 22px; font-weight: bold; color: {colors["text_main"]}; }}
    QLabel.Subtitle {{ font-size: 14px; font-weight: bold; color: {colors["text_main"]}; }}
    QLabel.Muted {{ font-size: 12px; color: {colors["text_muted"]}; }}
    QLabel.ValueBig {{ font-size: 28px; font-weight: bold; }}
    
    QLabel.SysBadge {{
        color: #22c55e;
        background-color: {colors["badge_sys_bg"]};
        padding: 6px 12px;
        border-radius: 12px;
        font-weight: bold;
    }}
    QLabel.HealthBadge {{
        color: {colors["accent"]};
        background-color: {colors["badge_health_bg"]};
        padding: 6px 12px;
        border-radius: 12px;
        font-weight: bold;
    }}

    QFrame.IssueRow {{
        border: 1px solid {colors["border_light"]};
        border-radius: 8px;
    }}
    
    QPushButton.IssueBtn {{
        border: 1px solid {colors["border_hover"]};
        background-color: transparent;
    }}

    /* Inputs */
    QLineEdit {{
        background-color: {colors["input_bg"]};
        border: 1px solid {colors["border_light"]};
        border-radius: 8px;
        padding: 8px 12px;
        color: {colors["text_main"]};
    }}
    QLineEdit:focus {{ border: 1px solid {colors["accent"]}; }}

    /* Combo Boxes */
    QComboBox {{
        background-color: {colors["input_bg"]};
        border: 1px solid {colors["border_light"]};
        border-radius: 8px;
        padding: 6px 12px;
        color: {colors["text_main"]};
        font-size: 13px;
    }}
    QComboBox:hover {{
        border: 1px solid {colors["border_hover"]};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 28px;
        border-left: 1px solid {colors["border_light"]};
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
        background: transparent;
    }}
    QComboBox::down-arrow {{
        image: none;
        border: none;
        width: 0;
        height: 0;
    }}
    QComboBox QAbstractItemView {{
        background-color: {colors["bg_card"]};
        border: 1px solid {colors["border_hover"]};
        border-radius: 6px;
        color: {colors["text_main"]};
        selection-background-color: {colors["accent"]};
        selection-color: white;
        padding: 4px;
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 6px 12px;
        min-height: 28px;
        color: {colors["text_main"]};
        background: transparent;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {colors["btn_bg"]};
        border-radius: 4px;
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: {colors["accent"]};
        color: white;
    }}

    /* Progress & Scrollbars */
    QProgressBar {{
        background-color: {colors["border_light"]};
        border: none;
        border-radius: 4px;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {colors["accent"]};
        border-radius: 4px;
    }}
    
    QScrollBar:vertical {{ border: none; background-color: transparent; width: 12px; margin: 0; }}
    QScrollBar::handle:vertical {{ background-color: {colors["border_light"]}; min-height: 20px; border-radius: 6px; margin: 2px; }}
    QScrollBar::handle:vertical:hover {{ background-color: {colors["border_hover"]}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    """

DARK_THEME_QSS = generate_qss(DARK_COLORS)
LIGHT_THEME_QSS = generate_qss(LIGHT_COLORS)
