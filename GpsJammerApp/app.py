import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from app.ui_mainwindow import MainWindow

def qt_message_handler(mode, context, message):
    if "Unknown property" in message and ("box-shadow" in message or "transform" in message):
        return
    if mode == QtMsgType.QtDebugMsg:
        print(f"Qt Debug: {message}")
    elif mode == QtMsgType.QtWarningMsg:
        print(f"Qt Warning: {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}")
    elif mode == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}")

if __name__ == "__main__":
    qInstallMessageHandler(qt_message_handler)
    app = QApplication(sys.argv)
    app.setApplicationName("GPS Jammer Detection")
    app.setApplicationDisplayName("GPS Jammer Detection")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("GPS Security Tools")
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_dir, "resources", "icon.png")
    icon = QIcon(icon_path)
    if icon.isNull():
        fallback_paths = [
            os.path.join(os.path.dirname(__file__), "icon.png"),
            os.path.join(os.path.dirname(__file__), "app", "icon.png"),
            "icon.png"
        ]
        for fallback_path in fallback_paths:
            if os.path.exists(fallback_path):
                icon = QIcon(fallback_path)
                if not icon.isNull():
                    print(f"Używam fallback ikony: {fallback_path}")
                    break

    app.setWindowIcon(icon)
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName("gps-jammer-detection")
    w = MainWindow()
    w.setWindowIcon(icon)
    w.setWindowTitle("GPS Jammer Detection - Analiza Sygnałów GNSS")
    w.show()
    w.raise_()
    w.activateWindow()
    sys.exit(app.exec())
