from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import QRect, QSize, Qt

from .utils import strip_bbcode, get_user_color


class MensajePreview(QStyledItemDelegate):
    def paint(self, painter, option, index):
        data = index.data(Qt.UserRole)
        if not data:
            return super().paint(painter, option, index)

        rect = option.rect
        painter.save()

        palette = option.palette  # <- aquí agarramos colores del tema

        # Fondo al seleccionar
        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, palette.highlight())

        # --- Usuario ---
        user_font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(user_font)
        username = data["username"]
        user_color = get_user_color(username)
        painter.setPen(user_color)

        user_x = rect.left() + 5
        user_y = rect.top() + 5
        painter.drawText(QRect(user_x, user_y, rect.width() - 120, 20),
                         Qt.AlignVCenter | Qt.AlignLeft, data["username"])

        # --- Fecha ---
        date_font = QFont("Segoe UI", 8)
        painter.setFont(date_font)
        date_color = (palette.highlightedText().color()
                      if option.state & QStyle.State_Selected
                      else palette.text().color())  # gris medio
        painter.setPen(date_color)
        painter.drawText(QRect(rect.right() - 100, rect.top() + 5, 95, 20),
                         Qt.AlignVCenter | Qt.AlignRight, data["date"])

        # --- Indicador de actualización ---
        clean_message = strip_bbcode(data["message"]).lstrip().lower()
        if clean_message.startswith("actualización") or clean_message.startswith("miniactualización"):
            badge_text = "Actualización"
            badge_font = QFont("Segoe UI", 8, QFont.Bold)
            painter.setFont(badge_font)

            # Badge colores independientes del tema
            badge_bg = QColor("#2980b9")
            badge_fg = QColor("#ffffff")

            if clean_message.startswith("miniactualización"):
                badge_text = "Miniactualización"
                badge_bg = QColor("#d35400")
                badge_fg = QColor("#ffffff")

            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(badge_text) + 10
            text_height = metrics.height()
            badge_rect = QRect(user_x + 100, user_y, text_width, text_height)

            painter.fillRect(badge_rect, badge_bg)
            painter.setPen(badge_fg)
            painter.drawText(badge_rect, Qt.AlignCenter, badge_text)

        # --- Preview ---
        preview_font = QFont("Segoe UI", 9)
        painter.setFont(preview_font)
        preview_color = (palette.highlightedText().color()
                         if option.state & QStyle.State_Selected
                         else palette.text().color())
        painter.setPen(preview_color)

        preview = data["preview"]
        painter.drawText(QRect(rect.left() + 5, rect.top() + 25,
                               rect.width() - 10, 35),
                         Qt.TextWordWrap, preview)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 65)
