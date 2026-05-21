import os
import time
import base64
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QApplication, QProgressBar, QTextEdit, QSpacerItem, QSizePolicy, QSplitter, QFileDialog, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor, QPixmap

from nxbgdhcm_db_manager import db
from nxbgdhcm_core_logic import TEMP_DIR
from nxbgdhcm_ui_utils import setup_shared_ai_combobox, THEME, TestConnectionWorker

class ProcessingThread(QThread):
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int, str)
    preview_signal = pyqtSignal(str, str)
    stream_signal = pyqtSignal(str, bool)
    finished_signal = pyqtSignal()

    def __init__(self, logic, folder_path, preset_config):
        super().__init__()
        self.logic = logic; self.folder_path = folder_path; self.preset_config = preset_config
        self.task_key = "ocr"

    def run(self):
        try: import pythoncom; pythoncom.CoInitialize()
        except: pass
        
        doc_types_str = db.get_document_types_string()
        prompt_page_1 = self.logic.get_prompt_page_1(doc_types_str)
        prompt_page_n = self.logic.get_prompt_page_n()

        ext_pdf = ['.pdf']
        ext_img = ['.jpg', '.jpeg', '.png', '.bmp', '.heic', '.heif']
        ext_doc = ['.txt', '.csv', '.xml', '.py', '.rtf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']

        files = self.logic.get_all_target_files(self.folder_path)
        if isinstance(files, str):
            self.log_signal.emit(f"Lỗi truy cập: {files}", THEME['log_error']); self.finished_signal.emit(); return
            
        total_files = len(files)
        self.log_signal.emit(f"[QUET] Phân tích tìm thấy {total_files} tập tin hợp lệ.", THEME['log_info'])
        
        file_data = []
        for i, filepath in enumerate(files):
            if not self.logic.is_running(self.task_key): break
            filename = os.path.basename(filepath)
            md5_val = self.logic.calculate_md5(filepath)
            if md5_val: file_data.append({"path": filepath, "name": filename, "md5": md5_val})
            self.progress_signal.emit(i+1, total_files, "Đang tính MD5...")
            
        if not self.logic.is_running(self.task_key):
            self.finished_signal.emit()
            return
            
        self.log_signal.emit("[THANH CONG] Quét MD5 hoàn tất. Bắt đầu trích xuất!", THEME['log_success'])
        
        success_count, skip_count = 0, 0
        failed_files = []

        def process_files_list(files_list, is_retry=False):
            nonlocal success_count, skip_count
            for data in files_list:
                if not self.logic.is_running(self.task_key): break
                filepath, filename, file_md5 = data["path"], data["name"], data["md5"]
                ext = os.path.splitext(filename)[1].lower()
                file_type_str = ext.replace(".", "").upper()
                
                curr_prog = success_count + skip_count
                prog_str = f"{curr_prog+1}/{total_files}"
                
                self.log_signal.emit(f"\n{'='*40}", THEME['log_system'])
                self.log_signal.emit(f"[FILE] Đang xử lý {'(LẦN CUỐI)' if is_retry else ''}: {filename} [{prog_str}]", THEME['log_system'])
                self.progress_signal.emit(curr_prog+1, total_files, filename)
                self.preview_signal.emit(filepath, ext)

                status, msg = db.check_file_md5_exists(file_md5, filepath, filename)
                if not is_retry and status:
                    self.log_signal.emit(f"[SKIP] Đã có trong Database. Bỏ qua AI.", THEME['log_success'])
                    skip_count += 1; continue

                meta = {"Loại văn bản": "", "Số văn bản": "", "Ngày": "", "Tháng": "", "Năm": "", "Đơn vị soạn văn bản": "", "Người ký": ""}
                has_err = False
                temp_text_buf = os.path.join(TEMP_DIR, f"buf_{file_md5}.txt")
                with open(temp_text_buf, "w", encoding="utf-8") as f: f.write("")

                if ext in ext_doc:
                    self.log_signal.emit(f"-> Đang bóc tách Text trực tiếp (Không dùng AI Vision)...", THEME['log_text_mode'])
                    extracted_text = self.logic.extract_text_from_file(filepath, ext)
                    
                    if extracted_text is None:
                        self.log_signal.emit(f"[LOI] Python không thể đọc file này.", THEME['log_error'])
                        has_err = True
                    else:
                        text_for_ai = extracted_text[:3500] 
                        prompt = self.logic.get_prompt_text_metadata(doc_types_str, text_for_ai)
                        
                        ai_json_data = None
                        for attempt in range(3):
                            if not self.logic.is_running(self.task_key): break
                            self.log_signal.emit(f"  -> Gửi Text cho AI phân tích Metadata (Lần {attempt+1})", THEME['log_text_mode'])
                            self.stream_signal.emit(f"\n[A.I] Đang nội suy Metadata (Lần {attempt+1})...\n", True)
                            
                            raw_ai_text = ""
                            gen = self.logic.call_ai_chat_stream_generator(self.preset_config['URL'], self.preset_config['Model_Name'], self.preset_config['API_Key'], [{"role": "user", "content": prompt}], task_key=self.task_key)
                            for c in gen:
                                if not self.logic.is_running(self.task_key): break
                                raw_ai_text += c; self.stream_signal.emit(c, False)

                            ai_json_data = self.logic.extract_json(raw_ai_text, is_page_1=True) 
                            if ai_json_data:
                                self.log_signal.emit(f"     [THANH CONG] Đã lấy được Metadata!", THEME['log_success']); break
                            else:
                                self.log_signal.emit(f"     [CANH BAO] JSON hỏng, đang thử lại...", THEME['log_warning']); time.sleep(1)

                        if ai_json_data:
                            for k in ["Loại văn bản", "Số văn bản", "Ngày", "Tháng", "Năm", "Đơn vị soạn văn bản", "Người ký"]:
                                if ai_json_data.get(k): meta[k] = str(ai_json_data.get(k, "")).strip()
                        else:
                            self.log_signal.emit(f"[CANH BAO] AI không chốt được Metadata. Vẫn lưu Full Text.", THEME['log_warning'])

                        with open(temp_text_buf, "w", encoding="utf-8") as f_buf:
                            f_buf.write(extracted_text)

                else:
                    is_pdf = (ext in ext_pdf)
                    total_p = self.logic.get_pdf_page_count(filepath) if is_pdf else 1
                    
                    for p_num in range(1, total_p + 1):
                        if not self.logic.is_running(self.task_key): break
                        
                        tmp_img = os.path.join(TEMP_DIR, f"ocr_scan_{file_md5}_{p_num}.jpg")
                        img_ok = False
                        
                        if is_pdf: img_ok = self.logic.render_pdf_page_to_image(filepath, p_num, tmp_img)
                        else: img_ok = self.logic.resize_image_for_ai(filepath, tmp_img)

                        if not img_ok:
                            self.log_signal.emit(f"[CANH BAO] Lỗi chụp ảnh trang {p_num}", THEME['log_error'])
                            has_err = True; continue
                            
                        self.preview_signal.emit(tmp_img, '.jpg') 
                        with open(tmp_img, "rb") as f_img: b64_img = base64.b64encode(f_img.read()).decode('utf-8')
                        
                        ai_json_data = None
                        for attempt in range(3):
                            if not self.logic.is_running(self.task_key): break
                            self.log_signal.emit(f"  -> Gửi AI Vision Trang {p_num}/{total_p} (Thử lần {attempt+1})", THEME['log_image_mode'])
                            
                            prompt = prompt_page_1 if p_num == 1 else prompt_page_n
                            self.stream_signal.emit(f"\n[A.I] Đang phân tích Ảnh Trang {p_num} (Lần {attempt+1})...\n", True)
                            
                            raw_ai_text = ""
                            gen = self.logic.call_ai_stream_generator(self.preset_config['URL'], self.preset_config['Model_Name'], self.preset_config['API_Key'], prompt, b64_img, task_key=self.task_key)
                            for c in gen:
                                if not self.logic.is_running(self.task_key): break
                                raw_ai_text += c; self.stream_signal.emit(c, False)

                            ai_json_data = self.logic.extract_json(raw_ai_text, is_page_1=(p_num == 1))
                            if ai_json_data:
                                self.log_signal.emit(f"     [THANH CONG] Dữ liệu trang {p_num} OK!", THEME['log_success']); break
                            else:
                                self.log_signal.emit(f"     [CANH BAO] Dữ liệu hỏng, đang thử lại...", THEME['log_warning']); time.sleep(1)

                        with open(temp_text_buf, "a", encoding="utf-8") as f_buf:
                            if ai_json_data:
                                for k in ["Loại văn bản", "Số văn bản", "Ngày", "Tháng", "Năm", "Đơn vị soạn văn bản"]:
                                    if not meta.get(k) and ai_json_data.get(k): meta[k] = str(ai_json_data.get(k, "")).strip()
                                meta["Người ký"] = self.logic.merge_signers(meta.get("Người ký", ""), str(ai_json_data.get("Người ký", "")).strip())
                                f_buf.write(f"--- TRANG {p_num} ---\n{ai_json_data.get('Toàn văn', '[AI TRỐNG]')}\n\n")
                            else:
                                self.log_signal.emit(f"     [LOI] AI từ chối trang {p_num}.", THEME['log_error'])
                                has_err = True; f_buf.write(f"--- TRANG {p_num} ---\n[LỖI TỪ CHỐI]\n\n")

                        try: os.remove(tmp_img)
                        except: pass
                
                if not self.logic.is_running(self.task_key): break

                if has_err:
                    self.log_signal.emit("[CANH BAO] File lỗi AI hoặc không đọc được, đưa vào Hàng Chờ.", THEME['log_warning'])
                    if not is_retry: failed_files.append(data)
                else:
                    try:
                        with open(temp_text_buf, "r", encoding="utf-8") as f_buf: full_document_text = f_buf.read()
                        db.save_document(file_md5, filename, filepath, file_type_str, meta, full_document_text)
                        self.log_signal.emit("[THANH CONG] Đã nạp DB.", THEME['log_success'])
                        if not is_retry: success_count += 1
                    except Exception as e:
                        self.log_signal.emit(f"[LOI] Nạp DB: {e}", THEME['log_error'])
                try: os.remove(temp_text_buf)
                except: pass

        if self.logic.is_running(self.task_key): process_files_list(file_data)
        if failed_files and self.logic.is_running(self.task_key):
            self.log_signal.emit(f"\n[THONG BAO] Phát hiện file lỗi. Thử lại LẦN CUỐI!", THEME['log_warning'])
            process_files_list(failed_files, is_retry=True)

        if self.logic.is_running(self.task_key):
            self.log_signal.emit("\n[HOAN TAT] TOÀN BỘ QUÁ TRÌNH QUÉT.", THEME['log_success'])
        
        try: import pythoncom; pythoncom.CoUninitialize()
        except: pass
        self.finished_signal.emit()

class PageOCR(QWidget):
    def __init__(self, parent_main, shared_logic):
        super().__init__()
        self.parent_main = parent_main
        self.logic = shared_logic 
        self.task_key = "ocr" 
        self.worker_thread = None
        self.init_ui()
        self.init_backend()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        header_lbl = QLabel("SỐ HÓA TÀI LIỆU CỦA BẠN")
        header_lbl.setObjectName("MainHeader")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header_lbl)

        self.cols_splitter = QSplitter(Qt.Orientation.Horizontal)

        col1_widget = QWidget(); col1_layout = QVBoxLayout(col1_widget); col1_layout.setContentsMargins(0, 0, 0, 0); col1_layout.setSpacing(10)

        toolbar1 = QHBoxLayout(); toolbar1.setSpacing(5)
        # SỬA LỖI 1: Placeholder an toàn
        default_path = "Bấm vào nút Duyệt để chọn thư mục quét.."
        self.path_input = QLineEdit(default_path); self.path_input.setObjectName("PathInput")
        self.btn_chon_thu_muc = QPushButton("Duyệt..")
        self.btn_bat_dau = QPushButton("Bắt đầu")
        
        self.btn_chon_thu_muc.setObjectName("ToolbarBtn")
        self.btn_bat_dau.setObjectName("BtnBatDau")
        self.btn_chon_thu_muc.clicked.connect(self.on_chon_thu_muc)
        self.btn_bat_dau.clicked.connect(self.on_bat_dau_dung)

        toolbar1.addWidget(self.path_input, 1)
        toolbar1.addWidget(self.btn_chon_thu_muc)
        toolbar1.addWidget(self.btn_bat_dau)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(" Sẵn sàng...")
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        log_btns_layout = QHBoxLayout(); log_btns_layout.setSpacing(10)
        self.btn_luu_log = QPushButton("Lưu log"); self.btn_luu_error = QPushButton("Lưu Error")
        self.btn_luu_log.setObjectName("ToolbarBtn"); self.btn_luu_error.setObjectName("ToolbarBtn")
        self.btn_luu_log.clicked.connect(lambda: self.on_luu_file(False))
        self.btn_luu_error.clicked.connect(lambda: self.on_luu_file(True))
        log_btns_layout.addStretch(); log_btns_layout.addWidget(self.btn_luu_log); log_btns_layout.addWidget(self.btn_luu_error); log_btns_layout.addStretch()

        col1_layout.addLayout(toolbar1)
        col1_layout.addWidget(self.progress_bar)
        col1_layout.addWidget(self.log_text, 1)
        col1_layout.addLayout(log_btns_layout)
        self.cols_splitter.addWidget(col1_widget)

        col2_widget = QWidget(); col2_layout = QVBoxLayout(col2_widget); col2_layout.setContentsMargins(0, 0, 0, 0); col2_layout.setSpacing(10)
        spacer2 = QSpacerItem(20, 68, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        col2_layout.addItem(spacer2)
        
        self.analysis_view = QLabel("Khu vực hiển thị tài liệu")
        self.analysis_view.setObjectName("ImageReviewLabel")
        self.analysis_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.analysis_view.setWordWrap(True)
        col2_layout.addWidget(self.analysis_view, 1) 
        
        col2_layout.addItem(QSpacerItem(20, 32, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.cols_splitter.addWidget(col2_widget)

        col3_widget = QWidget(); col3_layout = QVBoxLayout(col3_widget); col3_layout.setContentsMargins(0, 0, 0, 0); col3_layout.setSpacing(10)

        toolbar3 = QHBoxLayout(); toolbar3.setSpacing(5)
        self.combo_server = QComboBox()
        self.btn_test_server = QPushButton("Test"); self.btn_test_server.setObjectName("ToolbarBtn")
        self.btn_test_server.clicked.connect(self.on_test_server_clicked)
        self.combo_server.currentIndexChanged.connect(self.on_combo_server_changed)

        toolbar3.addWidget(QLabel("Server:")); toolbar3.addWidget(self.combo_server, 1); toolbar3.addWidget(self.btn_test_server)
        spacer3 = QSpacerItem(20, 27, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.stream_text = QTextEdit(); self.stream_text.setReadOnly(True)
        self.stream_text.setStyleSheet("color: #2563eb; font-family: 'Consolas', monospace;") 

        col3_layout.addLayout(toolbar3); col3_layout.addItem(spacer3); col3_layout.addWidget(self.stream_text, 1)
        col3_layout.addItem(QSpacerItem(20, 32, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.cols_splitter.addWidget(col3_widget)

        self.cols_splitter.setSizes([600, 300, 300])
        self.main_layout.addWidget(self.cols_splitter, 1)

    def init_backend(self):
        setup_shared_ai_combobox(self.combo_server, store_full_dict=False)
        if self.combo_server.count() > 0:
            self.add_log(f"Đã tải {self.combo_server.count()} Server AI.", "#10B981")
        else:
            self.combo_server.addItem("Lỗi tải AI")

    def on_combo_server_changed(self):
        name = self.combo_server.currentText()
        self.add_log(f"Đã chọn A.I Server: {name}", "#2563eb")

    def add_log(self, text, color="black"):
        time_str = datetime.now().strftime("%H:%M:%S")
        bold_tag = "<b>" if text.startswith("[FILE]") or text.startswith("[SKIP]") else ""
        end_bold = "</b>" if bold_tag else ""
        self.log_text.append(f"<span style='color:{color};'>[{time_str}] {bold_tag}{text}{end_bold}</span>")

    def update_progress(self, current, total, filename):
        self.progress_bar.setValue(int((current/total)*100) if total > 0 else 0)
        self.progress_bar.setFormat(f" {current}/{total} | {filename}")

    def show_preview(self, filepath, ext):
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.heic', '.heif']:
            try:
                from PIL import Image
                img = Image.open(filepath).convert("RGBA")
                data = img.tobytes("raw", "RGBA")
                from PyQt6.QtGui import QImage
                qim = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qim)
                scaled = pixmap.scaled(self.analysis_view.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.analysis_view.setPixmap(scaled)
            except:
                self.analysis_view.setText("Không thể hiển thị bản xem trước ảnh.")
        else:
            self.analysis_view.clear()
            self.analysis_view.setText(f"📄 TÀI LIỆU VĂN BẢN\nĐang phân tích ngầm:\n\n{os.path.basename(filepath)}")

    def append_stream(self, text_chunk, is_clear=False):
        if is_clear: self.stream_text.clear()
        cursor = self.stream_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text_chunk)
        self.stream_text.setTextCursor(cursor)
        self.stream_text.ensureCursorVisible()

    def on_worker_finished(self):
        self.add_log("Tiến trình đã dừng lại/kết thúc.", "#db2777")
        self.btn_bat_dau.setText("Bắt đầu")
        self.btn_bat_dau.setStyleSheet("") 

    def on_chon_thu_muc(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục", os.path.expanduser("~"))
        if folder_path:
            self.path_input.setText(os.path.normpath(folder_path) + os.sep)
            self.add_log(f"Đã chọn thư mục: {folder_path}", "#2563eb")

    def on_luu_file(self, is_error=False):
        now_str = datetime.now().strftime("%y%m%d-%H%M%S")
        suffix = "error" if is_error else "logs"
        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu tập tin", f"{now_str}-NXB-{suffix}.txt", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f: f.write(self.log_text.toPlainText())

    def on_test_server_clicked(self):
        preset_id = self.combo_server.currentData()
        name = self.combo_server.currentText()
        if not preset_id: return
        
        self.btn_test_server.setEnabled(False)
        self.add_log(f"====== Gửi tín hiệu Test đến: {name} ======", "#2563eb")
        
        config = db.get_ai_config_by_id(preset_id)
        if config:
            self.test_thread = TestConnectionWorker(self.logic, config)
            self.test_thread.result_signal.connect(self.on_test_finished)
            self.test_thread.start()
        else:
            self.btn_test_server.setEnabled(True)

    def on_test_finished(self, success, msg):
        self.btn_test_server.setEnabled(True)
        if success: self.add_log(f"[AI Phản hồi]: {msg}", "#10B981")
        else: self.add_log(f"[LỖI]: {msg}", "#ef4444")

    def on_bat_dau_dung(self):
        folder_path = self.path_input.text()
        if folder_path.startswith("Bấm vào nút"): return
            
        if not os.path.exists(folder_path):
            self.add_log("Thư mục không tồn tại!", "#ef4444"); return

        is_running = self.logic.toggle_running_state(self.task_key)
        if is_running:
            self.btn_bat_dau.setText("Dừng")
            self.btn_bat_dau.setStyleSheet("background-color: #ef4444; border: 1px solid #dc2626; color: white;")
            
            preset_id = self.combo_server.currentData()
            config = db.get_ai_config_by_id(preset_id)
            if not config:
                self.add_log("Lỗi: Không tìm thấy AI Server!", "#ef4444"); self.on_bat_dau_dung(); return

            self.worker_thread = ProcessingThread(self.logic, folder_path, config)
            self.worker_thread.log_signal.connect(self.add_log)
            self.worker_thread.progress_signal.connect(self.update_progress)
            self.worker_thread.preview_signal.connect(self.show_preview)
            self.worker_thread.stream_signal.connect(self.append_stream)
            self.worker_thread.finished_signal.connect(self.on_worker_finished)
            self.worker_thread.start()
        else:
            self.add_log("Đang chờ hủy tiến trình...", "#db2777")