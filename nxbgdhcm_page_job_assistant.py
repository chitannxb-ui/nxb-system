import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QComboBox, QTextEdit, QSplitter, QListWidget, 
                             QListWidgetItem, QFrame, QMessageBox, QMenu, QInputDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor, QFont

from nxbgdhcm_db_manager import db
from nxbgdhcm_ui_utils import THEME, setup_shared_ai_combobox

# =========================================================================
# 1. LUỒNG XỬ LÝ CHAT STREAMING 
# =========================================================================
class JobAssistantChatThread(QThread):
    stream_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    debug_signal = pyqtSignal(str)

    def __init__(self, logic, chat_messages, ai_config):
        super().__init__()
        self.logic = logic
        self.chat_messages = chat_messages
        self.ai_config = ai_config
        self.task_key = "job_assistant_chat"

    def run(self):
        self.logic.set_running_state(self.task_key, True)
        try:
            debug_text = json.dumps(self.chat_messages, ensure_ascii=False, indent=2)
            self.debug_signal.emit(f"=== [PAYLOAD GỬI ĐẾN API SERVER] ===\n{debug_text}\n\n")

            gen_chat = self.logic.call_ai_chat_stream_generator(
                self.ai_config['URL'],
                self.ai_config['Model_Name'],
                self.ai_config['API_Key'],
                self.chat_messages,
                task_key=self.task_key
            )
            
            for chunk in gen_chat:
                if not self.logic.is_running(self.task_key):
                    break
                self.stream_signal.emit(chunk)
                
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.logic.set_running_state(self.task_key, False)
            self.finished_signal.emit()

# =========================================================================
# 2. LUỒNG NGẦM TỰ ĐỘNG ĐẶT TÊN HỘI THOẠI 
# =========================================================================
class TitleGeneratorThread(QThread):
    title_generated_signal = pyqtSignal(int, str) 

    def __init__(self, logic, chat_id, first_user_message, ai_config):
        super().__init__()
        self.logic = logic
        self.chat_id = chat_id
        self.first_user_message = first_user_message
        self.ai_config = ai_config

    def run(self):
        prompt = f"Hãy đóng vai một thư ký. Đọc câu hỏi sau của người dùng và tạo ra một TIÊU ĐỀ ngắn gọn (tối đa 6 chữ) thể hiện chủ đề. CHỈ TRẢ VỀ TIÊU ĐỀ, KHÔNG GIẢI THÍCH THÊM.\nCâu hỏi: {self.first_user_message}"
        
        full_response = ""
        gen = self.logic.call_ai_stream_generator(
            self.ai_config['URL'], self.ai_config['Model_Name'], self.ai_config['API_Key'], prompt
        )
        for chunk in gen:
            full_response += chunk
            
        new_title = full_response.strip().replace('"', '').replace('\n', '')
        if new_title:
            db.update_aia_chat_title(self.chat_id, new_title)
            self.title_generated_signal.emit(self.chat_id, new_title)

# =========================================================================
# 3. LUỒNG CHẠY NGẦM CHƯNG CẤT TRÍ NHỚ
# =========================================================================
class MemoryBuilderThread(QThread):
    finished_signal = pyqtSignal(bool, str) 

    def __init__(self, logic, chat_id, ai_config, prompt_template):
        super().__init__()
        self.logic = logic
        self.chat_id = chat_id
        self.ai_config = ai_config
        self.prompt_template = prompt_template

    def run(self):
        msgs = db.fetch_unsummarized_messages(self.chat_id)
        if not msgs:
            self.finished_signal.emit(False, "Không có tin nhắn mới cần tóm tắt.")
            return

        curr_s = db.get_aia_session_by_id(self.chat_id)
        if not curr_s: return

        old_summary = curr_s.get('chat_summary') or ""
        old_datasheet = curr_s.get('chat_datasheet') or ""

        new_msg_str = ""
        processed_l1_ids = []
        for m in msgs:
            processed_l1_ids.append(m['chat_l1_id'])
            role_str = "Người dùng" if m['role'] == 'user' else "Trợ lý AI"
            new_msg_str += f"{role_str}: {m['content']}\n"

        final_prompt = self.prompt_template.replace('{old_summary}', old_summary)\
                                           .replace('{old_datasheet}', old_datasheet)\
                                           .replace('{new_messages}', new_msg_str)

        full_response = ""
        gen = self.logic.call_ai_stream_generator(
            self.ai_config['URL'], self.ai_config['Model_Name'], self.ai_config['API_Key'], final_prompt
        )
        for chunk in gen:
            full_response += chunk

        ai_data = self.logic.extract_json(full_response)
        if ai_data and ('summary' in ai_data or 'datasheet' in ai_data):
            new_sum = str(ai_data.get('summary', old_summary)).strip()
            new_data = str(ai_data.get('datasheet', old_datasheet)).strip()
            
            success = db.update_aia_memory(self.chat_id, new_sum, new_data, processed_l1_ids)
            self.finished_signal.emit(success, "Đã chưng cất Trí nhớ & Sổ số liệu thành công!")
        else:
            self.finished_signal.emit(False, "Lỗi bóc tách JSON trí nhớ từ AI.")

# =========================================================================
# GIAO DIỆN CHÍNH CỦA PHÂN HỆ TRỢ LÝ CÔNG VIỆC AI ASSISTANT
# =========================================================================
class PageJobAssistant(QWidget):
    def __init__(self, parent_main, shared_logic):
        super().__init__()
        self.parent_main = parent_main
        self.logic = shared_logic
        
        self.current_chat_id = None
        self.current_ai_response = ""
        self._is_loading_history = False 
        
        # [CẢI TIẾN] Cache prompt vào RAM để tối ưu vòng lặp truy vấn MySQL
        self._cached_prompts = {}
        
        self.init_ui()
        self.load_ai_presets()
        self.refresh_chat_list()

    def get_cached_prompt(self, key, default_val=""):
        """Hàm lấy prompt từ RAM, nếu chưa có mới gọi Database"""
        if key not in self._cached_prompts:
            val = db.get_prompt(key)
            self._cached_prompts[key] = val if val else default_val
        return self._cached_prompts[key]

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        header_lbl = QLabel("PHÂN HỆ TRỢ LÝ CÔNG VIỆC THÔNG MINH")
        header_lbl.setObjectName("MainHeader")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header_lbl)

        self.cols_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.cols_splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: transparent; }} "
            f"QSplitter::handle:horizontal {{ width: 6px; }} "
            f"QSplitter::handle:hover {{ background-color: {THEME['accent_green']}; }}"
        )

        # ---------------------------------------------------------------------
        # CỘT 1: QUẢN LÝ DANH SÁCH PHIÊN THẢO LUẬN
        # ---------------------------------------------------------------------
        col1_widget = QWidget()
        col1_layout = QVBoxLayout(col1_widget)
        col1_layout.setContentsMargins(0, 0, 0, 0)
        col1_layout.setSpacing(6)

        lbl_chat_list = QLabel("💬 LỊCH SỬ THẢO LUẬN")
        lbl_chat_list.setStyleSheet("font-weight: bold; color: #355C8E;")
        
        self.btn_new_chat = QPushButton("➕ Cuộc trò chuyện mới")
        self.btn_new_chat.setObjectName("ToolbarBtn")
        self.btn_new_chat.clicked.connect(self.on_new_chat_clicked)
        
        self.list_conversations = QListWidget()
        self.list_conversations.setStyleSheet(f"font-size: 15px; padding: 5px; border: 1px solid {THEME['border_color']}; border-radius: 3px;")
        self.list_conversations.itemSelectionChanged.connect(self.on_conversation_changed)
        self.list_conversations.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_conversations.customContextMenuRequested.connect(self.show_context_menu)

        col1_layout.addWidget(lbl_chat_list)
        col1_layout.addWidget(self.btn_new_chat)
        col1_layout.addWidget(self.list_conversations)
        self.cols_splitter.addWidget(col1_widget)

        # ---------------------------------------------------------------------
        # CỘT 2: KHUNG TRÒ CHUYỆN & ĐIỀU PHỐI MÔ HÌNH AI
        # ---------------------------------------------------------------------
        col2_widget = QWidget()
        col2_layout = QVBoxLayout(col2_widget)
        col2_layout.setContentsMargins(0, 0, 0, 0)
        col2_layout.setSpacing(6)

        chat_header_layout = QHBoxLayout()
        lbl_chat_box = QLabel("🤖 TRỢ LÝ TƯ VẤN AI")
        lbl_chat_box.setStyleSheet("font-weight: bold; color: #2563eb;")
        
        self.combo_server = QComboBox()
        self.combo_server.setFixedWidth(200)
        
        chat_header_layout.addWidget(lbl_chat_box)
        chat_header_layout.addStretch()
        chat_header_layout.addWidget(QLabel("Mô hình AI:"))
        chat_header_layout.addWidget(self.combo_server)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet(f"font-family: 'Segoe UI', Arial; font-size: 15px; background-color: #FFFFFF; border: 1px solid {THEME['border_color']}; border-radius: 3px;")

        chat_input_frame = QFrame()
        chat_input_frame.setStyleSheet(f"background-color: #FFFFFF; border: 1px solid {THEME['border_color']}; border-radius: 3px;")
        chat_input_layout = QHBoxLayout(chat_input_frame)
        chat_input_layout.setContentsMargins(5, 5, 5, 5)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Nhập tin nhắn hoặc nội dung công việc cần trợ lý hỗ trợ...")
        self.chat_input.setStyleSheet("border: none; padding: 5px;")
        self.chat_input.returnPressed.connect(self.handle_action_btn)
        
        self.btn_action = QPushButton("Gửi ➢")
        self.btn_action.setFixedWidth(100)
        self.btn_action.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; border-radius: 3px; padding: 6px 15px;")
        self.btn_action.clicked.connect(self.handle_action_btn)
        
        chat_input_layout.addWidget(self.chat_input, 1)
        chat_input_layout.addWidget(self.btn_action)

        col2_layout.addLayout(chat_header_layout)
        col2_layout.addWidget(self.chat_history, 1)
        col2_layout.addWidget(chat_input_frame)
        self.cols_splitter.addWidget(col2_widget)

        # ---------------------------------------------------------------------
        # CỘT 3: KHUNG CANVAS THEO DÕI SIÊU DỮ LIỆU PROMPT LOG
        # ---------------------------------------------------------------------
        col3_widget = QWidget()
        col3_layout = QVBoxLayout(col3_widget)
        col3_layout.setContentsMargins(0, 0, 0, 0)
        col3_layout.setSpacing(6)

        lbl_canvas = QLabel("📄 CANVAS / KHÔNG GIAN THEO DÕI PROMPT")
        lbl_canvas.setStyleSheet("font-weight: bold; color: #10B981;")

        self.canvas_content = QTextEdit()
        self.canvas_content.setReadOnly(True)
        self.canvas_content.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.canvas_content.setStyleSheet(f"font-family: 'Consolas', 'Courier New', monospace; color: #c85a17; background-color: #fcfbf7; border: 1px solid {THEME['border_color']}; border-radius: 3px; font-size: 13px;")
        self.canvas_content.setPlaceholderText("Nội dung Debug và Canvas sẽ hiển thị ở đây...")

        col3_layout.addWidget(lbl_canvas)
        col3_layout.addWidget(self.canvas_content)
        self.cols_splitter.addWidget(col3_widget)

        self.cols_splitter.setSizes([160, 360, 240])
        self.main_layout.addWidget(self.cols_splitter, 1)

    # =========================================================================
    # ĐIỀU PHỐI DỮ LIỆU & MENU NGỮ CẢNH (CONTEXT MENU)
    # =========================================================================
    def load_ai_presets(self):
        setup_shared_ai_combobox(self.combo_server, store_full_dict=False)

    def refresh_chat_list(self, select_chat_id=None):
        self.list_conversations.blockSignals(True)
        self.list_conversations.clear()
        
        sessions = db.fetch_aia_chat_sessions()
        target_item = None
        
        for s in sessions:
            c_id = s['chat_id']
            title = s['chat_title']
            total_msgs = s.get('chat_total_messages', 0)
            
            display_text = f"🔹 {title}"
            if total_msgs > 0:
                display_text += f" ({total_msgs})"
                
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, c_id)
            self.list_conversations.addItem(item)
            
            if select_chat_id and c_id == select_chat_id:
                target_item = item
                
        self.list_conversations.blockSignals(False)
        
        if target_item:
            self.list_conversations.setCurrentItem(target_item)
        elif self.list_conversations.count() > 0:
            self.list_conversations.setCurrentRow(0)
        else:
            self.current_chat_id = None
            self.chat_history.clear()
            self.canvas_content.clear()

    def show_context_menu(self, pos):
        item = self.list_conversations.itemAt(pos)
        if not item: return

        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ font-size: 14px; background-color: white; border: 1px solid {THEME['border_color']}; }} QMenu::item:selected {{ background-color: {THEME['row_success']}; color: black; }}")
        
        rename_action = menu.addAction("✏️ Đổi tên hội thoại")
        delete_action = menu.addAction("🗑️ Xóa hội thoại")
        
        action = menu.exec(self.list_conversations.mapToGlobal(pos))
        
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        
        if action == rename_action:
            old_name = item.text().split("🔹 ")[-1].split(" (")[0]
            new_name, ok = QInputDialog.getText(self, "Đổi tên", "Nhập tên cuộc hội thoại mới:", QLineEdit.EchoMode.Normal, old_name)
            if ok and new_name.strip():
                if db.update_aia_chat_title(chat_id, new_name.strip()):
                    self.refresh_chat_list(select_chat_id=self.current_chat_id)
                    
        elif action == delete_action:
            reply = QMessageBox.question(self, "Xóa", "Xóa vĩnh viễn cuộc trò chuyện này và toàn bộ lịch sử?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if db.delete_aia_chat_session(chat_id):
                    if self.current_chat_id == chat_id:
                        self.current_chat_id = None
                    self.refresh_chat_list(select_chat_id=self.current_chat_id)

    def on_new_chat_clicked(self):
        new_id = db.create_aia_chat_session()
        if new_id:
            self.refresh_chat_list(select_chat_id=new_id)
            self.chat_history.clear()
            self.chat_history.setPlaceholderText(f"Xin chào {db.danh_xung} {db.ho_ten}, tôi có thể giúp gì cho công việc của bạn hôm nay?")
            self.chat_input.setFocus()

    def on_conversation_changed(self):
        selected_items = self.list_conversations.selectedItems()
        if not selected_items: return
        self.current_chat_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        self.load_current_chat_history()

    def load_current_chat_history(self):
        if not self.current_chat_id: return
        
        self._is_loading_history = True
        self.chat_history.clear()
        self.canvas_content.clear()
        
        # [CẢI TIẾN] Sử dụng hàm query tối ưu 1 dòng thay vì loop toàn bộ DB
        curr_session = db.get_aia_session_by_id(self.current_chat_id)
        
        if curr_session:
            summary = curr_session.get('chat_summary') or '[Trống - Chưa thực hiện tích lũy]'
            datasheet = curr_session.get('chat_datasheet') or '[Trống - Chưa ghi nhận số liệu]'
            
            memory_log = (
                f"=== [TRÍ NHỚ CỐ ĐỊNH HIỆN HÀNH CỦA PHIÊN CHAT KHÓA: #{self.current_chat_id}] ===\n"
                f"📝 TÓM TẮT BỐI CẢNH:\n{summary}\n\n"
                f"📊 SỔ THEO DÕI SỐ LIỆU:\n{datasheet}\n"
                f"{'='*60}\n\n"
            )
            self.canvas_content.setText(memory_log)

        messages = db.fetch_aia_chat_messages(self.current_chat_id)
        for msg in messages:
            role = msg['role']
            content = msg['content'].replace('\n', '<br>')
            
            if role == "user":
                self.chat_history.append(f"<div style='margin-top: 10px;'><b style='color:#2563eb;'>Bạn:</b><br>{content}</div>")
            elif role == "assistant":
                self.chat_history.append(f"<div style='margin-top: 10px;'><b style='color:#10B981;'>A.I:</b><br>{content}</div><br>")
                
        self.chat_history.ensureCursorVisible()
        self._is_loading_history = False

    # =========================================================================
    # LUỒNG ĐIỀU PHỐI ĐẶC VỤ CHAT & CƠ CHẾ NÚT 2 TRONG 1
    # =========================================================================
    def append_chat_html(self, text, role):
        formatted_text = text.replace('\n', '<br>')
        if role == "user":
            self.chat_history.append(f"<div style='margin-top: 10px;'><b style='color:#2563eb;'>Bạn:</b><br>{formatted_text}</div>")
        elif role == "ai_start":
            self.chat_history.append(f"<div style='margin-top: 10px;'><b style='color:#10B981;'>A.I:</b><br></div>")
        self.chat_history.ensureCursorVisible()

    def append_chat_stream(self, chunk):
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()
        self.current_ai_response += chunk

    def append_canvas_debug(self, debug_text):
        cursor = self.canvas_content.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(debug_text)
        self.canvas_content.setTextCursor(cursor)
        self.canvas_content.ensureCursorVisible()

    def handle_action_btn(self):
        if self.logic.is_running("job_assistant_chat"):
            self.stop_message()
        else:
            self.send_message()

    def send_message(self):
        user_text = self.chat_input.text().strip()
        if not user_text: return

        if self.logic.is_running("job_assistant_chat"): return
        
        if not self.current_chat_id:
            self.current_chat_id = db.create_aia_chat_session()
            if not self.current_chat_id: return
            
        preset_id = self.combo_server.currentData()
        config = db.get_ai_config_by_id(preset_id)
        if not config:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn cấu hình Máy chủ AI!")
            return

        self.chat_input.clear()
        self.append_chat_html(user_text, "user")
        db.save_aia_chat_message(self.current_chat_id, "user", user_text)
        self.append_chat_html("", "ai_start")
        
        # [CẢI TIẾN] Xóa dòng trùng lặp mã khóa UI
        self.chat_input.setEnabled(False)
        self.chat_input.setPlaceholderText("Trợ lý AI đang suy nghĩ hành động và kết xuất văn bản...")
        
        self.btn_action.setText("Dừng ⏹")
        self.btn_action.setStyleSheet(f"background-color: {THEME['accent_red']}; color: white; font-weight: bold; border-radius: 3px; padding: 6px 15px;")
        self.btn_action.setEnabled(False)
        QTimer.singleShot(1500, lambda: self.btn_action.setEnabled(True))
        
        self.list_conversations.setEnabled(False)
        self.btn_new_chat.setEnabled(False)        
        
        # [CẢI TIẾN] Gọi Prompt từ RAM thay vì chọc CSDL liên tục
        prompt_1 = self.get_cached_prompt('aia_systemprompt_1', "Bạn là trợ lý ảo của {danh_xung} {ho_ten} tại NXBGDHCM.")
        # [CẢI TIẾN] Chỉnh sửa biến thay thế {cong_tac} chính xác từ db.cong_tac
        prompt_1 = prompt_1.replace('{danh_xung}', db.danh_xung)\
                           .replace('{ho_ten}', db.ho_ten)\
                           .replace('{chuc_vu}', db.chuc_vu)\
                           .replace('{phong_ban}', db.phong_ban)\
                           .replace('{cong_tac}', db.cong_tac) 
                           
        prompt_2 = self.get_cached_prompt('aia_systemprompt_2')

        curr_s = db.get_aia_session_by_id(self.current_chat_id)
        
        memory_instruction = ""
        if curr_s:
            c_summary = curr_s.get('chat_summary') or ""
            c_datasheet = curr_s.get('chat_datasheet') or ""
            if c_summary or c_datasheet:
                memory_instruction = f"\n[TRÍ NHỚ CŨ TẬP HỢP TRƯỚC ĐÓ]:\n- Tóm tắt thảo luận quá khứ: {c_summary}\n- Sổ dữ liệu/Số liệu đã ghi nhận: {c_datasheet}\nCần ghi nhớ thông tin này để phản hồi nhất quán."

        final_system_prompt = f"{prompt_1}\n{prompt_2}{memory_instruction}"

        if curr_s and curr_s['chat_title'] == 'Hội thoại mới' and curr_s['chat_sum_counter'] <= 1:
            self.title_thread = TitleGeneratorThread(self.logic, self.current_chat_id, user_text, config)
            self.title_thread.title_generated_signal.connect(self.on_title_generated)
            self.title_thread.start()

        raw_msgs = db.fetch_unsummarized_messages(self.current_chat_id)
        
        MAX_HISTORY = 15
        if len(raw_msgs) > MAX_HISTORY:
            raw_msgs = raw_msgs[-MAX_HISTORY:]
            
        api_payload = [{"role": "system", "content": final_system_prompt}]
        for m in raw_msgs:
            api_payload.append({"role": m['role'], "content": m['content']})

        self.current_ai_response = ""

        self.chat_thread = JobAssistantChatThread(self.logic, api_payload, config)
        self.chat_thread.stream_signal.connect(self.append_chat_stream)
        self.chat_thread.debug_signal.connect(self.append_canvas_debug)
        self.chat_thread.error_signal.connect(lambda error_text: self.append_chat_stream(f"\n[LỖI API MẠNG]: {error_text}"))
        self.chat_thread.finished_signal.connect(self.on_chat_finished)
        self.chat_thread.start()

    def stop_message(self):
        self.logic.set_running_state("job_assistant_chat", False)
        self.btn_action.setText("Đang ngắt...")
        self.btn_action.setEnabled(False)

    def on_chat_finished(self):
        if self.current_ai_response:
            db.save_aia_chat_message(self.current_chat_id, "assistant", self.current_ai_response)
            
        self.append_chat_stream("\n\n")
        
        self.chat_input.setEnabled(True)
        self.chat_input.setPlaceholderText("Nhập tin nhắn hoặc nội dung công việc cần trợ lý hỗ trợ...")
        
        self.btn_action.setEnabled(True)
        self.btn_action.setText("Gửi ➢")
        self.btn_action.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; border-radius: 3px; padding: 6px 15px;")
        
        self.list_conversations.setEnabled(True)
        self.btn_new_chat.setEnabled(True)
        
        self.refresh_chat_list(select_chat_id=self.current_chat_id)
        self.chat_input.setFocus()

        # [CẢI TIẾN] Kích hoạt luồng chưng cất ngầm sau khi đã nhường 500ms cho EventLoop nhả khóa giao diện
        QTimer.singleShot(500, self._check_and_run_memory_builder)

    def _check_and_run_memory_builder(self):
        """Hàm con đóng vai trò kích hoạt luồng dọn rác bộ nhớ sau khi UI đã được giải phóng"""
        curr_s = db.get_aia_session_by_id(self.current_chat_id)
        if curr_s and curr_s['chat_sum_counter'] >= 10:
            preset_id = self.combo_server.currentData()
            config = db.get_ai_config_by_id(preset_id)
            if config:
                prompt_template = self.get_cached_prompt(
                    'aia_systemprompt_memory', 
                    'Nhiệm vụ của bạn là chưng cất trí nhớ. Gộp tóm tắt cũ và tin nhắn mới. Trích xuất số liệu thành "Key = Value;".\nTRẢ VỀ JSON: {"summary": "...", "datasheet": "..."}\n[TÓM TẮT CŨ]: {old_summary}\n[SỔ SỐ LIỆU CŨ]: {old_datasheet}\n[TIN NHẮN MỚI]:\n{new_messages}'
                )
                self.append_canvas_debug("\n[HỆ THỐNG]: Đã chạm ngưỡng 10 tin nhắn. Đang chạy ngầm AI chưng cất Sổ số liệu...\n")
                self.memory_thread = MemoryBuilderThread(self.logic, self.current_chat_id, config, prompt_template)
                self.memory_thread.finished_signal.connect(self.on_memory_built)
                self.memory_thread.start()

    def on_memory_built(self, success, log_message):
        if success:
            self.append_canvas_debug(f"\n[HỆ THỐNG]: {log_message}\n")
            self.load_current_chat_history()
            self.refresh_chat_list(select_chat_id=self.current_chat_id)
        else:
            self.append_canvas_debug(f"\n[HỆ THỐNG - LỖI]: {log_message}\n")

    def on_title_generated(self, chat_id, new_title):
        self.refresh_chat_list(select_chat_id=self.current_chat_id)