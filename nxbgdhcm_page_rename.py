import os
import time
import re
import copy
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QComboBox, QProgressBar, QTextEdit, QSpacerItem, QSizePolicy, 
                             QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont, QKeyEvent

from nxbgdhcm_db_manager import db
from nxbgdhcm_ui_utils import setup_shared_ai_combobox, THEME, TestConnectionWorker

# LỚP MỚI: BẮT SỰ KIỆN PHÍM SPACE TRÊN BẢNG
class CustomRenameTableWidget(QTableWidget):
    space_pressed = pyqtSignal() 
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            self.space_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

class FolderCheckWorker(QThread):
    finished_signal = pyqtSignal(bool, list, str) 

    def __init__(self, logic, folder_path):
        super().__init__()
        self.logic = logic
        self.folder_path = folder_path
        self.task_key = "rename"

    def run(self):
        files = self.logic.get_all_target_files(self.folder_path)
        if isinstance(files, str):
            self.finished_signal.emit(False, [], f"Lỗi đọc thư mục: {files}"); return
            
        if not files:
            self.finished_signal.emit(False, [], "Thư mục trống hoặc không chứa định dạng hỗ trợ."); return

        md5_list = []
        file_map = {}
        for f in files:
            if not self.logic.is_running(self.task_key): 
                self.finished_signal.emit(False, [], "Đã hủy bởi người dùng."); return
                
            md5_val = self.logic.calculate_md5(f)
            if md5_val:
                md5_list.append(md5_val)
                file_map[md5_val] = f

        all_exist = db.check_folder_files_in_db(md5_list)
        if not all_exist:
            self.finished_signal.emit(False, [], "Phát hiện tập tin CHƯA ĐƯỢC SỐ HÓA.\nVui lòng quay lại 'Trang 1: Số hóa tài liệu' để quét thư mục này trước khi đổi tên.")
            return

        self.finished_signal.emit(True, list(file_map.items()), "Hợp lệ")

class AIGenerateNameWorker(QThread):
    row_update_signal = pyqtSignal(str, str, str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal()

    def __init__(self, logic, states_to_process, template, db_metadata, ai_config):
        super().__init__()
        self.logic = logic
        self.states_to_process = states_to_process
        self.template = template
        self.db_metadata = db_metadata
        self.ai_config = ai_config
        self.task_key = "rename"

    def run(self):
        total = len(self.states_to_process)
        for i, state in enumerate(self.states_to_process):
            if not self.logic.is_running(self.task_key): break
            
            md5 = state['md5']
            if md5 not in self.db_metadata: continue
            
            meta = self.db_metadata[md5]['meta']
            summary = self.db_metadata[md5]['summary']
            rejected = state.get('rejected_names', [])
            
            prompt = self.logic.get_prompt_rename(self.template, meta, summary, state['ext'], rejected)
            
            new_name = ""
            err_msg = ""
            for attempt in range(3):
                if not self.logic.is_running(self.task_key): break
                raw_resp = ""
                gen = self.logic.call_ai_stream_generator(self.ai_config['URL'], self.ai_config['Model_Name'], self.ai_config['API_Key'], prompt, task_key=self.task_key)
                for c in gen: 
                    if not self.logic.is_running(self.task_key): break
                    raw_resp += c

                json_data = self.logic.extract_json(raw_resp)
                if json_data and "Tên mới" in json_data:
                    new_name = str(json_data["Tên mới"]).strip()
                    break
                else:
                    time.sleep(1)
            
            if not new_name: 
                err_msg = "AI không phản hồi định dạng chuẩn"
            else:
                new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
                if not new_name.lower().endswith(state['ext'].lower()):
                    new_name = os.path.splitext(new_name)[0] + state['ext'].lower()
                    
            self.row_update_signal.emit(md5, new_name, err_msg)
            self.progress_signal.emit(i+1, total)

        self.finished_signal.emit()

class ExecuteRenameWorker(QThread):
    finished_signal = pyqtSignal(int, list) 
    row_updated_signal = pyqtSignal(str, str, str, str)
    
    def __init__(self, accepted_states):
        super().__init__()
        self.accepted_states = copy.deepcopy(accepted_states)
        
    def run(self):
        success_count = 0
        error_msgs = []
        for state in self.accepted_states:
            old_path = state['path']
            dir_path = os.path.dirname(old_path)
            new_path = os.path.join(dir_path, state['new_name'])
            
            if os.path.exists(new_path):
                self.row_updated_signal.emit(state['md5'], 'error', "Tên mới đã tồn tại", "")
                error_msgs.append(f"{state['old_name']} -> Trùng tên")
                continue
                
            try:
                os.rename(old_path, new_path)
                db_ok = db.update_filename_and_history(state['md5'], state['old_name'], state['new_name'], dir_path)
                if db_ok:
                    self.row_updated_signal.emit(state['md5'], 'success', "", new_path)
                    success_count += 1
                else:
                    self.row_updated_signal.emit(state['md5'], 'error', "Lỗi lưu Database", "")
                    error_msgs.append(f"{state['old_name']} -> Lỗi DB")
            except Exception as e:
                self.row_updated_signal.emit(state['md5'], 'error', str(e), "")
                error_msgs.append(f"{state['old_name']} -> Lỗi OS")
                
        self.finished_signal.emit(success_count, error_msgs)

class PageRename(QWidget):
    def __init__(self, parent_main, shared_logic):
        super().__init__()
        self.parent_main = parent_main
        self.logic = shared_logic
        self.file_states = [] 
        self.cached_db_metadata = {} 
        self._is_updating = False
        self.task_key = "rename"
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        header_lbl = QLabel("ĐỔI TÊN TẬP TIN BẰNG A.I", styleSheet=f"background-color: {THEME['header_bg']}; color: {THEME['text_dark']}; font-size: 20px; font-weight: bold; padding: 10px; border: 1px solid {THEME['border_color']}; border-radius: 4px;")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header_lbl)

        row1 = QHBoxLayout(); row1.setSpacing(5)
        self.path_input = QLineEdit("Hãy bấm nút Duyệt để chọn thư mục."); self.path_input.setReadOnly(True)
        self.btn_chon_thu_muc = QPushButton("Duyệt..")
        self.btn_chon_thu_muc.setObjectName("ToolbarBtn")
        self.btn_chon_thu_muc.clicked.connect(self.on_chon_thu_muc)
        row1.addWidget(self.path_input, 1); row1.addWidget(self.btn_chon_thu_muc)
        self.main_layout.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(5)
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("Nhập cấu trúc tên file (Ví dụ: [Loại văn bản] - [Tên ngắn gọn] - [Năm]). Để trống AI sẽ tự đặt.")
        self.combo_server = QComboBox()
        self.btn_start = QPushButton("🚀 Bắt đầu Quét")
        self.btn_start.setObjectName("BtnBatDau"); self.btn_start.setFixedWidth(150)
        self.btn_start.clicked.connect(self.on_start)
        
        row2.addWidget(QLabel("Tên mẫu:")); row2.addWidget(self.template_input, 1)
        row2.addWidget(QLabel(" Server AI:")); row2.addWidget(self.combo_server); row2.addWidget(self.btn_start)
        self.main_layout.addLayout(row2)

        self.progress_bar = QProgressBar(); self.progress_bar.setFixedHeight(15); self.progress_bar.setValue(0); self.progress_bar.setTextVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        row3 = QHBoxLayout(); row3.setSpacing(5)
        self.lbl_status = QLabel("Chưa tải thư mục.", styleSheet="color: #2563eb; font-weight: bold;")
        self.btn_retry = QPushButton("🔄 Đặt tên lại"); self.btn_retry.setObjectName("ToolbarBtn"); self.btn_retry.setEnabled(False)
        self.btn_execute = QPushButton("💾 Đổi tên file (OS)"); self.btn_execute.setObjectName("BtnBatDau"); self.btn_execute.setEnabled(False)
        
        self.btn_retry.clicked.connect(self.on_retry_names)
        self.btn_execute.clicked.connect(self.on_execute_os_rename)
        
        row3.addWidget(self.lbl_status); row3.addStretch()
        row3.addWidget(self.btn_retry); row3.addWidget(self.btn_execute)
        self.main_layout.addLayout(row3)

        self.table = CustomRenameTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Tên cũ", "Tên mới (AI)", "Loại văn bản", "Loại file", "Diễn giải (Tóm tắt)", "Đồng ý"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 200); self.table.setColumnWidth(1, 200); self.table.setColumnWidth(2, 120); self.table.setColumnWidth(3, 80); self.table.setColumnWidth(5, 80)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True) 
        self.table.space_pressed.connect(self.on_space_pressed) # Lắng nghe phím Space
        
        self.main_layout.addWidget(self.table, 1)

    def load_ai_presets(self):
        setup_shared_ai_combobox(self.combo_server, store_full_dict=False)

    def on_chon_thu_muc(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục đổi tên")
        if folder: self.path_input.setText(os.path.normpath(folder))

    def on_start(self):
        folder_path = self.path_input.text()
        if not os.path.exists(folder_path) or folder_path.startswith("Hãy bấm"):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thư mục hợp lệ!"); return

        if self.logic.is_running(self.task_key):
            self.logic.set_running_state(self.task_key, False)
            self.btn_start.setText("Đang Dừng...")
            return

        self.btn_start.setText("🛑 Dừng"); self.btn_start.setStyleSheet(f"background-color: {THEME['accent_red']}; color: white;")
        
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self.table.setSortingEnabled(True)
        
        self.file_states = []
        self.cached_db_metadata = {}
        self.btn_retry.setEnabled(False); self.btn_execute.setEnabled(False)
        self.lbl_status.setText("Đang quét và kiểm tra CSDL...")
        self.progress_bar.setValue(0)
        
        self.logic.set_running_state(self.task_key, True)
        
        self.check_worker = FolderCheckWorker(self.logic, folder_path)
        self.check_worker.finished_signal.connect(self.on_folder_checked)
        self.check_worker.start()

    def on_folder_checked(self, is_valid, file_map, msg):
        if not self.logic.is_running(self.task_key): 
            self._reset_ui()
            self.lbl_status.setText(msg); return
            
        if not is_valid:
            self.logic.set_running_state(self.task_key, False); self._reset_ui()
            QMessageBox.critical(self, "Từ chối", msg)
            self.lbl_status.setText(msg); return

        md5_list = [m for m, p in file_map]
        self.cached_db_metadata = db.get_metadata_for_rename(md5_list)
        
        for md5, path in file_map:
            ext = os.path.splitext(path)[1]
            old_name = os.path.basename(path)
            doc_type = self.cached_db_metadata.get(md5, {}).get('meta', {}).get('Loại văn bản', '')
            self.file_states.append({
                'md5': md5, 'path': path, 'old_name': old_name, 'new_name': '', 'ext': ext,
                'doc_type': doc_type,
                'summary': self.cached_db_metadata.get(md5, {}).get('summary', ''), 'status': 'waiting',
                'error_msg': '', 'rejected_names': []
            })
            
        self.lbl_status.setText(f"Bắt đầu nhờ AI đặt tên cho {len(self.file_states)} file...")
        self.full_sync_table() # Dựng bảng trống ngay lúc đầu để User nhìn thấy
        self.run_ai_worker(self.file_states, self.cached_db_metadata)

    def run_ai_worker(self, states_to_process, db_metadata):
        preset_id = self.combo_server.currentData()
        config = db.get_ai_config_by_id(preset_id)
        template = self.template_input.text()
        
        self.ai_worker = AIGenerateNameWorker(self.logic, states_to_process, template, db_metadata, config)
        self.ai_worker.row_update_signal.connect(self.on_ai_name_generated)
        self.ai_worker.progress_signal.connect(lambda c, t: self.progress_bar.setValue(int((c/t)*100)))
        self.ai_worker.finished_signal.connect(self.on_ai_finished)
        self.ai_worker.start()

    def on_ai_name_generated(self, md5, new_name, err_msg):
        target_state = None
        for state in self.file_states:
            if state['md5'] == md5:
                if err_msg:
                    state['status'] = 'error'; state['error_msg'] = err_msg
                else:
                    state['status'] = 'ai_done'; state['new_name'] = new_name
                target_state = state
                break
                
        # FIX: CHỈ UPDATE ĐÚNG DÒNG ĐÓ, KHÔNG LOAD LẠI BẢNG GÂY GIẬT LAG UI
        if target_state:
            for r in range(self.table.rowCount()):
                w = self.table.cellWidget(r, 5)
                if w:
                    chk = w.findChild(QCheckBox)
                    if chk and chk.property("md5") == md5:
                        self.apply_style_to_row(r, target_state)
                        break
        self.check_button_states()

    def on_ai_finished(self):
        self.logic.set_running_state(self.task_key, False)
        self._reset_ui()
        self.lbl_status.setText("Đã hoàn tất gọi AI.")

    def _reset_ui(self):
        self.btn_start.setText("🚀 Bắt đầu Quét")
        self.btn_start.setStyleSheet(f"background-color: {THEME['accent_green']}; color: white;")
        self.progress_bar.setValue(0)

    def on_retry_names(self):
        if self.logic.is_running(self.task_key): return
        self.logic.set_running_state(self.task_key, True)
        self.btn_start.setText("🛑 Dừng"); self.btn_start.setStyleSheet(f"background-color: {THEME['accent_red']}; color: white;")
        
        states_to_process = []
        for state in self.file_states:
            if state['status'] in ['ai_done', 'error', 'waiting']:
                if state['new_name']: state['rejected_names'].append(state['new_name'])
                state['status'] = 'waiting'
                states_to_process.append(state)
        
        if not states_to_process:
            self.logic.set_running_state(self.task_key, False); self._reset_ui(); return
            
        self.lbl_status.setText(f"Đang đặt tên lại cho {len(states_to_process)} file...")
        self.full_sync_table() # Đẩy các row bị gỡ "accepted" lên trên
        self.run_ai_worker(states_to_process, self.cached_db_metadata)

    def on_execute_os_rename(self):
        accepted_states = [s for s in self.file_states if s['status'] == 'accepted']
        if not accepted_states: return
        
        msg_box = QMessageBox.question(self, "Xác nhận", f"Bạn sắp đổi tên hệ thống cho {len(accepted_states)} tập tin.\nViệc này không thể hoàn tác trên Win. Tiếp tục?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if msg_box == QMessageBox.StandardButton.No: return

        self.btn_execute.setEnabled(False)
        self.btn_retry.setEnabled(False)
        self.lbl_status.setText(f"Đang đổi tên trong OS và nạp CSDL...")
        
        self.rename_worker = ExecuteRenameWorker(accepted_states)
        self.rename_worker.row_updated_signal.connect(self.on_single_rename_done)
        self.rename_worker.finished_signal.connect(self.on_all_rename_done)
        self.rename_worker.start()

    def on_single_rename_done(self, md5, status, error_msg, new_path):
        target_state = None
        for state in self.file_states:
            if state['md5'] == md5:
                state['status'] = status
                if status == 'success':
                    state['path'] = new_path
                    state['old_name'] = state['new_name']
                else:
                    state['error_msg'] = error_msg
                target_state = state
                break
                
        if target_state:
            for r in range(self.table.rowCount()):
                w = self.table.cellWidget(r, 5)
                if w:
                    chk = w.findChild(QCheckBox)
                    if chk and chk.property("md5") == md5:
                        self.apply_style_to_row(r, target_state)
                        break

    def on_all_rename_done(self, success_count, error_msgs):
        self.full_sync_table()
        err_str = f"\nLỗi {len(error_msgs)} file:\n" + "\n".join(error_msgs[:5]) + ("\n..." if len(error_msgs)>5 else "") if error_msgs else ""
        self.lbl_status.setText(f"Hoàn tất. Thành công: {success_count}.")
        QMessageBox.information(self, "Báo cáo Đổi Tên", f"Thành công: {success_count} tập tin.{err_str}")

    def apply_style_to_row(self, r, state):
        it_old = self.table.item(r, 0)
        it_new = self.table.item(r, 1)
        it_doc = self.table.item(r, 2)
        it_ext = self.table.item(r, 3)
        it_sum = self.table.item(r, 4)
        list_items = [it_old, it_new, it_doc, it_ext, it_sum]
        
        w = self.table.cellWidget(r, 5)
        chk = w.findChild(QCheckBox) if w else None
        
        it_old.setText(state['old_name'])
        if state['status'] == 'waiting': it_new.setText("[Đang chờ AI...]")
        else: it_new.setText(state['new_name'] if state['status'] != 'error' else state['error_msg'])
        
        if state['status'] == 'success':
            if chk: chk.setEnabled(False)
            it_new.setText("ĐÃ ĐỔI TÊN XONG")
            bg_color = QColor(THEME['row_success'])
            txt_color = QColor(THEME['text_success'])
            font = QFont(); font.setBold(False)
            for it in list_items:
                it.setBackground(QBrush(bg_color)); it.setForeground(QBrush(txt_color)); it.setFont(font)
        else:
            if state['status'] == 'accepted':
                bg_color = QColor(THEME['row_accepted'])
                txt_color = QColor(THEME['text_dark'])
                font = QFont(); font.setBold(True)
            else:
                bg_color = QColor("#FFFFFF")
                txt_color = QColor(THEME['text_dark'])
                font = QFont(); font.setBold(False)
                
            if state['status'] == 'error':
                it_new.setForeground(QBrush(QColor(THEME['accent_red'])))
                
            for it in list_items:
                it.setBackground(QBrush(bg_color)); it.setFont(font)
                if state['status'] != 'error' or it != it_new: it.setForeground(QBrush(txt_color))

    def full_sync_table(self):
        self._is_updating = True
        
        def sort_key(s):
            if s['status'] == 'success': return 3
            if s['status'] == 'accepted': return 2
            return 1
        self.file_states.sort(key=sort_key)
        
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        for i, state in enumerate(self.file_states):
            self.table.insertRow(i)
            
            it_old = QTableWidgetItem()
            it_new = QTableWidgetItem()
            it_doc_type = QTableWidgetItem(state['doc_type'])
            it_ext = QTableWidgetItem(state['ext'])
            it_sum = QTableWidgetItem(state['summary'])
            
            chk_widget = QWidget(); chk_layout = QHBoxLayout(chk_widget); chk_layout.setContentsMargins(0,0,0,0); chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setProperty("md5", state['md5'])
            chk_layout.addWidget(chk)
            
            self.table.setItem(i, 0, it_old); self.table.setItem(i, 1, it_new)
            self.table.setItem(i, 2, it_doc_type); self.table.setItem(i, 3, it_ext)
            self.table.setItem(i, 4, it_sum); self.table.setCellWidget(i, 5, chk_widget)
            
            self.apply_style_to_row(i, state)
            
            chk.setChecked(state['status'] == 'accepted')
            chk.stateChanged.connect(self.on_check_changed)

        self.table.setSortingEnabled(True) 
        self.check_button_states()
        self._is_updating = False

    def on_check_changed(self):
        if self._is_updating: return
        chk = self.sender()
        md5 = chk.property("md5")
        
        target_state = None
        for state in self.file_states:
            if state['md5'] == md5 and state['status'] not in ['success', 'waiting']:
                target_state = state
                target_state['status'] = 'accepted' if chk.isChecked() else 'ai_done'
                break
                
        if target_state:
            for r in range(self.table.rowCount()):
                w = self.table.cellWidget(r, 5)
                if w:
                    c = w.findChild(QCheckBox)
                    if c and c.property("md5") == md5:
                        self.apply_style_to_row(r, target_state)
                        break
        self.check_button_states()

    # FIX LỖI 5: Nhanh chóng tick "Đồng ý" cho nhiều dòng bằng phím Space
    def on_space_pressed(self):
        if self._is_updating: return
        selected_rows = sorted(list(set(item.row() for item in self.table.selectedItems())))
        if not selected_rows: return
        
        self._is_updating = True
        
        for r in selected_rows:
            w = self.table.cellWidget(r, 5)
            if w:
                chk = w.findChild(QCheckBox)
                if chk and chk.isEnabled():
                    # Đảo ngược trạng thái Checkbox
                    new_chk_state = not chk.isChecked()
                    chk.setChecked(new_chk_state)
                    
                    md5 = chk.property("md5")
                    target_state = None
                    for state in self.file_states:
                        if state['md5'] == md5 and state['status'] not in ['success', 'waiting']:
                            target_state = state
                            target_state['status'] = 'accepted' if new_chk_state else 'ai_done'
                            break
                            
                    if target_state: self.apply_style_to_row(r, target_state)
                    
        self._is_updating = False
        self.check_button_states()

    def check_button_states(self):
        has_accepted = any(s['status'] == 'accepted' for s in self.file_states)
        has_pending = any(s['status'] in ['ai_done', 'error'] for s in self.file_states)
        self.btn_execute.setEnabled(has_accepted)
        self.btn_retry.setEnabled(has_pending)