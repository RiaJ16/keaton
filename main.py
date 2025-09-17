import sys

from PySide6.QtWidgets import QApplication

from keaton import Keaton

import os

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = Keaton("El Templo de Piedra.json", app)
    viewer.show()
    sys.exit(app.exec())


