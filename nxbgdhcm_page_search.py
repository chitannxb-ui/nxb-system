import os
import json
import re
import time
import shutil
import sys
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QApplication, QTextEdit, QSpacerItem, QSizePolicy, QSplitter, QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QTextCursor, QPixmap, QColor, QFont, QBrush

from nxbgdhcm_db_manager import db
from nxbgdhcm_core_logic import TEMP_DIR
from nxbgdhcm_ui_utils import setup_shared_ai_combobox

EXT_COLORS = {
    "doc": "#2563eb", "docx": "#1d4ed8", "xls": "#059669", "xlsx": "#047857",     
    "ppt": "#d97706", "pptx": "#c2410c", "txt": "#4b5563", "jpg": "#9333ea",      
    "png": "#c026d3", "pdf": "#dc2626", "html": "#059669"      
}

class SortableTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        if column == 2: 
            d1_str = self.text(column)
            d2_str = other.text(column)
            try: d1 = datetime.strptime(d1_str, "%d/%m/%Y")
            except: d1 = datetime.min
            try: d2 = datetime.strptime(d2_str, "%d/%m/%Y")
            except: d2 = datetime.min
            return d1 < d2
        return super().__lt__(other)

class LoadDataWorker(QThread):
    finished_signal = pyqtSignal(bool, list, list)
    def run(self):
        success, all_files, created_docs = db.fetch_all_user_documents()
        self.finished_signal.emit(success, all_files, created_docs)

class ExportWorker(QThread):
    finished_signal = pyqtSignal(int, int)
    def __init__(self, valid_paths, dest_dir):
        super().__init__()
        self.valid_paths = valid_paths; self.dest_dir = dest_dir
    def run(self):
        success, err = 0, 0
        for filepath, filename in self.valid_paths:
            try:
                base_name, ext = os.path.splitext(filename)
                dest_path = os.path.join(self.dest_dir, filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(self.dest_dir, f"{base_name} ({counter}){ext}")
                    counter += 1
                shutil.copy2(filepath, dest_path)
                success += 1
            except: err += 1
        self.finished_signal.emit(success, err)

class ExportJsonWorker(QThread):
    finished_signal = pyqtSignal(bool, str, int)
    def __init__(self, md5_set, db_path, all_fetched_files, searched_files, created_docs):
        super().__init__()
        self.md5_set = md5_set
        self.db_path = db_path
        self.all_fetched_files = all_fetched_files
        self.searched_files = searched_files
        self.created_docs = created_docs
        
    def run(self):
        try:
            export_list = []
            combined_list = list(self.all_fetched_files) + list(self.searched_files) + list(self.created_docs)
            unique_docs = {doc['md5']: doc for doc in combined_list}
            
            for md5 in self.md5_set:
                if md5 in unique_docs:
                    doc = unique_docs[md5]
                    # Phải fetch full_text vì lúc load ban đầu không có
                    full_text = doc.get('full_text', '')
                    if not full_text: full_text = db.get_fulltext_by_md5(md5)
                    
                    formatted_doc = {
                        "Ten_File": doc.get('file_name', ''),
                        "Loai_Van_Ban": doc.get('doc_type', ''),
                        "So_Hieu": doc.get('doc_number', ''),
                        "Ngay_Ban_Hanh": f"{doc.get('doc_day','')}/{doc.get('doc_month','')}/{doc.get('doc_year','')}".strip('/'),
                        "Co_Quan_Ban_Hanh": doc.get('doc_org', ''),
                        "Nguoi_Ky": doc.get('doc_signer', ''),
                        "Tom_Tat_Summary": doc.get('summary', ''),
                        "Toan_Van": full_text,
                        "Duong_Dan": doc.get('file_path', ''),
                        "MD5": doc.get('md5', '')
                    }
                    export_list.append(formatted_doc)

            def date_converter(o):
                if isinstance(o, datetime): return o.__str__()
                
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(export_list, f, ensure_ascii=False, indent=4, default=date_converter)

            self.finished_signal.emit(True, self.db_path, len(export_list))
        except Exception as e:
            self.finished_signal.emit(False, str(e), 0)

class ExportExcelWorker(QThread):
    finished_signal = pyqtSignal(bool, str, int)
    def __init__(self, md5_set, db_path, all_fetched_files, searched_files, created_docs):
        super().__init__()
        self.md5_set = md5_set
        self.db_path = db_path
        self.all_fetched_files = all_fetched_files
        self.searched_files = searched_files
        self.created_docs = created_docs
        
    def run(self):
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "DuLieu_NXBGDHCM"
            
            headers = ["Tên File", "Loại Văn Bản", "Số Hiệu", "Ngày Ban Hành", "Cơ Quan", "Người Ký", "Tóm Tắt (Summary)", "Toàn Văn", "Đường Dẫn", "MD5"]
            ws.append(headers)
            
            from openpyxl.styles import Font
            for col in range(1, 11):
                ws.cell(row=1, column=col).font = Font(bold=True)

            export_count = 0
            combined_list = list(self.all_fetched_files) + list(self.searched_files) + list(self.created_docs)
            unique_docs = {doc['md5']: doc for doc in combined_list}
            
            for md5 in self.md5_set:
                if md5 in unique_docs:
                    doc = unique_docs[md5]
                    full_text = doc.get('full_text', '')
                    if not full_text: full_text = db.get_fulltext_by_md5(md5)
                    
                    row_data = [
                        doc.get('file_name', ''),
                        doc.get('doc_type', ''),
                        doc.get('doc_number', ''),
                        f"{doc.get('doc_day','')}/{doc.get('doc_month','')}/{doc.get('doc_year','')}".strip('/'),
                        doc.get('doc_org', ''),
                        doc.get('doc_signer', ''),
                        doc.get('summary', ''),
                        full_text,
                        doc.get('file_path', ''),
                        doc.get('md5', '')
                    ]
                    ws.append(row_data)
                    export_count += 1
                    
            wb.save(self.db_path)
            self.finished_signal.emit(True, self.db_path, export_count)
        except ImportError:
            self.finished_signal.emit(False, "Thiếu thư viện openpyxl. Vui lòng chạy lệnh: pip install openpyxl", 0)
        except Exception as e:
            self.finished_signal.emit(False, str(e), 0)

class AISearchWorker(QThread):
    progress_msg_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, list, list, str) 

    def __init__(self, logic, user_query, expanded_keywords, folder_paths, ai_config):
        super().__init__()
        self.logic = logic
        self.user_query = user_query
        self.expanded_keywords = expanded_keywords
        self.folder_paths = folder_paths
        self.ai_config = ai_config
        self.task_key = "search"

    def _get_snippet(self, text, words):
        if not text: return ""
        text_lower = text.lower()
        snippets = []
        found_count = 0
        for w in words:
            if not w: continue
            w_lower = w.lower()
            pos = text_lower.find(w_lower)
            start_search = 0
            while pos != -1 and found_count < 3:
                start = max(0, pos - 100)
                end = min(len(text), pos + len(w) + 100)
                snippets.append(text[start:end].replace('\n', ' ').strip())
                found_count += 1
                start_search = end
                pos = text_lower.find(w_lower, start_search)
            if found_count >= 3: break
        return " [...] ".join(snippets)

    def run(self):
        self.logic.set_running_state(self.task_key, True)
        
        kw_list = [k.strip() for k in re.sub(r'[\[\]\"\']', '', self.expanded_keywords).replace(';', ',').split(',') if k.strip()]
        if not kw_list: kw_list = [self.expanded_keywords.strip()]
        bool_kw = " ".join([f'"{k}"' for k in kw_list])

        raw_results = db.search_documents_fulltext(bool_kw, folder_paths=self.folder_paths)

        if not raw_results:
            self.finished_signal.emit(False, [], [], "Không tìm thấy tài liệu phù hợp (Vòng 1).")
            self.logic.set_running_state(self.task_key, False)
            return

        self.progress_msg_signal.emit(f"⚙️ [HỆ THỐNG]: Vòng 1 tìm thấy {len(raw_results)} tài liệu. Đang đưa A.I chắt lọc (Vòng 2)...")

        # [FIX] Khôi phục lại biến giới hạn ký tự Token chống tràn
        MAX_CHARS = 28000
        base_prompt = db.get_prompt('prompt_search_filter')
        if not base_prompt:
            base_prompt = "Người dùng yêu cầu tìm: [{user_query}]. Dưới đây là danh sách các file tìm được kèm nội dung trích dẫn. Hãy kiểm tra lại và CHỈ GIỮ LẠI những file thực sự liên quan đến yêu cầu. Trả về đúng một khối JSON DUY NHẤT chứa một mảng (Array), không giải thích thêm.\nCấu trúc JSON yêu cầu:\n[\n  {\n    \"md5\": \"mã md5 của file\",\n    \"y_kien\": \"Lý do ngắn gọn tại sao file này liên quan\"\n  }\n]\n\nDANH SÁCH FILE:\n"
            
        payload_text = base_prompt.replace('{user_query}', self.user_query)
        included_md5s = set()
        top_results = raw_results[:50] 
        valid_raw_results = []

        for file_doc in top_results:
            snippet = self._get_snippet(file_doc.get('full_text', ''), kw_list)
            doc_desc = f"""\n---
MD5: {file_doc['md5']}
Tên file: {file_doc.get('file_name', '')}
Loại: {file_doc.get('doc_type', '')}, Số: {file_doc.get('doc_number', '')}
Cơ quan: {file_doc.get('doc_org', '')}, Ngày: {file_doc.get('doc_day','')}/{file_doc.get('doc_month','')}/{file_doc.get('doc_year','')}
Tóm tắt: {file_doc.get('summary', '')}
Trích dẫn: {snippet}"""

            if len(payload_text) + len(doc_desc) > MAX_CHARS: break 

            payload_text += doc_desc
            included_md5s.add(file_doc['md5'])
            valid_raw_results.append(file_doc)

        ai_resp = ""
        gen = self.logic.call_ai_chat_stream_generator(self.ai_config['URL'], self.ai_config['Model_Name'], self.ai_config['API_Key'], [{"role": "user", "content": payload_text}], task_key=self.task_key)
        for chunk in gen:
            ai_resp += chunk

        try:
            match = re.search(r'\[\s*\{.*?\}\s*\]', ai_resp, re.DOTALL)
            if match: ai_json_array = json.loads(match.group(0))
            else: ai_json_array = json.loads(ai_resp)

            if not isinstance(ai_json_array, list): raise ValueError("Format rác")

            final_results = []
            reasons = []

            for item in ai_json_array:
                m_md5 = item.get("md5", "")
                y_kien = item.get("y_kien", "")
                if m_md5 in included_md5s: 
                    for f in valid_raw_results:
                        if f['md5'] == m_md5:
                            final_results.append(f)
                            reasons.append({"file_name": f.get('file_name', ''), "y_kien": y_kien})
                            break

            if not final_results:
                self.finished_signal.emit(False, [], [], "Không tìm thấy tài liệu phù hợp sau khi kiểm tra lại.")
            else:
                self.finished_signal.emit(True, final_results, reasons, f"A.I đã lọc ra {len(final_results)} tài liệu chính xác nhất.")

        except Exception as e:
            self.finished_signal.emit(False, [], [], f"Lỗi phân tích cú pháp AI vòng 2: Không tìm thấy tài liệu phù hợp.")
            
        self.logic.set_running_state(self.task_key, False)    

class AIChatThread(QThread):
    chat_start_signal = pyqtSignal(str, str)
    stream_signal = pyqtSignal(str) 
    search_signal = pyqtSignal(str, str) 
    create_doc_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool) 

    def __init__(self, logic, user_text, chat_messages, ai_config):
        super().__init__()
        self.logic = logic
        self.user_text = user_text; self.chat_messages = chat_messages; self.ai_config = ai_config
        self.task_key = "search"

    def run(self):
        self.logic.set_running_state(self.task_key, True)
        
        sys_prompt = db.get_prompt('prompt_system_chat')
        if not sys_prompt:
            sys_prompt = "Bạn là trợ lý của {danh_xung} {ho_ten}. Phản hồi JSON:\n1. Tìm kiếm: {\"Yêu cầu\": \"Tìm kiếm\", \"Nội dung\": \"từ gốc, từ đồng nghĩa 1, từ đồng nghĩa 2, cụm từ liên quan 1, ... (Tạo ra 8 đến 12 từ/cụm từ liên quan, biến thể văn phong hành chính, mỗi cụm từ không vượt quá 5 chữ)\"}\n2. Tạo văn bản: {\"Yêu cầu\": \"Tạo văn bản\", \"Nội dung\": \"Mã HTML\", \"tên file\": \"tên\"}\n3. Tán gẫu: Trả lời tự nhiên."
            
        sys_prompt = sys_prompt.replace('{danh_xung}', db.danh_xung).replace('{ho_ten}', db.ho_ten)
        
        if not self.chat_messages: self.chat_messages.append({"role": "system", "content": sys_prompt})
        else: self.chat_messages[0]["content"] = sys_prompt
        self.chat_messages.append({"role": "user", "content": self.user_text})

        MAX_HISTORY = 10
        if len(self.chat_messages) > MAX_HISTORY + 1:
            self.chat_messages[:] = [self.chat_messages[0]] + self.chat_messages[-MAX_HISTORY:]

        self.chat_start_signal.emit(f"Bạn: {self.user_text}\n", "user")
        self.chat_start_signal.emit("A.I: ", "ai")

        full_response = ""
        gen = self.logic.call_ai_chat_stream_generator(self.ai_config['URL'], self.ai_config['Model_Name'], self.ai_config['API_Key'], self.chat_messages, task_key=self.task_key)
        for chunk in gen:
            full_response += chunk
            self.stream_signal.emit(chunk) 
            
        self.stream_signal.emit("\n\n")
        self.chat_messages.append({"role": "assistant", "content": full_response})

        is_task_triggered = False
        json_match = re.search(r'\{.*\}', full_response, re.DOTALL)
        if json_match:
            try:
                ai_data = json.loads(json_match.group(0))
                req_type = ai_data.get("Yêu cầu", "")
                raw_content = ai_data.get("Nội dung", "")
                
                if isinstance(raw_content, list): content = ", ".join(str(x) for x in raw_content)
                else: content = str(raw_content)

                if req_type == "Tìm kiếm" and content: 
                    is_task_triggered = True
                    self.search_signal.emit(self.user_text, content)
                elif req_type == "Tạo văn bản" and content:
                    is_task_triggered = True
                    self.create_doc_signal.emit(str(ai_data.get("tên file", "Văn bản AI")), content)
            except: pass
            
        self.logic.set_running_state(self.task_key, False)
        self.finished_signal.emit(is_task_triggered)

class PageSearch(QWidget):
    def __init__(self, parent_main, shared_logic):
        super().__init__()
        self.parent_main = parent_main
        self.logic = shared_logic 
        self.all_fetched_files = []; self.searched_files = []; self.created_docs = []
        self.chat_messages = []; self.current_file_vals = None
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        header_lbl = QLabel("TÌM KIẾM TÀI LIỆU CỦA BẠN")
        header_lbl.setObjectName("MainHeader")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header_lbl)

        self.cols_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        col1_splitter = QSplitter(Qt.Orientation.Vertical)
        
        folder_widget = QWidget(); folder_layout = QVBoxLayout(folder_widget); folder_layout.setContentsMargins(0, 0, 0, 0); folder_layout.setSpacing(0)
        
        hdr1_frame = QFrame()
        hdr1_frame.setStyleSheet("background-color: transparent;") 
        hdr1 = QHBoxLayout(hdr1_frame); hdr1.setContentsMargins(0, 0, 0, 5)
        hdr1.addWidget(QLabel("📂 CẤU TRÚC THƯ MỤC", styleSheet="font-weight: bold; color: #d97706;"))
        self.btn_load = QPushButton("🗄️ Nạp dữ liệu"); self.btn_load.setObjectName("ToolbarBtn")
        self.btn_load.clicked.connect(self.load_data)
        hdr1.addStretch(); hdr1.addWidget(self.btn_load)
        
        self.tree_folders = QTreeWidget()
        self.tree_folders.setHeaderLabel("Thư Mục Trên Máy Tính")
        self.tree_folders.itemChanged.connect(self.on_folder_check_changed)
        self.tree_folders.itemSelectionChanged.connect(self.on_folder_selected)
        folder_layout.addWidget(hdr1_frame); folder_layout.addWidget(self.tree_folders)
        col1_splitter.addWidget(folder_widget)

        chat_widget = QWidget(); chat_layout = QVBoxLayout(chat_widget); chat_layout.setContentsMargins(0, 5, 0, 0); chat_layout.setSpacing(0)
        
        ai_combo_frame = QFrame()
        ai_combo_frame.setStyleSheet("background-color: transparent;")
        ai_combo_layout = QHBoxLayout(ai_combo_frame); ai_combo_layout.setContentsMargins(0, 0, 0, 5)
        ai_combo_layout.addWidget(QLabel("💬 TRỢ LÝ A.I", styleSheet="font-weight: bold; color: #10B981;"))
        self.combo_server = QComboBox()
        ai_combo_layout.addStretch(); ai_combo_layout.addWidget(self.combo_server)

        self.chat_history = QTextEdit(); self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("font-family: 'Segoe UI', Arial; font-size: 14px;")
        
        chat_input_frame = QFrame()
        chat_input_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E5B289; border-top: none;")
        chat_input_layout = QHBoxLayout(chat_input_frame); chat_input_layout.setContentsMargins(5, 5, 5, 5)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(f"Trò chuyện với trợ lý của {db.danh_xung}...")
        self.chat_input.returnPressed.connect(self.send_chat)
        self.chat_input.setStyleSheet("border: none; padding: 5px;")
        chat_input_layout.addWidget(self.chat_input)

        chat_layout.addWidget(ai_combo_frame); chat_layout.addWidget(self.chat_history); chat_layout.addWidget(chat_input_frame)
        col1_splitter.addWidget(chat_widget)
        col1_splitter.setSizes([400, 300]) 
        self.cols_splitter.addWidget(col1_splitter)

        col2_widget = QWidget(); col2_layout = QVBoxLayout(col2_widget); col2_layout.setContentsMargins(0, 0, 0, 0); col2_layout.setSpacing(0)
        
        hdr2_frame = QFrame()
        hdr2_frame.setStyleSheet("background-color: transparent;")
        hdr2_layout = QHBoxLayout(hdr2_frame); hdr2_layout.setContentsMargins(0, 0, 0, 5)
        hdr2_layout.addWidget(QLabel("📄 DANH SÁCH TẬP TIN", styleSheet="font-weight: bold; color: #2563eb;"))
        
        self.btn_export_file = QPushButton("📥 Xuất file"); self.btn_export_file.setObjectName("ToolbarBtn"); self.btn_export_file.setEnabled(False)
        self.btn_export_db = QPushButton("JSON"); self.btn_export_db.setObjectName("ToolbarBtn"); self.btn_export_db.setEnabled(False)
        self.btn_export_excel = QPushButton("Excel"); self.btn_export_excel.setObjectName("ToolbarBtn"); self.btn_export_excel.setEnabled(False) 
        self.btn_delete = QPushButton("🗑️ Xóa AI"); self.btn_delete.setObjectName("ToolbarBtn"); self.btn_delete.setEnabled(False)
        
        self.btn_export_file.clicked.connect(self.export_files)
        self.btn_export_db.clicked.connect(self.export_json)
        self.btn_export_excel.clicked.connect(self.export_excel)
        self.btn_delete.clicked.connect(self.delete_ai_doc)
        
        hdr2_layout.addStretch()
        hdr2_layout.addWidget(self.btn_export_file)
        hdr2_layout.addWidget(QLabel(" | "))
        hdr2_layout.addWidget(self.btn_export_db)
        hdr2_layout.addWidget(self.btn_export_excel)
        hdr2_layout.addWidget(self.btn_delete)

        self.tree_files = QTreeWidget()
        self.tree_files.setHeaderLabels(["Tên văn bản", "Loại", "Ngày ban hành", "md5", "path"])
        self.tree_files.hideColumn(3); self.tree_files.hideColumn(4); self.tree_files.setColumnWidth(0, 250)
        self.tree_files.setSortingEnabled(True) 
        
        self.tree_files.itemChanged.connect(self.on_file_check_changed)
        self.tree_files.itemSelectionChanged.connect(self.on_file_selected)

        col2_layout.addWidget(hdr2_frame); col2_layout.addWidget(self.tree_files, 1)
        self.cols_splitter.addWidget(col2_widget)

        col3_widget = QWidget(); col3_layout = QVBoxLayout(col3_widget); col3_layout.setContentsMargins(0, 0, 0, 0); col3_layout.setSpacing(0)
        
        hdr3_frame = QFrame()
        hdr3_frame.setStyleSheet("background-color: transparent;")
        hdr3_layout = QHBoxLayout(hdr3_frame); hdr3_layout.setContentsMargins(0, 0, 0, 5)
        hdr3_layout.addWidget(QLabel("👁️ XEM TRƯỚC NỘI DUNG", styleSheet="font-weight: bold; color: #10B981;"))
        
        self.btn_open_file = QPushButton("🖼️ Xem File Gốc"); self.btn_open_file.setObjectName("ToolbarBtn")
        self.btn_open_file.clicked.connect(self.open_system_file)
        hdr3_layout.addStretch(); hdr3_layout.addWidget(self.btn_open_file)
        
        self.text_content = QTextEdit(); self.text_content.setReadOnly(True)
        self.text_content.document().setDefaultStyleSheet("p { margin: 2px 0; } h3 { margin: 10px 0 2px 0; }")

        col3_layout.addWidget(hdr3_frame); col3_layout.addWidget(self.text_content, 1)
        self.cols_splitter.addWidget(col3_widget)

        self.cols_splitter.setSizes([400, 400, 400])
        self.main_layout.addWidget(self.cols_splitter, 1)

    def load_ai_presets(self):
        setup_shared_ai_combobox(self.combo_server, store_full_dict=False)

    def on_combo_server_changed(self):
        name = self.combo_server.currentText()
        self.append_chat_start(f"Đã chọn AI Server: {name}", "system")

    def load_data(self):
        self.btn_load.setText("Đang nạp...")
        self.btn_load.setEnabled(False)
        self.load_thread = LoadDataWorker()
        self.load_thread.finished_signal.connect(self.on_data_loaded)
        self.load_thread.start()
        
    def on_data_loaded(self, success, all_files, created_docs):
        if success:
            self.all_fetched_files = all_files
            self.created_docs = created_docs
            self.build_folder_tree()
        self.btn_load.setText("🗄️ Nạp dữ liệu")
        self.btn_load.setEnabled(True)

    def build_folder_tree(self):
        self.tree_folders.blockSignals(True)
        self.tree_folders.setUpdatesEnabled(False)
        self.tree_folders.clear()
        
        if self.created_docs:
            root_create = QTreeWidgetItem(self.tree_folders, ["📝 Tạo văn bản"])
            root_create.setData(0, Qt.ItemDataRole.UserRole, "create")
            root_create.setFlags(root_create.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            root_create.setCheckState(0, Qt.CheckState.Unchecked)
            
        if self.searched_files:
            root_search = QTreeWidgetItem(self.tree_folders, ["🔍 Kết quả tìm kiếm"])
            root_search.setData(0, Qt.ItemDataRole.UserRole, "search")
            root_search.setFlags(root_search.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            root_search.setCheckState(0, Qt.CheckState.Unchecked)

        root_main = QTreeWidgetItem(self.tree_folders, ["🗂️ Cơ sở dữ liệu"])
        root_main.setData(0, Qt.ItemDataRole.UserRole, "all")
        root_main.setFlags(root_main.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        root_main.setCheckState(0, Qt.CheckState.Unchecked)

        paths = set(os.path.dirname(f['file_path']) for f in self.all_fetched_files if f['file_path'])
        node_map = {"": root_main}
        for path in sorted(list(paths)):
            if not path: continue
            parts = path.replace('\\', '/').split('/')
            curr = ""
            for p in parts:
                if not p: continue
                parent = curr
                curr = f"{curr}/{p}" if curr else p
                if curr not in node_map:
                    if parent not in node_map: node_map[parent] = root_main
                    item = QTreeWidgetItem(node_map[parent], [p])
                    item.setData(0, Qt.ItemDataRole.UserRole, curr)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                    node_map[curr] = item
                    
        for i in range(self.tree_folders.topLevelItemCount()):
            top_item = self.tree_folders.topLevelItem(i)
            top_item.setExpanded(True)
            
        self.tree_folders.setUpdatesEnabled(True)
        self.tree_folders.blockSignals(False)

    def select_tree_node(self, node_role_name):
        for i in range(self.tree_folders.topLevelItemCount()):
            item = self.tree_folders.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == node_role_name:
                self.tree_folders.setCurrentItem(item)
                item.setExpanded(True)
                break

    def apply_highlight(self, item, is_checked):
        bg_color = QColor("#e0f2fe") if is_checked else QColor("#FFFFFF")
        font = item.font(0)
        font.setBold(is_checked)
        for col in range(item.columnCount()):
            item.setBackground(col, QBrush(bg_color))
            item.setFont(col, font)

    def on_folder_check_changed(self, item, column):
        self.tree_folders.blockSignals(True) 
        state = item.checkState(column)
        is_checked = (state == Qt.CheckState.Checked)
        
        self.apply_highlight(item, is_checked)
        
        def set_children_state(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                child.setCheckState(0, state)
                self.apply_highlight(child, is_checked)
                set_children_state(child) 
                
        set_children_state(item)
        self.tree_folders.blockSignals(False) 
        self.update_btn_states()

    def on_folder_selected(self):
        selected = self.tree_folders.selectedItems()
        if not selected: return
        item = selected[0]
        source_type = "all"
        target_path = item.data(0, Qt.ItemDataRole.UserRole)

        curr = item
        while curr.parent(): curr = curr.parent()
        if curr.text(0) == "📝 Tạo văn bản": source_type = "create"
        elif curr.text(0) == "🔍 Kết quả tìm kiếm": source_type = "search"

        self.tree_files.blockSignals(True)
        self.tree_files.setUpdatesEnabled(False) 
        self.tree_files.clear()
        
        source_list = self.created_docs if source_type == 'create' else (self.searched_files if source_type == 'search' else self.all_fetched_files)

        for f in source_list:
            match = False
            if target_path in ("create", "search", "all"): match = True
            elif f['file_path'] and f['file_path'].replace('\\', '/').startswith(target_path): match = True
            
            if match:
                dtype = f.get('doc_type', 'Văn bản')
                ext = os.path.splitext(f['file_name'])[1].lower().replace('.', '')
                if not ext and dtype == "Văn bản AI": ext = "html"
                date_str = f"{f.get('doc_day','')}/{f.get('doc_month','')}/{f.get('doc_year','')}"
                
                f_item = SortableTreeWidgetItem(self.tree_files, [f['file_name'], dtype, date_str, f['md5'], f['file_path']])
                f_item.setFlags(f_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                f_item.setCheckState(0, Qt.CheckState.Unchecked)
                
                if ext in EXT_COLORS:
                    for col in range(3): f_item.setForeground(col, QBrush(QColor(EXT_COLORS[ext])))
                    
        self.tree_files.setUpdatesEnabled(True) 
        self.tree_files.blockSignals(False)

    def on_file_check_changed(self, item, column): 
        is_checked = (item.checkState(0) == Qt.CheckState.Checked)
        self.apply_highlight(item, is_checked)
        self.update_btn_states()

    def on_file_selected(self):
        selected = self.tree_files.selectedItems()
        if not selected: return
        item = selected[0]
        self.current_file_vals = {"name": item.text(0), "md5": item.text(3), "path": item.text(4)}
        self.render_text_preview()

    def get_all_tree_items(self, tree, parent=None):
        items = []
        root = tree.invisibleRootItem() if parent is None else parent
        for i in range(root.childCount()):
            child = root.child(i)
            items.append(child)
            items.extend(self.get_all_tree_items(tree, child))
        return items

    def update_btn_states(self):
        has_file = False; has_ai_del = False
        for i in range(self.tree_files.topLevelItemCount()):
            item = self.tree_files.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                has_file = True
                if item.text(3).startswith('db_ai_gen_'): has_ai_del = True

        has_folder = False
        all_folder_items = self.get_all_tree_items(self.tree_folders)
        for item in all_folder_items:
            if item.checkState(0) == Qt.CheckState.Checked:
                has_folder = True
                break
                
        self.btn_export_file.setEnabled(has_file)
        self.btn_export_db.setEnabled(has_folder)
        self.btn_export_excel.setEnabled(has_folder) 
        self.btn_delete.setEnabled(has_ai_del)
        if has_ai_del: self.btn_delete.setStyleSheet("background-color: #ef4444; color: white;")
        else: self.btn_delete.setStyleSheet("")

    def open_system_file(self):
        if not self.current_file_vals: return
        path = self.current_file_vals['path']
        if path and os.path.exists(path):
            try:
                if sys.platform == "win32": os.startfile(path)
                elif sys.platform == "darwin":
                    import subprocess; subprocess.call(["open", path])
                else:
                    import subprocess; subprocess.call(["xdg-open", path])
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể mở file:\n{e}")
        else:
            QMessageBox.warning(self, "Lỗi", "File không tồn tại trên hệ thống!")

    def render_text_preview(self):
        if not self.current_file_vals: return
        target_md5 = self.current_file_vals["md5"]
        file_dict = next((f for lst in [self.all_fetched_files, self.searched_files, self.created_docs] for f in lst if f['md5'] == target_md5), None)
        if not file_dict: return

        self.text_content.clear()
        
        self.text_content.append(f"<h3 style='color: #2563eb;'>--- SIÊU DỮ LIỆU ---</h3>")
        meta_mapping = {
            'file_name': 'Tên file', 'file_path': 'Đường dẫn', 'file_type': 'Đuôi file',
            'doc_type': 'Loại văn bản', 'doc_number': 'Số hiệu', 'doc_day': 'Ngày',
            'doc_month': 'Tháng', 'doc_year': 'Năm', 'doc_org': 'Cơ quan', 'doc_signer': 'Người ký'
        }
        for k, label in meta_mapping.items():
            val = file_dict.get(k)
            if val and str(val).strip() and str(val).strip() not in ["None", "N/A"]:
                self.text_content.append(f"<p><b>{label}:</b> {val}</p>")

        summary = str(file_dict.get('summary', '')).strip()
        if summary and summary not in ["None", "N/A"]:
            self.text_content.append(f"<br><h3 style='color: #d97706;'>--- TÓM TẮT ---</h3>")
            self.text_content.append(f"<p style='color: #2563eb; font-style: italic;'>{summary.replace(chr(10), '<br>')}</p>")

        self.text_content.append(f"<br><h3 style='color: #10B981;'>--- TOÀN VĂN ---</h3>")
        
        filepath = file_dict.get('file_path', '')
        if filepath and os.path.exists(filepath):
            thumb_path = os.path.join(TEMP_DIR, f"thumb_{target_md5}.jpg")
            success, msg = self.logic.generate_thumbnail(filepath, thumb_path)
            if success:
                img_src = "file:///" + thumb_path.replace("\\", "/")
                self.text_content.append(f"<img src='{img_src}' width='300'><br>")
            else:
                if msg: self.text_content.append(f"<p style='color: #ef4444;'>[Lỗi tạo ảnh: {msg}]</p><br>")
        elif filepath:
            self.text_content.append("<p style='color: #ef4444;'>[Lỗi: Không tìm thấy file gốc trên máy tính!]</p><br>")

        full_text = str(file_dict.get('full_text', '')).strip()
        # Nạp Full Text ngầm nếu DB chưa có
        if not full_text: 
            full_text = db.get_fulltext_by_md5(target_md5)
            file_dict['full_text'] = full_text # Gán vào dict để lần bấm sau không cần load lại
            
        if full_text and full_text not in ["None", "N/A"]:
            self.text_content.append(f"<p>{full_text.replace(chr(10), '<br>')}</p>")
        
        cursor = self.text_content.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text_content.setTextCursor(cursor)
        self.text_content.verticalScrollBar().setValue(0)

    def append_chat_start(self, text, role):
        color = "#10B981" if role == "ai" else ("#d97706" if role == "system" else "#2563eb")
        bold = "<b>" if role == "user" else ""
        self.chat_history.append(f"<span style='color:{color};'>{bold}{text}</span>")
        self.chat_history.ensureCursorVisible() 

    def append_chat_stream(self, chunk):
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible() 

    def send_chat(self):
        text = self.chat_input.text().strip()
        if not text: return
        
        self.chat_input.clear()
        
        self.chat_input.setEnabled(False)
        self.chat_input.setPlaceholderText("A.I đang suy nghĩ và xử lý...")
        
        preset_id = self.combo_server.currentData()
        config = db.get_ai_config_by_id(preset_id)
        if not config: 
            self.append_chat_start("⚠️ Vui lòng chọn AI Server trước!", "system")
            self._reset_chat_input()
            return
        
        self.chat_thread = AIChatThread(self.logic, text, self.chat_messages, config)
        self.chat_thread.chat_start_signal.connect(self.append_chat_start)
        self.chat_thread.stream_signal.connect(self.append_chat_stream) 
        self.chat_thread.search_signal.connect(self.execute_ai_search)
        self.chat_thread.create_doc_signal.connect(self.execute_ai_create)
        self.chat_thread.finished_signal.connect(self.on_chat_thread_finished)
        self.chat_thread.start()

    def on_chat_thread_finished(self, is_task_triggered):
        if not is_task_triggered:
            self._reset_chat_input()

    def _reset_chat_input(self):
        self.chat_input.setEnabled(True)
        self.chat_input.setPlaceholderText(f"Trò chuyện với trợ lý của {db.danh_xung}...")
        self.chat_input.setFocus()

    def execute_ai_search(self, user_query, expanded_keywords):
        self.append_chat_start(f"⚙️ [HỆ THỐNG]: Nhận lệnh TÌM KIẾM. Đang kích hoạt tiến trình...", "system")
        
        selected_folders = []
        search_all = False
        for i in range(self.tree_folders.topLevelItemCount()):
            item = self.tree_folders.topLevelItem(i)
            if item.text(0) == "🗂️ Cơ sở dữ liệu":
                if item.checkState(0) == Qt.CheckState.Checked: search_all = True
                break

        if not search_all:
            all_folder_items = self.get_all_tree_items(self.tree_folders)
            for item in all_folder_items:
                if item.checkState(0) == Qt.CheckState.Checked:
                    path = item.data(0, Qt.ItemDataRole.UserRole)
                    if path not in ("all", "create", "search"):
                        selected_folders.append(path)
        
        folder_param = None if search_all or not selected_folders else selected_folders
        
        preset_id = self.combo_server.currentData()
        config = db.get_ai_config_by_id(preset_id)

        self.search_worker = AISearchWorker(self.logic, user_query, expanded_keywords, folder_param, config)
        self.search_worker.progress_msg_signal.connect(lambda msg: self.append_chat_start(msg, "system"))
        self.search_worker.finished_signal.connect(self.on_ai_search_finished)
        self.search_worker.start()

    def on_ai_search_finished(self, success, filtered_files, reasons, msg):
        self.append_chat_start(f"⚙️ [HỆ THỐNG]: {msg}", "system")
        
        if success:
            self.searched_files = filtered_files
            self.build_folder_tree()
            self.select_tree_node("search") # Tự động chọn kết quả tìm kiếm
            
            html_reasons = "<br>"
            for r in reasons:
                html_reasons += f"📄 <b>{r['file_name']}</b><br>   → <span style='color: #2563eb;'>{r['y_kien']}</span><br><br>"
            
            self.chat_history.append(html_reasons)
            self.chat_history.ensureCursorVisible()

        self._reset_chat_input()

    def execute_ai_create(self, name, content):
        ten_file_ai = f"{time.strftime('%y%m%d')} {name}"
        success, new_id = db.save_ai_generated_document(ten_file_ai, content)
        if success:
            self.append_chat_start(f"⚙️ [HỆ THỐNG]: Nhận lệnh TẠO VĂN BẢN. Đã lưu vào CSDL.", "system")
            # Nạp thẳng vào RAM thay vì load lại toàn bộ DB
            t = datetime.now()
            day, month, year = (str(t.day).zfill(2), str(t.month).zfill(2), str(t.year))
            new_doc = {
                'md5': f"db_ai_gen_{new_id}", 'file_name': ten_file_ai, 'file_path': "", 'file_type': "html",
                'doc_type': "Văn bản AI", 'doc_day': day, 'doc_month': month, 'doc_year': year, 'doc_org': "A.I Assistant",
                'doc_signer': db.ho_ten, 'summary': "Văn bản do A.I tự động soạn thảo.", 'full_text': content
            }
            self.created_docs.append(new_doc)
            self.build_folder_tree()
            self.select_tree_node("create") # Tự động chọn mục tạo VB
            
            # Chọn chính xác file vừa tạo
            for i in range(self.tree_files.topLevelItemCount()):
                item = self.tree_files.topLevelItem(i)
                if item.text(3) == f"db_ai_gen_{new_id}":
                    self.tree_files.setCurrentItem(item)
                    break
        self._reset_chat_input()

    def export_files(self):
        paths = [(self.tree_files.topLevelItem(i).text(4), self.tree_files.topLevelItem(i).text(0)) for i in range(self.tree_files.topLevelItemCount()) if self.tree_files.topLevelItem(i).checkState(0) == Qt.CheckState.Checked]
        if not paths: return
        dest_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu")
        if not dest_dir: return

        self.btn_export_file.setText("Đang xuất...")
        self.exp_thread = ExportWorker(paths, dest_dir)
        self.exp_thread.finished_signal.connect(lambda s, e: self.btn_export_file.setText("📥 Xuất file") or QMessageBox.information(self, "Xong", f"Copy xong: {s} file\nLỗi: {e} file"))
        self.exp_thread.start()

    def _get_selected_md5s(self):
        selected_md5s = set()
        all_folder_items = self.get_all_tree_items(self.tree_folders)
        checked_folders = [item for item in all_folder_items if item.checkState(0) == Qt.CheckState.Checked]

        if not checked_folders: return selected_md5s

        for item in checked_folders:
            source_type = "all"
            target_path = item.data(0, Qt.ItemDataRole.UserRole)

            curr = item
            while curr.parent(): curr = curr.parent()
            if curr.text(0) == "📝 Tạo văn bản": source_type = "create"
            elif curr.text(0) == "🔍 Kết quả tìm kiếm": source_type = "search"

            source_list = self.created_docs if source_type == 'create' else (self.searched_files if source_type == 'search' else self.all_fetched_files)

            for f in source_list:
                match = False
                if target_path in ("create", "search", "all"): match = True
                elif f['file_path'] and f['file_path'].replace('\\', '/').startswith(target_path): match = True
                if match: selected_md5s.add(f['md5'])
        return selected_md5s

    def export_json(self):
        selected_md5s = self._get_selected_md5s()
        if not selected_md5s:
            QMessageBox.warning(self, "Trống", "Thư mục bạn chọn không chứa tập tin nào.")
            return

        db_path, _ = QFileDialog.getSaveFileName(self, f"Lưu {len(selected_md5s)} tài liệu", f"Export_{time.strftime('%y%m%d')}.json", "JSON File (*.json)")
        if not db_path: return

        self.btn_export_db.setText("Đang xuất...")
        self.btn_export_db.setEnabled(False)

        self.json_thread = ExportJsonWorker(selected_md5s, db_path, self.all_fetched_files, self.searched_files, self.created_docs)
        self.json_thread.finished_signal.connect(lambda success, path, count: self.on_export_finished(success, path, count, is_excel=False))
        self.json_thread.start()

    def export_excel(self):
        selected_md5s = self._get_selected_md5s()
        if not selected_md5s:
            QMessageBox.warning(self, "Trống", "Thư mục bạn chọn không chứa tập tin nào.")
            return

        db_path, _ = QFileDialog.getSaveFileName(self, f"Lưu {len(selected_md5s)} tài liệu", f"Export_{time.strftime('%y%m%d')}.xlsx", "Excel File (*.xlsx)")
        if not db_path: return

        self.btn_export_excel.setText("Đang xuất...")
        self.btn_export_excel.setEnabled(False)

        self.excel_thread = ExportExcelWorker(selected_md5s, db_path, self.all_fetched_files, self.searched_files, self.created_docs)
        self.excel_thread.finished_signal.connect(lambda success, path, count: self.on_export_finished(success, path, count, is_excel=True))
        self.excel_thread.start()

    def on_export_finished(self, success, path, count, is_excel=False):
        if is_excel: self.btn_export_excel.setText("Excel")
        else: self.btn_export_db.setText("JSON")
        
        self.update_btn_states()
        
        if success: QMessageBox.information(self, "Hoàn tất", f"Đã xuất thành công {count} bản ghi ra file:\n{path}")
        else: QMessageBox.critical(self, "Lỗi", f"Không thể xuất file!\nChi tiết: {path}")

    def delete_ai_doc(self):
        items_to_del = []
        ids = []
        for i in range(self.tree_files.topLevelItemCount()):
            item = self.tree_files.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked and item.text(3).startswith("db_ai_gen_"):
                ids.append(item.text(3).replace("db_ai_gen_", ""))
                items_to_del.append(item)
                
        if ids and QMessageBox.question(self, "Xác nhận", f"Xóa vĩnh viễn {len(ids)} văn bản?") == QMessageBox.StandardButton.Yes:
            if db.delete_ai_documents(ids):
                # XÓA FILE ẢO TRÊN GIAO DIỆN (Nhanh mượt, không load lại CSDL)
                for item in items_to_del:
                    root = item.treeWidget().invisibleRootItem()
                    root.removeChild(item)
                
                self.created_docs = [d for d in self.created_docs if d['md5'].replace("db_ai_gen_", "") not in ids]
                self.update_btn_states()