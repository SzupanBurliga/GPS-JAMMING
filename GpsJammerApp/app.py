import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from app.ui_mainwindow import MainWindow 

def qt_message_handler(mode, context, message):
    """Filtruje niepotrzebne komunikaty Qt."""
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
    w = MainWindow()
    w.show()
    sys.exit(app.exec())