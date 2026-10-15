import time
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)

def process_via_pancake(phone_number, source, nhu_cau):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        
        # Load state đăng nhập của Pancake
        state_file = "pancake_state.json"
        if os.path.exists(state_file):
            context = browser.new_context(storage_state=state_file)
        else:
            print("❌ Lỗi: Không tìm thấy file pancake_state.json. Vui lòng thêm secret PANCAKE_STATE trên GitHub Actions.")
            browser.close()
            return False
            
        page = context.new_page()
        
        print(f"🚀 Bắt đầu tương tác Pancake với SĐT: {phone_number} (Nguồn: {source})")
        try:
            page.goto("https://pages.fm/", timeout=45000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2) 
            
            # Kiểm tra xem Server Pancake có bị sập (502 / 504) không
            content = page.content()
            if "502 Bad Gateway" in content or "504 Gateway Time-out" in content:
                print("❌ Lỗi: Server Pancake hiện đang sập (502/504 Bad Gateway).")
                try:
                    page.screenshot(path="error.png")
                except:
                    pass
                browser.close()
                return "SERVER_ERROR"

            # Kiểm tra xem có bị văng đăng nhập không
            if page.locator("text=Đăng nhập").is_visible() or "login" in page.url:
                print("❌ Lỗi: Phiên đăng nhập Pancake đã hết hạn. Cần lấy lại pancake_state.json mới.")
                try:
                    page.screenshot(path="error.png")
                except:
                    pass
                browser.close()
                return False

            # --- CẤU HÌNH PANCAKE ---
            TARGET_DASHBOARD = "Eztech Consultant"
            
            # --- KỊCH BẢN THEO NGUỒN ---
            MESSAGE_TEMPLATES = {
                "contact-page": "Chào bạn, mình là Eztech Consultant. Mình thấy bạn để lại thông tin qua website, không biết EzTech có thể hỗ trợ gì cho bạn!",
                "report:quan-tri-pl": "Chào bạn, cảm ơn bạn đã quan tâm đến báo cáo Quản trị PL. Kết bạn với mình để nhận tư vấn file chi tiết nhé!",
                "report:cong-no-phai-thu-tr": "Chào bạn, cảm ơn bạn đã quan tâm đến báo cáo Công nợ phải thu. Kết bạn với mình để nhận tư vấn file chi tiết nhé!",
                "course:data-finance": "Chào bạn, cảm ơn bạn đã quan tâm đến khóa học Data Finance của EzTech. Mình xin phép kết bạn để gửi bạn thông tin chi tiết nhé!",
                "course:data-business": "Chào bạn, cảm ơn bạn đã quan tâm đến khóa học Data in Business của EzTech. Mình xin phép kết bạn để gửi bạn thông tin chi tiết nhé!",
                "data-talk-20": "Chào bạn, cảm ơn bạn đã đăng ký tham gia sự kiện Data Talk 20. Kết bạn với mình để nhận thông tin sự kiện nhé!",
                "service:dao-tao": "Chào bạn, cảm ơn bạn đã quan tâm đến dịch vụ đào tạo của Eztech. Mình xin phép kết bạn để gửi bạn thông tin chi tiết nhé!",
                "qua-tang-file-aio": "Chào bạn, mình là Eztech Consultant. Mình xin phép kết bạn để gửi bạn thông tin về bộ file AIO miễn phí bên mình nhé!",
                "qua-tang-prompt-ai": "Chào bạn, mình là Eztech Consultant. Mình xin phép kết bạn để gửi bạn thông tin về bộ file prompt AI miễn phí bên mình nhé!",
                "Landing khóa AI cho Kế toán" : "Chào bạn, mình là Eztech Consultant. Mình xin phép kết bạn để gửi bạn thông tin về khoá học AI dành riêng cho kế toán bên mình nhé!"
            }
            
            # Lấy kịch bản dựa vào tên nguồn trong sheet, nếu nguồn lạ thì dùng câu mặc định
            MESSAGE = MESSAGE_TEMPLATES.get(source, "Chào bạn, mình là Eztech Consultant. Mình xin phép kết bạn để trao đổi chi tiết hơn về dịch vụ bên mình nhé ạ!")
            
            print(f"🔍 Đang tìm kiếm Dashboard: '{TARGET_DASHBOARD}'...")
            dashboard_item = page.locator('.dashboard-page-item', has_text=TARGET_DASHBOARD).first
            dashboard_item.wait_for(state="visible", timeout=30000)
            dashboard_item.click(force=True)
            
            page.wait_for_load_state('domcontentloaded')
            time.sleep(1.5)
            
            print("Đang mở menu tạo tin nhắn...")
            # Nút tạo tin nhắn / tìm kiếm SĐT (click trực tiếp, không cần hover SVG cũ)
            target_button = page.locator('button.conversation-menu-item.create-conversation-button').first
            target_button.wait_for(state="visible", timeout=10000)
            target_button.click(force=True)
            time.sleep(1.5)
            
            print(f"🔍 Nhập SĐT {phone_number}...")
            target_input = page.get_by_placeholder("Nhập số điện thoại")
            target_input.wait_for(state="visible", timeout=10000)
            target_input.click()
            target_input.fill(phone_number)
            target_input.press("Enter")
            
            time.sleep(2)
            # Kiểm tra xem có thông báo không tìm thấy không
            notice = page.locator('.ant-notification-notice-description', has_text="Không tìm thấy")
            if notice.count() > 0 and notice.first.is_visible():
                print(f"❌ Không tìm thấy SĐT {phone_number} trên hệ thống.")
                browser.close()
                return "NOT_FOUND"

            print("Nhấn Kết bạn lần 1...")
            # Nếu sau 5s không có nút Kết bạn thì số này không dùng Zalo / không tìm thấy
            try:
                target_button4 = page.get_by_text("Kết bạn").first
                target_button4.wait_for(state="visible", timeout=5000)
                target_button4.click(force=True)
            except Exception:
                print(f"❌ Không tìm thấy SĐT {phone_number} (Không xuất hiện nút Kết bạn).")
                browser.close()
                return "NOT_FOUND"
            
            print("Điền nội dung tin nhắn...")
            # Tìm trực tiếp ô nhập liệu trong hộp thoại
            target_input2 = page.locator('textarea.ant-input, input.ant-input, textarea').last
            target_input2.wait_for(state="visible", timeout=10000)
            target_input2.fill(MESSAGE)
            
            time.sleep(1.5)
            print("Nhấn Kết bạn lần 2 (Xác nhận)...")
            # Xác định chính xác nút Kết bạn (màu xanh/color-primary) trong footer của modal gửi lời mời kết bạn
            target_button5 = None
            candidates = [
                page.locator('.send-friend-request-modal .ant-modal-footer button.color-primary'),
                page.locator('.send-friend-request-modal button.color-primary'),
                page.locator('.send-friend-request-modal .ant-modal-footer button').last,
                page.locator('.ant-modal-footer button', has_text="Kết bạn").first,
                page.locator('button.ant-btn-primary.color-primary', has_text="Kết bạn").first
            ]
            
            for btn in candidates:
                try:
                    if btn.count() > 0 and btn.first.is_visible():
                        target_button5 = btn.first
                        break
                except:
                    continue
                    
            if not target_button5:
                target_button5 = page.locator('.send-friend-request-modal button', has_text="Kết bạn").first
                target_button5.wait_for(state="visible", timeout=5000)
                
            target_button5.click(force=True)
            print(f"✅ Đã gửi kết bạn thành công tới {phone_number} bằng kịch bản: '{MESSAGE}'")
            
            # Đợi modal gửi kết bạn đóng lại hoàn toàn
            try:
                page.locator('.send-friend-request-modal').wait_for(state="hidden", timeout=6000)
            except:
                pass
            time.sleep(1)
            
            # --- BỔ SUNG: MỞ HỘP THOẠI NHẮN TIN ---
            try:
                print("Đang mở hộp thoại Nhắn tin/Ghi chú...")
                target_button6 = page.locator('.item-actions button, button').filter(has_text="Nhắn tin").first
                target_button6.wait_for(state="visible", timeout=7000)
                target_button6.click(force=True)
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ Cảnh báo: Không thể bấm nút Nhắn tin: {e}")

            # --- BỔ SUNG: GHI CHÚ VÀO PANCAKE ---
            try:
                print("Đang nhập nội dung ghi chú...")
                target_input3 = page.locator('textarea[placeholder*="ghi chú"], textarea.rc-textarea, [placeholder*="Nhập ghi chú"]').first
                target_input3.wait_for(state="visible", timeout=7000)
                target_input3.click(force=True)
                
                note_content = f"Nguồn: {source} | Nhu cầu: {nhu_cau}"
                target_input3.fill(note_content)
                target_input3.press("Enter")
                print(f"✅ Đã gửi ghi chú thành công: '{note_content}'")
            except Exception as e:
                print(f"⚠️ Cảnh báo: Lỗi khi điền ghi chú: {e}")
                
            # --- BỔ SUNG: GỬI TIN NHẮN CHÀO HỎI ---
            try:
                time.sleep(1)
                print("Đang gửi tin nhắn chào hỏi...")
                reply_box = page.locator('#replyBoxComposer, textarea[placeholder*="Trả lời từ"]').first
                reply_box.wait_for(state="visible", timeout=7000)
                reply_box.click(force=True)
                reply_box.fill(MESSAGE)
                reply_box.press("Enter")
                print(f"✅ Đã gửi tin nhắn chào hỏi thành công: '{MESSAGE}'")
            except Exception as e:
                print(f"⚠️ Cảnh báo: Lỗi khi nhắn tin: {e}")
                
            # --- BỔ SUNG: GẮN THẺ (TAG) ---
            try:
                time.sleep(1)
                print("Đang gắn thẻ 'Web'...")
                tag_button = page.locator('button.btn-tag-item', has_text="Web").first
                tag_button.wait_for(state="visible", timeout=7000)
                tag_button.click(force=True)
                print("✅ Đã gắn thẻ 'Web' thành công")
            except Exception as e:
                print(f"⚠️ Cảnh báo: Lỗi khi gắn thẻ: {e}")
                
            time.sleep(1.5)
            browser.close()
            return True
            
        except Exception as e:
            print(f"❌ Xảy ra lỗi khi xử lý SĐT {phone_number}: {e}")
            try:
                page.screenshot(path="error.png")
                print("📸 Đã chụp ảnh màn hình lưu vào error.png")
            except:
                pass
            time.sleep(3)
            browser.close()
            return False

def main():
    print("⏳ Đang kiểm tra Google Sheet lấy dữ liệu mới...")
    client = gspread.authorize(CREDS)
    # TODO: Thay thế ĐIỀN_LINK_SHEET bằng URL Google Sheet thực tế của bạn
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1BTZJgFpH662ehdWVV2WafL4Cyzegu23Ueiz4fXKvfK8/edit?gid=0#gid=0").sheet1 
    
    all_values = sheet.get_all_values()
    has_new_numbers = False
    
    # Bỏ qua dòng tiêu đề (dòng 0), chạy từ dòng 1 trở đi
    for i in range(1, len(all_values)):
        row = all_values[i]
        
        # Đảm bảo row có đủ 8 cột (Cột H là cột thứ 8, index = 7)
        while len(row) < 8:
            row.append("")
            
        # Làm sạch tuyệt đối: Lọc bỏ toàn bộ ký tự lạ (chỉ giữ lại số)
        raw_phone = row[2]
        phone = ''.join(filter(str.isdigit, raw_phone))
        # Nếu có đầu 84 (do +84 lọc mất dấu +), tự động chuyển thành số 0
        if phone.startswith("84") and len(phone) >= 10:
            phone = "0" + phone[2:]
            
        source = row[6].strip()  # Cột G (Nguồn)
        status = row[7].strip()  # Cột H (Trạng thái)
        
        # Lấy dữ liệu cột F (Nhu cầu), nếu bảng thiếu cột F thì để trống
        nhu_cau = row[5].strip() if len(row) > 5 else ""
        
        if phone and (not status or status == "Lỗi Timeout"): # Nếu có SĐT và cột Trạng thái đang trống hoặc bị Lỗi Timeout
            # Tạm thời bỏ qua nguồn ezexcel-dung-thu
            SKIP_SOURCES = [
                "ezexcel-dung-thu",
                "ezexcel-dung-thu | zalo/zalo/zalo",
                "ezhoadon-dung-thu",
                "ezexcel-dung-thu | chatgpt.com",
                "hoi-vien",
            ]
            
            # Tự động bỏ qua nếu nguồn trùng khớp hoặc bắt đầu bằng các từ khóa trên
            if any(source == s or source.startswith(s) for s in SKIP_SOURCES):
                continue

            if source in SKIP_SOURCES:
                continue
                
            has_new_numbers = True
            print(f"🔥 Phát hiện SĐT mới: {phone} ở dòng {i + 1} (Nguồn: {source})")
            
            # Xử lý kết bạn với cơ chế Retry tối đa 2 lần để tránh tốn thời gian
            max_retries = 2
            for attempt in range(1, max_retries + 1):
                success = process_via_pancake(phone, source, nhu_cau)
                
                # Nếu server sập thì thoát luôn toàn bộ tiến trình, không làm phiền tiếp
                if success == "SERVER_ERROR":
                    print("🛑 Server Pancake đang gặp sự cố (502/504). Dừng đợt chạy này để bảo vệ số phút!")
                    return

                # Nếu thành công (True) hoặc nhận diện chắc chắn số không tồn tại ("NOT_FOUND") thì thoát vòng lặp
                if success is True or success == "NOT_FOUND":
                    break
                    
                # Nếu lỗi Timeout (False) và chưa hết số lượt thử
                if attempt < max_retries:
                    print(f"⚠️ Pancake bị lag/timeout với SĐT {phone} (Lần thử {attempt}/{max_retries}). Thử lại sau 5s...")
                    time.sleep(5)
            
            # Đánh dấu trạng thái vào cột H
            try:
                if success is True:
                    sheet.update_cell(i + 1, 8, "Đã gửi KB")
                elif success == "NOT_FOUND":
                    sheet.update_cell(i + 1, 8, "Không tìm thấy")
                else:
                    sheet.update_cell(i + 1, 8, "Lỗi Timeout")
            except Exception as e:
                print(f"⚠️ Lỗi khi cập nhật Google Sheet: {e}")
                
            # Khoảng nghỉ an toàn giữa các lượt thao tác
            print("⏳ Chờ 5s trước khi chạy số tiếp theo...")
            time.sleep(5)
            
    if not has_new_numbers:
        print("✅ Trạng thái: Tất cả các số điện thoại trong Sheet đã được xử lý.")

if __name__ == "__main__":
    main()
