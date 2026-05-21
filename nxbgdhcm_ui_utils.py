from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtCore import Qt
from nxbgdhcm_db_manager import db

def setup_shared_ai_combobox(combo_widget, store_full_dict=False):
    combo_widget.blockSignals(True)
    combo_widget.clear()
    
    success, presets = db.get_ai_presets()
    default_index = -1
    
    if success and presets:
        for i, p in enumerate(presets):
            # Kiểm tra trạng thái mặc định
            is_default = str(p.get("Default", "")).upper() in ["TRUE", "1", "YES"] or p.get("Is_Default") == True
            display_name = p["Preset_Name"]
            
            if is_default:
                display_name = display_name +" ⭐"
                
            # Phân định dữ liệu lưu trữ theo nhu cầu của trang gọi hàm
            user_data = p if store_full_dict else p["ID"]
            combo_widget.addItem(display_name, userData=user_data)
            
            # Tô màu phân quyền
            if p.get("person_key") is None:
                combo_widget.setItemData(i, QBrush(QColor("#1A365D")), Qt.ItemDataRole.ForegroundRole) # Hệ thống
            else:
                combo_widget.setItemData(i, QBrush(QColor("#059669")), Qt.ItemDataRole.ForegroundRole) # Cá nhân
            
            # In đậm mặc định
            if is_default:
                font = QFont()
                font.setBold(True)
                combo_widget.setItemData(i, font, Qt.ItemDataRole.FontRole)
                default_index = i
                
    combo_widget.blockSignals(False)
    
    # Tự động chọn tiêu điểm vào vị trí mặc định nếu tìm thấy
    if combo_widget.count() > 0:
        combo_widget.setCurrentIndex(default_index if default_index != -1 else 0)