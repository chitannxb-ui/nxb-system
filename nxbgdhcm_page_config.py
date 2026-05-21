import os
import pymysql
import pymysql.cursors
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QComboBox, QGroupBox, QScrollArea, QFormLayout, QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from nxbgdhcm_db_manager import db
from nxbgdhcm_ui_utils import setup_shared_ai_combobox

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

        # Dùng ScrollArea vì cấu hình có thể mở rộng
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        self.main_vbox = QVBoxLayout(container)
        self.main_vbox.setSpacing(20)

        # ====================================================
        # HÀNG 1: THÔNG TIN NGƯỜI DÙNG & CẤU HÌNH MÁY CHỦ AI
        # ====================================================
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(20)

        # --- PHẦN 1 (Top-Left): THÔNG TIN NGƯỜI DÙNG ---
        user_group = QGroupBox("👤 Thông tin Người dùng")
        user_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        
        # [QUAN TRỌNG]: Ép tất cả các Label phải tự động xuống dòng và chấp nhận bị ép nhỏ
        for label in [self.lbl_ho_ten, self.lbl_danh_xung, self.lbl_phong_ban, self.lbl_chuc_vu,
                       self.lbl_cong_tac, self.lbl_nv_phong, self.lbl_chuc_danh_khac, self.lbl_syll]:
            label.setEnabled(False)
            label.setWordWrap(True) # Cho phép rớt dòng
            label.setMinimumWidth(100) # Phá bỏ sự kháng cự của Layout
            label.setStyleSheet("QLabel { color: #333333; background-color: #f3f4f6; padding: 4px; border: 1px solid #e5e7eb; border-radius: 3px; }")

        user_group_layout.addRow("Họ và Tên:", self.lbl_ho_ten)
        user_group_layout.addRow("Danh xưng:", self.lbl_danh_xung)
        user_group_layout.addRow("Phòng Ban:", self.lbl_phong_ban)
        user_group_layout.addRow("Chức vụ:", self.lbl_chuc_vu)
        user_group_layout.addRow("Công tác:", self.lbl_cong_tac)
        user_group_layout.addRow("Nhiệm vụ Phòng:", self.lbl_nv_phong)
        user_group_layout.addRow("Chức danh khác:", self.lbl_chuc_danh_khac)
        user_group_layout.addRow("Sơ yếu lý lịch:", self.lbl_syll)

        # --- PHẦN 2 (Top-Right): CẤU HÌNH MÁY CHỦ AI ---
        ai_group = QGroupBox("🤖 Cấu hình Máy chủ AI")
        ai_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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

        # [QUAN TRỌNG]: Ép các QLineEdit chấp nhận bị thu hẹp tối đa (ẩn bớt text thay vì cản trở layout)
        for txt in [self.txt_preset_name, self.txt_url_endpoint, self.txt_model_name, self.txt_api_key]:
            txt.setMinimumWidth(100)

        form_ai_layout.addRow("Tên Preset:", self.txt_preset_name)
        form_ai_layout.addRow("URL Endpoint:", self.txt_url_endpoint)
        form_ai_layout.addRow("Tên Model:", self.txt_model_name)
        form_ai_layout.addRow("API Key:", self.txt_api_key)
        ai_group_layout.addLayout(form_ai_layout)

        ai_buttons_layout = QHBoxLayout()
        self.btn_create_ai_preset = QPushButton("➕ Tạo mới")
        self.btn_create_ai_preset.setObjectName("ToolbarBtn")
        self.btn_create_ai_preset.clicked.connect(self._create_ai_preset)

        self.btn_delete_ai_preset = QPushButton("🗑️ Xóa")
        self.btn_delete_ai_preset.setObjectName("ToolbarBtn")
        self.btn_delete_ai_preset.setStyleSheet("background-color: #ef4444; color: white;")
        self.btn_delete_ai_preset.clicked.connect(self._delete_ai_preset)

        self.btn_set_default_ai = QPushButton("⭐ Đặt mặc định")
        self.btn_set_default_ai.setObjectName("ToolbarBtn")
        self.btn_set_default_ai.clicked.connect(self._set_default_ai_preset)

        self.btn_save_ai_preset = QPushButton("💾 Lưu")
        self.btn_save_ai_preset.setObjectName("BtnBatDau")
        self.btn_save_ai_preset.clicked.connect(self._save_ai_preset)

        ai_buttons_layout.addStretch()
        ai_buttons_layout.addWidget(self.btn_delete_ai_preset)
        ai_buttons_layout.addWidget(self.btn_create_ai_preset) 
        ai_buttons_layout.addWidget(self.btn_set_default_ai)
        ai_buttons_layout.addWidget(self.btn_save_ai_preset)
        ai_group_layout.addLayout(ai_buttons_layout)
        
        # Đưa 2 Group vào Hàng 1, thiết lập tỷ lệ chia đều 1:1
        row1_layout.addWidget(user_group, 1)
        row1_layout.addWidget(ai_group, 1)


        # ====================================================
        # HÀNG 2: BỘ LỆNH CỦA AI & QUY TẮC VĂN BẢN
        # ====================================================
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(20)

        # --- PHẦN 3 (Bottom-Left): BỘ LỆNH CỦA AI ---
        prompt_group = QGroupBox("🧠 Bộ lệnh của AI")
        prompt_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.addWidget(QLabel("Đang chờ cập nhật..."))
        prompt_layout.addStretch()

        # --- PHẦN 4 (Bottom-Right): QUY TẮC VĂN BẢN ---
        rules_group = QGroupBox("📜 Quy tắc văn bản")
        rules_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        rules_layout = QVBoxLayout(rules_group)
        rules_layout.addWidget(QLabel("Đang chờ cập nhật..."))
        rules_layout.addStretch()

        # Đưa 2 Group vào Hàng 2, thiết lập tỷ lệ chia đều 1:1
        row2_layout.addWidget(prompt_group, 1)
        row2_layout.addWidget(rules_group, 1)

        # Thêm 2 Hàng vào Layout chính, thiết lập tỷ lệ chiều dọc chia đều 1:1
        self.main_vbox.addLayout(row1_layout, 1)
        self.main_vbox.addLayout(row2_layout, 1)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _load_ai_presets_to_combo(self):
        setup_shared_ai_combobox(self.combo_ai_presets, store_full_dict=True)
        if self.combo_ai_presets.count() > 0:
            self._on_ai_preset_selected(self.combo_ai_presets.currentIndex())
        else:
            self._clear_ai_fields()
            self.current_preset_id = None
            self.current_preset_is_global = False
            self._update_ai_buttons_state()

    def _on_ai_preset_selected(self, index):
        if index == -1:
            return
        preset_data = self.combo_ai_presets.currentData()
        if preset_data:
            self.current_preset_id = preset_data.get("ID")
            self.current_preset_is_global = (preset_data.get("person_key") is None)
            
            self.txt_preset_name.setText(preset_data.get("Preset_Name", ""))
            self.txt_url_endpoint.setText(preset_data.get("URL", ""))
            self.txt_model_name.setText(preset_data.get("Model_Name", ""))
            self.txt_api_key.setText(preset_data.get("API_Key", ""))
            
            if self.current_preset_is_global:
                self.txt_preset_name.setEnabled(False)
                self.txt_url_endpoint.setEnabled(False)
                self.txt_model_name.setEnabled(False)
                self.txt_api_key.setEnabled(False)
            else:
                self.txt_preset_name.setEnabled(True)
                self.txt_url_endpoint.setEnabled(True)
                self.txt_model_name.setEnabled(True)
                self.txt_api_key.setEnabled(True)
        else:
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
        if self.current_preset_id is None: 
            self.btn_save_ai_preset.setEnabled(True)
            self.btn_set_default_ai.setEnabled(False)
            self.btn_delete_ai_preset.setEnabled(False)
        elif self.current_preset_is_global: 
            self.btn_save_ai_preset.setEnabled(False)
            self.btn_set_default_ai.setEnabled(False)
            self.btn_delete_ai_preset.setEnabled(False)
        else: 
            self.btn_save_ai_preset.setEnabled(True)
            self.btn_set_default_ai.setEnabled(True)
            self.btn_delete_ai_preset.setEnabled(True)

    def _create_ai_preset(self):
        self.current_preset_id = None
        self.current_preset_is_global = False
        self._clear_ai_fields()
        
        self.txt_preset_name.setEnabled(True)
        self.txt_url_endpoint.setEnabled(True)
        self.txt_model_name.setEnabled(True)
        self.txt_api_key.setEnabled(True)
        
        self.combo_ai_presets.blockSignals(True)
        self.combo_ai_presets.setCurrentIndex(-1)
        self.combo_ai_presets.blockSignals(False)
        
        self._update_ai_buttons_state()
        self.txt_preset_name.setFocus()

    def _save_ai_preset(self):
        preset_name = self.txt_preset_name.text().strip()
        url = self.txt_url_endpoint.text().strip()
        model_name = self.txt_model_name.text().strip()
        api_key = self.txt_api_key.text().strip()

        if not all([preset_name, url, model_name, api_key]):
            QMessageBox.warning(self, "Lỗi", "Vui lòng điền đầy đủ thông tin Preset AI.")
            return

        conn = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            if self.current_preset_id is None:
                # SỬA: Bỏ truyền ID, để MySQL tự động sinh (AUTO_INCREMENT) chống đụng độ
                query = """
                    INSERT INTO ket_noi_ai (Preset_Name, URL, Model_Name, API_Key, `Default`, person_key) 
                    VALUES (%s, %s, %s, %s, 'FALSE', %s)
                """
                cursor.execute(query, (preset_name, url, model_name, api_key, db.person_key))
                # Lấy ID vừa được MySQL tạo ra
                self.current_preset_id = cursor.lastrowid
                QMessageBox.information(self, "Thành công", "Đã lưu mới cấu hình AI của riêng bạn.")
            else:
                if self.current_preset_is_global:
                    QMessageBox.warning(self, "Lỗi", "Không thể chỉnh sửa cấu hình hệ thống dùng chung.")
                    return
                
                query = """
                    UPDATE ket_noi_ai 
                    SET Preset_Name = %s, URL = %s, Model_Name = %s, API_Key = %s 
                    WHERE ID = %s AND person_key = %s
                """
                cursor.execute(query, (preset_name, url, model_name, api_key, self.current_preset_id, db.person_key))
                QMessageBox.information(self, "Thành công", "Đã cập nhật cấu hình AI cá nhân.")
                
            conn.commit()
            cursor.close()
            self._load_ai_presets_to_combo()
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu cấu hình AI vào CSDL:\n{e}")
        finally:
            if conn and conn.open: conn.close() # SỬA: Đảm bảo luôn dọn dẹp Connection

    def _set_default_ai_preset(self):
        if self.current_preset_id is None or self.current_preset_is_global:
            QMessageBox.warning(self, "Lỗi", "Thao tác không hợp lệ trên Preset này.")
            return

        conn = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE ket_noi_ai SET `Default` = 'FALSE' WHERE person_key = %s", (db.person_key,))
            cursor.execute("UPDATE ket_noi_ai SET `Default` = 'TRUE' WHERE ID = %s AND person_key = %s", 
                           (self.current_preset_id, db.person_key))
            conn.commit()
            cursor.close()
            
            QMessageBox.information(self, "Thành công", "Đã đặt cấu hình này làm mặc định cá nhân của bạn.")
            self._load_ai_presets_to_combo()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể đặt cấu hình mặc định:\n{e}")
        finally:
            if conn and conn.open: conn.close()

    def _delete_ai_preset(self):
        if self.current_preset_id is None:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một Preset cá nhân để xóa.")
            return
        if self.current_preset_is_global:
            QMessageBox.warning(self, "Lỗi", "Không thể xóa cấu hình hệ thống mặc định.")
            return

        reply = QMessageBox.question(self, "Xác nhận xóa",
                                     f"Bạn có chắc chắn muốn xóa vĩnh viễn cấu hình '{self.txt_preset_name.text()}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = None
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ket_noi_ai WHERE ID = %s AND person_key = %s", (self.current_preset_id, db.person_key))
                conn.commit()
                cursor.close()
                
                QMessageBox.information(self, "Thành công", "Đã xóa cấu hình AI cá nhân.")
                self.current_preset_id = None
                self._load_ai_presets_to_combo()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa cấu hình AI:\n{e}")
            finally:
                if conn and conn.open: conn.close()

    def _load_user_info(self):
        conn = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM nguoi_dung WHERE Person_key = %s", (db.person_key,))
            user_info = cursor.fetchone()
            cursor.close()
            
            if user_info:
                self.lbl_ho_ten.setText(user_info.get("Ho_Va_Ten") or "Chưa cập nhật")
                self.lbl_danh_xung.setText(user_info.get("danh_xung") or "Bạn")
                self.lbl_phong_ban.setText(user_info.get("Phong_Ban") or "N/A")
                self.lbl_chuc_vu.setText(user_info.get("Chuc_vu") or "N/A")
                self.lbl_cong_tac.setText(user_info.get("Cong_tac") or "Chưa có dữ liệu phân công")
                self.lbl_nv_phong.setText(user_info.get("NV_Phong") or "Chưa định nghĩa")
                self.lbl_chuc_danh_khac.setText(user_info.get("Chuc_danh_khac") or "Không có")
                self.lbl_syll.setText(user_info.get("SYLL") or "Trống")
            else:
                for lbl in [self.lbl_ho_ten, self.lbl_danh_xung, self.lbl_phong_ban, self.lbl_chuc_vu,
                            self.lbl_cong_tac, self.lbl_nv_phong, self.lbl_chuc_danh_khac, self.lbl_syll]:
                    lbl.setText("N/A")
        except Exception as e:
            print(f"Lỗi tải dữ liệu hồ sơ nhân sự: {e}")
        finally:
            if conn and conn.open: conn.close()