"""PySide6 desktop Markdown editor."""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QAbstractItemView, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QSpinBox, QStatusBar, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

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
}


class ReorderTreeWidget(QTreeWidget):
    """Tree widget that delegates drag ordering to the editor instead of moving files."""
    def __init__(self, on_drop, parent=None) -> None:
        super().__init__(parent); self.on_drop = on_drop
        self.setDragEnabled(True); self.setAcceptDrops(True); self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def dropEvent(self, event) -> None:
        source, target = self.currentItem(), self.itemAt(event.position().toPoint())
        if source and target and source is not target:
            rectangle = self.visualItemRect(target); y = event.position().y()
            before = y < rectangle.center().y()
            into_folder = target.data(0, Qt.UserRole) is None and rectangle.top() + rectangle.height() * 0.25 <= y <= rectangle.bottom() - rectangle.height() * 0.25
            self.on_drop(source, target, before, into_folder)
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
        self.current_file: Path | None = None
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists(): self.write_index([])
        if not self.site_text_path.exists(): self.write_site_texts(SITE_TEXT_DEFAULTS)
        self.setWindowTitle("עורך תוכן"); self.resize(1380, 820); self.setMinimumSize(1050, 650)
        self.build_ui(); self.refresh_tree()

    def build_ui(self) -> None:
        self.setStyleSheet("""
            QMainWindow,QDialog{background:#081421;color:#edf5fa;font-family:Assistant,Arial;font-size:14px}
            QFrame#header,QFrame#details,QFrame#toolbar{background:#13243a;border-radius:10px}
            QLabel{color:#dbe8f1} QLineEdit,QPlainTextEdit,QComboBox,QTreeWidget,QTextBrowser{background:#07111d;color:#edf5fa;border:1px solid #28516c;border-radius:7px;padding:7px}
            QTreeWidget{background:#0c1a2a;border:0} QTreeWidget::item:selected{background:#15516a} QComboBox QAbstractItemView{background:#13243a;color:white;selection-background-color:#15516a}
            QPushButton{background:#1b4261;color:white;border:0;border-radius:7px;padding:8px 11px} QPushButton:hover{background:#285775}
            QPushButton#save{background:#00a878;color:#06121d;font-weight:bold} QPushButton#save:hover{background:#00c58c} QPushButton#danger{background:#8d3144}
            QStatusBar{background:#102238;color:#aebdca}
        """)
        root = QWidget(); outer = QVBoxLayout(root); outer.setContentsMargins(18, 14, 18, 14); outer.setSpacing(12)
        header = QFrame(); header.setObjectName("header"); header_layout = QHBoxLayout(header)
        heading = QLabel("עורך תוכן"); heading.setStyleSheet("font-size:23px;font-weight:700;color:#00d4ff")
        header_layout.addWidget(heading); header_layout.addStretch(); header_layout.addWidget(QLabel("כל שמירה מעדכנת את אינדקס האתר"))
        button = QPushButton("⚙ טקסטים קבועים באתר"); button.clicked.connect(self.edit_site_texts); header_layout.addWidget(button)
        button = QPushButton("↻ רענון"); button.clicked.connect(self.refresh_tree); header_layout.addWidget(button); outer.addWidget(header)
        splitter = QSplitter(Qt.Horizontal); splitter.setLayoutDirection(Qt.RightToLeft)
        sidebar = QWidget(); side = QVBoxLayout(sidebar); title = QLabel("עמודי האתר"); title.setStyleSheet("font-size:18px;font-weight:700;color:#ffd93d"); side.addWidget(title)
        button = QPushButton("＋ עמוד חדש"); button.clicked.connect(self.new_page); side.addWidget(button)
        button = QPushButton("✎ שינוי שם תיקייה"); button.clicked.connect(self.rename_folder_dialog); side.addWidget(button)
        button = QPushButton("מחק פריט נבחר"); button.setObjectName("danger"); button.clicked.connect(self.delete_selected_tree_item); side.addWidget(button)
        self.tree = ReorderTreeWidget(self.reorder_tree_item); self.tree.setHeaderHidden(True); self.tree.itemSelectionChanged.connect(self.open_selected); side.addWidget(self.tree); splitter.addWidget(sidebar)
        edit = QWidget(); layout = QVBoxLayout(edit); layout.setContentsMargins(10, 0, 0, 0); layout.setSpacing(9)
        details = QFrame(); details.setObjectName("details"); form = QFormLayout(details); form.setLabelAlignment(Qt.AlignRight); form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.title_edit = QLineEdit(); self.filename_edit = QLineEdit(); self.folder_combo = QComboBox(); self.order_edit = QSpinBox(); self.order_edit.setRange(1, 9999)
        for field in (self.title_edit, self.filename_edit):
            field.setAlignment(Qt.AlignRight); field.setLayoutDirection(Qt.RightToLeft)
        self.folder_combo.setLayoutDirection(Qt.RightToLeft)
        folder_row = QWidget(); folders = QHBoxLayout(folder_row); folders.setContentsMargins(0, 0, 0, 0); folders.addWidget(self.folder_combo, 1)
        button = QPushButton("＋ תיקייה"); button.clicked.connect(self.new_folder_dialog); folders.addWidget(button)
        form.addRow("כותרת", self.title_edit); form.addRow("מיקום בתיקיות", folder_row); form.addRow("שם הקובץ", self.filename_edit); form.addRow("סדר תצוגה", self.order_edit); layout.addWidget(details)
        toolbar = QFrame(); toolbar.setObjectName("toolbar"); tools = QHBoxLayout(toolbar); tools.setContentsMargins(8, 6, 8, 6)
        tools.addWidget(QLabel("כיוון התוכן:"))
        self.direction_combo = QComboBox(); self.direction_combo.addItem("RTL — ימין לשמאל", Qt.RightToLeft); self.direction_combo.addItem("LTR — שמאל לימין", Qt.LeftToRight); tools.addWidget(self.direction_combo)
        tools.addWidget(QLabel("סוג טקסט:"))
        self.heading_combo = QComboBox(); self.heading_combo.addItem("בחרו סגנון"); self.heading_combo.addItem("כותרת 1", "# "); self.heading_combo.addItem("כותרת 2", "## "); self.heading_combo.addItem("כותרת 3", "### "); self.heading_combo.addItem("טקסט רגיל", ""); tools.addWidget(self.heading_combo)
        for label, callback in [("B מודגש", lambda: self.wrap("**", "**")), ("I נטוי", lambda: self.wrap("*", "*")), ("• רשימה", lambda: self.prefix("- ")), ("1. רשימה", lambda: self.prefix("1. ")), ("ציטוט", lambda: self.prefix("> ")), ("קישור", self.insert_link), ("תמונה", self.image_library_dialog), ("קו מפריד", self.insert_horizontal_rule), ("באתר RTL", lambda: self.wrap_website_direction("rtl")), ("באתר LTR", lambda: self.wrap_website_direction("ltr")), ("Mermaid", self.mermaid_block), ("קוד", lambda: self.wrap("`", "`")), ("בלוק קוד", self.code_block)]:
            button = QPushButton(label); button.clicked.connect(callback); tools.addWidget(button)
        tools.addStretch(); layout.addWidget(toolbar)
        self.body = QPlainTextEdit(); self.body.setPlaceholderText("כתבו כאן את תוכן השיעור ב-Markdown…"); self.direction_combo.currentIndexChanged.connect(self.set_body_direction); self.heading_combo.currentIndexChanged.connect(self.apply_heading); self.set_body_direction(); layout.addWidget(self.body, 1)
        actions = QHBoxLayout()
        for label, callback, object_name in [("תצוגה מקדימה", self.preview, ""), ("הדבק", self.body.paste, ""), ("העתק", self.body.copy, ""), ("גזור", self.body.cut, ""), ("מחק עמוד", self.delete_page, "danger"), ("שמור ועדכן אתר", self.save_page, "save")]:
            button = QPushButton(label)
            if object_name: button.setObjectName(object_name)
            button.clicked.connect(callback); actions.addWidget(button)
            if label == "גזור": actions.addStretch()
        layout.addLayout(actions); splitter.addWidget(edit); splitter.setSizes([300, 1030]); outer.addWidget(splitter, 1)
        self.setCentralWidget(root); self.setStatusBar(QStatusBar()); self.statusBar().showMessage("בחרו עמוד או צרו עמוד חדש")
        for label, callback, shortcut in [("שמירה", self.save_page, "Ctrl+S"), ("עמוד חדש", self.new_page, "Ctrl+N")]:
            action = QAction(label, self); action.setShortcut(shortcut); action.triggered.connect(callback); self.addAction(action)

    def index_paths(self) -> list[str]:
        try:
            entries = json.loads(self.index_path.read_text(encoding="utf-8"))
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
        self.refresh_folder_options(); self.tree.clear(); folders: dict[str, QTreeWidgetItem | None] = {"": None}
        for file in self.markdown_files():
            relative = file.relative_to(self.content_dir).as_posix(); parts = relative.split("/"); parent_key = ""
            for depth, name in enumerate(parts[:-1], 1):
                key = "/".join(parts[:depth])
                if key not in folders:
                    parent = folders[parent_key]; item = QTreeWidgetItem([name]); item.setData(0, Qt.UserRole, None); (self.tree.invisibleRootItem() if parent is None else parent).addChild(item); folders[key] = item
                parent_key = key
            item = QTreeWidgetItem([self.title_from_markdown(file.read_text(encoding="utf-8"), file.stem)]); item.setData(0, Qt.UserRole, relative); (self.tree.invisibleRootItem() if folders[parent_key] is None else folders[parent_key]).addChild(item)
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
        parts = []
        current = item
        while current:
            parts.append(current.text(0)); current = current.parent()
        return "/".join(reversed(parts))

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
        old_paths = [file.relative_to(self.content_dir).as_posix() for file in self.markdown_files()]
        old_prefix, new_prefix = source_relative + "/", (target_folder + "/" if target_folder else "") + source_path.name + "/"
        source_path.rename(destination)
        if self.current_file and self.current_file.is_relative_to(source_path):
            self.current_file = destination / self.current_file.relative_to(source_path)
        moved_paths = [new_prefix + path.removeprefix(old_prefix) if path.startswith(old_prefix) else ((target_folder + "/" if target_folder else "") + source_path.name if path == source_relative else path) for path in old_paths]
        self.rebuild_index(moved_paths); self.refresh_tree()
        self.statusBar().showMessage(f"הועבר אל: content/{destination.relative_to(self.content_dir).as_posix()}")

    def reorder_tree_item(self, source: QTreeWidgetItem, target: QTreeWidgetItem, before: bool, into_folder: bool = False) -> None:
        dragged = self.tree_item_paths(source); target_paths = self.tree_item_paths(target)
        if not dragged or not target_paths or set(dragged) & set(target_paths):
            return
        target_folder = self.tree_folder_path(target)
        if into_folder and target_folder is not None:
            try:
                self.move_tree_item_into_folder(source, target_folder)
            except (OSError, ValueError) as error:
                self.statusBar().showMessage(str(error))
            return
        all_paths = [file.relative_to(self.content_dir).as_posix() for file in self.markdown_files()]
        remaining = [path for path in all_paths if path not in dragged]
        target_indexes = [remaining.index(path) for path in target_paths if path in remaining]
        if not target_indexes:
            return
        insert_at = min(target_indexes) if before else max(target_indexes) + 1
        self.rebuild_index([*remaining[:insert_at], *dragged, *remaining[insert_at:]])
        self.refresh_tree(); self.statusBar().showMessage("סדר התצוגה עודכן באמצעות גרירה בתפריט.")

    def open_selected(self) -> None:
        selected = self.tree.selectedItems()
        if not selected or not (relative := selected[0].data(0, Qt.UserRole)): return
        file = self.content_dir / relative; text = file.read_text(encoding="utf-8"); path = file.relative_to(self.content_dir); self.current_file = file
        self.title_edit.setText(self.title_from_markdown(text, file.stem)); self.refresh_folder_options(path.parent.as_posix() if path.parent != Path(".") else ROOT_OPTION); self.filename_edit.setText(file.name); self.order_edit.setValue(self.display_position(relative)); self.body.setPlainText(text); self.set_body_direction(); self.statusBar().showMessage(f"עורכים: content/{path.as_posix()}")

    def new_page(self) -> None:
        self.current_file = None; self.title_edit.clear(); self.filename_edit.setText("שיעור-חדש.md"); self.order_edit.setValue(len(self.markdown_files()) + 1); self.refresh_folder_options(ROOT_OPTION); self.body.setPlainText("# כותרת השיעור\n\nכתבו כאן את תוכן השיעור…\n"); self.set_body_direction(); self.title_edit.setFocus(); self.statusBar().showMessage("עמוד חדש — הגדירו כותרת, תיקייה, סדר ושם קובץ ואז שמרו")

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
            body = self.body.toPlainText().strip(); body = re.sub(r"^#\s+.+$", f"# {title}", body, count=1, flags=re.MULTILINE) if re.search(r"^#\s+.+$", body, flags=re.MULTILINE) else f"# {title}\n\n{body}"
            old_relative = self.current_file.relative_to(self.content_dir).as_posix() if self.current_file else None
            target.parent.mkdir(parents=True, exist_ok=True); target.write_text(body + "\n", encoding="utf-8")
            if self.current_file and self.current_file.resolve() != target and self.current_file.exists(): self.current_file.unlink()
            self.current_file = target; self.rebuild_index(self.ordered_paths_with(target.relative_to(self.content_dir).as_posix(), self.order_edit.value(), old_relative)); self.refresh_tree(); self.statusBar().showMessage(f"נשמר והאינדקס עודכן: content/{target.relative_to(self.content_dir).as_posix()}")
        except (OSError, ValueError) as error: QMessageBox.critical(self, "לא ניתן לשמור", str(error))

    def rebuild_index(self, paths: list[str] | None = None) -> None:
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

    def edit_site_texts(self) -> None:
        dialog = QDialog(self); dialog.setWindowTitle("טקסטים קבועים באתר"); dialog.resize(720, 680)
        layout = QVBoxLayout(dialog); layout.addWidget(QLabel("שנו כאן טקסטים של הממשק בלבד — לא תוכן שיעורים או שמות עמודים."))
        form_widget = QWidget(); form = QFormLayout(form_widget); form.setLabelAlignment(Qt.AlignRight)
        texts, fields = self.read_site_texts(), {}
        labels = {
            "site_title": "כותרת הדפדפן", "brand_prefix": "שם מותג — חלק ראשון", "brand_accent": "שם מותג — חלק מודגש", "brand_home_label": "תיאור קישור הבית", "tagline": "שורת תיאור עליונה", "menu_label": "כפתור תפריט נייד", "theme_light_label": "כפתור מצב בהיר", "theme_dark_label": "כפתור מצב כהה", "learning_path_label": "כותרת סרגל הצד", "navigation_label": "תיאור ניווט נגיש", "loading_content": "הודעת טעינת תכנים", "page_count": "מונה עמודים ({count})", "empty_title": "כותרת ללא תכנים", "empty_description": "הודעה ללא תכנים", "loading_page": "הודעת טעינת עמוד", "load_error_title": "כותרת שגיאת טעינה", "load_error_description": "הודעת שגיאת טעינה ({file})", "missing_index_title": "כותרת אינדקס חסר", "missing_index_description": "הודעת אינדקס חסר",
        }
        for key, label in labels.items():
            field = QLineEdit(texts[key]); field.setLayoutDirection(Qt.RightToLeft); field.setAlignment(Qt.AlignRight); fields[key] = field; form.addRow(label, field)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(form_widget); layout.addWidget(scroll, 1)
        actions = QHBoxLayout(); actions.addStretch(); cancel = QPushButton("ביטול"); save = QPushButton("שמור טקסטים"); save.setObjectName("save"); actions.addWidget(cancel); actions.addWidget(save); layout.addLayout(actions)
        cancel.clicked.connect(dialog.reject)
        def save_texts() -> None:
            self.write_site_texts({key: field.text() for key, field in fields.items()}); self.statusBar().showMessage("הטקסטים הקבועים באתר נשמרו."); dialog.accept()
        save.clicked.connect(save_texts); dialog.exec()

    def delete_page(self) -> None:
        if not self.current_file or not self.current_file.exists(): QMessageBox.information(self, "מחיקת עמוד", "בחרו עמוד למחיקה תחילה."); return
        if QMessageBox.question(self, "מחיקת עמוד", f"למחוק את {self.current_file.name}?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        self.current_file.unlink(); self.current_file = None; self.refresh_tree(); self.new_page()

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
        message = f"למחוק את {detail} {target.name}? פעולה זו אינה ניתנת לביטול."
        if QMessageBox.question(self, "מחיקת פריט", message, QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            if is_folder: shutil.rmtree(target)
            else: target.unlink()
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
            old_paths = [file.relative_to(self.content_dir).as_posix() for file in self.markdown_files()]
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
            message = f"למחוק את התמונה {image.name}? קישורים קיימים אליה בעמודים לא יתעדכנו."
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
    def preview(self) -> None:
        dialog = QDialog(self); dialog.setWindowTitle("תצוגה מקדימה"); dialog.resize(760, 650); layout = QVBoxLayout(dialog); view = QTextBrowser(); output = []
        for line in self.body.toPlainText().splitlines():
            safe = html.escape(line)
            if line.startswith("# "): output.append(f"<h1>{html.escape(line[2:])}</h1>")
            elif line.startswith("## "): output.append(f"<h2>{html.escape(line[3:])}</h2>")
            elif line.startswith("> "): output.append(f"<blockquote>💡 {html.escape(line[2:])}</blockquote>")
            elif line.startswith("- "): output.append(f"<div>• {html.escape(line[2:])}</div>")
            else: output.append(f"<p>{safe}</p>")
        view.setHtml("<style>body{background:#07111d;color:#edf5fa;font-family:Assistant,Arial;font-size:17px;direction:rtl}h1{color:#00d4ff}h2{color:#ffd93d}blockquote{color:#9fdcf0;border-right:3px solid #00d4ff;padding-right:12px}</style>" + "".join(output)); layout.addWidget(view); dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv); window = CyberLearnEditor(); window.show(); sys.exit(app.exec())
