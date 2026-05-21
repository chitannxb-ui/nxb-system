import os
import time
import base64
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QComboBox, QProgressBar, QTextEdit, QSpacerItem, QSizePolicy, 
                             QSplitter, QFileDialog, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QBrush, QFont, QKeyEvent

from nxbgdhcm_db_manager import db
from nxbgdhcm_core_logic import TEMP_DIR
from nxbgdhcm_ui_utils import setup_shared_ai_combobox, THEME

class CustomTableWidget(QTableWidget):
    hotkey_pressed = pyqtSignal(str) 

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Space:
            self.hotkey_pressed.emit("SPACE")
            event.accept()
        elif key == Qt.Key.Key_X:
            self.hotkey_pressed.emit("X")
            event.accept()
        elif key == Qt.Key.Key_A:
            self.hotkey_pressed.emit("A")
            event.accept()
        elif key == Qt.Key.Key_S:
            self.hotkey_pressed.emit("S")
            event.accept()
        elif key == Qt.Key.Key_Z:
            self.hotkey_pressed.emit("Z")
            event.accept()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.hotkey_pressed.emit("ENTER")
            event.accept()
        else:
            super().keyPressEvent(event)

class ResizablePreviewLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: #f8fafc; border: 1px solid {THEME['border_color']}; border-radius: 3px; color: #999;")
        self.setText("Khu vực xem trước trang ngắt")
        self._pixmap = None
        self.setMinimumSize(50, 50)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def set_image(self, pixmap):
        self._pixmap = pixmap
        if pixmap is None:
            self.clear()
        else:
            self.update_image()

    def update_image(self):
        if self._pixmap and not self._pixmap.isNull():
            scaled_pixmap = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            super().setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        if self._pixmap is not None:
            self.update_image()
        super().resizeEvent(event)

class PageScanWorker(QThread):
    log_signal = pyqtSignal(str, str)
    page_scanned_signal = pyqtSignal(int, str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal()

    def __init__(self, logic, file_path, md5_hash, db_data, ai_config):
        super().__init__()
        self.logic = logic; self.file_path = file_path; self.md5_hash = md5_hash
        self.db_data = db_data; self.ai_config = ai_config
        self.task_key = "split" 

    def run(self):
        for f in os.listdir(TEMP_DIR):
            if f.startswith(f"split_scan_{self.md5_hash}_") and f.endswith(".jpg"):
                try: os.remove(os.path.join(TEMP_DIR, f))
                except: pass

        total_p = self.logic.get_pdf_page_count(self.file_path)
        self.log_signal.emit(f"Bắt đầu xử lý {total_p} trang PDF...", "#10B981")
        
        prev_text = ""

        for p_num in range(1, total_p + 1):
            if not self.logic.is_running(self.task_key): break
            
            tmp_img = os.path.join(TEMP_DIR, f"split_scan_{self.md5_hash}_{p_num}.jpg")
            
            if not self.logic.render_pdf_page_to_image(self.file_path, p_num, tmp_img):
                self.log_signal.emit(f"Lỗi tạo ảnh trang {p_num}", "#ef4444"); continue
            
            ai_eval = "Không xác định"
            ai_text = None
            
            if p_num in self.db_data and self.db_data[p_num]["Toan_van"] is not None:
                ai_eval = self.db_data[p_num]["Nhan_xet"]
                ai_text = self.db_data[p_num]["Toan_van"]
            else:
                self.log_signal.emit(f"Đang gửi A.I phân tích trang {p_num}...", "#2563eb")
                with open(tmp_img, "rb") as f_img: b64_img = base64.b64encode(f_img.read()).decode('utf-8')
                prompt = self.logic.get_prompt_page_evaluation_v2(prev_text)
                
                for attempt in range(3):
                    if not self.logic.is_running(self.task_key): break
                    raw_ai_text = ""
                    gen = self.logic.call_ai_stream_generator(self.ai_config['URL'], self.ai_config['Model_Name'], self.ai_config['API_Key'], prompt, b64_img, task_key=self.task_key)
                    for c in gen:
                        if not self.logic.is_running(self.task_key): break
                        raw_ai_text += c

                    ai_json_data = self.logic.extract_json(raw_ai_text)
                    if ai_json_data and "Phân tích" in ai_json_data:
                        ai_eval = ai_json_data["Phân tích"]
                        ai_text = ai_json_data.get("Toàn văn", "")
                        break
                    else: time.sleep(1)

                if ai_eval == "Trang trắng": ai_text = ""
                # LƯU Ý: Vẫn tự động lưu cho từng trang KHI AI ĐANG CHẠY QUÉT để tránh mất dữ liệu nếu đứt mạng
                db.save_split_page(self.md5_hash, p_num, ai_text, ai_eval)

            if ai_eval == "Trang trắng": pass 
            elif ai_eval in ["1 trang", "Trang cuối"]: prev_text = "" 
            else: prev_text = ai_text or ""
            
            self.page_scanned_signal.emit(p_num, ai_eval)
            self.progress_signal.emit(p_num, total_p)

        self.log_signal.emit(f"Hoàn tất xử lý {total_p} trang.", "#10B981")
        self.finished_signal.emit()

class CutPdfWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, list)
    
    def __init__(self, logic, pdf_path, blocks, output_dir):
        super().__init__()
        self.logic = logic; self.pdf_path = pdf_path; self.blocks = blocks; self.output_dir = output_dir
        
    def run(self):
        success, results = self.logic.execute_custom_pdf_split(self.pdf_path, self.blocks, self.output_dir)
        self.finished_signal.emit(success, results)

class PageSplit(QWidget):
    def __init__(self, parent_main, shared_logic):
        super().__init__()
        self.parent_main = parent_main
        self.logic = shared_logic
        self.current_md5 = None
        self.page_states = []
        self._is_updating_table = False
        self.task_key = "split" 
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        header_lbl = QLabel("TÁCH TÀI LIỆU PDF TỰ ĐỘNG", styleSheet=f"background-color: {THEME['header_bg']}; color: {THEME['text_dark']}; font-size: 20px; font-weight: bold; padding: 10px; border: 1px solid {THEME['border_color']}; border-radius: 4px;")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header_lbl)

        self.cols_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.cols_splitter.setStyleSheet(f"QSplitter::handle {{ background-color: transparent; }} QSplitter::handle:horizontal {{ width: 6px; }} QSplitter::handle:hover {{ background-color: {THEME['accent_green']}; }}")

        col1_widget = QWidget(); col1_layout = QVBoxLayout(col1_widget); col1_layout.setContentsMargins(0, 0, 0, 0); col1_layout.setSpacing(8)
        
        BTN_WIDTH = 150 

        row1 = QHBoxLayout(); row1.setContentsMargins(0,0,0,0)
        self.file_input = QLineEdit(); self.file_input.setPlaceholderText("File PDF nguồn...")
        self.btn_select_file = QPushButton("Chọn file pdf"); self.btn_select_file.setObjectName("ToolbarBtn"); self.btn_select_file.setFixedWidth(BTN_WIDTH)
        self.btn_select_file.clicked.connect(self.on_select_file)
        row1.addWidget(self.file_input, 1); row1.addWidget(self.btn_select_file)
        
        row2 = QHBoxLayout(); row2.setContentsMargins(0,0,0,0)
        self.dest_input = QLineEdit(); self.dest_input.setPlaceholderText("Thư mục đích...")
        self.btn_select_dest = QPushButton("Chọn thư mục đích"); self.btn_select_dest.setObjectName("ToolbarBtn"); self.btn_select_dest.setFixedWidth(BTN_WIDTH)
        self.btn_select_dest.clicked.connect(self.on_select_dest)
        row2.addWidget(self.dest_input, 1); row2.addWidget(self.btn_select_dest)

        row3 = QHBoxLayout(); row3.setContentsMargins(0,0,0,0)
        self.progress_bar = QProgressBar(); self.progress_bar.setFixedHeight(28); self.progress_bar.setValue(0); self.progress_bar.setFormat("")
        self.btn_start = QPushButton("Bắt đầu"); self.btn_start.setObjectName("BtnBatDau"); self.btn_start.setFixedWidth(BTN_WIDTH)
        self.btn_start.clicked.connect(self.on_start_stop)
        row3.addWidget(self.progress_bar, 1); row3.addWidget(self.btn_start)

        self.log_text = QTextEdit(); self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(f"background-color: #FFFFFF; border: 1px solid {THEME['border_color']}; padding: 10px; border-radius: 3px;")

        col1_layout.addLayout(row1); col1_layout.addLayout(row2); col1_layout.addLayout(row3); col1_layout.addWidget(self.log_text, 1)
        self.cols_splitter.addWidget(col1_widget)

        col2_widget = QWidget(); col2_layout = QVBoxLayout(col2_widget); col2_layout.setContentsMargins(0, 0, 0, 0); col2_layout.setSpacing(8)
        
        hdr2 = QHBoxLayout(); hdr2.setContentsMargins(0,0,0,0)
        self.combo_view_mode = QComboBox()
        # THÊM CHẾ ĐỘ: Ẩn điểm ngắt
        self.combo_view_mode.addItems(["👁️ Xem đầy đủ", "🙈 Ẩn trang trắng", "⬜ Chỉ xem trang trắng", "🚫 Ẩn điểm ngắt"])
        self.combo_view_mode.setStyleSheet(f"QComboBox {{ padding: 0px 8px; border: 1px solid {THEME['border_color']}; background-color: #FFFFFF; color: #333333; height: 26px; }}")
        self.combo_view_mode.currentIndexChanged.connect(self.sync_ui_from_state)
        
        self.btn_reload = QPushButton("Nạp Lại"); self.btn_reload.setObjectName("ToolbarBtn"); self.btn_reload.setEnabled(False)
        self.btn_save_db = QPushButton("Lưu CSDL"); self.btn_save_db.setObjectName("ToolbarBtn"); self.btn_save_db.setEnabled(False)
        self.btn_execute = QPushButton("✂️ Tiến hành cắt"); self.btn_execute.setObjectName("BtnBatDau"); self.btn_execute.setEnabled(False)
        
        self.btn_reload.clicked.connect(self.on_reload_from_db)
        self.btn_save_db.clicked.connect(self.on_save_db_manual)
        self.btn_execute.clicked.connect(self.execute_cut)

        hdr2.addWidget(self.combo_view_mode); hdr2.addStretch()
        hdr2.addWidget(self.btn_reload); hdr2.addWidget(self.btn_save_db); hdr2.addWidget(self.btn_execute)
        
        self.table = CustomTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Trang", "Trang con", "Tên file", "Phân tích"])
        self.table.verticalHeader().setVisible(False) 
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) 
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) 
        self.table.setStyleSheet(f"background-color: #FFFFFF; border: 1px solid {THEME['border_color']};")
        
        self.table.itemSelectionChanged.connect(self.on_table_select)
        self.table.hotkey_pressed.connect(self.handle_hotkeys)

        col2_layout.addLayout(hdr2); col2_layout.addWidget(self.table, 1)
        self.cols_splitter.addWidget(col2_widget)

        col3_widget = QWidget(); col3_layout = QVBoxLayout(col3_widget); col3_layout.setContentsMargins(0, 0, 0, 0); col3_layout.setSpacing(8)
        
        top3 = QHBoxLayout(); top3.setContentsMargins(0,0,0,0)
        self.combo_server = QComboBox()
        self.combo_server.setStyleSheet(f"QComboBox {{ padding: 0px 8px; border: 1px solid #C0C0C0; background-color: #FFFFFF; color: black; height: 26px; }}")
        self.btn_test = QPushButton("Test"); self.btn_test.setObjectName("ToolbarBtn")
        self.btn_test.clicked.connect(self.on_test_server_clicked)
        top3.addWidget(QLabel("Server AI:")); top3.addWidget(self.combo_server, 1); top3.addWidget(self.btn_test)
        
        self.preview_label = ResizablePreviewLabel()
        
        col3_layout.addLayout(top3); col3_layout.addWidget(self.preview_label, 1)
        self.cols_splitter.addWidget(col3_widget)

        self.cols_splitter.setSizes([350, 550, 300])
        self.main_layout.addWidget(self.cols_splitter, 1)

    def load_ai_presets(self):
        setup_shared_ai_combobox(self.combo_server, store_full_dict=False)

    def add_log(self, text, color="#333333"):
        self.log_text.append(f"<span style='color:{color};'>[{time.strftime('%H:%M:%S')}] {text}</span>")

    def on_test_server_clicked(self):
        preset_id = self.combo_server.currentData()
        name = self.combo_server.currentText()
        if not preset_id: return
        self.btn_test.setEnabled(False)
        self.add_log(f"====== Gửi tín hiệu Test đến: {name} ======", "#2563eb")
        config = db.get_ai_config_by_id(preset_id)
        if config:
            self.test_thread = TestConnectionWorker(self.logic, config)
            self.test_thread.result_signal.connect(self.on_test_finished)
            self.test_thread.start()
        else: self.btn_test.setEnabled(True)

    def on_test_finished(self, success, msg):
        self.btn_test.setEnabled(True)
        if success: self.add_log(f"[AI Phản hồi]: {msg}", "#10B981")
        else: self.add_log(f"[LỖI]: {msg}", "#ef4444")

    def on_select_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Chọn file PDF", "", "PDF Files (*.pdf)")
        if f: self.file_input.setText(os.path.normpath(f))

    def on_select_dest(self):
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu đích")
        if d: self.dest_input.setText(os.path.normpath(d))

    def on_start_stop(self):
        pdf_path = self.file_input.text()
        if not os.path.exists(pdf_path):
            self.add_log("Vui lòng chọn File PDF nguồn hợp lệ!", THEME['accent_red']); return
            
        if self.logic.is_running(self.task_key):
            self.logic.set_running_state(self.task_key, False)
            self.add_log("Đang dừng tiến trình...", "#db2777")
            return
            
        self.logic.set_running_state(self.task_key, True)
        self.btn_start.setText("Dừng")
        self.btn_start.setStyleSheet(f"background-color: {THEME['accent_red']}; color: white;")
        
        self.current_md5 = self.logic.calculate_md5(pdf_path)
        if not self.current_md5: 
            self.add_log("Lỗi tính MD5 file!", THEME['accent_red']); return

        total_p = self.logic.get_pdf_page_count(pdf_path)
        self.page_states = [{"page": p, "eval": "Đang chờ..."} for p in range(1, total_p + 1)]
        self.sync_ui_from_state()
        self.table.setEnabled(False) 
        self.btn_reload.setEnabled(False); self.btn_save_db.setEnabled(False)
        
        success, db_data = db.get_split_data(self.current_md5)
        preset_id = self.combo_server.currentData()
        config = db.get_ai_config_by_id(preset_id)
        
        self.worker = PageScanWorker(self.logic, pdf_path, self.current_md5, db_data, config)
        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(lambda c, t: self.progress_bar.setValue(int((c/t)*100)))
        self.worker.page_scanned_signal.connect(self.update_scanned_page)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.start()

    def update_scanned_page(self, p_num, ai_eval):
        for item in self.page_states:
            if not item.get("is_split") and item.get("page") == p_num:
                item["eval"] = ai_eval
                break
                
        for r in range(self.table.rowCount()):
            it0 = self.table.item(r, 0)
            if it0 and not it0.data(Qt.ItemDataRole.UserRole) == "split" and it0.text() == str(p_num):
                cb = self.table.cellWidget(r, 3)
                if cb:
                    cb.blockSignals(True)
                    if cb.findText("Đang chờ...") != -1: cb.removeItem(cb.findText("Đang chờ..."))
                    cb.setCurrentText(ai_eval)
                    cb.blockSignals(False)
                    
                is_blank = (ai_eval == "Trang trắng")
                it0.setData(Qt.ItemDataRole.UserRole, "deleted" if is_blank else "normal")
                
                # Áp dụng màu cho UI trực tiếp khi quét
                color_hex = THEME['eval_colors'].get(ai_eval, "#FFFFFF")
                bg_brush = QBrush(QColor(color_hex))
                
                if is_blank:
                    if self.table.item(r, 1): self.table.item(r, 1).setText("-")
                    if self.table.item(r, 2): self.table.item(r, 2).setText("[Bỏ qua]")
                    for c in range(4): 
                        if self.table.item(r, c): self.table.item(r, c).setBackground(bg_brush)
                    if cb: cb.setStyleSheet(f"border: none; background-color: {color_hex}; color: #333333;")
                else:
                    for c in range(4): 
                        if self.table.item(r, c): self.table.item(r, c).setBackground(bg_brush)
                    if cb: cb.setStyleSheet(f"border: none; background: {color_hex}; color: #333333;")
                
                self.table.scrollToItem(it0)
                break

    def on_worker_finished(self):
        self.btn_start.setText("Bắt đầu")
        self.btn_start.setStyleSheet(f"background-color: {THEME['accent_green']}; color: white;") 
        self.table.setEnabled(True)
        self.progress_bar.setValue(0)
        self.btn_reload.setEnabled(True); self.btn_save_db.setEnabled(True)
        self.on_reload_from_db()

    def on_reload_from_db(self):
        if not self.current_md5: return
        success, db_data = db.get_split_data(self.current_md5)
        self.page_states = []
        if success:
            for p in sorted(db_data.keys()):
                self.page_states.append({"page": p, "eval": db_data[p]["Nhan_xet"]})
        self.auto_format_splits()
        self.add_log("Đã nạp lại dữ liệu từ CSDL.", "#2563eb")

    def on_save_db_manual(self):
        if not self.current_md5: return
        eval_dict = {}
        for state in self.page_states:
            if not state.get("is_split"):
                eval_dict[state["page"]] = state["eval"]
                
        if db.batch_update_split_evals(self.current_md5, eval_dict):
            self.add_log("Đã lưu trạng thái các trang vào CSDL.", "#10B981")
            QMessageBox.information(self, "Thành công", "Đã lưu CSDL!")
        else:
            QMessageBox.critical(self, "Lỗi", "Lỗi lưu CSDL!")

    def auto_format_splits(self, preserve_selection=None):
        new_states = []
        for i, item in enumerate(self.page_states):
            if item.get("is_split"): continue 
            
            ev = item.get("eval", "")
            if ev in ["1 trang", "Trang đầu"]:
                if not new_states or not new_states[-1].get("is_split"):
                    new_states.append({"is_split": True})
            
            new_states.append(item)
            
            if ev in ["1 trang", "Trang cuối"]:
                new_states.append({"is_split": True})

        cleaned_states = []
        for item in new_states:
            if item.get("is_split"):
                if not cleaned_states or cleaned_states[-1].get("is_split"): continue
            cleaned_states.append(item)
            
        if cleaned_states and cleaned_states[0].get("is_split"): cleaned_states.pop(0)
        if cleaned_states and cleaned_states[-1].get("is_split"): cleaned_states.pop()

        self.page_states = cleaned_states
        self.sync_ui_from_state(preserve_selection)

    def sync_ui_from_state(self, preserve_selection=None):
        self._is_updating_table = True
        
        # Lưu lại selection hiện tại nếu không được truyền vào
        if preserve_selection is None:
            preserve_selection = []
            for item in self.table.selectedItems():
                r = item.row()
                val = self.table.item(r, 0).text()
                if val.isdigit(): preserve_selection.append(int(val))

        self.table.setRowCount(0)
        
        base_name = os.path.splitext(os.path.basename(self.file_input.text()))[0]
        view_mode = self.combo_view_mode.currentIndex()
        doc_idx, child_idx = 1, 1
        
        for item in self.page_states:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            if item.get("is_split"):
                doc_idx += 1
                child_idx = 1 
                for c in range(4):
                    val = "X" if c == 0 else ""
                    it = QTableWidgetItem(val)
                    it.setBackground(QBrush(QColor(THEME['split_bg'])))
                    it.setForeground(QBrush(QColor("white")))
                    if c == 0: 
                        it.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                        it.setData(Qt.ItemDataRole.UserRole, "split")
                    self.table.setItem(row, c, it)
                self.table.setRowHidden(row, view_mode == 2 or view_mode == 3) # Chế độ 3 ẩn điểm ngắt
            else:
                p_num = item["page"]
                ev = item["eval"]
                is_blank = (ev == "Trang trắng")
                is_waiting = (ev == "Đang chờ...")
                
                it0 = QTableWidgetItem(str(p_num))
                it0.setData(Qt.ItemDataRole.UserRole, "deleted" if is_blank else "normal")
                it1 = QTableWidgetItem("")
                it2 = QTableWidgetItem("")
                it3 = QTableWidgetItem("")
                
                self.table.setItem(row, 0, it0)
                self.table.setItem(row, 1, it1)
                self.table.setItem(row, 2, it2)
                self.table.setItem(row, 3, it3)

                cb = QComboBox()
                cb_items = ["Trang trắng", "1 trang", "Trang đầu", "Trang tiếp", "Trang cuối"]
                if is_waiting: cb_items.append("Đang chờ...")
                cb.addItems(cb_items)
                cb.setCurrentText(ev)
                
                color_hex = THEME['eval_colors'].get(ev, "#FFFFFF")
                bg_brush = QBrush(QColor(color_hex))
                
                cb.setStyleSheet(f"border: none; background: {color_hex}; color: #333333;")
                cb.setProperty("page_num", p_num)
                cb.currentTextChanged.connect(self.on_combobox_changed)
                self.table.setCellWidget(row, 3, cb)
                
                if is_blank:
                    it1.setText("-"); it2.setText("[Bỏ qua]")
                    for c in range(4): 
                        if self.table.item(row, c): self.table.item(row, c).setBackground(bg_brush)
                    self.table.setRowHidden(row, view_mode == 1)
                else:
                    if is_waiting:
                        it1.setText(""); it2.setText("")
                    else:
                        it1.setText(str(child_idx)); it2.setText(f"{base_name}-Split-{doc_idx:03d}.pdf")
                        child_idx += 1
                    for c in range(4): 
                        if self.table.item(row, c): self.table.item(row, c).setBackground(bg_brush)
                    self.table.setRowHidden(row, view_mode == 2)
                    
                # Phục hồi Focus
                if p_num in preserve_selection:
                    for c in range(4): self.table.item(row, c).setSelected(True)

        self._is_updating_table = False
        has_split = any(i.get("is_split") for i in self.page_states)
        self.btn_execute.setEnabled(has_split)

    def on_combobox_changed(self, new_text):
        if self._is_updating_table: return
        cb = self.sender()
        p_num = cb.property("page_num")
        
        for item in self.page_states:
            if not item.get("is_split") and item.get("page") == p_num:
                item["eval"] = new_text
                break
        
        # Chỉ cập nhật State mảng tạm thời, không gọi DB
        # Focus sẽ được truyền giữ nguyên
        self.auto_format_splits([p_num])

    def handle_hotkeys(self, key_str):
        if self._is_updating_table: return
        selected_rows = sorted(list(set(item.row() for item in self.table.selectedItems())))
        if not selected_rows: return
        
        # Lấy trang đích để focus lại sau khi thay đổi (chống trôi vệt sáng)
        target_pages = []
        for r in selected_rows:
            val = self.table.item(r, 0).text()
            if val.isdigit(): target_pages.append(int(val))
        
        changed = False
        
        if key_str == "SPACE":
            for r in selected_rows:
                if not self.page_states[r].get("is_split"):
                    p_num = self.page_states[r]["page"]
                    curr_eval = self.page_states[r]["eval"]
                    new_val = "1 trang" if curr_eval == "Trang trắng" else "Trang trắng"
                    self._update_state_from_hotkey(p_num, new_val)
                    changed = True
                    
        elif key_str == "ENTER":
            r = selected_rows[0]
            if self.page_states[r].get("is_split"):
                self.page_states.pop(r) 
            else:
                self.page_states.insert(r, {"is_split": True}) 
            self.sync_ui_from_state(target_pages) 
            return

        elif key_str == "X":
            if len(selected_rows) > 1: 
                normal_rows = [r for r in selected_rows if not self.page_states[r].get("is_split")]
                if normal_rows:
                    for i, r in enumerate(normal_rows):
                        if i == 0: new_val = "Trang đầu"
                        elif i == len(normal_rows) - 1: new_val = "Trang cuối"
                        else: new_val = "Trang tiếp"
                        self._update_state_from_hotkey(self.page_states[r]["page"], new_val)
                    
                    min_idx, max_idx = min(normal_rows), max(normal_rows)
                    new_states = []
                    for i, item in enumerate(self.page_states):
                        if item.get("is_split") and min_idx < i < max_idx: continue
                        new_states.append(item)
                    self.page_states = new_states
                    changed = True
            else:
                r = selected_rows[0]
                if not self.page_states[r].get("is_split"):
                    self._update_state_from_hotkey(self.page_states[r]["page"], "1 trang")
                    changed = True

        elif key_str in ["A", "S", "Z"]:
            val_map = {"A": "Trang đầu", "S": "Trang tiếp", "Z": "Trang cuối"}
            for r in selected_rows:
                if not self.page_states[r].get("is_split"):
                    self._update_state_from_hotkey(self.page_states[r]["page"], val_map[key_str])
                    changed = True

        if changed: self.auto_format_splits(target_pages)

    def _update_state_from_hotkey(self, p_num, new_eval):
        for item in self.page_states:
            if not item.get("is_split") and item.get("page") == p_num:
                item["eval"] = new_eval
                break

    def on_table_select(self):
        selected = self.table.selectedItems()
        if not selected: return
        
        row = selected[0].row()
        page_str = self.table.item(row, 0).text()
        
        if page_str == 'X':
            self.preview_label.set_image(None)
            self.preview_label.setText("✂️\nĐIỂM NGẮT TÀI LIỆU")
            font = self.preview_label.font()
            font.setPointSize(20); font.setBold(True)
            self.preview_label.setFont(font)
            self.preview_label.setStyleSheet(f"background-color: #f8fafc; border: 1px solid {THEME['border_color']}; color: {THEME['split_bg']};")
        elif page_str.isdigit():
            font = self.preview_label.font()
            font.setPointSize(14); font.setBold(False)
            self.preview_label.setFont(font)
            self.preview_label.setStyleSheet(f"background-color: #f8fafc; border: 1px solid {THEME['border_color']}; color: #999;")
            
            page_num = int(page_str)
            thumb_path = os.path.join(TEMP_DIR, f"split_scan_{self.current_md5}_{page_num}.jpg")
            if os.path.exists(thumb_path):
                self.preview_label.set_image(QPixmap(thumb_path))

    def execute_cut(self):
        pdf_path = self.file_input.text()
        dest_path = self.dest_input.text()
        if not os.path.exists(pdf_path) or not os.path.exists(dest_path):
            QMessageBox.warning(self, "Lỗi", "Vui lòng kiểm tra file nguồn và đích!")
            return

        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        blocks = []
        current_pages = []
        doc_idx = 1
        
        for item in self.page_states:
            if item.get("is_split"):
                if current_pages: 
                    blocks.append((current_pages, f"{base_name}-Split-{doc_idx:03d}.pdf"))
                    doc_idx += 1
                current_pages = []
            else:
                if item.get("eval") == "Trang trắng": continue 
                current_pages.append(item["page"])
        
        if current_pages: 
            blocks.append((current_pages, f"{base_name}-Split-{doc_idx:03d}.pdf"))
            
        if not blocks: return

        # Khi người dùng chốt phương án cắt, ta mới ngầm save lên CSDL
        self.on_save_db_manual()

        self.table.setEnabled(False) 
        self.btn_start.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.add_log("Bắt đầu tiến trình cắt file...")
        
        self.cut_thread = CutPdfWorker(self.logic, pdf_path, blocks, dest_path)
        self.cut_thread.finished_signal.connect(self.on_cut_finished)
        self.cut_thread.start()

    def on_cut_finished(self, success, results):
        self.table.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_execute.setEnabled(True)
        
        if success:
            for f in results: self.add_log(f"-> Đã tạo: {os.path.basename(f)}", "#10B981")
            QMessageBox.information(self, "Hoàn tất", f"Đã tách xong {len(results)} tập tin!")
        else:
            self.add_log(f"[LỖI CẮT FILE]: {results}", "#ef4444")