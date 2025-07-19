import sys
from PySide6 import QtWidgets
from qt_material import apply_stylesheet

from CSESP.Overlay import ESPOverlay



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_purple.xml')
    overlay = ESPOverlay()
    overlay.show()
    sys.exit(app.exec())