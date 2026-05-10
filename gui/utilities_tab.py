"""
Utilities Tab — System Vital
Shows all 21 categories with live theme-aware styling.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QPushButton, QScrollArea, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
import config

class ToolWorkerThread(QThread):
    result_ready = Signal(str, dict)

    def __init__(self, uid, run_func):
        super().__init__()
        self.uid = uid
        self.run_func = run_func

    def run(self):
        try:
            res = self.run_func()
            self.result_ready.emit(self.uid, res)
        except Exception as e:
            self.result_ready.emit(self.uid, {'success': False, 'message': str(e)})

class UtilitiesTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.active_category = 'all'
        self.search_text = ""
        self.threads = {}
        self.util_cards = {}
        self.all_utilities = []
        self.cat_buttons = {}
        self.create_widgets()

    def _ensure_utilities_loaded(self):
        if not self.all_utilities:
            from utilities import ALL_UTILITIES
            self.all_utilities = ALL_UTILITIES

    # ── Theme helpers (call each time, never cache) ───────
    def _t(self):
        """Returns a dict of current theme colors."""
        dark = config.THEME == "dark"
        return {
            "card_bg":   "#1e2130" if dark else "#ffffff",
            "card_hover":"#252839" if dark else "#f0f2f7",
            "text":      "#e8eaf6" if dark else "#1e293b",
            "muted":     "#8b90b8" if dark else "#64748b",
            "border":    "#2d3150" if dark else "#e2e8f0",
            "pill_bg":   "#2d3150" if dark else "#f0f1f5",
            "pill_fg":   "#8b90b8" if dark else "#475569",
            "pill_bdr":  "#3f4468" if dark else "#e2e4ea",
            "input_bg":  "#1a1d27" if dark else "#f8fafc",
        }

    def create_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(28, 28, 28, 28)
        self.container_layout.setSpacing(18)

        # ── Title row ─────────────────────────────────────────
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(4)

        self.title_lbl = QLabel("Utilities Hub")
        self.title_lbl.setProperty("class", "Title")
        
        self._ensure_utilities_loaded()
        count = len(self.all_utilities)
        self.sub_lbl = QLabel(f"{count} one-click tools for every Windows problem")
        self.sub_lbl.setProperty("class", "Muted")
        header_text.addWidget(self.title_lbl)
        header_text.addWidget(self.sub_lbl)

        header.addLayout(header_text)
        header.addStretch()

        # Search field — styled via QSS in themes.py (QLineEdit rule)
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("🔍 Search utilities…")
        self.search_entry.setFixedSize(240, 36)
        self.search_entry.textChanged.connect(self._on_search)
        header.addWidget(self.search_entry, alignment=Qt.AlignVCenter)
        self.container_layout.addLayout(header)

        # ── Category pill bar (Scrollable) ───────────────────
        from utilities import CATEGORY_MAP
        
        cat_scroll = QScrollArea()
        cat_scroll.setFixedHeight(50)
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cat_scroll.setStyleSheet("background: transparent;")
        
        cat_container = QWidget()
        cat_container.setStyleSheet("background: transparent;")
        cat_layout = QHBoxLayout(cat_container)
        cat_layout.setContentsMargins(0, 5, 0, 5)
        cat_layout.setSpacing(8)

        sorted_cats = [('all', CATEGORY_MAP['all'])] + sorted(
            [(k, v) for k, v in CATEGORY_MAP.items() if k != 'all'],
            key=lambda x: x[1]
        )

        for cat_id, cat_label in sorted_cats:
            u_count = len(self.all_utilities) if cat_id == 'all' else len(
                [u for u in self.all_utilities if u['category'] == cat_id]
            )
            text = f"{cat_label} ({u_count})"
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._pill_style(cat_id == 'all'))
            if cat_id == 'all':
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, c=cat_id: self._set_category(c))
            cat_layout.addWidget(btn)
            self.cat_buttons[cat_id] = btn

        cat_layout.addStretch()
        cat_scroll.setWidget(cat_container)
        self.container_layout.addWidget(cat_scroll)

        # ── Grid area ─────────────────────────────────────────
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.container_layout.addWidget(self.grid_widget)
        self.container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        self._refresh_grid()

    # ── CATEGORY PILLS ────────────────────────────────────────

    def _pill_style(self, active: bool) -> str:
        t = self._t()
        if active:
            return (
                f"background-color: {config.ACCENT_COLOR}; color: white; "
                f"border: none; border-radius: 17px; padding: 0 14px; "
                f"font-weight: bold; font-size: 12px;"
            )
        return (
            f"background-color: {t['pill_bg']}; color: {t['pill_fg']}; "
            f"border: 1px solid {t['pill_bdr']}; border-radius: 17px; "
            f"padding: 0 14px; font-size: 12px;"
        )

    def _set_category(self, cat):
        self.active_category = cat
        for cid, btn in self.cat_buttons.items():
            btn.setStyleSheet(self._pill_style(cid == cat))
            btn.setChecked(cid == cat)
        self._refresh_grid()

    # ── SEARCH ────────────────────────────────────────────────

    def _on_search(self, text):
        self.search_text = text.lower()
        self._refresh_grid()

    # ── GRID ──────────────────────────────────────────────────

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _refresh_grid(self):
        self._ensure_utilities_loaded()
        self._clear_grid()
        self.util_cards = {}

        filtered = [
            u for u in self.all_utilities
            if (self.active_category == 'all' or u['category'] == self.active_category)
            and (self.search_text == '' or self.search_text in u['name'].lower() or self.search_text in u['desc'].lower())
        ]

        if not filtered:
            t = self._t()
            lbl = QLabel("🔍 No utilities found")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {t['muted']}; font-size: 14px; padding: 40px;")
            self.grid_layout.addWidget(lbl, 0, 0, 1, 5, Qt.AlignCenter)
            return

        cols = 5
        for idx, util in enumerate(filtered):
            row, col = divmod(idx, cols)
            card = self._create_card(util)
            self.grid_layout.addWidget(card, row, col)

    # ── CARD ──────────────────────────────────────────────────

    def _create_card(self, util):
        uid = util['id']
        color = util.get('color', config.ACCENT_COLOR)
        t = self._t()

        card = QFrame()
        card.setObjectName("UtilCard")
        card.setStyleSheet(f"""
            QFrame#UtilCard {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 12px;
                padding: 0;
            }}
            QFrame#UtilCard:hover {{
                border: 1px solid {config.ACCENT_COLOR};
                background-color: {t['card_hover']};
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 16, 16, 14)
        cl.setSpacing(8)

        icon_lbl = QLabel(util['icon'])
        icon_lbl.setStyleSheet("font-size: 24px; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(icon_lbl)

        name_lbl = QLabel(util['name'])
        name_lbl.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {t['text']}; background: transparent;"
        )
        name_lbl.setWordWrap(True)
        cl.addWidget(name_lbl)

        desc_lbl = QLabel(util['desc'])
        desc_lbl.setStyleSheet(
            f"font-size: 11px; color: {t['muted']}; background: transparent;"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setMinimumHeight(32)
        cl.addWidget(desc_lbl)

        cl.addStretch()

        btn = QPushButton("▷ Run")
        btn.setObjectName("RunLink")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton#RunLink {{
                background: transparent; border: none;
                color: {color}; font-weight: bold; font-size: 13px;
                text-align: left; padding: 0;
            }}
            QPushButton#RunLink:hover {{ text-decoration: underline; }}
        """)
        btn.setFixedHeight(24)
        btn.clicked.connect(lambda checked=False, u=util: self._run_utility(u))
        cl.addWidget(btn)

        self.util_cards[uid] = {'btn': btn, 'color': color}
        return card

    # ── EXECUTE ───────────────────────────────────────────────

    def _run_utility(self, util):
        uid = util['id']
        if uid in self.threads:
            return

        card_info = self.util_cards.get(uid)
        if card_info:
            card_info['btn'].setText("⟳ Running…")
            card_info['btn'].setEnabled(False)

        thread = ToolWorkerThread(uid, util['run'])
        thread.result_ready.connect(self._handle_result)
        self.threads[uid] = thread
        thread.start()

    def _handle_result(self, uid, result):
        if uid in self.threads:
            del self.threads[uid]

        card_info = self.util_cards.get(uid)
        if card_info:
            color = card_info['color']
            card_info['btn'].setText("▷ Run")
            card_info['btn'].setEnabled(True)

        msg = result.get('message', 'Done')[:80]
        icon = '✅' if result.get('success') else '⚠️'
        if self.main_window:
            self.main_window.update_status(f"{icon} {msg}")
