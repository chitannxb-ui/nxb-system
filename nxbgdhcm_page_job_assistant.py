import os
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QComboBox, QTextEdit, QSplitter, QListWidget, QFrame)
from PyQt6.QtCore import Qt
from nxbgdhcm_ui_utils import THEME, setup_shared_ai_combobox

class PageJobAssistant(QWidget):
    def __init__(self, parent_main, shared_logic):
        super().__init__()
        self.parent_main = parent_main
        self.logic = shared_logic
        self.init_ui()
        self.load_ai_presets()

    def init_ui(self):
        # Layout tổng thể của trang
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        # Tiêu đề trang đồng bộ phong cách hệ thống
        header_lbl = QLabel("TRỢ LÝ CÔNG VIỆC & KHÔNG GIAN CANVAS")
        header_lbl.setObjectName("MainHeader")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header_lbl)

        # Sử dụng QSplitter chia 3 cột để người dùng có thể tự co giãn nếu muốn
        self.cols_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.cols_splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: transparent; }} "
            f"QSplitter::handle:horizontal {{ width: 6px; }} "
            f"QSplitter::handle:hover {{ background-color: {THEME['accent_green']}; }}"
        )

        # ----------------------------------------------------
        # CỘT 1 (Bên trái - Chiếm 1/6): DANH SÁCH CUỘC TRÒ CHUYỆN
        # ----------------------------------------------------
        col1_widget = QWidget()
        col1_layout = QVBoxLayout(col1_widget)
        col1_layout.setContentsMargins(0, 0, 0, 0)
        col1_layout.setSpacing(6)

        lbl_chat_list = QLabel("💬 LỊCH SỬ THẢO LUẬN")
        lbl_chat_list.setStyleSheet("font-weight: bold; color: #355C8E;")
        
        self.list_conversations = QListWidget()
        # Dữ liệu giả lập demo cấu trúc hiển thị
        self.list_conversations.addItems([
            "Thảo luận kế hoạch biên soạn tài liệu", 
            "Hỗ trợ viết công văn gửi đối tác", 
            "Phân tích báo cáo số liệu quý II"
        ])

        col1_layout.addWidget(lbl_chat_list)
        col1_layout.addWidget(self.list_conversations)
        self.cols_splitter.addWidget(col1_widget)

        # ----------------------------------------------------
        # CỘT 2 (Ở giữa - Chiếm 3/6): KHUNG CHAT THẢO LUẬN CHÍNH
        # ----------------------------------------------------
        col2_widget = QWidget()
        col2_layout = QVBoxLayout(col2_widget)
        col2_layout.setContentsMargins(0, 0, 0, 0)
        col2_layout.setSpacing(6)

        lbl_chat_box = QLabel("🤖 TRỢ LÝ TƯ VẤN AI")
        lbl_chat_box.setStyleSheet("font-weight: bold; color: #2563eb;")

        # Khu vực hiển thị nội dung tin nhắn chat
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Nội dung hội thoại trò chuyện cùng AI sẽ xuất hiện tại đây...")

        # Thanh nút chức năng nằm ngay TRÊN ô nhập chat theo yêu cầu
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)
        
        self.combo_server = QComboBox()
        self.btn_test = QPushButton("Test")
        self.btn_test.setObjectName("ToolbarBtn")
        
        toolbar_layout.addWidget(QLabel("Mô hình AI:"))
        toolbar_layout.addWidget(self.combo_server, 1)
        toolbar_layout.addWidget(self.btn_test)

        # Khung nhập nội dung chat dưới cùng
        chat_input_frame = QFrame()
        chat_input_frame.setStyleSheet(f"background-color: #FFFFFF; border: 1px solid {THEME['border_color']}; border-radius: 3px;")
        chat_input_layout = QHBoxLayout(chat_input_frame)
        chat_input_layout.setContentsMargins(5, 5, 5, 5)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Nhập tin nhắn hoặc ra lệnh tạo nội dung Canvas...")
        self.chat_input.setStyleSheet("border: none; padding: 5px;")
        
        self.btn_send = QPushButton("Gửi")
        self.btn_send.setObjectName("BtnBatDau")
        
        chat_input_layout.addWidget(self.chat_input, 1)
        chat_input_layout.addWidget(self.btn_send)

        col2_layout.addWidget(lbl_chat_box)
        col2_layout.addWidget(self.chat_history, 1)
        col2_layout.addLayout(toolbar_layout)
        col2_layout.addWidget(chat_input_frame)
        self.cols_splitter.addWidget(col2_widget)

        # ----------------------------------------------------
        # CỘT 3 (Bên phải - Chiếm 2/6): CANVAS KHÔNG GIAN FILE
        # ----------------------------------------------------
        col3_widget = QWidget()
        col3_layout = QVBoxLayout(col3_widget)
        col3_layout.setContentsMargins(0, 0, 0, 0)
        col3_layout.setSpacing(6)

        lbl_canvas = QLabel("📄 CANVAS / KHÔNG GIAN TÀI LIỆU")
        lbl_canvas.setStyleSheet("font-weight: bold; color: #10B981;")

        # Vùng hiển thị tài liệu đa năng (Hỗ trợ text, ảnh, HTML)
        self.canvas_content = QTextEdit()
        self.canvas_content.setReadOnly(True)
        self.canvas_content.setPlaceholderText("Nội dung văn bản, hình ảnh hoặc giao diện mã HTML do AI khởi tạo song song sẽ kết xuất tại không gian Canvas này...")

        col3_layout.addWidget(lbl_canvas)
        col3_layout.addWidget(self.canvas_content)
        self.cols_splitter.addWidget(col3_widget)

        # Áp cấu hình tỷ lệ bề ngang 1/6 : 3/6 : 2/6 tương đương định lượng [100, 300, 200]
        self.cols_splitter.setSizes([100, 300, 200])
        self.main_layout.addWidget(self.cols_splitter, 1)

    def load_ai_presets(self):
        # Tích hợp trực tiếp hàm dùng chung để đồng bộ font in đậm/in nghiêng
        setup_shared_ai_combobox(self.combo_server, store_full_dict=False)