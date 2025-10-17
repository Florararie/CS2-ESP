import sys
from PySide6 import QtWidgets

from CSESP.Overlay import ESPOverlay



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    overlay = ESPOverlay()
    overlay.show()
    sys.exit(app.exec())