import json
import os
import re

from PySide6.QtCore import Qt, QStringListModel, QTimer, QRegularExpression
from PySide6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, \
    QDesktopServices, QShortcut, QKeySequence, QTextDocument, QTextCursor, \
    QTextCharFormat, QColor
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QListView, QWidget, QVBoxLayout, QLineEdit,
    QHBoxLayout, QMenuBar, QTextBrowser, QPushButton, QLabel, QTextEdit
)

from bbcode_parser import build_bbcode_parser
from mensaje_preview import MensajePreview
from utils import format_date, load_settings, save_setting, \
    accent_insensitive_regex, strip_accents


class Keaton(QMainWindow):

    def __init__(self, json_file, app):
        super().__init__()
        self.threads_dir = "threads"

        self.themes_dir = "themes"
        self.app = app
        settings = load_settings()
        self.change_theme(f"{settings.get('theme')}.qss")
        # self.setWindowTitle("El Templo de Piedra")
        self.resize(1200, 700)
        self.data = []

        self.filtered = []
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_messages)
        self.search_timer_post = QTimer(self)
        self.search_timer_post.setSingleShot(True)
        self.search_timer_post.timeout.connect(self.highlight_all)
        self.message_list = QListView()
        self.message_model = QStringListModel()
        self.search_box = QLineEdit()

        self.matches = []
        self.post_search_bar = QWidget()
        self.post_search_input = QLineEdit()
        self.post_search_input.setPlaceholderText("Buscar en este post...")
        self.label_matches = QLabel()

        self.init_ui()
        self.post_search_bar.show()
        self.post_search_bar.hide()
        self.load_thread(settings.get("json_file"))

    def init_ui(self):
        main_splitter = QSplitter(Qt.Horizontal)

        # --- Menú de temas ---
        menubar = QMenuBar(self)
        theme_menu = menubar.addMenu("Temas")

        theme_icons = {
            "zelda": "icons/triforce.svg",
            "parchment": "icons/parchment.svg",
            "light": "icons/sun.svg",
            "dark": "icons/moon.svg",
            "default": "icons/default.svg"
        }

        # Lista de temas disponibles en la carpeta "themes"
        if os.path.exists(self.themes_dir):
            for file in os.listdir(self.themes_dir):
                if file.endswith(".qss"):
                    theme_name = file.replace(".qss", "")
                    action = QAction(theme_name, self)
                    icon_path = theme_icons.get(theme_name.lower(), theme_icons["default"])
                    if os.path.exists(icon_path):
                        action.setIcon(QIcon(icon_path))
                    action.triggered.connect(lambda checked, f=file: self.change_theme(f))
                    theme_menu.addAction(action)

        self.setMenuBar(menubar)
        thread_menu = menubar.addMenu("Hilos")

        if os.path.exists(self.threads_dir):
            for file in os.listdir(self.threads_dir):
                if file.endswith(".json"):
                    action = QAction(file.rstrip(".json"), self)
                    action.triggered.connect(
                        lambda checked, f=file: self.load_thread(f))
                    thread_menu.addAction(action)

        # Lista de mensajes
        self.message_list.setModel(self.message_model)
        main_splitter.addWidget(self.message_list)

        # Vista de contenido
        self.message_view = QTextBrowser()
        self.message_view.setReadOnly(True)
        self.message_list.setWordWrap(True)
        self.message_view.setOpenExternalLinks(True)
        self.message_view.setOpenLinks(False)
        self.message_view.anchorClicked.connect(
            lambda url: QDesktopServices.openUrl(url))

        self.create_search_bar()

        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)
        layout.setSpacing(0)
        layout.addWidget(self.message_view)
        layout.addWidget(self.post_search_bar)
        self.post_search_bar.setVisible(False)

        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([350, 850])

        # Layout principal
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Barra de búsqueda
        search_layout = QHBoxLayout()
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setPlaceholderText("Buscar en los mensajes...")
        self.search_box.textEdited.connect(self.search_with_delay)
        self.search_box.returnPressed.connect(self.search_messages)
        # self.search_box.signal_cleared.connect(self.search_messages)
        search_layout.addWidget(self.search_box)

        layout.addLayout(search_layout)
        layout.addWidget(main_splitter)
        self.setCentralWidget(central_widget)

        # Conexiones
        self.message_list.clicked.connect(self.show_message)

        # Cargar mensajes al inicio
        self.load_messages()

    def load_messages(self, query=None):
        model = QStandardItemModel()
        self.filtered = []
        for msg in self.data:
            text = msg["message_norm"]
            if query:
                query_norm = strip_accents(query.lower())
                username = (msg["username_norm"])
                if query_norm not in f"{text}{username}":
                    continue
            preview = re.sub(r"\[.*?]", "", text)  # quita tags BBCode
            preview = preview.strip().replace("\n", " ")[:80] + "..."
            item = QStandardItem()
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setData({
                "username": msg["username"],
                "date": format_date(msg["post_date"]),
                "preview": preview,
                "message": msg["message"]
            }, Qt.UserRole)
            model.appendRow(item)
            self.filtered.append(msg)
        self.message_list.setModel(model)
        self.message_list.setItemDelegate(MensajePreview())

    def show_message(self, index):
        msg = self.filtered[index.row()]
        parser = build_bbcode_parser()
        html = parser.format(msg["message"])
        # for ms in self.filtered:
        #     print(ms['post_id'])
        # self.message_view.setHtml(parser.format("[img]R:/Users/Jair/Pictures/3t7Bwwm.jpg[/img]"))
        self.message_view.setHtml(html)
        self.highlight_all()

    def search_messages(self):
        query = self.search_box.text().strip()
        self.load_messages(query if query else None)

    def change_theme(self, theme_file):
        """Cambia el tema al vuelo"""
        theme_path = os.path.join(self.themes_dir, theme_file)
        load_theme(self.app, theme_path)
        theme_key = theme_file.replace(".qss", "").lower()
        if theme_file.lower().startswith("zelda"):
            self.setWindowIcon(QIcon("icons/triforce.svg"))
        elif theme_file.lower().startswith("parchment"):
            self.setWindowIcon(QIcon("icons/parchment.svg"))
        elif theme_file.lower().startswith("light"):
            self.setWindowIcon(QIcon("icons/sun.svg"))
        elif theme_file.lower().startswith("dark"):
            self.setWindowIcon(QIcon("icons/moon.svg"))
        else:
            self.setWindowIcon(QIcon("icons/default.svg"))
        save_setting("theme", theme_key)

    def search_with_delay(self):
        if self.search_box.text() == "":
            self.search_messages()
        else:
            self.search_timer.start(800)

    def load_thread(self, filename):
        if filename:
            path = os.path.join(self.threads_dir, filename)
            self.load_messages_from_file(path)
            self.load_messages()
            self.setWindowTitle(f"Keaton - {filename.rstrip('.json')}")
            save_setting("json_file", filename)

    def load_messages_from_file(self, json_file):
        # Cargar datos
        with open(json_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        for msg in self.data:
            msg["message_norm"] = strip_accents(msg["message"].lower())
            msg["username_norm"] = strip_accents(msg["username"].lower())

    def toggle_post_search(self, visible):
        self.post_search_bar.setVisible(visible)
        if visible:
            self.post_search_input.setFocus()
            self.post_search_input.selectAll()

    def find_next(self, backward=False):
        if not hasattr(self, "matches") or not self.matches:
            self.label_matches.setText("")
            return

        if not hasattr(self, "current_match_index"):
            self.current_match_index = -1

        if backward:
            self.current_match_index -= 1
        else:
            self.current_match_index += 1

        # wrap-around
        if self.current_match_index >= len(self.matches):
            self.current_match_index = 0
        if self.current_match_index < 0:
            self.current_match_index = len(self.matches) - 1

        self.label_matches.setText(f"{self.current_match_index+1}/{len(self.matches)}")

        start, length = self.matches[self.current_match_index]
        doc = self.message_view.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor,
                            length)
        self.message_view.setTextCursor(cursor)

    def create_search_bar(self):
        layout = QHBoxLayout(self.post_search_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        next_btn = QPushButton("↓")
        prev_btn = QPushButton("↑")
        close_btn = QPushButton("✖")
        layout.addWidget(self.post_search_input)
        layout.addWidget(self.label_matches)
        layout.addWidget(prev_btn)
        layout.addWidget(next_btn)
        layout.addWidget(close_btn)

        # Conectar botones
        next_btn.clicked.connect(self.find_next)
        prev_btn.clicked.connect(lambda: self.find_next(backward=True))
        close_btn.clicked.connect(
            lambda: self.post_search_bar.setVisible(False))
        self.post_search_input.returnPressed.connect(next_btn.click)

        # Atajo Ctrl+F
        shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut.activated.connect(lambda: self.toggle_post_search(True))

        # Highlight
        self.post_search_input.textChanged.connect(lambda: self.search_timer_post.start(400))

    from PySide6.QtWidgets import QTextEdit

    def highlight_all(self):
        # limpiar resaltados anteriores
        self.message_view.setExtraSelections([])
        self.label_matches.setText("")

        text = self.post_search_input.text()
        self.matches = []

        if not text:
            return

        # formato de resaltado
        extra_format = QTextCharFormat()
        extra_format.setBackground(QColor("#f39c12"))  # naranja brillante
        extra_format.setForeground(QColor("#000000"))  # texto negro

        doc = self.message_view.document()
        pattern = accent_insensitive_regex(text)
        regex = QRegularExpression(pattern,
                                   QRegularExpression.CaseInsensitiveOption)

        selections = []
        it = regex.globalMatch(doc.toPlainText())
        while it.hasNext():
            match = it.next()
            start, length = match.capturedStart(), match.capturedLength()
            self.matches.append((start, length))

            cur = self.message_view.textCursor()
            cur.setPosition(start)
            cur.setPosition(start + length, QTextCursor.KeepAnchor)

            sel = QTextEdit.ExtraSelection()
            sel.cursor = cur
            sel.format = extra_format
            selections.append(sel)

        self.message_view.setExtraSelections(selections)

        # resetear índice actual
        self.current_match_index = -1
        self.find_next()


def load_theme(app_, theme_file):
    qss = ""
    with open(os.path.join("styles", "global.qss"), "r", encoding="utf-8") as f:
        qss = f.read()
    if os.path.exists(theme_file):
        with open(theme_file, "r", encoding="utf-8") as f:
            qss += "\n" + f.read()
    app_.setStyleSheet(qss)

