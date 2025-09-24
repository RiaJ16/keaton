import json
import os
import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QRegularExpression, QSize
from PySide6.QtGui import (QAction, QIcon, QStandardItemModel, QStandardItem,
                           QDesktopServices, QShortcut, QKeySequence,
                           QTextCursor,
                           QTextCharFormat, QColor)
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QListView, QWidget, QVBoxLayout, QLineEdit,
    QHBoxLayout, QTextBrowser, QPushButton, QLabel, QTextEdit,
    QProgressBar, QMenu, QToolButton, QSizePolicy
)

from .bbcode_parser import build_bbcode_parser
from .mensaje_preview import MensajePreview
from ui import keaton_rc
from .utils import (format_date, load_settings, save_setting,
                    accent_insensitive_regex, strip_accents)


class Keaton(QMainWindow):

    def __init__(self, app):
        super().__init__()
        self.threads_dir = "threads"
        self.setWindowIcon(QIcon(":/main/icons/keaton.png"))

        self.themes_dir = "themes"
        self.app = app
        self.status = self.statusBar()
        self.status.setStyleSheet(
            "QStatusBar::item { border: 0px solid transparent; }")
        self.status_left = QLabel("")
        self.status_left.setContentsMargins(15, 0, 0, 0)
        self.progress_label = QLabel("0.00%")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setTextVisible(False)
        self.status.addWidget(self.status_left)
        self.status.addPermanentWidget(self.progress_bar)
        self.status.addPermanentWidget(self.progress_label)
        settings = load_settings()
        self.boton_games = QToolButton()
        self.boton_temas = QToolButton()
        self.boton_temas.setIconSize(QSize(30, 30))
        self.change_theme(f"{settings.get('theme')}.qss")
        self.change_theme(f"{settings.get('theme')}.qss")
        self.resize(1200, 700)
        self.thread_id = 0
        self.data = []
        self.total_len = 0

        self.filtered = []
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_messages)
        self.search_timer_post = QTimer(self)
        self.search_timer_post.setSingleShot(True)
        self.search_timer_post.timeout.connect(self.highlight_all)
        self.barra_de_herramientas = QWidget()
        self.load_menus()
        self.message_list = QListView()
        self.search_box = QLineEdit()

        self.current_post_id = 0
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

        # Lista de mensajes
        main_splitter.addWidget(self.message_list)

        # Vista de contenido
        self.message_view = QTextBrowser()
        self.message_view.setReadOnly(True)
        self.message_list.setWordWrap(True)
        self.message_view.setOpenExternalLinks(True)
        self.message_view.setOpenLinks(False)
        self.message_view.anchorClicked.connect(
            lambda url: QDesktopServices.openUrl(url))
        # self.message_view.verticalScrollBar().valueChanged.connect(
        #     self.check_scroll_end)

        self.create_search_bar()

        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
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

        self.barra_de_herramientas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.barra_de_herramientas)
        layout.addLayout(search_layout)
        layout.addWidget(main_splitter)
        self.setCentralWidget(central_widget)

        # Conexiones
        self.message_list.clicked.connect(self.show_message)

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
            preview = preview.strip().replace("\n", " ")[:280] + "..."
            item = QStandardItem()
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setData({
                "post_id": msg["post_id"],
                "username": msg["username"],
                "date": format_date(msg["post_date"]),
                "preview": preview,
                "message": msg["message"]
            }, Qt.UserRole)
            model.appendRow(item)
            self.filtered.append(msg)
        self.message_list.setModel(model)
        self.message_list.setItemDelegate(MensajePreview())
        self.select_index_by_post_id(self.current_post_id)
        if len(self.filtered) > 0:
            self.search_box.setStyleSheet("")
        else:
            self.search_box.setStyleSheet("background-color: #eb4d4b;")

    def show_message(self, index):
        self.current_post_id = index.data(Qt.UserRole).get("post_id")
        save_setting(f"current_post_id_{self.thread_id}", self.current_post_id)
        msg = self.filtered[index.row()]
        parser = build_bbcode_parser()
        html = parser.format(msg.get("message"))
        self.message_view.setHtml(html)
        self.highlight_all()
        self.actualizar_barra_de_estado(index)

    def actualizar_barra_de_estado(self, index):
        current_pos = next((i for i, msg in enumerate(self.data) if msg.get("post_id") == self.current_post_id), -1)
        accumulated_len = sum(
            len(self.data[i]["message_norm"]) for i in range(current_pos + 1))
        percentage = (accumulated_len / self.total_len) * 100
        pos = index.row() + 1
        total = len(self.filtered)
        self.status_left.setText(f"{pos} / {total}")
        self.progress_bar.setValue(int(percentage))
        self.progress_label.setText(f"{percentage:.2f}%")

    def select_index_by_post_id(self, post_id, first_load=False):
        index = None
        model = self.message_list.model()
        found = False
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            data = index.data(Qt.UserRole)
            if data and data.get("post_id") == post_id:
                found = True
                break
        if index and found:
            self.message_list.setCurrentIndex(index)
            if first_load:
                self.show_message(index)
            else:
                self.actualizar_barra_de_estado(index)

    def get_first_post_id(self):
        data = None
        model = self.message_list.model()
        if model and model.rowCount() > 0:
            first_index = model.index(0, 0)
            data = first_index.data(Qt.UserRole)
        if data:
            return data.get("post_id")
        else:
            return 0

    def search_messages(self):
        query = self.search_box.text().strip()
        self.load_messages(query if query else None)
        self.post_search_input.setText(self.search_box.text().strip())
        self.post_search_bar.setVisible(True)
        self.highlight_all()

    def load_menus(self):
        games_menu = QMenu(self.boton_games)
        themes_menu = QMenu(self.boton_temas)

        self.boton_games.setText("Seleccionar juego...")
        self.boton_games.setMenu(games_menu)
        self.boton_games.setPopupMode(QToolButton.InstantPopup)
        self.boton_temas.setMenu(themes_menu)
        self.boton_temas.setPopupMode(QToolButton.InstantPopup)
        self.boton_temas.setText("Temas")
        layout = QHBoxLayout()
        layout.addWidget(self.boton_games)
        layout.addStretch()
        layout.addWidget(self.boton_temas)
        layout.setContentsMargins(0, 0, 0, 0)
        self.barra_de_herramientas.setLayout(layout)

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
                    action = QAction(theme_name.capitalize(), self)
                    icon_path = theme_icons.get(theme_name.lower(), theme_icons["default"])
                    if os.path.exists(icon_path):
                        action.setIcon(QIcon(icon_path))
                    action.triggered.connect(lambda checked, f=file: self.change_theme(f))
                    themes_menu.addAction(action)

        actions = []
        if os.path.exists(self.threads_dir):
            for file in os.listdir(self.threads_dir):
                if file.endswith(".json"):
                    id_, name = file.split("#")
                    action = QAction(Path(name).stem, self)
                    action.setData(int(id_))
                    action.triggered.connect(
                        lambda checked, f=file: self.load_thread(f))
                    actions.append(action)
        actions = sorted(actions, key=lambda action_: action_.data())
        games_menu.addActions(actions)

    def change_theme(self, theme_file):
        theme_path = os.path.join(self.themes_dir, theme_file)
        load_theme(self.app, theme_path)
        theme_key = theme_file.replace(".qss", "").lower()

        icons = {
            "zelda": "icons/triforce.svg",
            "parchment": "icons/parchment.svg",
            "light": "icons/sun.svg",
            "dark": "icons/moon.svg",
            "default": "icons/default.svg"
        }
        icono = QIcon(icons.get(theme_key))

        self.boton_temas.setText(f"{theme_key.capitalize()} Theme")
        self.boton_temas.setIcon(icono)
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
            settings = load_settings()
            self.current_post_id = settings.get(
                f"current_post_id_{self.thread_id}")
            self.load_messages()
            if not self.current_post_id:
                self.current_post_id = self.get_first_post_id()
            self.select_index_by_post_id(self.current_post_id, True)
            new_filename = Path(filename.split("#")[-1]).stem
            self.setWindowTitle(f"Keaton - {new_filename}")
            self.boton_games.setText(new_filename)
            save_setting("json_file", filename)

    def load_messages_from_file(self, json_file):
        # Cargar datos
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            pass
        try:
            self.thread_id = self.data[0].get("thread_id")
        except IndexError:
            pass

        read_cache = False
        cache_file = json_file + ".cache"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                if len(cache) == len(self.data) and all(
                        c["post_id"] == d["post_id"] for c, d in
                        zip(cache, self.data)
                ):
                    for msg, cached in zip(self.data, cache):
                        msg["message_norm"] = cached["message_norm"]
                        msg["username_norm"] = cached["username_norm"]
                    read_cache = True
            except (json.decoder.JSONDecodeError, KeyError):
                pass
        if not read_cache:
            cache = []
            for msg in self.data:
                msg["message_norm"] = strip_accents(msg["message"].lower())
                msg["username_norm"] = strip_accents(msg["username"].lower())
                cache.append({
                    "post_id": msg["post_id"],
                    "message_norm": msg["message_norm"],
                    "username_norm": msg["username_norm"]
                })
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
        self.total_len = sum(len(m["message_norm"]) for m in self.data) or 1

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
        layout.setContentsMargins(0, 4, 0, 0)
        next_btn = QPushButton("↓")
        prev_btn = QPushButton("↑")
        close_btn = QPushButton("✖")
        next_btn.setFlat(True)
        prev_btn.setFlat(True)
        close_btn.setFlat(True)
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

    def highlight_all(self):
        # limpiar resaltados anteriores
        self.message_view.setExtraSelections([])
        self.label_matches.setText("")

        text = self.post_search_input.text()
        self.matches = []

        if not text:
            self.post_search_input.setStyleSheet("")
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

        if self.matches:
            self.post_search_input.setStyleSheet("")
        else:
            self.post_search_input.setStyleSheet("background-color: #eb4d4b;")
        self.message_view.setExtraSelections(selections)

        # resetear índice actual
        self.current_match_index = -1
        self.find_next()

    def check_scroll_end(self, value):
        bar = self.message_view.verticalScrollBar()
        if value >= bar.maximum():
            self.go_to_next_post()

    def go_to_next_post(self):
        current_index = self.message_list.currentIndex()
        next_index = self.message_list.model().index(current_index.row() + 1, 0)
        if next_index.isValid():
            self.message_list.setCurrentIndex(next_index)
            self.show_message(next_index)


def load_theme(app_, theme_file):
    qss = ""
    with open(os.path.join("styles", "global.qss"), "r", encoding="utf-8") as f:
        qss = f.read()
    if os.path.exists(theme_file):
        with open(theme_file, "r", encoding="utf-8") as f:
            qss += "\n" + f.read()
    app_.setStyleSheet(qss)

# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⣤⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣤⣾⠿⣻⣿⠟⠁⠀⠀⠀⠀⣠⣾⡆⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⡿⠟⢉⣴⣾⠟⠁⠀⠀⠀⢀⣴⡿⠋⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣾⠟⠉⢀⣴⣿⠟⠁⠀⠀⠀⢀⣴⡿⠋⠀⣸⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⡿⠟⠁⠀⣠⣾⠟⠁⠀⠀⠀⢀⣴⡿⠋⠀⠀⢠⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⡿⠋⠀⠀⢀⣾⡿⠁⠀⠀⠀⢀⣴⡿⠋⠀⠀⠀⢀⣾⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⠟⠁⠀⠀⣰⣿⠏⠀⠀⠀⢀⣴⡿⠋⠀⠀⠀⠀⠀⣼⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⡿⠃⠀⠀⠀⣴⡿⠁⠀⠀⢀⣴⣿⠟⠁⠀⠀⠀⠀⠀⣼⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⠟⠁⠀⠀⠀⣸⡿⠁⠀⠀⣴⣿⠟⠁⠀⠀⠀⠀⠀⠀⣸⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⠏⠀⠀⠀⠀⢠⣿⠃⢀⣴⣾⠟⠁⠀⠀⠀⠀⠀⠀⠀⣼⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⠏⠀⠀⠀⠀⠀⠸⣿⣶⡿⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⣼⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⡿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⣿⣷⡀⠀⠀⠀⣠⣴⣶⣶⠀⠀⠀⣠⣾⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣧⢻⣿⡇⠀⢀⣾⣿⣿⣿⡟⠀⣠⣾⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣮⡙⠃⠀⠈⠻⠿⠟⣋⣴⡿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⣿⣿⠿⣿⣿⣿⣿⣅⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⣿⣦⡘⠀⠀⠀⢠⣾⡿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣶⡶⣶⡄
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣇⡀⣀⢀⣼⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣾⠏⣿⣿⢎⣷
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⡟⣸⡇⢿⣆⢻⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⡶⢟⣫⣵⡶⣶⡿⠿⠃
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⠃⣿⡇⠸⣿⡎⢻⣿⣿⣿⣶⣄⡀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣴⡶⢟⣫⣽⠾⠛⠉⠁⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⡿⣿⣿⠃⠀⣿⡇⠀⢻⣿⡄⠘⠿⣿⣿⣿⣿⣦⣄⠀⢀⣠⣴⡾⢟⣫⣵⠾⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⡿⢋⣼⡿⠃⠀⢸⣿⠃⠀⠀⠻⣿⣆⠀⠈⠻⣿⣷⣝⠻⣿⣿⣯⣴⠾⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⡿⠋⣠⣿⡿⠁⠀⠀⢸⣿⠀⠀⠀⠀⠹⣿⣧⡀⠀⠈⠙⢿⣷⣮⡻⣿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⡿⠁⣰⣿⠟⠀⠀⠀⠀⣿⡟⢿⠀⠀⠀⠀⠈⢿⣷⣄⠀⠀⠀⠙⢿⣿⣌⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣧⣴⣿⡟⠀⠀⠀⠀⢸⣿⠃⠀⠀⠀⠀⠀⠀⠀⠻⣿⣦⠀⠀⣠⣾⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠻⣿⣤⣄⣀⠀⠀⣿⡿⠠⠀⠀⠀⠀⠀⣀⣤⣤⣿⣿⣷⣾⠿⢿⡿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣽⡿⠿⠿⠿⣿⣿⣶⣶⣶⣶⣶⣿⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣴⠾⠛⠉⣀⣤⡶⠟⠛⠉⠉⢿⣿⣇⠀⠀⢹⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⡶⠟⢋⣡⣴⠶⠟⠋⠁⠀⠀⠀⠀⠀⠘⣿⣿⡀⠀⠸⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣴⠾⢛⣡⣴⠾⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⡇⠀⠀⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⢀⣠⡴⣚⣭⡶⠟⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⣿⠀⠀⢹⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⣀⣤⣶⣿⠷⠛⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⢀⣴⡾⠿⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⡆⠀⢸⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡇⠀⢸⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⠃⠀⠈⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀