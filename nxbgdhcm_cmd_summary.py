import os
import sys
import time
import json
import re
import threading
import signal
from datetime import datetime
import requests

# Bật hỗ trợ màu ANSI cho Windows CMD/PowerShell
os.system('') 

class Colors:
    SYSTEM = '\033[93m'      # Vàng
    SUCCESS = '\033[92m'     # Xanh lá
    ERROR = '\033[91m'       # Đỏ
    INFO = '\033[97m'        # Trắng
    AI_THINK = '\033[94m'    # Xanh dương sáng (Bright Blue)
    AI_STREAM = '\033[32m'   # Xanh lá cây đậm (Dark Green)
    WARNING = '\033[95m'     # Hồng tím (Magenta)
    ANIM = '\033[93m'        # Vàng (Dành cho vệt sáng ASCII)
    RESET = '\033[0m'

# Xử lý Namespace Import an toàn
try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False
    print(f"{Colors.ERROR}[LOI FATAL] Chưa cài đặt mysql-connector-python. Hãy chạy lệnh: pip install mysql-connector-python{Colors.RESET}")
    sys.exit(1)

# ==========================================
# BIẾN TOÀN CỤC & CẤU HÌNH
# ==========================================
API_URL = ""
MODEL = ""
API_KEY = ""
HEADERS = {}

is_running = True # Cờ hiệu điều khiển vòng đời app

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SQL_INI_FILE = os.path.join(BASE_DIR, "sql.ini")

# Hệ thống ghi Log JSON
LOGS_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)
SESSION_LOG_FILE = os.path.join(LOGS_DIR, f"summary_{datetime.now().strftime('%y%m%d-%H%M%S')}.log")

# Mặc định kết nối CSDL (sẽ bị ghi đè bởi sql.ini)
DB_USER = ""
DB_PASS = ""
DB_HOST = ""
DB_PORT = 3306
DB_NAME = ""

# ==========================================
# HÀM BẮT SỰ KIỆN CTRL+C (GRACEFUL EXIT)
# ==========================================
def signal_handler(sig, frame):
    global is_running
    if is_running:
        is_running = False
        log("\n[DUNG] Đã nhận lệnh dừng (Ctrl+C)! Đang hoàn tất tiến trình cuối trước khi ngủ đông...", "warning")
    else:
        log("\n[CANH BAO] Ép buộc thoát ngay lập tức!", "error")
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ==========================================
# HÀM LOG CLI VÀ GHI FILE JSON
# ==========================================
def log(message, level="info"):
    now = datetime.now()
    console_time = now.strftime("[%y-%m-%d] [%H:%M:%S]")
    json_time = now.strftime("%y-%m-%d :: %H:%M:%S")
    
    color = Colors.INFO
    if level == "system": color = Colors.SYSTEM
    elif level == "success": color = Colors.SUCCESS
    elif level == "error": color = Colors.ERROR
    elif level == "warning": color = Colors.WARNING
    elif level == "ai": color = Colors.AI_THINK
    
    print(f"{color}{console_time} {message}{Colors.RESET}")
    
    if level != "ai":
        try:
            log_entry = {
                "thời điểm": json_time,
                "thông báo": message
            }
            with open(SESSION_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

# ==========================================
# HÀM XỬ LÝ MYSQL
# ==========================================
def init_sql_config():
    global DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
    if not os.path.exists(SQL_INI_FILE):
        log(f"[CANH BAO] Không tìm thấy {SQL_INI_FILE}. Đang tạo cấu hình mẫu.", "warning")
        with open(SQL_INI_FILE, "w", encoding="utf-8") as f:
            f.write("ip: 192.168.192.12\nport: 3306\nuser: nxbgdhcm\npass: chitan1811\ndatabase: nxbgdhcm_vanban\n")
    try:
        with open(SQL_INI_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == "ip": DB_HOST = v
                    elif k == "port": DB_PORT = int(v) if v.isdigit() else 3306
                    elif k == "user": DB_USER = v
                    elif k == "pass": DB_PASS = v
                    elif k == "database": DB_NAME = v
    except Exception as e:
        log(f"[LOI] Lỗi đọc file sql.ini: {e}", "error")

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST, 
        port=DB_PORT, 
        user=DB_USER, 
        password=DB_PASS, 
        database=DB_NAME
    )

# ==========================================
# CẤU HÌNH AI VÀ PROMPT
# ==========================================
def load_connections():
    global API_URL, MODEL, API_KEY, HEADERS
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Ưu tiên lấy Default = 1, hoặc '1', hoặc 'True'
        c.execute("SELECT Preset_Name, URL, Model_Name, API_Key, `Default` FROM ket_noi_ai")
        rows = c.fetchall()
        c.close()
        conn.close()

        if not rows:
            log("[LOI] Bảng ket_noi_ai trên Database đang trống! Vui lòng cấu hình AI trước.", "error")
            sys.exit(1)

        # Lọc tìm preset mặc định (Default = 1 hoặc chuỗi '1'/'true')
        selected = None
        for r in rows:
            if str(r[4]).lower() in ['1', 'true']:
                selected = r
                break
        if not selected:
            selected = rows[0] # Fallback lấy cái đầu tiên
            
        name, API_URL, MODEL, API_KEY, _ = selected
        HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
        log(f"[KET NOI] Đã thiết lập liên kết Server A.I: [{name}]", "success")
        
    except Exception as e: 
        log(f"[LOI] Tải cấu hình AI từ Database thất bại: {e}", "error")
        sys.exit(1)

def load_document_types(db_conn):
    types = []
    try:
        c = db_conn.cursor()
        c.execute("SELECT Loai_VB FROM loai_van_ban")
        rows = c.fetchall()
        types = [row[0].strip() for row in rows if row[0]]
        c.close()
        if types:
            return ", ".join(types)
    except Exception as e:
        log(f"[CANH BAO] Lỗi tải danh mục loại văn bản từ DB: {e}", "warning")
    return ""

def get_prompt_summary(db_conn, doc_types_str=""):
    try:
        db_conn.ping(reconnect=True, attempts=3, delay=1)
        c = db_conn.cursor()
        c.execute("SELECT Prompt_Content FROM cau_hinh_prompt WHERE Prompt_Key = 'prompt_cmd_summary'")
        row = c.fetchone()
        c.close()
        prompt = row[0] if row else ""
    except:
        prompt = ""
        
    if not prompt:
        prompt = 'Bạn là một hệ thống AI chuyên gia về phân tích tài liệu của Nhà xuất bản. BẠN PHẢI TRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT. TUYỆT ĐỐI KHÔNG giải thích.\nNhiệm vụ của bạn là đọc nội dung văn bản dưới đây và trả về 2 trường theo cấu trúc Json:\n1. "Loại văn bản": Phân loại văn bản dựa vào danh sách sau: {types_instruction}. Nếu không chắc chắn, hãy ghi là "Văn bản".\n2. "Summary": Tóm tắt toàn bộ nội dung chứa các từ khóa quan trọng, KHÔNG dài dòng, KHÔNG có câu chào/giới thiệu, NGẮN GỌN TRONG TỐI ĐA 100 TỪ.\n\nLƯU Ý QUAN TRỌNG: \n1. Kết quả bắt buộc bắt đầu bằng { và kết thúc bằng }.\n2. Trả về đúng 2 key: "Loại văn bản" và "Summary".\n\n[NỘI DUNG VĂN BẢN]:\n'
        
    types_instruction = f'[{doc_types_str}]' if doc_types_str else 'danh sách nội bộ'
    return prompt.replace('{types_instruction}', types_instruction)

def extract_json(text):
    try: return json.loads(text, strict=False)
    except: pass
    
    match = re.search(r'`{3}(?:json)?(.*?)`{3}', text, re.DOTALL | re.IGNORECASE)
    if match:
        try: return json.loads(match.group(1).strip(), strict=False)
        except: pass
        
    start, end = text.find('{'), text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try: return json.loads(text[start:end+1], strict=False)
        except: pass
        
    # Bóc tách Regex thô cứu cánh
    result = {}
    type_match = re.search(r'"Loại văn bản"\s*:\s*"?(.*?)"?(?:,|"Summary"|\Z)', text, re.IGNORECASE)
    if type_match: result["Loại văn bản"] = type_match.group(1).strip()
    
    sum_match = re.search(r'"Summary"\s*:\s*"?(.*?)"?(?:,|\Z)', text, re.IGNORECASE | re.DOTALL)
    if sum_match: 
        res_sum = sum_match.group(1).strip()
        if res_sum.endswith('}'): res_sum = res_sum[:-1].strip()
        if res_sum.endswith('"'): res_sum = res_sum[:-1].strip()
        result["Summary"] = res_sum
        
    if result: return result
    return None

# ==========================================
# CƠ CHẾ GỌI API & HOẠT ẢNH TERMINAL
# ==========================================
def call_ai_stream(prompt_text, file_name, current_idx, total):
    global is_running
    messages = [{"role": "user", "content": prompt_text}]
    payload = {"model": MODEL, "messages": messages, "stream": True, "temperature": 0.2, "max_tokens": 1500}
    full_response = ""
    
    now_str = datetime.now().strftime("[%y-%m-%d] [%H:%M:%S]")
    msg = f"{Colors.AI_THINK}[A.I] Phân tích {Colors.SUCCESS}{current_idx}/{total}{Colors.AI_THINK} : {Colors.SYSTEM}{file_name}{Colors.AI_THINK} "
        
    print(f"\n{Colors.INFO}{now_str}{Colors.RESET} {msg}", end="", flush=True)

    is_waiting = True
    def light_anim():
        frames = ["▓▒░░░", "▒▓▒░░", "░▒▓▒░", "░░▒▓▒", "░░░▒▓", "░░▒▓▒", "░▒▓▒░", "▒▓▒░░"]
        i = 0
        while is_waiting and is_running:
            print(f"{Colors.ANIM}{frames[i % len(frames)]}{Colors.RESET}", end="", flush=True)
            time.sleep(0.15)
            if is_waiting and is_running:
                print("\b" * 5, end="", flush=True)
            i += 1
        print("\b" * 5 + " " * 5 + "\b" * 5, end="", flush=True)
    
    anim_thread = threading.Thread(target=light_anim)
    anim_thread.start()
    
    try:
        with requests.post(API_URL, headers=HEADERS, json=payload, stream=True, timeout=120) as response:
            response.raise_for_status()
            first_chunk = False
            
            for line in response.iter_lines():
                if not is_running: break
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        if data_str == "[DONE]": break
                        try:
                            data = json.loads(data_str)
                            chunk = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if chunk:
                                if not first_chunk:
                                    is_waiting = False
                                    anim_thread.join(timeout=2)
                                    if is_running: 
                                        print(f"\n{Colors.AI_STREAM}   => ", end="", flush=True)
                                    first_chunk = True
                                full_response += chunk
                                if is_running: 
                                    print(f"{Colors.AI_STREAM}{chunk}", end="", flush=True)
                        except json.JSONDecodeError: pass
    except Exception as e:
        is_waiting = False
        print(f"\n{Colors.INFO}{now_str}{Colors.RESET} {Colors.ERROR}[LOI] Lỗi kết nối AI: {e}{Colors.RESET}")
        return ""
        
    is_waiting = False
    print(Colors.RESET) 
    return full_response

# ==========================================
# TIẾN TRÌNH LÕI (CORE PROCESS)
# ==========================================
def smart_truncate(text, max_length=12000):
    """
    Thuật toán cắt văn bản thông minh chống tràn Token.
    Nếu văn bản quá dài, cắt lấy phần đầu và phần cuối (Nơi thường chứa thông tin quan trọng nhất).
    """
    if not text: return ""
    if len(text) <= max_length:
        return text
    half = max_length // 2
    return text[:half] + "\n\n...[ĐÃ LƯỢC BỎ BỚT NỘI DUNG GIỮA VÌ QUÁ DÀI]...\n\n" + text[-half:]

def process_summaries():
    global is_running
    db_conn = None
    try:
        db_conn = get_db_connection()
    except Exception as e:
        log(f"[LOI] Lỗi khởi tạo Database tổng: {e}", "error")
        return

    try:
        # Load danh sách loại văn bản làm kim chỉ nam
        doc_types_str = load_document_types(db_conn)
        base_prompt = get_prompt_summary(db_conn, doc_types_str)

        log("[TRUY VAN] Đang tìm kiếm các văn bản chưa được Tóm tắt...", "info")
        c = db_conn.cursor(dictionary=True)
        # Chỉ lấy những file có full_text và chưa có summary
        c.execute("""
            SELECT md5, person_key, file_name, full_text 
            FROM documents 
            WHERE (summary IS NULL OR summary = '') AND full_text IS NOT NULL AND full_text != ''
        """)
        target_docs = c.fetchall()
        c.close()

        total_docs = len(target_docs)
        if total_docs == 0:
            log("[HOAN TAT] Tuyệt vời! Toàn bộ CSDL đã được tóm tắt đầy đủ, không còn hồ sơ nào ứ đọng.", "success")
            return

        log(f"[QUET] Tìm thấy {total_docs} văn bản cần tóm tắt. Khởi động AI Engine...", "system")
        
        processed_count = 0
        success_count = 0
        failed_docs = []

        for doc in target_docs:
            if not is_running: break
            processed_count += 1
            
            md5 = doc['md5']
            p_key = doc['person_key']
            f_name = doc['file_name']
            f_text = doc['full_text']

            # Cắt gọn nội dung để không bị quá tải AI
            optimized_text = smart_truncate(f_text)
            prompt = base_prompt + optimized_text

            ai_data = None
            # Retry mechanism (Bọc thép vòng lặp)
            for attempt in range(3):
                if not is_running: break
                raw_response = call_ai_stream(prompt, f_name, processed_count, total_docs)
                ai_data = extract_json(raw_response)
                
                if ai_data and ai_data.get("Summary"):
                    break
                else:
                    if is_running: log(f"[CANH BAO] JSON lỗi hoặc AI không tóm tắt được, đang thử lại (Lần {attempt+2})...", "warning")
                    time.sleep(2)

            if not is_running: break

            if ai_data and ai_data.get("Summary"):
                try:
                    # Ping DB để chắc chắn không rớt kết nối sau thời gian dài AI suy nghĩ
                    db_conn.ping(reconnect=True, attempts=3, delay=1)
                    update_c = db_conn.cursor()
                    
                    loai_vb = ai_data.get("Loại văn bản", "").strip()
                    summary = ai_data.get("Summary", "").strip()
                    
                    # Update thẳng vào DB (Giữ nguyên doc_type cũ nếu AI không bóc được loai_vb)
                    update_query = """
                        UPDATE documents 
                        SET summary = %s, 
                            doc_type = CASE WHEN %s != '' THEN %s ELSE doc_type END
                        WHERE md5 = %s AND person_key = %s
                    """
                    update_c.execute(update_query, (summary, loai_vb, loai_vb, md5, p_key))
                    db_conn.commit()
                    update_c.close()
                    
                    success_count += 1
                    log(f"[THANH CONG] Đã lưu tóm tắt cho {f_name}", "success")
                except Exception as e:
                    log(f"[LOI GHI DB] Không thể lưu kết quả của {f_name}: {e}", "error")
                    failed_docs.append(f_name)
            else:
                log(f"[LOI] A.I từ chối trích xuất thông tin cho: {f_name}", "error")
                failed_docs.append(f_name)

        # Tổng kết báo cáo
        if is_running:
            log(f"\n{'='*60}", "system")
            log(f"[TONG KET] Xử lý: {processed_count}/{total_docs} | Thành công: {success_count} | Lỗi: {len(failed_docs)}", "system")
            if failed_docs:
                log(f"[DANH SACH LOI] {', '.join(failed_docs)}", "warning")
            log(f"{'='*60}\n", "system")

    except Exception as e: 
        if is_running: log(f"\n[LOI FATAL] LỖI HỆ THỐNG NẶNG: {e}", "error")
    finally:
        if db_conn:
            try: db_conn.close()
            except: pass

# ==========================================
# KHỞI CHẠY (ENTRY POINT)
# ==========================================
if __name__ == "__main__":
    log("\n" + "="*60, "system")
    log("[HE THONG] ROBOT TÓM TẮT & PHÂN LOẠI TỰ ĐỘNG - NXBGDHCM", "system")
    log("="*60 + "\n", "system")
    
    init_sql_config()
    load_connections()
    
    # Kích hoạt ngay lập tức mà không cần hỏi thêm thao tác nào
    process_summaries()