from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from nxbgdhcm_db_manager import db

# ==========================================
# BỘ MÀU SẮC CHUNG CHO TOÀN BỘ HỆ THỐNG
# ==========================================
THEME = {
    "primary_bg": "#FCF9F2", "header_bg": "#F8CBA6", "accent_green": "#10B981", 
    "accent_red": "#ef4444", "border_color": "#E5B289", "text_dark": "#333333", 
    "text_light": "#FFFFFF", "input_bg": "#FFFFFF", "sidebar_bg": "#355C8E", 
    "sidebar_active": "#1A365D", "matrix_bg": "#FFFFFF", "matrix_text": "#2563eb",  
    "log_info": "#000000", "log_system": "#c85a17", "log_success": "#10B981", 
    "log_error": "#ef4444", "log_image_mode": "#d97706", "log_text_mode": "#2563eb", 
    "log_warning": "#db2777", "split_bg": "#6b7280", "blank_bg": "#f3f4f6",
    "eval_colors": {
        "Trang trắng": "#ffffff", "1 trang": "#fef08a", "Trang đầu": "#bbf7d0",
        "Trang tiếp": "#86efac", "Trang cuối": "#4ade80", "Đang chờ...": "#FFFFFF",
        "Không xác định": "#fecaca"
    },
    "row_accepted": "#dcfce7", "row_success": "#f3f4f6", "text_success": "#9ca3af"
}

# ==========================================
# CLASS DÙNG CHUNG: KIỂM TRA KẾT NỐI AI
# ==========================================
class TestConnectionWorker(QThread):
    result_signal = pyqtSignal(bool, str)
    def __init__(self, logic, config):
        super().__init__()
        self.logic = logic
        self.config = config
    def run(self):
        success, msg = self.logic.test_ai_connection(self.config['URL'], self.config['Model_Name'], self.config['API_Key'])
        self.result_signal.emit(success, msg)

# ==========================================
# HÀM DÙNG CHUNG: ĐỊNH DẠNG COMBOBOX
# ==========================================
def setup_shared_ai_combobox(combo_widget, store_full_dict=False):
    combo_widget.blockSignals(True)
    combo_widget.clear()
    
    success, presets = db.get_ai_presets()
    default_index = -1
    
    if success and presets:
        for i, p in enumerate(presets):
            is_default = str(p.get("Default", "")).upper() in ["TRUE", "1", "YES"] or p.get("Is_Default") == True
            display_name = p["Preset_Name"]
            
            user_data = p if store_full_dict else p["ID"]
            combo_widget.addItem(display_name, userData=user_data)
            
            # Cấu hình Style (Font chữ)
            font = QFont()
            
            # Nhóm cá nhân -> In nghiêng
            if p.get("person_key") is not None:
                font.setItalic(True)
                
            # Mặc định -> In đậm (Nếu vừa là cá nhân vừa mặc định thì sẽ in đậm nghiêng)
            if is_default:
                font.setBold(True)
                default_index = i
                
            combo_widget.setItemData(i, font, Qt.ItemDataRole.FontRole)
                
    combo_widget.blockSignals(False)
    
    if combo_widget.count() > 0:
        combo_widget.setCurrentIndex(default_index if default_index != -1 else 0)