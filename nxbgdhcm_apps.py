import sys
from PyQt6.QtWidgets import QApplication
from nxbgdhcm_core_interface import MainWindow

def main():
    print("[SYSTEM] Khởi động Phần mềm quản lý file nội bộ NXBGDHCM...")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    main_window = MainWindow()
    main_window.showMaximized()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()