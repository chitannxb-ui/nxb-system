import os
import sys
import json
import uuid
import platform
import getpass
import time
import pymysql
import pymysql.cursors

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SQL_INI_FILE = os.path.join(BASE_DIR, "sql.ini")
_appdata = os.getenv('APPDATA') or os.path.expanduser("~")
APPDATA_DIR = os.path.join(_appdata, "NXBGDHCM_OCR")
if not os.path.exists(APPDATA_DIR): os.makedirs(APPDATA_DIR)
KEY_FILE = os.path.join(APPDATA_DIR, "nhanviennxbgdhcm.json")

DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME = "", 3306, "", "", ""

class DBManager:
    def __init__(self):
        self.mac_address, self.computer_name, self.user_name = "", "", ""
        self.danh_xung, self.ho_ten, self.chuc_vu, self.phong_ban = "Bạn", "", "CBNV", "NXBGDHCM"
        self.person_key = "" 
        
    def init_person_key(self):
        mac_num = uuid.getnode()
        self.mac_address = ':'.join(('%012X' % mac_num)[i:i+2] for i in range(0, 12, 2))
        self.computer_name, self.user_name = platform.node(), getpass.getuser()

        if os.path.exists(KEY_FILE):
            try:
                with open(KEY_FILE, "r", encoding="utf-8") as f:
                    self.person_key = json.load(f).get("Person_key", "")
            except: pass

        if not self.person_key:
            self.person_key = str(uuid.uuid4())
            try:
                with open(KEY_FILE, "w", encoding="utf-8") as f:
                    json.dump({"Person_key": self.person_key, "Mac_Address": self.mac_address}, f, indent=4)
            except: pass
        return self.person_key, self.mac_address, self.computer_name, self.user_name

    def load_sql_ini(self):
        global DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
        if not os.path.exists(SQL_INI_FILE):
            try:
                with open(SQL_INI_FILE, "w", encoding="utf-8") as f: 
                    f.write("ip: 192.168.192.12\nport: 3306\nuser: nxbgdhcm\npass: chitan1811\ndatabase: nxbgdhcm_vanban\n")
            except: pass
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
        except: pass

    def get_connection(self, include_db=True, timeout=5):
        conn_params = {
            "host": DB_HOST, 
            "port": DB_PORT, 
            "user": DB_USER, 
            "password": DB_PASS, 
            "connect_timeout": timeout,
            "charset": 'utf8mb4'
        }
        if include_db: conn_params["database"] = DB_NAME
        return pymysql.connect(**conn_params)

    def setup_database_and_user(self):
        conn = None
        try:
            self.load_sql_ini(); self.init_person_key()
            conn = self.get_connection(include_db=False)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit(); cursor.close(); conn.close()

            conn = self.get_connection()
            cursor = conn.cursor()
            
            tables_sql = [
                '''CREATE TABLE IF NOT EXISTS nguoi_dung (Person_key VARCHAR(255) PRIMARY KEY, Mac_Address VARCHAR(100), Computer_Name VARCHAR(255), User_Name VARCHAR(255), danh_xung VARCHAR(11) DEFAULT NULL, Ho_Va_Ten VARCHAR(255) DEFAULT '', Chuc_vu VARCHAR(255) DEFAULT '', Phong_Ban VARCHAR(255) DEFAULT '') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;''',
                '''CREATE TABLE IF NOT EXISTS cau_hinh_prompt (Prompt_Key VARCHAR(50) PRIMARY KEY, Prompt_Content TEXT NOT NULL, prompt_type VARCHAR(50) NOT NULL DEFAULT 'in_app', Description VARCHAR(255) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;''',
                '''CREATE TABLE IF NOT EXISTS ket_noi_ai (ID INT(11) AUTO_INCREMENT PRIMARY KEY, Preset_Name VARCHAR(255), URL VARCHAR(500), Model_Name VARCHAR(100), API_Key VARCHAR(255), `Default` VARCHAR(10)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;''',
                '''CREATE TABLE IF NOT EXISTS loai_van_ban (ID INT(11) AUTO_INCREMENT PRIMARY KEY, Loai_VB VARCHAR(255) NOT NULL, Mo_ta VARCHAR(500) DEFAULT NULL, Tu_khoa VARCHAR(255) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;''',
                '''CREATE TABLE IF NOT EXISTS documents (md5 VARCHAR(255) NOT NULL, person_key VARCHAR(255) NOT NULL, file_name TEXT, file_path TEXT, file_type VARCHAR(50), doc_type VARCHAR(255), doc_number VARCHAR(255), doc_day VARCHAR(10), doc_month VARCHAR(10), doc_year VARCHAR(10), doc_org TEXT, doc_signer TEXT, full_text LONGTEXT, summary VARCHAR(255), last_scan BIGINT(20), Fixed TINYINT(4), PRIMARY KEY (md5, person_key)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;''',
                '''CREATE TABLE IF NOT EXISTS deleted_documents (md5 VARCHAR(255) NOT NULL, person_key VARCHAR(255) NOT NULL, file_name TEXT, file_path TEXT, file_type VARCHAR(50), doc_type VARCHAR(255), doc_number VARCHAR(255), doc_day VARCHAR(10), doc_month VARCHAR(10), doc_year VARCHAR(10), doc_org TEXT, doc_signer TEXT, full_text LONGTEXT, deleted_time BIGINT(20), PRIMARY KEY (md5, person_key)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;''',
                '''CREATE TABLE IF NOT EXISTS tao_van_ban (ID INT AUTO_INCREMENT PRIMARY KEY, Person_key VARCHAR(255), thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP, ten_van_ban VARCHAR(255), noi_dung LONGTEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;''',
                '''CREATE TABLE IF NOT EXISTS Tach_file (MD5 VARCHAR(255) NOT NULL, Trang INT NOT NULL, Toan_van LONGTEXT DEFAULT NULL, Nhan_xet VARCHAR(50), PRIMARY KEY (MD5, Trang)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;''',
                '''CREATE TABLE IF NOT EXISTS Lich_Su_Ten_File (ID INT AUTO_INCREMENT PRIMARY KEY, Person_key VARCHAR(255), MD5 VARCHAR(255), File_Path TEXT, Ten_Hien_Tai TEXT, Ten_Cu TEXT, Thoi_Diem TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;'''
            ]
            for sql in tables_sql: cursor.execute(sql)

            cursor.execute('''INSERT INTO nguoi_dung (Person_key, Mac_Address, Computer_Name, User_Name) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE Mac_Address=VALUES(Mac_Address), Computer_Name=VALUES(Computer_Name), User_Name=VALUES(User_Name)''', (self.person_key, self.mac_address, self.computer_name, self.user_name))
            
            cursor.execute("SELECT * FROM nguoi_dung WHERE Person_key = %s", (self.person_key,))
            user_row = cursor.fetchone()
            if user_row:
                self.danh_xung = user_row[4] or "Bạn"
                self.ho_ten = user_row[5] or ""
                self.chuc_vu = user_row[6] or "CBNV"
                self.phong_ban = user_row[7] or "NXBGDHCM"

            cursor.execute("SELECT COUNT(*) FROM ket_noi_ai")
            if cursor.fetchone()[0] == 0:
                cursor.execute('''INSERT INTO ket_noi_ai (Preset_Name, URL, Model_Name, API_Key, `Default`) VALUES ('AI_NXBGDHCM', 'http://127.0.0.1:8000/v1/chat/completions', 'gpt-3.5-turbo', 'TEST_KEY', 'TRUE')''')

            conn.commit()
            return True, f"Khởi tạo CSDL thành công."
        except Exception as e: return False, str(e)
        finally:
            if conn and conn.open: conn.close()

    def get_ai_presets(self):
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            # Đã thêm các trường cần thiết và điều kiện lọc person_key
            cursor.execute("SELECT ID, Preset_Name, URL, Model_Name, API_Key, `Default`, person_key FROM ket_noi_ai WHERE person_key IS NULL OR person_key = %s", (self.person_key,))
            presets = list(cursor.fetchall()) 
            for p in presets: p["Is_Default"] = True if str(p.get("Default", "")).upper() in ["TRUE", "1", "YES"] else False
            return True, presets
        except Exception as e: return False, str(e)
        finally:
            if conn and conn.open: conn.close()

    def get_ai_config_by_id(self, preset_id):
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT URL, Model_Name, API_Key FROM ket_noi_ai WHERE ID = %s", (preset_id,))
            config = cursor.fetchone()
            return config
        except: return None
        finally:
            if conn and conn.open: conn.close()

    def get_total_scanned_files(self):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM documents WHERE person_key = %s", (self.person_key,))
            count = c.fetchone()[0]
            return count
        except: return 0
        finally:
            if conn and conn.open: conn.close()

    def fetch_all_user_documents(self):
        conn = None
        try:
            conn = self.get_connection()
            c = conn.cursor(pymysql.cursors.DictCursor)
            # TỐI ƯU HIỆU NĂNG: KHÔNG SELECT full_text LÚC LOAD LIST BAN ĐẦU
            c.execute("SELECT md5, file_name, file_path, file_type, doc_type, doc_number, doc_day, doc_month, doc_year, doc_org, doc_signer, summary FROM documents WHERE person_key = %s", (self.person_key,))
            main_docs = list(c.fetchall()) 
            
            # Với văn bản tự tạo, cũng không nạp nội dung lúc đầu
            c.execute("SELECT ID, thoi_gian, ten_van_ban FROM tao_van_ban WHERE Person_key = %s", (self.person_key,))
            ai_rows = list(c.fetchall()) 
            
            created_docs = []
            for r in ai_rows:
                t = r['thoi_gian']
                day, month, year = (str(t.day).zfill(2), str(t.month).zfill(2), str(t.year)) if t else ("","","")
                created_docs.append({
                    'md5': f"db_ai_gen_{r['ID']}", 'file_name': r['ten_van_ban'], 'file_path': "", 'file_type': "html",
                    'doc_type': "Văn bản AI", 'doc_day': day, 'doc_month': month, 'doc_year': year, 'doc_org': "A.I Assistant",
                    'doc_signer': self.ho_ten, 'summary': "Văn bản do A.I tự động soạn thảo."
                })
            return True, main_docs, created_docs
        except Exception as e: return False, [], []
        finally:
            if conn and conn.open: conn.close()

    # HÀM MỚI: NẠP FULL TEXT THEO YÊU CẦU (ON DEMAND)
    def get_fulltext_by_md5(self, md5_hash):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            if md5_hash.startswith("db_ai_gen_"):
                doc_id = md5_hash.replace("db_ai_gen_", "")
                c.execute("SELECT noi_dung FROM tao_van_ban WHERE ID = %s AND Person_key = %s", (doc_id, self.person_key))
            else:
                c.execute("SELECT full_text FROM documents WHERE md5 = %s AND person_key = %s", (md5_hash, self.person_key))
            res = c.fetchone()
            return res[0] if res else ""
        except: return ""
        finally:
            if conn and conn.open: conn.close()

    def get_document_types_string(self):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT Loai_VB FROM loai_van_ban")
            types = [row[0].strip() for row in c.fetchall() if row[0]]
            if types: return ", ".join(types)
        except: pass
        finally:
            if conn and conn.open: conn.close()
        return ""

    def search_documents_fulltext(self, boolean_keywords, folder_paths=None):
        conn = None
        try:
            # Lúc tìm kiếm thì PHẢI LẤY full_text để cắt snippet
            sql_query = """
                SELECT md5, file_name, file_path, file_type, doc_type, doc_number, 
                       doc_day, doc_month, doc_year, doc_org, doc_signer, summary, full_text 
                FROM documents 
                WHERE person_key = %s AND MATCH(full_text) AGAINST(%s IN BOOLEAN MODE)
            """
            params = [self.person_key, boolean_keywords]
            
            if folder_paths:
                folder_conditions = []
                for path in folder_paths:
                    p = path.replace('\\', '/')
                    folder_conditions.append("(REPLACE(file_path, '\\\\', '/') LIKE %s OR REPLACE(file_path, '\\\\', '/') = %s)")
                    params.extend([f"{p}/%", p])
                sql_query += " AND (" + " OR ".join(folder_conditions) + ")"
                
            sql_query += " ORDER BY MATCH(full_text) AGAINST(%s IN BOOLEAN MODE) DESC;"
            params.append(boolean_keywords)

            conn = self.get_connection()
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(sql_query, tuple(params))
            results = list(c.fetchall()) 
            return results
        except Exception as e: return []
        finally:
            if conn and conn.open: conn.close()

    def check_file_md5_exists(self, md5_hash, filepath, filename):
        conn = None
        try:
            conn = self.get_connection(); ct = int(time.time())
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute("SELECT md5 FROM documents WHERE md5 = %s AND person_key = %s", (md5_hash, self.person_key))
            if c.fetchone():
                c.execute("UPDATE documents SET file_name=%s, file_path=%s, last_scan=%s WHERE md5=%s AND person_key=%s", (filename, filepath, ct, md5_hash, self.person_key))
                conn.commit()
                return True, "Đã có trong hệ thống"
            
            c.execute("SELECT * FROM deleted_documents WHERE md5 = %s AND person_key = %s", (md5_hash, self.person_key))
            row = c.fetchone()
            if row:
                c.execute("""INSERT INTO documents 
                             (md5, person_key, file_name, file_path, file_type, doc_type, doc_number, doc_day, doc_month, doc_year, doc_org, doc_signer, full_text, last_scan) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                          (row['md5'], row['person_key'], row['file_name'], row['file_path'], row['file_type'], row['doc_type'], row['doc_number'], row['doc_day'], row['doc_month'], row['doc_year'], row['doc_org'], row['doc_signer'], row['full_text'], ct))
                c.execute("DELETE FROM deleted_documents WHERE md5 = %s AND person_key = %s", (md5_hash, self.person_key))
                conn.commit()
                return True, "Khôi phục từ thùng rác"
            return False, "File mới"
        except Exception as e: return False, f"Lỗi: {e}"
        finally:
            if conn and conn.open: conn.close()

    def save_document(self, md5_hash, filename, filepath, file_type, metadata, full_text):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            c.execute('''INSERT INTO documents (md5, person_key, file_name, file_path, file_type, doc_type, doc_number, doc_day, doc_month, doc_year, doc_org, doc_signer, full_text, last_scan) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE file_name=VALUES(file_name), file_path=VALUES(file_path), file_type=VALUES(file_type), doc_type=VALUES(doc_type), doc_number=VALUES(doc_number), doc_day=VALUES(doc_day), doc_month=VALUES(doc_month), doc_year=VALUES(doc_year), doc_org=VALUES(doc_org), doc_signer=VALUES(doc_signer), full_text=VALUES(full_text), last_scan=VALUES(last_scan)''',
                      (md5_hash, self.person_key, filename, filepath, file_type, metadata.get("Loại văn bản", ""), metadata.get("Số văn bản", ""), metadata.get("Ngày", ""), metadata.get("Tháng", ""), metadata.get("Năm", ""), metadata.get("Đơn vị soạn văn bản", ""), metadata.get("Người ký", ""), full_text, int(time.time())))
            conn.commit()
        except: pass
        finally:
            if conn and conn.open: conn.close()

    def save_ai_generated_document(self, ten_van_ban, noi_dung):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            c.execute("INSERT INTO tao_van_ban (Person_key, ten_van_ban, noi_dung) VALUES (%s, %s, %s)", (self.person_key, ten_van_ban, noi_dung))
            new_id = c.lastrowid
            conn.commit()
            return True, new_id
        except: return False, None
        finally:
            if conn and conn.open: conn.close()

    def delete_ai_documents(self, ids):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            format_strings = ','.join(['%s'] * len(ids))
            query = f"DELETE FROM tao_van_ban WHERE ID IN ({format_strings}) AND Person_key = %s"
            params = ids + [self.person_key]
            c.execute(query, tuple(params))
            conn.commit()
            return True
        except: return False
        finally:
            if conn and conn.open: conn.close()

    def get_split_data(self, md5_hash):
        conn = None
        try:
            conn = self.get_connection()
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute("SELECT Trang, Toan_van, Nhan_xet FROM Tach_file WHERE MD5 = %s ORDER BY Trang ASC", (md5_hash,))
            results = list(c.fetchall()) 
            data_dict = {}
            for r in results: data_dict[r['Trang']] = {"Toan_van": r['Toan_van'], "Nhan_xet": r['Nhan_xet']}
            return True, data_dict
        except Exception as e: return False, {}
        finally:
            if conn and conn.open: conn.close()

    def save_split_page(self, md5_hash, page_num, toan_van, nhan_xet):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            tv_val = toan_van if (toan_van is not None and toan_van != "") else None
            c.execute('''INSERT INTO Tach_file (MD5, Trang, Toan_van, Nhan_xet) 
                         VALUES (%s, %s, %s, %s) 
                         ON DUPLICATE KEY UPDATE Toan_van=VALUES(Toan_van), Nhan_xet=VALUES(Nhan_xet)''',
                      (md5_hash, page_num, tv_val, nhan_xet))
            conn.commit()
            return True
        except: return False
        finally:
            if conn and conn.open: conn.close()

    # HÀM MỚI: Cập nhật CSDL hàng loạt khi user nhấn nút LƯU ở Trang 3
    def batch_update_split_evals(self, md5_hash, eval_dict):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            for page_num, nhan_xet in eval_dict.items():
                c.execute("UPDATE Tach_file SET Nhan_xet = %s WHERE MD5 = %s AND Trang = %s", (nhan_xet, md5_hash, page_num))
                if nhan_xet == "Trang trắng":
                    c.execute("UPDATE Tach_file SET Toan_van = '' WHERE MD5 = %s AND Trang = %s", (md5_hash, page_num))
            conn.commit()
            return True
        except: return False
        finally:
            if conn and conn.open: conn.close()

    def check_folder_files_in_db(self, md5_list):
        if not md5_list: return True
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor()
            format_strings = ','.join(['%s'] * len(md5_list))
            query = f"SELECT COUNT(DISTINCT md5) FROM documents WHERE person_key = %s AND md5 IN ({format_strings})"
            params = [self.person_key] + md5_list
            c.execute(query, tuple(params))
            found_count = c.fetchone()[0]
            return found_count == len(md5_list)
        except Exception: return False
        finally:
            if conn and conn.open: conn.close()

    def get_metadata_for_rename(self, md5_list):
        if not md5_list: return {}
        conn = None
        try:
            conn = self.get_connection()
            c = conn.cursor(pymysql.cursors.DictCursor)
            format_strings = ','.join(['%s'] * len(md5_list))
            query = f"SELECT md5, file_name, file_type, doc_type, doc_number, doc_day, doc_month, doc_year, doc_org, doc_signer, summary FROM documents WHERE person_key = %s AND md5 IN ({format_strings})"
            params = [self.person_key] + md5_list
            c.execute(query, tuple(params))
            results = c.fetchall()
            
            data = {}
            for r in results:
                meta = {
                    "Loại văn bản": r.get('doc_type', ''), "Số hiệu": r.get('doc_number', ''),
                    "Ngày tháng": f"{r.get('doc_day','')}/{r.get('doc_month','')}/{r.get('doc_year','')}".strip('/'),
                    "Cơ quan ban hành": r.get('doc_org', ''), "Người ký": r.get('doc_signer', '')
                }
                data[r['md5']] = {"old_name": r.get('file_name', ''), "meta": meta, "summary": r.get('summary', '')}
            return data
        except Exception: return {}
        finally:
            if conn and conn.open: conn.close()

    def update_filename_and_history(self, md5_hash, old_name, new_name, new_dir_path):
        conn = None
        try:
            conn = self.get_connection(); c = conn.cursor(); ct = int(time.time())
            c.execute("UPDATE documents SET file_name=%s, file_path=%s, last_scan=%s WHERE md5=%s AND person_key=%s", 
                      (new_name, new_dir_path, ct, md5_hash, self.person_key))
            
            c.execute("INSERT INTO Lich_Su_Ten_File (Person_key, MD5, File_Path, Ten_Hien_Tai, Ten_Cu) VALUES (%s, %s, %s, %s, %s)",
                      (self.person_key, md5_hash, new_dir_path, new_name, old_name))
            
            conn.commit()
            return True
        except: return False
        finally:
            if conn and conn.open: conn.close()

def get_prompt(self, prompt_key):
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Prompt_Content FROM cau_hinh_prompt WHERE Prompt_Key = %s", (prompt_key,))
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else ""
        except:
            return ""
        finally:
            if conn and conn.open: conn.close()

db = DBManager()