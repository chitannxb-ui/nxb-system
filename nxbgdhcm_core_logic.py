import os
import sys
import hashlib
import requests
import json
import re
import base64
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

try: import docx
except ImportError: docx = None
try: import pandas as pd
except ImportError: pd = None
try: import pptx
except ImportError: pptx = None
try:
    import win32com.client as win32
    import pythoncom
except ImportError:
    win32 = None; pythoncom = None

try: import fitz
except ImportError: fitz = None
try: from pdf2image import convert_from_path
except ImportError: convert_from_path = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "AI_Temp")
POPPLER_PATH = os.path.join(BASE_DIR, "poppler", "Library", "bin")

class OCRLogic:
    def __init__(self):
        self.running_states = {"ocr": False, "split": False, "rename": False, "search": False}
        if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)
            
    def get_missing_libs(self):
        missing = []
        if not docx: missing.append("python-docx")
        if not pd: missing.append("pandas")
        if not pptx: missing.append("python-pptx")
        if not win32: missing.append("pywin32")
        if not fitz: missing.append("PyMuPDF (fitz)")
        if not convert_from_path: missing.append("pdf2image")
        if not pillow_heif: missing.append("pillow-heif (Hỗ trợ ảnh iPhone)")
        return missing

    def get_all_target_files(self, folder_path):
        target_files = []
        valid_exts = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.heic', '.heif', 
                      '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                      '.txt', '.csv', '.xml', '.rtf', '.py']
        try:
            for root_dir, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.startswith('~$') or file.startswith('._'): continue
                    ext = os.path.splitext(file)[1].lower()
                    if ext in valid_exts:
                        filepath = os.path.join(root_dir, file)
                        try:
                            if os.path.getsize(filepath) == 0: continue
                            target_files.append(filepath)
                        except: pass
            return target_files
        except Exception as e: return str(e)

    def toggle_running_state(self, task_key):
        if task_key in self.running_states:
            self.running_states[task_key] = not self.running_states[task_key]
            return self.running_states[task_key]
        return False

    # FIX: Hàm setter chuẩn mực để không truy cập thẳng vào biến dictionary
    def set_running_state(self, task_key, state: bool):
        if task_key in self.running_states:
            self.running_states[task_key] = state

    def is_running(self, task_key):
        return self.running_states.get(task_key, False)

    def calculate_md5(self, filepath):
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""): hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception: return None
            
    def clean_word_text(self, text):
        text = re.sub(r'[\x07\x0b\x0c]', '\n', text)
        return re.sub(r'\n+', '\n', text).strip()
        
    def merge_signers(self, existing_signers, new_signers):
        if not new_signers: return existing_signers
        if not existing_signers: return new_signers
        existing_list = [s.strip() for s in re.split(r'[,;]', existing_signers) if s.strip()]
        new_list = [s.strip() for s in re.split(r'[,;]', new_signers) if s.strip()]
        for s in new_list:
            if s not in existing_list: existing_list.append(s)
        return ", ".join(existing_list)

    def resize_image_for_ai(self, img_path, output_path, max_size=1920):
        try:
            img = Image.open(img_path).convert("RGB")
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1.0: img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
            img.save(output_path, "JPEG", quality=90)
            return True
        except: return False

    def get_pdf_page_count(self, filepath):
        if fitz:
            try:
                doc = fitz.open(filepath)
                total = len(doc); doc.close()
                return total
            except: pass
        return 1

    def render_pdf_page_to_image(self, filepath, page_num, output_path):
        if convert_from_path:
            try:
                images = convert_from_path(filepath, first_page=page_num, last_page=page_num, poppler_path=POPPLER_PATH, dpi=200)
                if images:
                    images[0].save(output_path, 'JPEG', quality=90)
                    return True
            except: pass
        if fitz:
            try:
                doc = fitz.open(filepath)
                page = doc.load_page(page_num - 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                pix.save(output_path)
                doc.close()
                return True
            except: pass
        return False

    def generate_thumbnail(self, filepath, output_path):
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.heic', '.heif']:
                img = Image.open(filepath).convert("RGB")
                img.thumbnail((300, 300))
                img.save(output_path, "JPEG")
                return True, ""
            elif ext == '.pdf':
                if fitz:
                    doc = fitz.open(filepath)
                    page = doc.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
                    pix.save(output_path)
                    doc.close()
                    return True, ""
                elif convert_from_path:
                    images = convert_from_path(filepath, first_page=1, last_page=1, poppler_path=POPPLER_PATH, dpi=100)
                    if images:
                        images[0].save(output_path, 'JPEG')
                        return True, ""
            return False, "Không hỗ trợ tạo ảnh thu nhỏ cho định dạng này."
        except Exception as e:
            return False, str(e)

    def execute_custom_pdf_split(self, input_pdf_path, blocks_to_cut, output_dir):
        if not fitz: return False, "Thiếu thư viện PyMuPDF (fitz)"
        if not os.path.exists(output_dir): return False, "Thư mục đích không tồn tại"
        
        try:
            doc = fitz.open(input_pdf_path)
            results = []
            
            for pages, filename in blocks_to_cut:
                if not pages: continue
                new_doc = fitz.Document()
                for p in pages:
                    new_doc.insert_pdf(doc, from_page=p-1, to_page=p-1)
                
                out_path = os.path.join(output_dir, filename)
                new_doc.save(out_path)
                new_doc.close()
                results.append(filename)
                
            doc.close()
            return True, results
        except Exception as e:
            return False, str(e)

    def extract_text_from_file(self, filepath, ext):
        text_content = ""
        try:
            if ext == '.docx' and docx:
                doc = docx.Document(filepath)
                text_content = "\n".join([para.text for para in doc.paragraphs])
            elif ext in ['.xlsx', '.xls', '.csv'] and pd:
                if ext == '.csv':
                    df = pd.read_csv(filepath)
                    text_content = df.to_string(index=False)
                else:
                    xls = pd.ExcelFile(filepath)
                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(filepath, sheet_name=sheet_name)
                        text_content += f"\n--- Sheet: {sheet_name} ---\n"
                        text_content += df.to_string(index=False)
            elif ext in ['.pptx', '.ppt'] and pptx:
                prs = pptx.Presentation(filepath)
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text_content += shape.text + "\n"
            elif ext in ['.txt', '.xml', '.py', '.rtf']:
                for enc in ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']:
                    try:
                        with open(filepath, 'r', encoding=enc) as f:
                            text_content = f.read()
                        break 
                    except UnicodeDecodeError: continue
            elif ext == '.doc' and win32:
                word = win32.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(filepath)
                text_content = doc.Content.Text
                doc.Close()
                word.Quit()
        except Exception as e:
            print(f"Lỗi đọc text file {filepath}: {e}")
            return None
            
        return self.clean_word_text(text_content)

    def get_prompt_page_evaluation_v2(self, prev_text=""):
        return f"""Bạn là hệ thống phân tích hình ảnh văn bản.
Hình ảnh mà bạn nhận được là 1 trang trong một tập các văn bản.
[Nội dung Trang trước]:
{prev_text if prev_text else "Không có dữ liệu"}

TRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT:
{{
    "Phân tích": "1 trang" | "Trang đầu" | "Trang tiếp" | "Trang cuối" | "Trang trắng",
    "Toàn văn": "Nội dung toàn văn của trang văn bản."
}}"""

    def get_prompt_page_1(self, doc_types_str=""):
        types_instruction = f'Dựa vào danh sách sau: [{doc_types_str}]. ' if doc_types_str else ''
        return f"""Bạn là một hệ thống trích xuất dữ liệu API tự động. BẠN PHẢI TRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT. TUYỆT ĐỐI KHÔNG giải thích.
- Hãy trích xuất các nội dung sau theo cấu trúc Json: "Loại văn bản" ({types_instruction}nếu không rõ ghi "Văn bản"); "Số văn bản"; "Ngày" (2 số); "Tháng" (2 số); "Năm" (4 số); "Đơn vị soạn văn bản"; "Người ký" (Nếu nhiều người thì cách nhau bằng dấu phẩy); "Toàn văn" (nếu là ảnh scan của văn bản, trả về nội dung toàn văn, nếu là ảnh chụp/bản vẽ, trả về nội dung phân tích chi tiết bức ảnh).
LƯU Ý QUAN TRỌNG: 1. Bắt buộc bắt đầu bằng {{ và kết thúc bằng }}. 2. Luôn đặt trường "Toàn văn" ở cuối cùng."""

    def get_prompt_page_n(self):
        return """Bạn là một hệ thống trích xuất dữ liệu API. TRẢ VỀ ĐÚNG MỘT KHỐI JSON.
Trích xuất: "Người ký"; "Toàn văn". 1. Luôn đặt "Toàn văn" ở cuối cùng trong JSON."""

    def get_prompt_text_metadata(self, doc_types_str="", text_content=""):
        types_instruction = f'Gợi ý loại văn bản: [{doc_types_str}]. ' if doc_types_str else ''
        return f"""Dưới đây là phần đầu của một văn bản (đã được bóc tách thành Text).
Nhiệm vụ của bạn là đọc Text này và trích xuất ra các thông tin Siêu dữ liệu (Metadata).
BẠN PHẢI TRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT, KHÔNG GIẢI THÍCH THÊM.

[Nội dung Văn bản]:
{text_content}

[Cấu trúc JSON yêu cầu]:
{{
    "Loại văn bản": "({types_instruction}Ví dụ: Quyết định, Báo cáo, Hợp đồng, Mã nguồn, Bảng tính...)",
    "Số văn bản": "(Số hiệu nếu có)",
    "Ngày": "(2 số)",
    "Tháng": "(2 số)",
    "Năm": "(4 số)",
    "Đơn vị soạn văn bản": "",
    "Người ký": ""
}}"""

    def get_prompt_rename(self, template, meta_json, summary, ext, rejected_names):
        reject_str = f"\n- TUYỆT ĐỐI TRÁNH CÁC TÊN SAU: {', '.join(rejected_names)}" if rejected_names else ""
        template_str = f"theo cấu trúc: '{template}'" if template.strip() else "ngắn gọn, xúc tích, phản ánh đúng nội dung."
        
        return f"""Bạn là một trợ lý đặt tên file thông minh. Dựa vào thông tin sau đây của một văn bản, hãy đặt một tên file mới {template_str}.

[THÔNG TIN VĂN BẢN]:
Metadata: {json.dumps(meta_json, ensure_ascii=False)}
Tóm tắt nội dung: {summary}

YÊU CẦU BẮT BUỘC:
- Tên file bắt buộc phải kết thúc bằng đuôi '{ext}'.
- Trả về ĐÚNG MỘT KHỐI JSON DUY NHẤT chứa tên file mới.{reject_str}

CẤU TRÚC JSON TRẢ VỀ:
{{
    "Tên mới": "ten_file_ban_nghi_ra{ext}" 
}}"""

    def test_ai_connection(self, url, model, api_key):
        if not url.startswith("http"): url = "http://" + url
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        payload = {"model": model, "messages": [{"role": "user", "content": "Hãy trả lời ngắn gọn nếu bạn nhận được tin này."}], "temperature": 0.1, "max_tokens": 50}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status() 
            data = response.json()
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return True, reply.strip() if reply else f"Thành công, nhưng AI trả lời rỗng."
        except Exception as e: return False, f"Lỗi: {e}"

    def extract_json(self, text, is_page_1=False):
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
            
        result = {}
        signer_match = re.search(r'"Người ký"\s*:\s*"?(.*?)"?(?:,|"Toàn văn"|\Z)', text, re.IGNORECASE | re.DOTALL)
        if signer_match: result["Người ký"] = signer_match.group(1).strip().strip('"').strip()
        tv_match = re.search(r'"Toàn văn"\s*:\s*(.*)', text, re.IGNORECASE | re.DOTALL)
        if tv_match:
            tv_text = tv_match.group(1).strip()
            if tv_text.startswith('"'): tv_text = tv_text[1:]
            if tv_text.endswith('}'): tv_text = tv_text[:-1].strip()
            if tv_text.endswith('"'): tv_text = tv_text[:-1].strip()
            result["Toàn văn"] = tv_text
        if is_page_1:
            for key in ["Loại văn bản", "Số văn bản", "Ngày", "Tháng", "Năm", "Đơn vị soạn văn bản"]:
                m = re.search(f'"{key}"\\s*:\\s*"?(.*?)"?(?:,|$)', text, re.IGNORECASE)
                if m: result[key] = m.group(1).strip().strip('"').strip()
        
        pt_match = re.search(r'"Phân tích"\s*:\s*"?(.*?)"?(?:,|}|\Z)', text, re.IGNORECASE)
        if pt_match: result["Phân tích"] = pt_match.group(1).strip().strip('"')
        
        nm_match = re.search(r'"Tên mới"\s*:\s*"?(.*?)"?(?:,|}|\Z)', text, re.IGNORECASE)
        if nm_match: result["Tên mới"] = nm_match.group(1).strip().strip('"')
        
        if result.get("Toàn văn") or result.get("Người ký") or result.get("Phân tích") or result.get("Tên mới") or (is_page_1 and result.get("Loại văn bản")): return result
        return None

    def call_ai_stream_generator(self, url, model, api_key, prompt_text, base64_img=None, task_key=None):
        if not url.startswith("http"): url = "http://" + url
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        messages = []
        if base64_img: messages.append({"role": "user", "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}]})
        else: messages.append({"role": "user", "content": prompt_text})
        payload = {"model": model, "messages": messages, "stream": True, "temperature": 0.1, "max_tokens": 4000}
        
        try:
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=300) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if task_key and not self.is_running(task_key): break
                    if line:
                        decoded_line = line.decode('utf-8').strip()
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]
                            if data_str == "[DONE]": break
                            try:
                                data = json.loads(data_str)
                                chunk = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if chunk: yield chunk
                            except: pass
        except Exception as e: yield f"\n[LỖI LIÊN KẾT: {str(e)}]\n"

    def call_ai_chat_stream_generator(self, url, model, api_key, messages_list, task_key=None):
        if not url.startswith("http"): url = "http://" + url
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        payload = {"model": model, "messages": messages_list, "stream": True, "temperature": 0.7, "max_tokens": 4000}
        try:
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if task_key and not self.is_running(task_key): break
                    if line:
                        decoded_line = line.decode('utf-8').strip()
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]
                            if data_str == "[DONE]": break
                            try:
                                data = json.loads(data_str)
                                chunk = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if chunk: yield chunk
                            except: pass
        except Exception as e: yield f"\n[LỖI API: {str(e)}]\n"