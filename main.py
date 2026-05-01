import sys
from PySide6.QtWidgets import QStyleFactory
from PySide6.QtWidgets import QApplication
from uitestauto.ui.main_window import UiTestAutoWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Windows"))
    
    window = UiTestAutoWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
