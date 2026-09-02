"""PySide6 desktop Markdown editor."""
from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from editor.content import ContentRepository

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QSpinBox, QStatusBar, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

ROOT_OPTION = "כללי (ללא תיקייה)"
SITE_TEXT_DEFAULTS = {
    "site_title": "CyberLearn | למידה חכמה",
    "brand_prefix": "Cyber",
    "brand_accent": "Learn",
    "brand_home_label": "דף הבית של CyberLearn",
    "tagline": "הנדסת תוכנה וסייבר · לומדים, מתרגלים, מבינים",
    "menu_label": "תכנים ☰",
    "theme_light_label": "☀ מצב בהיר",
    "theme_dark_label": "🌙 מצב כהה",
    "learning_path_label": "מסלול הלמידה",
    "navigation_label": "ניווט בתכני הלמידה",
    "loading_content": "טוען תכנים…",
    "page_count": "{count} עמודים זמינים",
    "empty_title": "עוד אין תכנים",
    "empty_description": "צרו את העמוד הראשון דרך תוכנת העורך. היא תעדכן את האינדקס אוטומטית.",
    "loading_page": "טוען את השיעור…",
    "load_error_title": "לא הצלחנו לטעון את העמוד",
    "load_error_description": "ודאו שהקובץ {file} קיים, ושהאתר מופעל דרך שרת מקומי.",
    "missing_index_title": "חסר קובץ אינדקס",
    "missing_index_description": "פתחו את תוכנת העורך ושמרו עמוד כדי ליצור את האינדקס אוטומטית.",
    "font_size_body": "18",
    "font_size_h1": "56",
    "font_size_h2": "29",
    "font_size_h3": "21",
    "font_size_sidebar": "16",
    "font_size_sidebar_heading": "18",
    "sidebar_spacing": "4",
    "navigation_default_expanded": "true",
}


class ReorderTreeWidget(QTreeWidget):
    """Read-only navigation tree; ordering is managed through page metadata."""
    def __init__(self, on_drop, parent=None) -> None:
        super().__init__(parent); self.on_drop = on_drop
        self.dragged_item: QTreeWidgetItem | None = None
        self.setDragEnabled(False); self.setAcceptDrops(False); self.setDropIndicatorShown(False)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)

    def startDrag(self, supported_actions) -> None:
        self.dragged_item = self.currentItem()
        super().startDrag(supported_actions)

    def dropEvent(self, event) -> None:
        source, target = self.dragged_item, self.itemAt(event.position().toPoint())
        if source and target and source is not target:
            rectangle = self.visualItemRect(target); y = event.position().y()
            before = y < rectangle.center().y()
            # Drag-and-drop is intentionally ordering-only: moving a folder into another
            # folder made it look as if the source had disappeared from the tree.
            self.on_drop(source, target, before, False)
        self.dragged_item = None
        event.accept()


class CyberLearnEditor(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.project = Path(__file__).resolve().parent
        self.content_dir = self.project / "public" / "content"
        self.images_dir = self.project / "public" / "assets" / "images"
        self.index_path = self.project / "public" / "content-index.json"
        self.site_text_path = self.project / "public" / "site-texts.json"
        self.homepage_path = self.project / "public" / "homepage.json"
        self.editor_settings_path = self.project / ".editor-settings.json"
        self.current_file: Path | None = None
        self.repository = ContentRepository(self.project)
        self._clean_snapshot = ""
        self._loading_document = False
        self._local_server: subprocess.Popen | None = None
        self._local_server_port: int | None = None
        self.editor_font_size = self.read_editor_font_size()
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists(): self.write_index([])
        if not self.site_text_path.exists(): self.write_site_texts(SITE_TEXT_DEFAULTS)
        self.setWindowTitle("עורך תוכן"); self.resize(1380, 820); self.setMinimumSize(1050, 650)
        self.build_ui(); self.refresh_tree(); self.restore_recovery()

    def build_ui(self) -> None:
        self._editor_style_template = """
            QMainWindow,QDialog{background:#081421;color:#edf5fa;font-family:Assistant,Arial;font-size:__EDITOR_FONT_SIZE__px}
            QFrame#header,QFrame#details,QFrame#toolbar{background:#13243a;border-radius:10px}
            QLabel{color:#dbe8f1} QLineEdit,QPlainTextEdit,QComboBox,QTreeWidget,QTextBrowser{background:#07111d;color:#edf5fa;border:1px solid #28516c;border-radius:7px;padding:7px}
            QTreeWidget{background:#0c1a2a;border:0} QTreeWidget::item:selected{background:#15516a} QComboBox QAbstractItemView{background:#13243a;color:white;selection-background-color:#15516a}
            QPushButton{background:#1b4261;color:white;border:0;border-radius:7px;padding:8px 11px} QPushButton:hover{background:#285775}
            QPushButton#save{background:#00a878;color:#06121d;font-weight:bold} QPushButton#save:hover{background:#00c58c} QPushButton#danger{background:#8d3144}
            QStatusBar{background:#102238;color:#aebdca}
        """
        self.setStyleSheet(self._editor_style_template.replace("__EDITOR_FONT_SIZE__", str(self.editor_font_size)))
        root = QWidget(); outer = QVBoxLayout(root); outer.setContentsMargins(18, 14, 18, 14); outer.setSpacing(12)
        header = QFrame(); header.setObjectName("header"); header_layout = QHBoxLayout(header)
        self.editor_heading = QLabel("עורך תוכן")
        self.editor_heading.setStyleSheet(f"font-size:{round(self.editor_font_size * 1.65)}px;font-weight:700;color:#00d4ff")
        header_layout.addWidget(self.editor_heading); header_layout.addStretch(); header_layout.addWidget(QLabel("כל שמירה מעדכנת את אינדקס האתר"))
        header_layout.addWidget(QLabel("גודל טקסט בעורך:"))
        self.editor_font_size_control = QSpinBox(); self.editor_font_size_control.setRange(10, 28); self.editor_font_size_control.setSuffix(" px"); self.editor_font_size_control.setValue(self.editor_font_size); self.editor_font_size_control.valueChanged.connect(self.set_editor_font_size); header_layout.addWidget(self.editor_font_size_control)
        self.local_site_button = QPushButton("▶ פתח אתר מקומי"); self.local_site_button.clicked.connect(self.toggle_local_site); header_layout.addWidget(self.local_site_button)
        button = QPushButton("◉ החלפת סמל אתר"); button.clicked.connect(self.change_favicon); header_layout.addWidget(button)
        button = QPushButton("⚙ טקסטים קבועים באתר"); button.clicked.connect(self.edit_site_texts); header_layout.addWidget(button)
        button = QPushButton("⌂ עמוד הבית"); button.clicked.connect(self.edit_homepage); header_layout.addWidget(button)
        button = QPushButton("✓ בדיקת האתר"); button.clicked.connect(self.validate_site); header_layout.addWidget(button)
        button = QPushButton("↻ רענון"); button.clicked.connect(self.refresh_with_guard); header_layout.addWidget(button); outer.addWidget(header)
        splitter = QSplitter(Qt.Horizontal); splitter.setLayoutDirection(Qt.RightToLeft)
        sidebar = QWidget(); side = QVBoxLayout(sidebar); self.sidebar_title = QLabel("עמודי האתר"); self.sidebar_title.setStyleSheet(f"font-size:{round(self.editor_font_size * 1.3)}px;font-weight:700;color:#ffd93d"); side.addWidget(self.sidebar_title)
        button = QPushButton("＋ עמוד חדש"); button.clicked.connect(self.new_page); side.addWidget(button)
        button = QPushButton("＋ תיקייה חדשה"); button.clicked.connect(self.new_folder_dialog); side.addWidget(button)
        publish_buttons = QHBoxLayout(); publish = QPushButton("פרסם נבחרים"); unpublish = QPushButton("הסר מפרסום"); publish.clicked.connect(lambda: self.set_selected_publication(True)); unpublish.clicked.connect(lambda: self.set_selected_publication(False)); publish_buttons.addWidget(publish); publish_buttons.addWidget(unpublish); side.addLayout(publish_buttons)
        order_buttons = QHBoxLayout(); up = QPushButton("↑ העלה"); down = QPushButton("↓ הורד"); up.clicked.connect(lambda: self.move_selected_in_order(-1)); down.clicked.connect(lambda: self.move_selected_in_order(1)); order_buttons.addWidget(up); order_buttons.addWidget(down); side.addLayout(order_buttons)
        button = QPushButton("✎ שינוי שם תיקייה"); button.clicked.connect(self.rename_folder_dialog); side.addWidget(button)
        button = QPushButton("מחק פריט נבחר"); button.setObjectName("danger"); button.clicked.connect(self.delete_selected_tree_item); side.addWidget(button)
        self.tree = ReorderTreeWidget(self.reorder_tree_item); self.tree.setHeaderHidden(True); self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection); self.tree.setContextMenuPolicy(Qt.CustomContextMenu); self.tree.customContextMenuRequested.connect(self.show_tree_context_menu); self.tree.itemSelectionChanged.connect(self.open_selected); side.addWidget(self.tree); splitter.addWidget(sidebar)
        edit = QWidget(); layout = QVBoxLayout(edit); layout.setContentsMargins(10, 0, 0, 0); layout.setSpacing(9)
        details = QFrame(); details.setObjectName("details"); form = QFormLayout(details); form.setLabelAlignment(Qt.AlignRight); form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.title_edit = QLineEdit(); self.filename_edit = QLineEdit(); self.folder_combo = QComboBox(); self.order_edit = QSpinBox(); self.order_edit.setRange(1, 9999); self.published_check = QCheckBox("פרסם עמוד זה באתר")
        for field in (self.title_edit, self.filename_edit):
            field.setAlignment(Qt.AlignRight); field.setLayoutDirection(Qt.RightToLeft)
        self.folder_combo.setLayoutDirection(Qt.RightToLeft)
        folder_row = QWidget(); folders = QHBoxLayout(folder_row); folders.setContentsMargins(0, 0, 0, 0); folders.addWidget(self.folder_combo, 1)
        form.addRow("כותרת", self.title_edit); form.addRow("מיקום בתיקיות", folder_row); form.addRow("שם הקובץ", self.filename_edit); form.addRow("סדר תצוגה", self.order_edit); form.addRow("פרסום", self.published_check); layout.addWidget(details)
        toolbar = QFrame(); toolbar.setObjectName("toolbar"); tools = QHBoxLayout(toolbar); tools.setContentsMargins(8, 6, 8, 6)
        tools.addWidget(QLabel("כיוון התוכן:"))
        self.direction_combo = QComboBox(); self.direction_combo.addItem("RTL — ימין לשמאל", Qt.RightToLeft); self.direction_combo.addItem("LTR — שמאל לימין", Qt.LeftToRight); tools.addWidget(self.direction_combo)
        tools.addWidget(QLabel("סוג טקסט:"))
        self.heading_combo = QComboBox(); self.heading_combo.addItem("בחרו סגנון"); self.heading_combo.addItem("כותרת 1", "# "); self.heading_combo.addItem("כותרת 2", "## "); self.heading_combo.addItem("כותרת 3", "### "); self.heading_combo.addItem("טקסט רגיל", ""); tools.addWidget(self.heading_combo)
        for label, callback in [("B מודגש", lambda: self.wrap("**", "**")), ("I נטוי", lambda: self.wrap("*", "*")), ("• רשימה", lambda: self.prefix("- ")), ("1. רשימה", lambda: self.prefix("1. ")), ("ציטוט", lambda: self.prefix("> ")), ("קישור", self.insert_link), ("תמונה", self.image_library_dialog), ("קו מפריד", self.insert_horizontal_rule), ("באתר RTL", lambda: self.wrap_website_direction("rtl")), ("באתר LTR", lambda: self.wrap_website_direction("ltr")), ("Mermaid", self.mermaid_block), ("קוד", lambda: self.wrap("`", "`")), ("בלוק קוד", self.code_block)]:
            button = QPushButton(label); button.clicked.connect(callback); tools.addWidget(button)
        tools.addStretch(); layout.addWidget(toolbar)
        self.body = QPlainTextEdit(); self.body.setPlaceholderText("כתבו כאן את תוכן השיעור ב-Markdown…"); self.apply_editor_content_font(); self.direction_combo.currentIndexChanged.connect(self.set_body_direction); self.heading_combo.currentIndexChanged.connect(self.apply_heading); self.set_body_direction(); layout.addWidget(self.body, 1)
        for field in (self.title_edit, self.filename_edit, self.body): field.textChanged.connect(self.update_dirty_state)
        actions = QHBoxLayout()
        for label, callback, object_name in [("הדבק", self.body.paste, ""), ("העתק", self.body.copy, ""), ("גזור", self.body.cut, ""), ("מחק עמוד", self.delete_page, "danger"), ("שמור ועדכן אתר", self.save_page, "save")]:
            button = QPushButton(label)
            if object_name: button.setObjectName(object_name)
            button.clicked.connect(callback); actions.addWidget(button)
            if label == "גזור": actions.addStretch()
        layout.addLayout(actions); splitter.addWidget(edit); splitter.setSizes([300, 1030]); outer.addWidget(splitter, 1)
        self.setCentralWidget(root); self.setStatusBar(QStatusBar()); self.statusBar().showMessage("בחרו עמוד או צרו עמוד חדש")
        for label, callback, shortcut in [("שמירה", self.save_page, "Ctrl+S"), ("עמוד חדש", self.new_page, "Ctrl+N"), ("מודגש", lambda: self.wrap("**", "**"), "Ctrl+B"), ("נטוי", lambda: self.wrap("*", "*"), "Ctrl+I"), ("קישור", self.insert_link, "Ctrl+K"), ("קוד פנימי", lambda: self.wrap("`", "`"), "Ctrl+`"), ("פתח/עצור אתר מקומי", self.toggle_local_site, "Ctrl+P"), ("חיפוש", self.focus_tree, "Ctrl+F")]:
            action = QAction(label, self); action.setShortcut(shortcut); action.triggered.connect(callback); self.addAction(action)

    def read_editor_font_size(self) -> int:
        try:
            settings = json.loads(self.editor_settings_path.read_text(encoding="utf-8"))
            return max(10, min(28, int(settings.get("font_size", 14))))
        except (OSError, ValueError, json.JSONDecodeError, TypeError):
            return 14

    def set_editor_font_size(self, size: int) -> None:
        self.editor_font_size = max(10, min(28, int(size)))
        self.setStyleSheet(self._editor_style_template.replace("__EDITOR_FONT_SIZE__", str(self.editor_font_size)))
        self.apply_editor_content_font()
        if hasattr(self, "editor_heading"):
            self.editor_heading.setStyleSheet(f"font-size:{round(self.editor_font_size * 1.65)}px;font-weight:700;color:#00d4ff")
            self.sidebar_title.setStyleSheet(f"font-size:{round(self.editor_font_size * 1.3)}px;font-weight:700;color:#ffd93d")
        try:
            self.editor_settings_path.write_text(json.dumps({"font_size": self.editor_font_size}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as error:
            self.statusBar().showMessage(f"לא ניתן לשמור את גודל הטקסט: {error}")

    def apply_editor_content_font(self) -> None:
        if not hasattr(self, "body"):
            return
        font = self.body.font()
        font.setPixelSize(self.editor_font_size)
        self.body.setFont(font)

    def snapshot(self) -> str:
        return "\0".join((self.title_edit.text(), self.filename_edit.text(), self.folder_combo.currentText(), str(self.order_edit.value()), self.body.toPlainText()))

    def update_dirty_state(self, *_args) -> None:
        if not self._loading_document:
            dirty = self.snapshot() != self._clean_snapshot
            self.setWindowTitle(("* " if dirty else "") + "עורך תוכן")
            if dirty: self.write_recovery()

    def is_dirty(self) -> bool: return bool(self._clean_snapshot) and self.snapshot() != self._clean_snapshot

    def mark_clean(self) -> None:
        self._clean_snapshot = self.snapshot(); self.setWindowTitle("עורך תוכן")
        recovery = self.project / ".editor-recovery.json"
        if recovery.exists(): recovery.unlink()

    def write_recovery(self) -> None:
        if not self.is_dirty() and self._clean_snapshot: return
        data = {"path": self.current_file.relative_to(self.content_dir).as_posix() if self.current_file else None, "title": self.title_edit.text(), "filename": self.filename_edit.text(), "folder": self.selected_folder(), "order": self.order_edit.value(), "body": self.body.toPlainText()}
        (self.project / ".editor-recovery.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def confirm_discard(self, action: str) -> bool:
        if not self.is_dirty(): return True
        dialog = QMessageBox(self); dialog.setWindowTitle("שינויים שלא נשמרו"); dialog.setText(f"יש שינויים שלא נשמרו לפני {action}."); save = dialog.addButton("שמירה", QMessageBox.AcceptRole); discard = dialog.addButton("המשך ללא שמירה", QMessageBox.DestructiveRole); dialog.addButton("ביטול", QMessageBox.RejectRole); dialog.exec()
        if dialog.clickedButton() == save: self.save_page(); return not self.is_dirty()
        return dialog.clickedButton() == discard

    def focus_tree(self) -> None: self.tree.setFocus()

    def refresh_with_guard(self) -> None:
        if self.confirm_discard("רענון"): self.refresh_tree()

    def index_paths(self) -> list[str]:
        try:
            entries = json.loads(self.index_path.read_text(encoding="utf-8"))
            if isinstance(entries, dict): entries = entries.get("pages", [])
            return [entry["path"] for entry in entries if isinstance(entry, dict) and isinstance(entry.get("path"), str)]
        except (OSError, ValueError, json.JSONDecodeError):
            return []

    def markdown_files(self) -> list[Path]:
        files = {file.relative_to(self.content_dir).as_posix(): file for file in self.content_dir.rglob("*.md")}
        ordered = [files.pop(path) for path in self.index_paths() if path in files]
        return [*ordered, *(files[path] for path in sorted(files, key=str.casefold))]

    def display_position(self, relative: str) -> int:
        paths = [file.relative_to(self.content_dir).as_posix() for file in self.markdown_files()]
        return paths.index(relative) + 1 if relative in paths else len(paths) + 1

    def ordered_paths_with(self, relative: str, position: int, old_relative: str | None = None) -> list[str]:
        paths = [file.relative_to(self.content_dir).as_posix() for file in self.markdown_files()]
        paths = [path for path in paths if path not in {relative, old_relative}]
        paths.insert(min(max(position - 1, 0), len(paths)), relative)
        return paths
    def folder_options(self) -> list[str]: return [ROOT_OPTION, *sorted((item.relative_to(self.content_dir).as_posix() for item in self.content_dir.rglob("*") if item.is_dir()), key=str.casefold)]
    def selected_folder(self) -> str: return "" if self.folder_combo.currentText() == ROOT_OPTION else self.folder_combo.currentText()
    @staticmethod
    def title_from_markdown(text: str, fallback: str) -> str:
        found = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
        return re.sub(r"[*_`]", "", found.group(1)).strip() if found else fallback.replace("-", " ").replace("_", " ")

    def refresh_folder_options(self, selected: str | None = None) -> None:
        current = selected if selected is not None else self.folder_combo.currentText(); self.folder_combo.blockSignals(True); self.folder_combo.clear(); self.folder_combo.addItems(self.folder_options())
        self.folder_combo.setCurrentIndex(max(0, self.folder_combo.findText(current))); self.folder_combo.blockSignals(False)

    def refresh_tree(self) -> None:
        self.refresh_folder_options(); self.tree.clear()
        index_orders = {entry["path"]: int(entry.get("order", 9999)) for entry in self.repository.read_index()}
        def page_order(file: Path) -> int: return index_orders.get(file.relative_to(self.content_dir).as_posix(), 9999)
        def folder_order(folder: Path) -> int:
            return min((page_order(file) for file in folder.rglob("*.md")), default=9999)
        def add_entries(folder: Path, parent: QTreeWidgetItem) -> None:
            entries = [*folder.iterdir()]
            entries.sort(key=lambda entry: ((folder_order(entry) if entry.is_dir() else page_order(entry)), 0 if entry.is_dir() else 1, entry.name.casefold()))
            for entry in entries:
                if entry.is_dir():
                    item = QTreeWidgetItem([entry.name])
                    item.setData(0, Qt.UserRole, None); item.setData(0, Qt.UserRole + 1, entry.relative_to(self.content_dir).as_posix()); parent.addChild(item); add_entries(entry, item)
                elif entry.suffix.lower() == ".md":
                    relative = entry.relative_to(self.content_dir).as_posix(); item = QTreeWidgetItem([self.title_from_markdown(entry.read_text(encoding="utf-8"), entry.stem)]); item.setData(0, Qt.UserRole, relative); parent.addChild(item)
        add_entries(self.content_dir, self.tree.invisibleRootItem())
        self.rebuild_index(); self.tree.expandAll()

    def tree_item_paths(self, item: QTreeWidgetItem) -> list[str]:
        paths = [file.relative_to(self.content_dir).as_posix() for file in self.markdown_files()]
        relative = item.data(0, Qt.UserRole)
        if relative:
            return [relative]
        parts = []
        current = item
        while current:
            parts.append(current.text(0)); current = current.parent()
        prefix = "/".join(reversed(parts)) + "/"
        return [path for path in paths if path.startswith(prefix)]

    @staticmethod
    def tree_folder_path(item: QTreeWidgetItem) -> str | None:
        if item.data(0, Qt.UserRole):
            return None
        if stored := item.data(0, Qt.UserRole + 1):
            return str(stored)
        parts = []
        current = item
        while current:
            parts.append(current.text(0)); current = current.parent()
        return "/".join(reversed(parts))

    def show_tree_context_menu(self, position) -> None:
        item = self.tree.itemAt(position)
        if not item or item.data(0, Qt.UserRole):
            return
        self.tree.setCurrentItem(item)
        menu = QMenu(self)
        move_action = menu.addAction("העבר תיקייה…")
        if menu.exec(self.tree.viewport().mapToGlobal(position)) == move_action:
            self.move_folder_dialog(item)

    def move_folder_dialog(self, item: QTreeWidgetItem) -> None:
        source_relative = self.tree_folder_path(item)
        if not source_relative:
            return
        options = [ROOT_OPTION, *(folder for folder in self.folder_options()[1:] if folder != source_relative and not folder.startswith(source_relative + "/"))]
        dialog = QDialog(self); dialog.setWindowTitle("העברת תיקייה"); layout = QFormLayout(dialog)
        layout.addRow(QLabel(f"תיקייה להעברה: {source_relative}"))
        target = QComboBox(); target.addItems(options); layout.addRow("תיקיית יעד", target)
        actions = QHBoxLayout(); cancel = QPushButton("ביטול"); move = QPushButton("העבר תיקייה"); move.setObjectName("save"); actions.addWidget(cancel); actions.addWidget(move); layout.addRow(actions)
        cancel.clicked.connect(dialog.reject)
        def move_folder() -> None:
            destination = "" if target.currentText() == ROOT_OPTION else target.currentText()
            try:
                self.move_tree_item_into_folder(item, destination); dialog.accept()
            except (OSError, ValueError) as error:
                QMessageBox.warning(dialog, "לא ניתן להעביר תיקייה", str(error))
        move.clicked.connect(move_folder); dialog.exec()

    def move_selected_in_order(self, direction: int) -> None:
        selected = self.tree.selectedItems()
        if not selected:
            self.statusBar().showMessage("בחרו עמוד או תיקייה תחילה."); return
        item = selected[0]; selected_path = item.data(0, Qt.UserRole) or self.tree_folder_path(item); is_file = bool(item.data(0, Qt.UserRole)); parent = item.parent() or self.tree.invisibleRootItem()
        published_paths = set(self.index_paths())
        if not any(path in published_paths for path in self.tree_item_paths(item)):
            self.statusBar().showMessage("כדי לשנות סדר באתר, פרסמו את העמוד תחילה."); return
        siblings = [parent.child(index) for index in range(parent.childCount())]
        current = siblings.index(item); destination = current + direction
        if destination < 0 or destination >= len(siblings):
            self.statusBar().showMessage("הפריט כבר בקצה הרשימה."); return
        siblings[current], siblings[destination] = siblings[destination], siblings[current]
        blocks = [[path for path in self.tree_item_paths(sibling) if path in published_paths] for sibling in siblings]
        parent_paths = {path for block in blocks for path in block}
        ordered = self.index_paths()
        replacement = [path for block in blocks for path in block]
        first = min(index for index, path in enumerate(ordered) if path in parent_paths)
        new_order = [path for path in ordered if path not in parent_paths]
        new_order[first:first] = replacement
        self.rebuild_index(new_order); self.refresh_tree(); self.reselect_tree_item(str(selected_path), is_file); self.statusBar().showMessage("סדר התצוגה עודכן.")

    def reselect_tree_item(self, path: str, is_file: bool) -> None:
        def find(parent: QTreeWidgetItem) -> QTreeWidgetItem | None:
            for index in range(parent.childCount()):
                item = parent.child(index)
                candidate = item.data(0, Qt.UserRole) if is_file else self.tree_folder_path(item)
                if candidate == path:
                    return item
                if found := find(item):
                    return found
            return None
        if item := find(self.tree.invisibleRootItem()):
            self.tree.setCurrentItem(item); self.tree.scrollToItem(item)

    def set_selected_publication(self, published: bool) -> None:
        selected_paths = [str(item.data(0, Qt.UserRole)) for item in self.tree.selectedItems() if item.data(0, Qt.UserRole)]
        if not selected_paths:
            self.statusBar().showMessage("בחרו עמוד אחד או יותר לפרסום."); return
        paths = self.index_paths()
        if published:
            paths.extend(path for path in selected_paths if path not in paths)
        else:
            paths = [path for path in paths if path not in selected_paths]
        self.rebuild_index(paths); self.refresh_tree()
        verb = "פורסמו" if published else "הוסרו מפרסום"
        self.statusBar().showMessage(f"{len(selected_paths)} עמודים {verb}.")

    def move_tree_item_into_folder(self, source: QTreeWidgetItem, target_folder: str) -> None:
        source_relative = source.data(0, Qt.UserRole) or self.tree_folder_path(source)
        source_path = self.content_dir / source_relative
        destination_folder = self.content_dir / target_folder
        destination = destination_folder / source_path.name
        if not source_path.exists() or not destination_folder.is_dir():
            raise ValueError("הפריט או תיקיית היעד אינם קיימים.")
        if source_path.is_dir() and destination_folder.is_relative_to(source_path):
            raise ValueError("אי אפשר להעביר תיקייה לתוך עצמה או לתוך אחת מתתי־התיקיות שלה.")
        if destination == source_path:
            return
        if destination.exists():
            raise ValueError(f"כבר קיים פריט בשם {destination.name} בתיקיית היעד.")
        old_paths = self.index_paths()
        old_prefix, new_prefix = source_relative + "/", (target_folder + "/" if target_folder else "") + source_path.name + "/"
        source_path.rename(destination)
        if self.current_file and self.current_file.is_relative_to(source_path):
            self.current_file = destination / self.current_file.relative_to(source_path)
        moved_paths = [new_prefix + path.removeprefix(old_prefix) if path.startswith(old_prefix) else ((target_folder + "/" if target_folder else "") + source_path.name if path == source_relative else path) for path in old_paths]
        self.rebuild_index(moved_paths); self.refresh_tree()
        self.statusBar().showMessage(f"הועבר אל: content/{destination.relative_to(self.content_dir).as_posix()}")

    def reorder_tree_item(self, source: QTreeWidgetItem, target: QTreeWidgetItem, before: bool, into_folder: bool = False) -> None:
        source_path = source.data(0, Qt.UserRole) or self.tree_folder_path(source)
        target_path = target.data(0, Qt.UserRole) or self.tree_folder_path(target)
        if not source_path or not target_path or source is target:
            return
        target_folder = self.tree_folder_path(target)
        if into_folder and target_folder is not None:
            try:
                self.move_tree_item_into_folder(source, target_folder)
            except (OSError, ValueError) as error:
                self.statusBar().showMessage(str(error))
            return
        source_parent, target_parent = source.parent() or self.tree.invisibleRootItem(), target.parent() or self.tree.invisibleRootItem()
        source_parent_path = self.tree_folder_path(source.parent()) if source.parent() else ""
        target_parent_path = self.tree_folder_path(target.parent()) if target.parent() else ""
        if source_parent_path != target_parent_path:
            self.statusBar().showMessage("אפשר לשנות סדר רק בין פריטים באותה תיקייה.")
            return
        siblings = [source_parent.child(index) for index in range(source_parent.childCount())]
        siblings.remove(source); target_index = siblings.index(target) + (0 if before else 1); siblings.insert(target_index, source)
        for position, item in enumerate(siblings, 1): self.set_tree_item_order(item, position * 10)
        self.rebuild_index()
        self.refresh_tree(); self.statusBar().showMessage("סדר התצוגה עודכן באמצעות גרירה בתפריט.")

    def set_tree_item_order(self, item: QTreeWidgetItem, order: int) -> None:
        """Ordering is intentionally stored only in content-index.json."""
        return

    def open_selected(self) -> None:
        selected = self.tree.selectedItems()
        if len(selected) != 1 or not (relative := selected[0].data(0, Qt.UserRole)): return
        if self.current_file and self.current_file.relative_to(self.content_dir).as_posix() != relative and not self.confirm_discard("מעבר לעמוד אחר"): return
        file = self.content_dir / relative; text = file.read_text(encoding="utf-8"); path = file.relative_to(self.content_dir); self.current_file = file
        self._loading_document = True
        self.title_edit.setText(self.title_from_markdown(text, file.stem)); self.refresh_folder_options(path.parent.as_posix() if path.parent != Path(".") else ROOT_OPTION); self.filename_edit.setText(file.name); self.order_edit.setValue(self.display_position(relative)); self.published_check.setChecked(relative in self.index_paths()); self.body.setPlainText(text); self.set_body_direction(); self.statusBar().showMessage(f"עורכים: content/{path.as_posix()}")
        self._loading_document = False; self.mark_clean()

    def new_page(self) -> None:
        if self.current_file and not self.confirm_discard("יצירת עמוד חדש"): return
        self._loading_document = True
        self.current_file = None; self.title_edit.clear(); self.filename_edit.setText("שיעור-חדש.md"); self.order_edit.setValue(len(self.index_paths()) + 1); self.refresh_folder_options(ROOT_OPTION); self.published_check.setChecked(False); self.body.setPlainText("# כותרת השיעור\n\nכתבו כאן את תוכן השיעור…\n"); self.set_body_direction(); self.title_edit.setFocus(); self.statusBar().showMessage("עמוד חדש — סמנו פרסום אם הוא מוכן להצגה באתר")
        self._loading_document = False; self.mark_clean()

    def set_body_direction(self, _index: int | None = None) -> None:
        """Apply the selected reading direction to existing and newly typed Markdown."""
        direction = self.direction_combo.currentData()
        alignment = Qt.AlignRight if direction == Qt.RightToLeft else Qt.AlignLeft
        selection = self.body.textCursor(); start, end = selection.selectionStart(), selection.selectionEnd()
        block_format = QTextBlockFormat(); block_format.setLayoutDirection(direction); block_format.setAlignment(alignment)
        text_option = self.body.document().defaultTextOption()
        text_option.setTextDirection(direction); text_option.setAlignment(alignment)
        self.body.document().setDefaultTextOption(text_option)
        block = self.body.document().begin()
        while block.isValid():
            cursor = QTextCursor(block); cursor.setBlockFormat(block_format); block = block.next()
        restored = QTextCursor(self.body.document()); restored.setPosition(start); restored.setPosition(end, QTextCursor.KeepAnchor)
        self.body.setTextCursor(restored); self.body.setLayoutDirection(direction)

    def target_file(self) -> Path:
        name = self.filename_edit.text().strip()
        if not name: raise ValueError("יש להזין שם קובץ.")
        if not name.endswith(".md"): name += ".md"
        target = (self.content_dir / self.selected_folder() / name).resolve()
        if self.content_dir.resolve() not in target.parents: raise ValueError("המיקום חייב להיות בתוך public/content.")
        return target

    def save_page(self) -> None:
        try:
            target = self.target_file(); title = self.title_edit.text().strip()
            if not title: raise ValueError("יש להזין כותרת לעמוד.")
            if target.exists() and (not self.current_file or target.resolve() != self.current_file.resolve()):
                raise ValueError("כבר קיים עמוד בשם זה. בחרו שם או מיקום אחרים כדי לא לדרוס תוכן.")
            raw_body = self.body.toPlainText().strip()
            body = re.sub(r"^#\s+.+$", f"# {title}", raw_body, count=1, flags=re.MULTILINE) if re.search(r"^#\s+.+$", raw_body, flags=re.MULTILINE) else f"# {title}\n\n{raw_body}"
            old_relative = self.current_file.relative_to(self.content_dir).as_posix() if self.current_file else None
            target.parent.mkdir(parents=True, exist_ok=True); target.write_text(body + "\n", encoding="utf-8")
            if self.current_file and self.current_file.resolve() != target and self.current_file.exists(): self.current_file.unlink()
            published_paths = [path for path in self.index_paths() if path != old_relative]
            target_relative = target.relative_to(self.content_dir).as_posix()
            if self.published_check.isChecked():
                published_paths = [path for path in published_paths if path != target_relative]
                published_paths.insert(min(max(self.order_edit.value() - 1, 0), len(published_paths)), target_relative)
            self.current_file = target; self.rebuild_index(published_paths); self.refresh_tree(); self.mark_clean(); self.statusBar().showMessage(f"נשמר: content/{target_relative}" + (" — פורסם באתר" if self.published_check.isChecked() else " — לא פורסם"))
        except (OSError, ValueError) as error: QMessageBox.critical(self, "לא ניתן לשמור", str(error))

    def rebuild_index(self, paths: list[str] | None = None) -> None:
        self.repository.build_index(paths)
        return
        files = {file.relative_to(self.content_dir).as_posix(): file for file in self.content_dir.rglob("*.md")}
        ordered_paths = [path for path in (paths or self.index_paths()) if path in files]
        ordered_paths.extend(path for path in sorted(files, key=str.casefold) if path not in ordered_paths)
        pages = []
        for order, relative in enumerate(ordered_paths, 1):
            file = files[relative]; parts = relative.removesuffix(".md").split("/")
            pages.append({"title": self.title_from_markdown(file.read_text(encoding="utf-8"), file.stem), "slug": "/".join(parts), "folder": " / ".join(parts[:-1]) or "כללי", "path": relative, "file": f"content/{relative}", "order": order})
        self.write_index(pages)

    def write_index(self, pages: list[dict]) -> None:
        temporary = self.index_path.with_suffix(".tmp"); temporary.write_text(json.dumps(pages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); temporary.replace(self.index_path)

    def read_site_texts(self) -> dict[str, str]:
        try:
            saved = json.loads(self.site_text_path.read_text(encoding="utf-8"))
            return {key: str(saved.get(key, default)) for key, default in SITE_TEXT_DEFAULTS.items()}
        except (OSError, ValueError, json.JSONDecodeError):
            return SITE_TEXT_DEFAULTS.copy()

    def write_site_texts(self, texts: dict[str, str]) -> None:
        temporary = self.site_text_path.with_suffix(".tmp"); temporary.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); temporary.replace(self.site_text_path)

    def read_homepage(self) -> dict:
        """Read optional homepage settings; old projects intentionally default to off."""
        defaults = {"enabled": False, "title": "", "description": "", "startPage": "", "showCategories": True, "showPageCounts": True, "showFeatured": False, "featuredPages": []}
        try:
            saved = json.loads(self.homepage_path.read_text(encoding="utf-8"))
            if not isinstance(saved, dict):
                return defaults
            result = defaults | {key: saved.get(key, value) for key, value in defaults.items()}
            result["enabled"] = bool(result["enabled"])
            result["showCategories"] = bool(result["showCategories"])
            result["showPageCounts"] = bool(result["showPageCounts"])
            result["showFeatured"] = bool(result["showFeatured"])
            result["featuredPages"] = [str(path) for path in result["featuredPages"] if isinstance(path, str)] if isinstance(result["featuredPages"], list) else []
            return result
        except (OSError, ValueError, json.JSONDecodeError):
            return defaults

    def write_homepage(self, homepage: dict) -> None:
        temporary = self.homepage_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(homepage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.homepage_path)

    def edit_homepage(self) -> None:
        dialog = QDialog(self); dialog.setWindowTitle("עמוד הבית"); dialog.resize(660, 620)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("הגדירו מסך פתיחה אופציונלי. ההגדרות נשמרות ב־homepage.json ואינן עמוד Markdown."))
        form = QFormLayout(); layout.addLayout(form)
        settings = self.read_homepage()
        enabled = QCheckBox("הפעל עמוד בית"); enabled.setChecked(settings["enabled"]); form.addRow(enabled)
        title = QLineEdit(settings["title"]); title.setLayoutDirection(Qt.RightToLeft); form.addRow("כותרת ראשית", title)
        description = QPlainTextEdit(settings["description"]); description.setFixedHeight(80); description.setLayoutDirection(Qt.RightToLeft); form.addRow("תיאור קצר", description)
        page_options = self.repository.read_index()
        start_page = QComboBox(); start_page.addItem("ללא עמוד התחל כאן", "")
        for page in page_options:
            start_page.addItem(f"{page.get('title', page['path'])} — {page['path']}", page["path"])
        start_page.setCurrentIndex(max(0, start_page.findData(settings["startPage"]))); form.addRow("עמוד התחל כאן", start_page)
        show_categories = QCheckBox("הצג קטגוריות ראשיות"); show_categories.setChecked(settings["showCategories"]); form.addRow(show_categories)
        show_counts = QCheckBox("הצג מספר עמודים בכל קטגוריה"); show_counts.setChecked(settings["showPageCounts"]); form.addRow(show_counts)
        show_featured = QCheckBox("הצג עמודים מומלצים"); show_featured.setChecked(settings["showFeatured"]); form.addRow(show_featured)
        featured = QListWidget(); featured.setSelectionMode(QAbstractItemView.MultiSelection); featured.setMinimumHeight(150)
        for page in page_options:
            choice = QListWidgetItem(f"{page.get('title', page['path'])} — {page['path']}")
            choice.setData(Qt.UserRole, page["path"])
            choice.setSelected(page["path"] in settings["featuredPages"])
            featured.addItem(choice)
        form.addRow("בחירת עמודים מומלצים", featured)
        dependent = [title, description, start_page, show_categories, show_counts, show_featured, featured]
        def update_enabled(checked: bool) -> None:
            for widget in dependent: widget.setEnabled(checked)
            show_counts.setEnabled(checked and show_categories.isChecked())
            featured.setEnabled(checked and show_featured.isChecked())
        enabled.toggled.connect(update_enabled); show_categories.toggled.connect(lambda _checked: update_enabled(enabled.isChecked())); show_featured.toggled.connect(lambda _checked: update_enabled(enabled.isChecked())); update_enabled(enabled.isChecked())
        actions = QHBoxLayout(); actions.addStretch(); cancel = QPushButton("ביטול"); save = QPushButton("שמור הגדרות"); save.setObjectName("save"); actions.addWidget(cancel); actions.addWidget(save); layout.addLayout(actions)
        cancel.clicked.connect(dialog.reject)
        def save_homepage() -> None:
            self.write_homepage({"enabled": enabled.isChecked(), "title": title.text().strip(), "description": description.toPlainText().strip(), "startPage": str(start_page.currentData() or ""), "showCategories": show_categories.isChecked(), "showPageCounts": show_counts.isChecked(), "showFeatured": show_featured.isChecked(), "featuredPages": [featured.item(index).data(Qt.UserRole) for index in range(featured.count()) if featured.item(index).isSelected()]})
            self.statusBar().showMessage("הגדרות עמוד הבית נשמרו."); dialog.accept()
        save.clicked.connect(save_homepage); dialog.exec()

    def edit_site_texts(self) -> None:
        dialog = QDialog(self); dialog.setWindowTitle("הגדרות האתר"); dialog.resize(720, 760)
        layout = QVBoxLayout(dialog); layout.addWidget(QLabel("שנו טקסטים, כותרות וגדלי פונטים באתר. השינויים נשמרים ב־site-texts.json."))
        form_widget = QWidget(); form = QFormLayout(form_widget); form.setLabelAlignment(Qt.AlignRight)
        texts, fields = self.read_site_texts(), {}
        labels = {
            "site_title": "כותרת הדפדפן", "brand_prefix": "שם מותג — חלק ראשון", "brand_accent": "שם מותג — חלק מודגש", "brand_home_label": "תיאור קישור הבית", "tagline": "שורת תיאור עליונה", "menu_label": "כפתור תפריט נייד", "theme_light_label": "כפתור מצב בהיר", "theme_dark_label": "כפתור מצב כהה", "learning_path_label": "כותרת סרגל הצד", "navigation_label": "תיאור ניווט נגיש", "loading_content": "הודעת טעינת תכנים", "page_count": "מונה עמודים ({count})", "empty_title": "כותרת ללא תכנים", "empty_description": "הודעה ללא תכנים", "loading_page": "הודעת טעינת עמוד", "load_error_title": "כותרת שגיאת טעינה", "load_error_description": "הודעת שגיאת טעינה ({file})", "missing_index_title": "כותרת אינדקס חסר", "missing_index_description": "הודעת אינדקס חסר",
        }
        for key, label in labels.items():
            field = QLineEdit(texts[key]); field.setLayoutDirection(Qt.RightToLeft); field.setAlignment(Qt.AlignRight); fields[key] = field; form.addRow(label, field)
        default_navigation = QComboBox(); default_navigation.addItem("כל השכבות פתוחות", "true"); default_navigation.addItem("כל השכבות סגורות", "false"); default_navigation.setCurrentIndex(0 if texts["navigation_default_expanded"] != "false" else 1); fields["navigation_default_expanded"] = default_navigation; form.addRow("ברירת מחדל לתפריט הצדדי", default_navigation)
        form.addRow(QLabel("גדלי פונטים באתר (פיקסלים)"), QLabel(""))
        font_labels = {"font_size_body": "טקסט תוכן", "font_size_h1": "כותרת ראשית", "font_size_h2": "כותרת משנה", "font_size_h3": "כותרת שלישית", "font_size_sidebar": "קישורים בתפריט הצדדי", "font_size_sidebar_heading": "כותרות בתפריט הצדדי", "sidebar_spacing": "רווח אנכי בתפריט הצדדי"}
        for key, label in font_labels.items():
            field = QSpinBox(); field.setRange(0 if key == "sidebar_spacing" else 10, 24 if key == "sidebar_spacing" else 96); field.setSuffix(" px")
            try: field.setValue(int(texts[key]))
            except ValueError: field.setValue(int(SITE_TEXT_DEFAULTS[key]))
            fields[key] = field; form.addRow(label, field)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(form_widget); layout.addWidget(scroll, 1)
        actions = QHBoxLayout(); actions.addStretch(); cancel = QPushButton("ביטול"); save = QPushButton("שמור טקסטים"); save.setObjectName("save"); actions.addWidget(cancel); actions.addWidget(save); layout.addLayout(actions)
        cancel.clicked.connect(dialog.reject)
        def save_texts() -> None:
            self.write_site_texts({key: str(field.value()) if isinstance(field, QSpinBox) else str(field.currentData()) if isinstance(field, QComboBox) else field.text() for key, field in fields.items()}); self.statusBar().showMessage("הגדרות האתר נשמרו."); dialog.accept()
        save.clicked.connect(save_texts); dialog.exec()

    def delete_page(self) -> None:
        if not self.current_file or not self.current_file.exists(): QMessageBox.information(self, "מחיקת עמוד", "בחרו עמוד למחיקה תחילה."); return
        if QMessageBox.question(self, "מחיקת עמוד", f"למחוק את {self.current_file.name}?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        trash = self.repository.trash / "pages"; trash.mkdir(parents=True, exist_ok=True)
        target = trash / self.current_file.name; counter = 2
        while target.exists(): target = trash / f"{self.current_file.stem}-{counter}{self.current_file.suffix}"; counter += 1
        self.current_file.replace(target); self.current_file = None; self.refresh_tree(); self.new_page()
        self.statusBar().showMessage(f"העמוד הועבר לסל המיחזור המקומי: .trash/pages/{target.name}")

    def new_folder_dialog(self) -> None:
        dialog = QDialog(self); dialog.setWindowTitle("תיקייה חדשה"); layout = QFormLayout(dialog); parent = QComboBox(); parent.addItems(self.folder_options()); parent.setCurrentText(self.selected_folder() or ROOT_OPTION); name = QLineEdit(); name.setPlaceholderText("שם התיקייה החדשה")
        layout.addRow("תיקיית אב", parent); layout.addRow("שם התיקייה", name); create = QPushButton("צור תיקייה"); layout.addRow(create)
        def create_folder() -> None:
            value = name.text().strip()
            if not value or value in {".", ".."} or any(char in value for char in "\\/"): QMessageBox.warning(dialog, "שם תיקייה לא תקין", "יש להזין שם תיקייה אחד, ללא / או \\."); return
            base = "" if parent.currentText() == ROOT_OPTION else parent.currentText(); target = (self.content_dir / base / value).resolve()
            if self.content_dir.resolve() not in target.parents: QMessageBox.warning(dialog, "מיקום לא תקין", "התיקייה חייבת להיות בתוך public/content."); return
            target.mkdir(parents=True, exist_ok=True); relative = target.relative_to(self.content_dir).as_posix(); self.refresh_folder_options(relative); dialog.accept(); self.statusBar().showMessage(f"נוצרה תיקייה: content/{relative}")
        create.clicked.connect(create_folder); dialog.exec()

    def selected_tree_folder(self) -> str | None:
        selected = self.tree.selectedItems()
        if not selected:
            return None
        item = selected[0]
        if item.data(0, Qt.UserRole):
            item = item.parent()
        if item is None:
            return None
        return self.tree_folder_path(item)

    def delete_selected_tree_item(self) -> None:
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.information(self, "מחיקת פריט", "בחרו קובץ או תיקייה בעץ תחילה."); return
        item = selected[0]
        relative = item.data(0, Qt.UserRole) or self.tree_folder_path(item)
        if not relative:
            QMessageBox.warning(self, "מחיקת פריט", "לא ניתן למחוק את תיקיית התוכן הראשית."); return
        target = (self.content_dir / relative).resolve()
        if self.content_dir.resolve() not in target.parents or not target.exists():
            QMessageBox.warning(self, "מחיקת פריט", "הפריט שנבחר אינו זמין למחיקה."); return
        is_folder = target.is_dir()
        detail = "התיקייה וכל הקבצים שבתוכה" if is_folder else "הקובץ"
        message = f"להעביר את {detail} {target.name} לסל המיחזור המקומי? אפשר לשחזר ידנית מתוך public/.trash."
        if QMessageBox.question(self, "מחיקת פריט", message, QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            trash = self.repository.trash / ("folders" if is_folder else "pages"); trash.mkdir(parents=True, exist_ok=True)
            destination = trash / target.name; counter = 2
            while destination.exists(): destination = trash / f"{target.stem}-{counter}{target.suffix}"; counter += 1
            target.replace(destination)
            if self.current_file and self.current_file.is_relative_to(target):
                self.current_file = None; self.new_page()
            self.rebuild_index(); self.refresh_tree(); self.statusBar().showMessage(f"נמחק: content/{relative}")
        except OSError as error:
            QMessageBox.critical(self, "לא ניתן למחוק", str(error))

    def rename_folder_dialog(self) -> None:
        options = self.folder_options()[1:]
        if not options:
            QMessageBox.information(self, "שינוי שם תיקייה", "עדיין אין תיקיות לשינוי שם."); return
        dialog = QDialog(self); dialog.setWindowTitle("שינוי שם תיקייה"); layout = QFormLayout(dialog)
        folder = QComboBox(); folder.addItems(options)
        selected = self.selected_tree_folder()
        if selected in options: folder.setCurrentText(selected)
        name = QLineEdit(); name.setPlaceholderText("שם התיקייה החדש")
        def fill_name(value: str) -> None: name.setText(value.rsplit("/", 1)[-1])
        folder.currentTextChanged.connect(fill_name); fill_name(folder.currentText())
        layout.addRow("תיקייה", folder); layout.addRow("שם חדש", name)
        rename = QPushButton("שינוי שם"); layout.addRow(rename)

        def rename_folder() -> None:
            source_relative, new_name = folder.currentText(), name.text().strip()
            if not new_name or new_name in {".", ".."} or any(char in new_name for char in "\\/"):
                QMessageBox.warning(dialog, "שם תיקייה לא תקין", "יש להזין שם תיקייה אחד, ללא / או \\. "); return
            source = self.content_dir / source_relative; target = source.parent / new_name
            if target == source:
                dialog.accept(); return
            if target.exists():
                QMessageBox.warning(dialog, "שם כבר קיים", "כבר קיימת תיקייה בשם זה באותו מיקום."); return
            old_paths = self.index_paths()
            old_prefix = source_relative + "/"; new_relative = (source.parent.relative_to(self.content_dir) / new_name).as_posix(); new_prefix = new_relative + "/"
            try:
                source.rename(target)
                if self.current_file and self.current_file.is_relative_to(source):
                    self.current_file = target / self.current_file.relative_to(source)
                self.rebuild_index([new_prefix + path.removeprefix(old_prefix) if path.startswith(old_prefix) else path for path in old_paths])
                self.refresh_tree(); self.refresh_folder_options(new_relative); self.statusBar().showMessage(f"שם התיקייה שונה ל־content/{new_relative}"); dialog.accept()
            except OSError as error:
                QMessageBox.critical(dialog, "לא ניתן לשנות שם", str(error))

        rename.clicked.connect(rename_folder); dialog.exec()

    def wrap(self, start: str, end: str) -> None:
        cursor = self.body.textCursor(); cursor.insertText(f"{start}{cursor.selectedText() or 'טקסט'}{end}")
    def prefix(self, marker: str) -> None:
        cursor = self.body.textCursor(); cursor.movePosition(QTextCursor.StartOfLine); cursor.insertText(marker)
    def apply_heading(self, index: int) -> None:
        if index == 0:
            return
        prefix = self.heading_combo.itemData(index)
        cursor = self.body.textCursor(); cursor.select(QTextCursor.BlockUnderCursor)
        text = re.sub(r"^#{1,3}\s+", "", cursor.selectedText())
        cursor.insertText(f"{prefix}{text}")
        self.heading_combo.blockSignals(True); self.heading_combo.setCurrentIndex(0); self.heading_combo.blockSignals(False)
    def insert_link(self) -> None:
        cursor = self.body.textCursor(); selected = cursor.selectedText() or "קישור"
        label, accepted = QInputDialog.getText(self, "הוספת קישור", "טקסט הקישור:", text=selected)
        if not accepted or not label.strip(): return
        url, accepted = QInputDialog.getText(self, "הוספת קישור", "כתובת הקישור (URL):", text="https://")
        if accepted and url.strip(): cursor.insertText(f"[{label.strip()}]({url.strip()})")
    def image_files(self) -> list[Path]:
        extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        return sorted((file for file in self.images_dir.rglob("*") if file.is_file() and file.suffix.lower() in extensions), key=lambda file: file.as_posix().casefold())

    def change_favicon(self) -> None:
        source_name, _ = QFileDialog.getOpenFileName(self, "בחירת סמל אתר", "", "סמל אתר (*.svg *.png *.ico);;כל הקבצים (*)")
        if not source_name:
            return
        source = Path(source_name)
        suffix = source.suffix.lower()
        mime_types = {".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}
        if suffix not in mime_types:
            QMessageBox.warning(self, "סמל אתר", "בחרו קובץ SVG, PNG או ICO.")
            return

        assets_dir = self.project / "public" / "assets"
        target = assets_dir / f"favicon{suffix}"
        index_file = self.project / "public" / "index.html"
        manifest_file = self.project / "public" / "manifest.webmanifest"
        try:
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            icon_link = f'<link rel="icon" href="assets/{target.name}" type="{mime_types[suffix]}" />'
            index_html = index_file.read_text(encoding="utf-8")
            updated_html, replacements = re.subn(r'<link rel="icon" href="assets/favicon\.(?:svg|png|ico)" type="[^"]+"\s*/?>', icon_link, index_html, count=1)
            if not replacements:
                updated_html = updated_html.replace('<link rel="manifest" href="manifest.webmanifest" />', f'<link rel="manifest" href="manifest.webmanifest" />\n    {icon_link}')
            index_file.write_text(updated_html, encoding="utf-8")

            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest["icons"] = [{"src": f"assets/{target.name}", "sizes": "any", "type": mime_types[suffix]}]
            manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            for old_suffix in mime_types:
                old_icon = assets_dir / f"favicon{old_suffix}"
                if old_icon != target and old_icon.exists():
                    old_icon.unlink()
        except (OSError, ValueError, json.JSONDecodeError) as error:
            QMessageBox.critical(self, "סמל אתר", f"לא ניתן לעדכן את סמל האתר:\n{error}")
            return
        self.statusBar().showMessage(f"סמל האתר עודכן: assets/{target.name}")
    def insert_image_reference(self, image: Path) -> bool:
        relative = image.relative_to(self.images_dir).as_posix()
        alt_text, accepted = QInputDialog.getText(self, "תיאור תמונה", "תיאור חלופי לתמונה:", text=image.stem)
        if not accepted:
            return False
        self.body.textCursor().insertText(f"![{alt_text.strip() or image.stem}](/assets/images/{quote(relative)})")
        self.statusBar().showMessage(f"התמונה נוספה לעמוד: assets/images/{relative}")
        return True
    def add_image_file(self) -> Path | None:
        source_name, _ = QFileDialog.getOpenFileName(self, "בחירת תמונה", "", "תמונות (*.png *.jpg *.jpeg *.gif *.webp *.svg);;כל הקבצים (*)")
        if not source_name:
            return None
        source = Path(source_name)
        destination = self.images_dir / source.name
        counter = 2
        while destination.exists():
            destination = self.images_dir / f"{source.stem}-{counter}{source.suffix}"; counter += 1
        try:
            shutil.copy2(source, destination)
            self.statusBar().showMessage(f"התמונה נוספה: assets/images/{destination.name}")
            return destination
        except OSError as error:
            QMessageBox.critical(self, "לא ניתן להוסיף תמונה", str(error))
            return None
    def image_library_dialog(self) -> None:
        dialog = QDialog(self); dialog.setWindowTitle("ספריית תמונות"); dialog.resize(620, 460)
        layout = QVBoxLayout(dialog); layout.addWidget(QLabel("בחרו תמונה קיימת, או הוסיפו תמונה חדשה לתיקיית הנכסים."))
        images = QListWidget(); layout.addWidget(images, 1)
        def refresh_images() -> None:
            images.clear()
            for image in self.image_files(): images.addItem(image.relative_to(self.images_dir).as_posix())
        refresh_images()
        actions = QHBoxLayout(); add = QPushButton("＋ הוספת תמונה חדשה"); delete = QPushButton("מחק תמונה"); delete.setObjectName("danger"); use = QPushButton("השתמשו בתמונה הנבחרת"); use.setObjectName("save"); cancel = QPushButton("ביטול")
        actions.addWidget(add); actions.addWidget(delete); actions.addStretch(); actions.addWidget(cancel); actions.addWidget(use); layout.addLayout(actions)
        def add_image() -> None:
            image = self.add_image_file()
            if image:
                refresh_images()
                if self.insert_image_reference(image): dialog.accept()
        def use_image() -> None:
            item = images.currentItem()
            if not item:
                QMessageBox.information(dialog, "בחירת תמונה", "בחרו תמונה מהרשימה תחילה."); return
            if self.insert_image_reference(self.images_dir / item.text()): dialog.accept()
        def delete_image() -> None:
            item = images.currentItem()
            if not item:
                QMessageBox.information(dialog, "מחיקת תמונה", "בחרו תמונה מהרשימה תחילה."); return
            image = (self.images_dir / item.text()).resolve()
            if self.images_dir.resolve() not in image.parents or not image.is_file():
                QMessageBox.warning(dialog, "מחיקת תמונה", "התמונה שנבחרה אינה זמינה למחיקה."); return
            references = self.repository.references_for_image(image)
            suffix = "\n\nהתמונה נמצאת בשימוש ב:\n" + "\n".join(references) if references else "\n\nלא נמצאו הפניות לתמונה זו."
            message = f"למחוק את התמונה {image.name}?" + suffix
            if QMessageBox.question(dialog, "מחיקת תמונה", message, QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
            try:
                image.unlink(); refresh_images(); self.statusBar().showMessage(f"נמחקה תמונה: assets/images/{item.text()}")
            except OSError as error:
                QMessageBox.critical(dialog, "לא ניתן למחוק תמונה", str(error))
        add.clicked.connect(add_image); delete.clicked.connect(delete_image); use.clicked.connect(use_image); cancel.clicked.connect(dialog.reject); dialog.exec()
    def insert_horizontal_rule(self) -> None:
        cursor = self.body.textCursor(); cursor.insertText("\n---\n")
    def wrap_website_direction(self, direction: str) -> None:
        cursor = self.body.textCursor()
        if not cursor.hasSelection(): cursor.select(QTextCursor.BlockUnderCursor)
        selected = cursor.selectedText().replace("\u2029", "\n").strip()
        cursor.insertText(f":::{direction}\n{selected or 'טקסט'}\n:::")
    def mermaid_block(self) -> None:
        cursor = self.body.textCursor()
        cursor.insertText("```mermaid\nflowchart TD\n    A[התחלה] --> B[שלב הבא]\n```")
    def code_block(self) -> None:
        cursor = self.body.textCursor(); cursor.insertText(f"```\n{cursor.selectedText() or 'כתבו כאן קוד'}\n```")

    def set_local_site_button_state(self, running: bool) -> None:
        label = "■ עצור אתר מקומי" if running else "▶ פתח אתר מקומי"
        self.local_site_button.setText(label)

    def toggle_local_site(self) -> None:
        if self._local_server and self._local_server.poll() is None:
            self.stop_local_site()
        else:
            self.start_local_site()

    def start_local_site(self) -> None:
        """Serve the actual static site locally and open it in the default browser."""
        if self._local_server and self._local_server.poll() is None:
            return

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        command = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(self.project / "public")]
        process_options = {"cwd": str(self.project), "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform == "win32":
            process_options["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            self._local_server = subprocess.Popen(command, **process_options)
        except OSError as error:
            self.set_local_site_button_state(False)
            QMessageBox.critical(self, "אתר מקומי", f"לא ניתן להפעיל את השרת המקומי:\n{error}")
            return

        self._local_server_port = port
        self.set_local_site_button_state(True)
        self.statusBar().showMessage(f"האתר המקומי הופעל בכתובת http://127.0.0.1:{port}")
        QTimer.singleShot(250, self.open_local_site)

    def open_local_site(self) -> None:
        if not self._local_server or self._local_server.poll() is not None or not self._local_server_port:
            self._local_server = None
            self._local_server_port = None
            self.set_local_site_button_state(False)
            QMessageBox.warning(self, "אתר מקומי", "השרת המקומי לא הופעל. נסו שוב.")
            return
        QDesktopServices.openUrl(QUrl(f"http://127.0.0.1:{self._local_server_port}/"))

    def stop_local_site(self) -> None:
        if not self._local_server or self._local_server.poll() is not None:
            return
        self._local_server.terminate()
        try:
            self._local_server.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._local_server.kill()
        self._local_server = None
        self._local_server_port = None
        self.set_local_site_button_state(False)
        self.statusBar().showMessage("האתר המקומי נעצר")

    def preview(self) -> None:
        previous_dialog = getattr(self, "_preview_dialog", None)
        if previous_dialog and previous_dialog.isVisible():
            previous_dialog.close()

        dialog = QDialog(self, Qt.WindowType.Window)
        dialog.setWindowTitle("תצוגה מקדימה — רינדור האתר")
        dialog.resize(1000, 760)
        layout = QVBoxLayout(dialog); view = QWebEngineView(); layout.addWidget(view)
        preview_source = self.body.toPlainText().replace("](/assets/", "](assets/")
        source = json.dumps(preview_source).replace("<", "\\u003c")
        document = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><link rel="stylesheet" href="assets/styles.css"><script src="assets/vendor/markdown-it.min.js"></script><script src="assets/vendor/purify.min.js"></script><script src="assets/vendor/highlight.min.js"></script><script src="assets/vendor/mermaid.min.js"></script><style>body{{padding:20px}}.article{{max-width:100%;margin:auto}}#fallback{{white-space:pre-wrap;direction:rtl;color:#edf5fa}}</style></head><body><main id="content"><article class="article"><pre id="fallback"></pre></article></main><script>document.querySelector('#fallback').textContent={source};</script><script>
const MarkdownIt=window.markdownit,DOMPurify=window.DOMPurify,hljs=window.hljs,mermaid=window.mermaid;
const source={source}; const safe=url=>/^(https?:|mailto:|tel:|\\/|\\.\\/|\\.\\.\\/|#)/i.test(url)?url:'#';
const md=new MarkdownIt({{html:false,linkify:true,highlight(code,lang){{const known=lang&&hljs.getLanguage(lang);return `<pre><code class="hljs language-${{lang||'text'}}">${{known?hljs.highlight(code,{{language:lang}}).value:MarkdownIt().utils.escapeHtml(code)}}</code></pre>`;}}}});
md.renderer.rules.link_open=(tokens,index,options,env,self)=>{{const href=safe(tokens[index].attrGet('href')||'');tokens[index].attrSet('href',href);if(/^https?:/i.test(href)){{tokens[index].attrSet('target','_blank');tokens[index].attrSet('rel','noopener noreferrer');}}return self.renderToken(tokens,index,options);}};
md.renderer.rules.image=(tokens,index,options,env,self)=>{{tokens[index].attrSet('src',safe(tokens[index].attrGet('src')||''));return self.renderToken(tokens,index,options);}};
const prepared=source.replace(/^:::(note|tip|warning|danger|exercise)\\s*$/gim,'<div class="callout $1">').replace(/^:::(rtl|ltr)\\s*$/gim,'<div class="markdown-direction" dir="$1">').replace(/^:::\\s*$/gm,'</div>');
document.querySelector('#content').innerHTML=`<article class="article">${{DOMPurify.sanitize(md.render(prepared),{{ADD_ATTR:['target','rel','dir'],ADD_TAGS:['div']}})}}</article>`;
const diagrams=document.querySelectorAll('code.language-mermaid');if(diagrams.length){{mermaid.initialize({{startOnLoad:false,securityLevel:'strict',theme:'dark'}});for(const code of diagrams){{const host=document.createElement('div');host.className='mermaid';host.textContent=code.textContent;code.closest('pre').replaceWith(host);mermaid.run({{nodes:[host]}}).catch(()=>{{host.textContent='שגיאה בתרשים Mermaid';}});}}}}
</script></body></html>'''
        preview_file = self.project / "public" / ".editor-preview.html"
        try:
            preview_file.write_text(document, encoding="utf-8")
        except OSError as error:
            QMessageBox.critical(self, "תצוגה מקדימה", f"לא ניתן ליצור את קובץ התצוגה המקדימה:\n{error}")
            return

        # טעינת קובץ HTML מקומי (ולא setHtml) מאפשרת ל-WebEngine לטעון את אותן ספריות
        # מקומיות שהאתר טוען, מאותו מקור file://.
        view.setUrl(QUrl.fromLocalFile(str(preview_file.resolve())))
        self._preview_dialog = dialog
        dialog.finished.connect(lambda: setattr(self, "_preview_dialog", None))
        dialog.show()

    def restore_recovery(self) -> None:
        path = self.project / ".editor-recovery.json"
        if not path.exists(): return
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError): return
        if QMessageBox.question(self, "שחזור טיוטה", "נמצאה טיוטה שלא נשמרה. לשחזר אותה?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        self._loading_document = True; self.current_file = self.content_dir / data["path"] if data.get("path") else None
        self.title_edit.setText(data.get("title", "")); self.filename_edit.setText(data.get("filename", "שיעור-חדש.md")); self.refresh_folder_options(data.get("folder") or ROOT_OPTION); self.order_edit.setValue(int(data.get("order", 1))); self.body.setPlainText(data.get("body", "")); self._loading_document = False; self._clean_snapshot = ""; self.update_dirty_state(); self.statusBar().showMessage("הטיוטה שוחזרה — שמרו אותה כשתהיו מוכנים.")

    def validate_site(self) -> None:
        report = self.repository.validate(); dialog = QDialog(self); dialog.setWindowTitle("בדיקת האתר"); dialog.resize(760, 560); layout = QVBoxLayout(dialog)
        labels = {"errors": "שגיאות", "warnings": "אזהרות", "info": "מידע"}
        for key in ("errors", "warnings", "info"):
            layout.addWidget(QLabel(f"{labels[key]} ({len(report[key])})")); box = QPlainTextEdit("\n".join(report[key]) or "אין"); box.setReadOnly(True); box.setMaximumHeight(150); layout.addWidget(box)
        close = QPushButton("סגור"); close.clicked.connect(dialog.accept); layout.addWidget(close); dialog.exec()

    def closeEvent(self, event) -> None:
        if self.confirm_discard("סגירת התוכנה"):
            self.stop_local_site()
            event.accept()
        else: event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv); window = CyberLearnEditor(); window.showMaximized(); sys.exit(app.exec())
