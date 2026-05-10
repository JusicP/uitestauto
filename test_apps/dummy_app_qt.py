import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

def main():
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("UiTestAuto Dummy App")
    window.resize(300, 200)

    layout = QVBoxLayout(window)

    lbl_title = QLabel("Test Automation Target")
    lbl_title.setObjectName("lbl_title")
    layout.addWidget(lbl_title)

    form_layout = QHBoxLayout()
    lbl_name = QLabel("Name:")
    form_layout.addWidget(lbl_name)

    entry_name = QLineEdit()
    entry_name.setObjectName("name_entry")
    form_layout.addWidget(entry_name)

    layout.addLayout(form_layout)

    btn_layout = QHBoxLayout()
    btn_click_me = QPushButton("Click Me")
    btn_click_me.setObjectName("click_btn")
    
    btn_submit = QPushButton("Submit")
    btn_submit.setObjectName("submit_btn")
    
    btn_layout.addWidget(btn_click_me)
    btn_layout.addWidget(btn_submit)
    layout.addLayout(btn_layout)

    lbl_status = QLabel("Waiting...")
    lbl_status.setObjectName("status_lbl")
    layout.addWidget(lbl_status)

    def on_click():
        lbl_status.setText("Button Clicked!")

    def on_submit():
        lbl_status.setText(f"Submitted: {entry_name.text()}")

    btn_click_me.clicked.connect(on_click)
    btn_submit.clicked.connect(on_submit)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
