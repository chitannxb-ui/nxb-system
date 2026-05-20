import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QComboBox, QGroupBox, QScrollArea, QFormLayout, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from nxbgdhcm_db_manager import db

class PageConfig(QWidget):
    def __init__(self, parent_main, shared_logic):
        super().__init__()
        self.parent_main = parent_main
        self.logic = shared_logic
        self.current_preset_id = None
        self.current_preset_is_global = False
        self.init_ui()
        self._load_ai_presets_to_combo()
        self._load_user_info()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header = QLabel("CẤU HÌNH HỆ THỐNG")
        header.setObjectName("MainHeader")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Dùng ScrollArea vì có rất nhiều tùy chọn
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        self.form_layout = QVBoxLayout(container)
        self.form_layout.setSpacing(20)

        # --- AI Server Configuration ---
        ai_group = QGroupBox("🤖 Cấu hình Máy chủ AI")
        ai_group_layout = QVBoxLayout(ai_group)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset AI:"))
        self.combo_ai_presets = QComboBox()
        self.combo_ai_presets.currentIndexChanged.connect(self._on_ai_preset_selected)
        preset_layout.addWidget(self.combo_ai_presets)
        ai_group_layout.addLayout(preset_layout)

        form_ai_layout = QFormLayout()
        self.txt_preset_name = QLineEdit()
        self.txt_url_endpoint = QLineEdit()
        self.txt_model_name = QLineEdit()
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        form_ai_layout.addRow("Tên Preset:", self.txt_preset_name)
        form_ai_layout.addRow("URL Endpoint:", self.txt_url_endpoint)
        form_ai_layout.addRow("Tên Model:", self.txt_model_name)
        form_ai_layout.addRow("API Key:", self.txt_api_key)
        ai_group_layout.addLayout(form_ai_layout)

        ai_buttons_layout = QHBoxLayout()
        self.btn_save_ai_preset = QPushButton("💾 Lưu Preset")
        self.btn_save_ai_preset.setObjectName("BtnBatDau")
        self.btn_save_ai_preset.clicked.connect(self._save_ai_preset)
        self.btn_set_default_ai = QPushButton("⭐ Đặt làm mặc định")
        self.btn_set_default_ai.setObjectName("ToolbarBtn")
        self.btn_set_default_ai.clicked.connect(self._set_default_ai_preset)
        self.btn_delete_ai_preset = QPushButton("🗑️ Xóa Preset")
        self.btn_delete_ai_preset.setObjectName("ToolbarBtn")
        self.btn_delete_ai_preset.setStyleSheet("background-color: #ef4444; color: white;")
        self.btn_delete_ai_preset.clicked.connect(self._delete_ai_preset)

        ai_buttons_layout.addStretch()
        ai_buttons_layout.addWidget(self.btn_delete_ai_preset)
        ai_buttons_layout.addWidget(self.btn_set_default_ai)
        ai_buttons_layout.addWidget(self.btn_save_ai_preset)
        ai_group_layout.addLayout(ai_buttons_layout)
        self.form_layout.addWidget(ai_group)

        # --- User Information ---
        user_group = QGroupBox("👤 Thông tin Người dùng")
        user_group_layout = QFormLayout(user_group)
        
        font_bold = QFont()
        font_bold.setBold(True)

        self.lbl_ho_ten = QLabel(); self.lbl_ho_ten.setFont(font_bold)
        self.lbl_danh_xung = QLabel()
        self.lbl_phong_ban = QLabel()
        self.lbl_chuc_vu = QLabel()
        self.lbl_cong_tac = QLabel()
        self.lbl_nv_phong = QLabel()
        self.lbl_chuc_danh_khac = QLabel()
        self.lbl_syll = QLabel()
        self.lbl_syll.setWordWrap(True)

        user_group_layout.addRow("Họ và Tên:", self.lbl_ho_ten)
        user_group_layout.addRow("Danh xưng:", self.lbl_danh_xung)
        user_group_layout.addRow("Phòng Ban:", self.lbl_phong_ban)
        user_group_layout.addRow("Chức vụ:", self.lbl_chuc_vu)
        user_group_layout.addRow("Công tác:", self.lbl_cong_tac)
        user_group_layout.addRow("Nhiệm vụ Phòng:", self.lbl_nv_phong)
        user_group_layout.addRow("Chức danh khác:", self.lbl_chuc_danh_khac)
        user_group_layout.addRow("Sơ yếu lý lịch:", self.lbl_syll)
        
        # Make all user info labels disabled (read-only appearance)
        for label in [self.lbl_ho_ten, self.lbl_danh_xung, self.lbl_phong_ban, self.lbl_chuc_vu,
                       self.lbl_cong_tac, self.lbl_nv_phong, self.lbl_chuc_danh_khac, self.lbl_syll]:
            label.setEnabled(False)
            label.setStyleSheet("QLabel { color: #666; }") # Grey out text

        self.form_layout.addWidget(user_group)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _load_ai_presets_to_combo(self):
        self.combo_ai_presets.blockSignals(True)
        self.combo_ai_presets.clear()
        success, presets = db.get_ai_presets()
        
        default_preset_index = -1
        
        if success and presets:
            for i, p in enumerate(presets):
                self.combo_ai_presets.addItem(p["Preset_Name"], userData=p)
                if p.get("Default"):
                    default_preset_index = i
        
        self.combo_ai_presets.addItem("--- Tạo mới ---", userData=None)
        
        if default_preset_index != -1:
            self.combo_ai_presets.setCurrentIndex(default_preset_index)
        else:
            self.combo_ai_presets.setCurrentIndex(self.combo_ai_presets.count() - 1) # Select "Tạo mới"
            self._clear_ai_fields()

        self.combo_ai_presets.blockSignals(False)
        self._update_ai_buttons_state()

    def _on_ai_preset_selected(self, index):
        preset_data = self.combo_ai_presets.currentData()
        if preset_data:
            self.current_preset_id = preset_data.get("ID")
            self.current_preset_is_global = (preset_data.get("person_key") is None)
            self.txt_preset_name.setText(preset_data.get("Preset_Name", ""))
            self.txt_url_endpoint.setText(preset_data.get("URL", ""))
            self.txt_model_name.setText(preset_data.get("Model_Name", ""))
            self.txt_api_key.setText(preset_data.get("API_Key", "")) # API Key might be sensitive, consider not loading it back
        else: # "--- Tạo mới ---" selected
            self._clear_ai_fields()
            self.current_preset_id = None
            self.current_preset_is_global = False
        self._update_ai_buttons_state()

    def _clear_ai_fields(self):
        self.txt_preset_name.clear()
        self.txt_url_endpoint.clear()
        self.txt_model_name.clear()
        self.txt_api_key.clear()

    def _update_ai_buttons_state(self):
        is_new_preset = (self.combo_ai_presets.currentData() is None)
        self.btn_save_ai_preset.setEnabled(True) # Always allow saving (either new or update)
        self.btn_set_default_ai.setEnabled(not is_new_preset and not self.current_preset_is_global)
        self.btn_delete_ai_preset.setEnabled(not is_new_preset and not self.current_preset_is_global)
        
        # If a global preset is selected, "Set Default" and "Delete" should be disabled
        if self.current_preset_is_global:
            self.btn_set_default_ai.setEnabled(False)
            self.btn_delete_ai_preset.setEnabled(False)

    def _save_ai_preset(self):
        preset_name = self.txt_preset_name.text().strip()
        url = self.txt_url_endpoint.text().strip()
        model_name = self.txt_model_name.text().strip()
        api_key = self.txt_api_key.text().strip()

        if not all([preset_name, url, model_name, api_key]):
            QMessageBox.warning(self, "Lỗi", "Vui lòng điền đầy đủ thông tin Preset AI.")
            return

        # Determine if this is a new preset or an update
        is_new_preset = (self.current_preset_id is None)
        
        # If a global preset is selected, we treat it as creating a new user-specific preset
        is_global_preset_being_modified = (not is_new_preset and self.current_preset_is_global)

        if db.save_ai_preset(
            self.current_preset_id, preset_name, url, model_name, api_key, False, is_global_preset_being_modified
        ):
            QMessageBox.information(self, "Thành công", "Đã lưu cấu hình AI.")
            self._load_ai_presets_to_combo() # Reload combo to show new/updated preset
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể lưu cấu hình AI vào CSDL.")

    def _set_default_ai_preset(self):
        if self.current_preset_id is None:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một Preset để đặt làm mặc định.")
            return
        
        if self.current_preset_is_global:
            QMessageBox.warning(self, "Lỗi", "Không thể đặt Preset dùng chung làm mặc định của cá nhân. Vui lòng tạo một bản sao của riêng bạn.")
            return

        if db.set_default_ai_preset(self.current_preset_id):
            QMessageBox.information(self, "Thành công", "Đã đặt Preset này làm mặc định.")
            self._load_ai_presets_to_combo() # Reload to update default indicator
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể đặt Preset làm mặc định.")

    def _delete_ai_preset(self):
        if self.current_preset_id is None:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một Preset để xóa.")
            return
        
        if self.current_preset_is_global:
            QMessageBox.warning(self, "Lỗi", "Không thể xóa Preset dùng chung. Chỉ có thể xóa Preset của riêng bạn.")
            return

        reply = QMessageBox.question(self, "Xác nhận xóa",
                                     f"Bạn có chắc chắn muốn xóa Preset '{self.txt_preset_name.text()}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ket_noi_ai WHERE ID = %s AND person_key = %s", (self.current_preset_id, db.PERSON_KEY))
                conn.commit()
                cursor.close()
                QMessageBox.information(self, "Thành công", "Đã xóa Preset AI.")
                self._load_ai_presets_to_combo()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa Preset AI: {e}")

    def _load_user_info(self):
        # user_info = db.get_user_info() # Commented out as per user request to ignore Nguoi_dung table creation
        # if user_info:
        #     self.lbl_ho_ten.setText(user_info.get("Ho_Va_Ten", "N/A"))
        #     self.lbl_danh_xung.setText(user_info.get("danh_xung", "N/A"))
        #     self.lbl_phong_ban.setText(user_info.get("Phong_Ban", "N/A"))
        #     self.lbl_chuc_vu.setText(user_info.get("Chuc_vu", "N/A"))
        #     self.lbl_cong_tac.setText(user_info.get("Cong_tac", "N/A"))
        #     self.lbl_nv_phong.setText(user_info.get("NV_Phong", "N/A"))
        #     self.lbl_chuc_danh_khac.setText(user_info.get("Chuc_danh_khac", "N/A"))
        #     self.lbl_syll.setText(user_info.get("SYLL", "N/A"))
        # else:
        #     QMessageBox.warning(self, "Thông tin người dùng", "Không thể tải thông tin người dùng từ CSDL.")
        # Hardcode default values for now
        self.lbl_ho_ten.setText("N/A")
        self.lbl_danh_xung.setText("N/A")
        self.lbl_phong_ban.setText("N/A")
        self.lbl_chuc_vu.setText("N/A")
        self.lbl_cong_tac.setText("N/A")
        self.lbl_nv_phong.setText("N/A")
        self.lbl_chuc_danh_khac.setText("N/A")
        self.lbl_syll.setText("N/A")