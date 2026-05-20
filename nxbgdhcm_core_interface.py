import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy, QStackedWidget)
from PyQt6.QtCore import Qt

from nxbgdhcm_db_manager import db
from nxbgdhcm_core_logic import OCRLogic
from nxbgdhcm_page_ocr import PageOCR
from nxbgdhcm_page_search import PageSearch
from nxbgdhcm_page_split import PageSplit
from nxbgdhcm_page_rename import PageRename 
from nxbgdhcm_page_config import PageConfig # Bước 1: Import trang cấu hình hệ thống vào giao diện chính

THEME = {
    "primary_bg": "#FCF9F2", "sidebar_bg": "#355C8E", "sidebar_active": "#1A365D", "header_bg": "#F8CBA6",
    "accent_green": "#10B981", "border_color": "#E5B289", "text_dark": "#333333", "text_light": "#FFFFFF"
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần mềm quản lý file nội bộ của Nhà xuất bản Giáo dục tại TP. Hồ Chí Minh")
        self.resize(1024, 768) 
        self.setMinimumSize(800, 600)
        
        db.setup_database_and_user()
        self.shared_logic = OCRLogic()
        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 25, 0, 25)
        
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        logo_lbl = QLabel("GD", styleSheet="background-color: #B31B1B; color: white; font-size: 20px; font-weight: bold; border-radius: 25px;")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setFixedSize(50, 50) 
        title_lbl = QLabel("QUẢN LÝ TÀI LIỆU\nNội bộ & Cá nhân\nv.1.0")
        title_lbl.setObjectName("SidebarTitle")
        title_layout.addWidget(logo_lbl); title_layout.addWidget(title_lbl)
        self.sidebar_layout.addWidget(title_container)
        self.sidebar_layout.addSpacing(30)

        self.btn_ocr = QPushButton("📁 Số hóa tài liệu")
        self.btn_search = QPushButton("🔍 Tìm kiếm tài liệu")
        self.btn_split = QPushButton("✂️ Tách tài liệu PDF")
        self.btn_rename = QPushButton("📝 Đổi tên file AI") 
        self.btn_config = QPushButton("⚙️ Cấu hình hệ thống") # Bước 2: Khởi tạo nút Menu cho trang cấu hình
        
        # Thêm nút btn_config vào vòng lặp định dạng style của Sidebar
        for btn in [self.btn_ocr, self.btn_search, self.btn_split, self.btn_rename, self.btn_config]:
            btn.setObjectName("MenuButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.sidebar_layout.addWidget(btn)

        self.btn_ocr.clicked.connect(lambda: self.switch_page(0))
        self.btn_search.clicked.connect(lambda: self.switch_page(1))
        self.btn_split.clicked.connect(lambda: self.switch_page(2))
        self.btn_rename.clicked.connect(lambda: self.switch_page(3))
        self.btn_config.clicked.connect(lambda: self.switch_page(4)) # Bước 3: Kết nối sự kiện click của nút chuyển sang index trang số 4

        self.sidebar_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        total_files = db.get_total_scanned_files()
        stats_html = f"""
        <div style='line-height: 1.5; padding: 15px;'>
            <span style='color: #DDE2EB;'>Thống kê nhanh:</span><br>
            <span style='color: #FFFFFF; font-weight: bold;'>{db.danh_xung} {db.ho_ten}</span><br>
            <span style='color: #DDE2EB;'>Phòng:</span> <span style='color: #FFFFFF;'>{db.phong_ban}</span><br>
            <span style='color: #DDE2EB;'>Số file đã quét:</span> <span style='color: #10B981; font-weight: bold;'>{total_files}</span>
        </div>
        """
        self.stats_lbl = QLabel(stats_html)
        self.sidebar_layout.addWidget(self.stats_lbl)
        self.main_layout.addWidget(self.sidebar)

        self.stacked_widget = QStackedWidget()
        
        self.page_ocr = PageOCR(self, self.shared_logic)
        self.page_search = PageSearch(self, self.shared_logic)
        self.page_split = PageSplit(self, self.shared_logic)
        self.page_rename = PageRename(self, self.shared_logic) 
        self.page_config = PageConfig(self, self.shared_logic) # Bước 4: Khởi tạo thực thể giao diện cấu hình
        
        self.stacked_widget.addWidget(self.page_ocr)
        self.stacked_widget.addWidget(self.page_search)
        self.stacked_widget.addWidget(self.page_split)
        self.stacked_widget.addWidget(self.page_rename)
        self.stacked_widget.addWidget(self.page_config) # Bước 5: Đưa thực thể trang cấu hình vào QStackedWidget (vị trí index số 4)
        self.main_layout.addWidget(self.stacked_widget, 1)

        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; color: {THEME['text_dark']}; }}
            QFrame#Sidebar {{ background-color: {THEME['sidebar_bg']}; }}
            QLabel#SidebarTitle {{ color: {THEME['text_light']}; font-weight: bold; font-size: 15px; }}
            
            QPushButton#MenuButton {{ color: {THEME['text_light']}; text-align: left; padding: 15px 20px; border: none; background-color: transparent; font-size: 15px; }}
            QPushButton#MenuButton:hover {{ background-color: #4A76AE; }}
            QPushButton#MenuButtonActive {{ background-color: {THEME['sidebar_active']}; color: {THEME['text_light']}; text-align: left; padding: 15px 20px; border: none; font-weight: bold; border-left: 5px solid {THEME['text_light']}; font-size: 15px; }}
            
            QLabel#MainHeader {{ background-color: {THEME['header_bg']}; color: {THEME['text_dark']}; font-size: 20px; font-weight: bold; padding: 10px; border: 1px solid {THEME['border_color']}; border-radius: 4px; }}
            
            QLineEdit, QComboBox {{ padding: 6px 10px; border: 1px solid #C0C0C0; background-color: #FFFFFF; border-radius: 3px; min-height: 20px; }}
            QComboBox:hover, QLineEdit:hover {{ border: 1px solid {THEME['accent_green']}; }}
            QComboBox::drop-down {{ border: none; width: 25px; }}
            
            QPushButton#ToolbarBtn {{ padding: 6px 15px; background-color: #E6E6E6; border: 1px solid #A0A0A0; border-radius: 3px; font-weight: bold; color: #333333; }}
            QPushButton#ToolbarBtn:hover {{ background-color: #D4D4D4; }}
            QPushButton#ToolbarBtn:disabled {{ background-color: #F3F4F6; color: #CBD5E1; border: 1px solid #E2E8F0; }}
            
            QPushButton#BtnBatDau {{ padding: 6px 15px; background-color: {THEME['accent_green']}; border: 1px solid #059669; border-radius: 3px; color: white; font-weight: bold; }}
            QPushButton#BtnBatDau:hover {{ background-color: #059669; }}
            QPushButton#BtnBatDau:disabled {{ background-color: #9ca3af; border: 1px solid #6b7280; }}
            
            QTextEdit, QTreeWidget, QTableWidget, QLabel#ImageReviewLabel {{ background-color: #FFFFFF; border: 1px solid {THEME['border_color']}; border-radius: 3px; outline: 0; }}
            QTreeWidget::item {{ padding: 4px; }}
            QTreeWidget::item:selected {{ background-color: #E6E6E6; color: black; }}
            QHeaderView::section {{ background-color: {THEME['header_bg']}; font-weight: bold; padding: 6px; border: 1px solid {THEME['border_color']}; border-top: none; border-left: none; }}
            
            QProgressBar {{ border: 1px solid #C0C0C0; background-color: #EAEAEA; text-align: left; color: black; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {THEME['accent_green']}; border-radius: 2px; }}
            
            QSplitter::handle {{ background-color: transparent; }}
            QSplitter::handle:horizontal {{ width: 8px; }}
            QSplitter::handle:vertical {{ height: 8px; }}
            QSplitter::handle:hover {{ background-color: {THEME['accent_green']}; }}
        """)
        self.switch_page(0) 

    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.btn_ocr.setObjectName("MenuButtonActive" if index == 0 else "MenuButton")
        self.btn_search.setObjectName("MenuButtonActive" if index == 1 else "MenuButton")
        self.btn_split.setObjectName("MenuButtonActive" if index == 2 else "MenuButton")
        self.btn_rename.setObjectName("MenuButtonActive" if index == 3 else "MenuButton")
        self.btn_config.setObjectName("MenuButtonActive" if index == 4 else "MenuButton") # Bước 6: Đảm bảo hiệu ứng làm sáng nút (Active) hoạt động đúng trên thanh Sidebar khi nhấn nút Config
        self.setStyleSheet(self.styleSheet())
        
        if index == 1: self.page_search.load_ai_presets()
        elif index == 2: self.page_split.load_ai_presets()
        elif index == 3: self.page_rename.load_ai_presets()
        elif index == 4: self.page_config._load_ai_presets_to_combo() # Bước 7: Tự động tải/đồng bộ lại danh sách các Preset từ CSDL lên ComboBox mỗi khi người dùng nhấn chuyển sang trang cấu hình