import sys

from PySide6.QtWidgets import QApplication

from keaton import Keaton


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = Keaton(app)
    viewer.show()
    sys.exit(app.exec())


