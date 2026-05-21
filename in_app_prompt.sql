INSERT INTO `cau_hinh_prompt` (`Prompt_Key`, `Prompt_Content`, `prompt_type`, `Description`) VALUES

-- 1. Prompt phân tích tách file PDF (nxbgdhcm_core_logic.py)
('prompt_page_split', 
'Bạn là hệ thống phân tích hình ảnh văn bản.\nHình ảnh mà bạn nhận được là 1 trang trong một tập các văn bản.\n[Nội dung Trang trước]:\n{prev_text}\n\nTRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT:\n{\n    "Phân tích": "1 trang" | "Trang đầu" | "Trang tiếp" | "Trang cuối" | "Trang trắng",\n    "Toàn văn": "Nội dung toàn văn của trang văn bản."\n}', 
'in_app', 
'Phục vụ tính năng tách tài liệu PDF tự động tại giao diện.'),

-- 2. Prompt OCR trích xuất trang đầu (nxbgdhcm_core_logic.py)
('prompt_ocr_page_1', 
'Bạn là một hệ thống trích xuất dữ liệu API tự động. BẠN PHẢI TRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT. TUYỆT ĐỐI KHÔNG giải thích.\n- Hãy trích xuất các nội dung sau theo cấu trúc Json: "Loại văn bản" ({types_instruction}nếu không rõ ghi "Văn bản"); "Số văn bản"; "Ngày" (2 số); "Tháng" (2 số); "Năm" (4 số); "Đơn vị soạn văn bản"; "Người ký" (Nếu nhiều người thì cách nhau bằng dấu phẩy); "Toàn văn" (nếu là ảnh scan của văn bản, trả về nội dung toàn văn, nếu là ảnh chụp/bản vẽ, trả về nội dung phân tích chi tiết bức ảnh).\nLƯU Ý QUAN TRỌNG: 1. Bắt buộc bắt đầu bằng { và kết thúc bằng }. 2. Luôn đặt trường "Toàn văn" ở cuối cùng.', 
'in_app', 
'Trích xuất siêu dữ liệu (Metadata) hành chính cho trang đầu tiên của văn bản ảnh/PDF.'),

-- 3. Prompt OCR trích xuất các trang sau (nxbgdhcm_core_logic.py)
('prompt_ocr_page_n', 
'Bạn là một hệ thống trích xuất dữ liệu API. TRẢ VỀ ĐÚNG MỘT KHỐI JSON.\nTrích xuất: "Người ký"; "Toàn văn". 1. Luôn đặt "Toàn văn" ở cuối cùng trong JSON.', 
'in_app', 
'Trích xuất nội dung toàn văn văn bản từ trang thứ 2 trở đi.'),

-- 4. Prompt bóc tách siêu dữ liệu từ file văn bản thô Word/Txt (nxbgdhcm_core_logic.py)
('prompt_text_metadata', 
'Dưới đây là phần đầu của một văn bản (đã được bóc tách thành Text).\nNhiệm vụ của bạn là đọc Text này và trích xuất ra các thông tin Siêu dữ liệu (Metadata).\nBẠN PHẢI TRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT, KHÔNG GIẢI THÍCH THÊM.\n\n[Nội dung Văn bản]:\n{text_content}\n\n[Cấu trúc JSON yêu cầu]:\n{\n    "Loại văn bản": "({types_instruction}Ví dụ: Quyết định, Báo cáo, Hợp đồng, Mã nguồn, Bảng tính...)",\n    "Số văn bản": "(Số hiệu nếu có)",\n    "Ngày": "(2 số)",\n    "Tháng": "(2 số)",\n    "Năm": "(4 số)",\n    "Đơn vị soạn văn bản": "",\n    "Người ký": ""\n}', 
'in_app', 
'Đọc hiểu văn bản thô để nội suy siêu dữ liệu không qua xử lý ảnh Vision.'),

-- 5. Prompt đổi tên tệp thông minh (nxbgdhcm_core_logic.py)
('prompt_file_rename', 
'Bạn là một trợ lý đặt tên file thông minh. Dựa vào thông tin sau đây của một văn bản, hãy đặt một tên file mới {template_str}.\n\n[THÔNG TIN VĂN BẢN]:\nMetadata: {meta_json}\nTóm tắt nội dung: {summary}\n\nYÊU CẦU BẮT BUỘC:\n- Tên file bắt buộc phải kết thúc bằng đuôi \'{ext}\'.\n- Trả về ĐÚNG MỘT KHỐI JSON DUY NHẤT chứa tên file mới.{reject_str}\n\nCẤU TRÚC JSON TRẢ VỀ:\n{\n    "Tên mới": "ten_file_ban_nghi_ra{ext}" \n}', 
'in_app', 
'Dựa vào Metadata và Tóm tắt để đặt tên file hệ thống theo mẫu.'),

-- 6. System Prompt điều hướng luồng trợ lý ảo (nxbgdhcm_page_search.py)
('prompt_system_chat', 
'Bạn là trợ lý của {danh_xung} {ho_ten}. Phản hồi JSON:\n1. Tìm kiếm: {"Yêu cầu": "Tìm kiếm", "Nội dung": "từ gốc, từ đồng nghĩa 1, từ đồng nghĩa 2, cụm từ liên quan 1, ... (Tạo ra 8 đến 12 từ/cụm từ liên quan, biến thể văn phong hành chính, mỗi cụm từ không vượt quá 5 chữ)"}\n2. Tạo văn bản: {"Yêu cầu": "Tạo văn bản", "Nội dung": "Mã HTML", "tên file": "tên"}\n3. Tán gẫu: Trả lời tự nhiên.', 
'in_app', 
'System Prompt cốt lõi điều hướng luồng tư duy nhận diện ý định của Trợ lý ảo.'),

-- 7. Prompt thẩm định kết quả tìm kiếm vòng 2 (nxbgdhcm_page_search.py)
('prompt_search_filter', 
'Người dùng yêu cầu tìm: [{user_query}]. Dưới đây là danh sách các file tìm được kèm nội dung trích dẫn. Hãy kiểm tra lại và CHỈ GIỮ LẠI những file thực sự liên quan đến yêu cầu. Trả về đúng một khối JSON DUY NHẤT chứa một mảng (Array), không giải thích thêm.\nCấu trúc JSON yêu cầu:\n[\n  {\n    "md5": "mã md5 của file",\n    "y_kien": "Lý do ngắn gọn tại sao file này liên quan"\n  }\n]\n\nDANH SÁCH FILE:\n', 
'in_app', 
'Lọc nâng cao vòng 2 để AI loại bỏ các kết quả tìm kiếm sai ngữ nghĩa ngữ cảnh.'),

-- 8. Prompt bóc tách trang sau dành cho Robot Indexing ngầm (nxbgdhcm_cmd_indexing.py)
('prompt_cmd_ocr_page_n', 
'Bạn là một hệ thống trích xuất dữ liệu API tự động. BẠN PHẢI TRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT.\nTrích xuất nội dung của trang này theo cấu trúc Json chỉ với 2 trường: "Người ký"; "Toàn văn" (nếu là ảnh scan của văn bản, trả về nội dung toàn văn, nếu là ảnh chụp/bản vẽ, trả về nội dung phân tích chi tiết bức ảnh).\nLƯU Ý QUAN TRỌNG: \n1. Luôn đặt trường "Toàn văn" ở cuối cùng trong khối JSON.\n2. Nếu gặp chữ ký không đọc được, ghi "[Ký tên và Đóng dấu]".', 
'in_app', 
'Sử dụng cho script dòng lệnh số hóa tự động chạy nền.'),

-- 9. Prompt chạy tiến trình Robot tóm tắt văn bản tự động (nxbgdhcm_cmd_summary.py)
('prompt_cmd_summary', 
'Bạn là một hệ thống AI chuyên gia về phân tích tài liệu của Nhà xuất bản. BẠN PHẢI TRẢ VỀ ĐÚNG MỘT KHỐI JSON DUY NHẤT. TUYỆT ĐỐI KHÔNG giải thích.\nNhiệm vụ của bạn là đọc nội dung văn bản dưới đây và trả về 2 trường theo cấu trúc Json:\n1. "Loại văn bản": Phân loại văn bản dựa vào danh sách sau: {types_instruction}. Nếu không chắc chắn, hãy ghi là "Văn bản".\n2. "Summary": Tóm tắt toàn bộ nội dung chứa các từ khóa quan trọng, KHÔNG dài dòng, KHÔNG có câu chào/giới thiệu, NGẮN GỌN TRONG TỐI ĐA 100 TỪ.\n\nLƯU Ý QUAN TRỌNG: \n1. Kết quả bắt buộc bắt đầu bằng { và kết thúc bằng }.\n2. Trả về đúng 2 key: "Loại văn bản" và "Summary".\n\n[NỘI DUNG VĂN BẢN]:\n', 
'in_app', 
'Nguồn prompt cho bot chạy ngầm tự động quét và thu gọn tóm tắt văn bản.')
ON DUPLICATE KEY UPDATE 
  `Prompt_Content` = VALUES(`Prompt_Content`), 
  `prompt_type` = VALUES(`prompt_type`), 
  `Description` = VALUES(`Description`);