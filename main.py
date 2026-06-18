import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import random
import sys
import signal

# --- CẤU HÌNH THÔNG TIN TÀI KHOẢN CỦA BẠN ---
TOKEN = '8884617053:AAFis8rXEU4MN9IBWamPW-0KQOEpYKHifX0'
OWNER_ID = 1087968824

bot = telebot.TeleBot(TOKEN)

# --- BỘ LƯU TRỮ TRẠNG THÁI (Lưu trên RAM) ---
bot_active = True            # Trạng thái ngủ/thức toàn cục của bot
activated_chats = set()      # Danh sách nhóm đã được Add
onchat_status = {}           # Bật/Tắt chế độ chửi hài hước từng nhóm
cc_status = {}               # Bật/Tắt chế độ chửi mất dạy từng nhóm
protected_users = {}         # Danh sách người được bảo vệ miễn nhiễm chửi tại từng nhóm
muted_users = {}             # Danh sách người bị khóa mõm: {chat_id: {user_id: thời_gian_hết_hạn}}

# --- KHO CÂU CHỬI KHỔNG LỒ (GỒM CẢ 2 CẤP ĐỘ) ---
CHUI_HAI_HUOC = [
    "Ăn nói xà lơ quá nha mậy, ra chuồng gà chơi đi!",
    "Đầu to mà óc như trái nho thế kia, bớt nói lại cho sang.",
    "Bố láo bố lếu quen thân, tí tao mách mẹ mày giờ.",
    "Nói câu nào nghe muốn tiền đình câu đó hà.",
    "Nghĩ mình là ai mà dám sủa gâu gâu ở đây hả bưởi?",
    "Gia đình nuôi ăn học để giờ vào đây cãi nhau với bot hả?",
    "Cái nết đánh chết cái đẹp, mà nhìn mày thì vừa xấu vừa mất nết.",
    "Não mày bị drop từ lúc lọt lòng rồi đúng không?",
    "Bớt tỏ ra nguy hiểm đi, cái độ dốt của mày lộ hết ra rồi.",
    "Người ta dùng não để tư duy, còn mày dùng não để làm cảnh à?",
    "Nói chuyện với mày thà tao đi nói chuyện với cái đầu gối còn có lý hơn.",
    "Tự tin là tốt nhưng tự tin kiểu ngáo ngơ như mày thì nên cất đi nha.",
    "Nhìn mặt cũng sáng sủa mà sao phát ngôn tối tăm vậy con?",
    "Nghe mày nói xong tao phải đi uống ngay viên thuốc hạ huyết áp.",
    "Đứng im đấy đừng cử động, để tao chụp tấm ảnh thờ cho."
]

CHUI_MAT_DAY = [
    "Ăn nói cẩn thận cái mồm m, thik t vả rụng răng ko?",
    "Loại m t chấp cả họ luôn đấy, bớt sủa dơ đi con lợn.",
    "M mù chữ hay sao mà vào đây kiếm chuyện vs bot?",
    "Mồm nhanh hơn não nó vừa vừa thôi, dthg mà dốt thế.",
    "Cút ngay trc khi t cho ăn liên hoàn vả, tml này.",
    "Nhìn m hãm l ko tả nổi, biến mẹ m đi cho sạch box.",
    "Mồm dơ thì ngậm lại, sủa ra thối hoắc cả cái nhóm.",
    "Sủa clg đấy thg mặt l, mún ăn đập ak?",
    "Não m chứa toàn bã đậu ak mà phát ngôn ngu l thế?",
    "Loại m ra đường chó nó còn khinh chứ tinh tướng cái j.",
    "Bố m nhịn m hơi lâu r đấy nhá thg ranh con.",
    "Sống tđn để ng ta nhìn vào chỉ mún nhổ bãi nước bọt vào mặt.",
    "Ăn j t cúng, sủa clm m à thg nhóc ranh.",
    "M ko có cửa nch vs t đâu, dbrrr rúc xó nào đi.",
    "Cay ko con zai? Cay thì làm j đc t nào hhh."
]

history_chui = {} # Bộ nhớ đệm lưu câu chửi tránh lặp quá 2 lần tại mỗi nhóm

# --- HÀM TRỢ GIÚP KIỂM TRA QUYỀN ADMIN ---
def is_chat_admin(chat_id, user_id):
    if chat_id > 0: return False
    if user_id == OWNER_ID: return True
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

# --- HÀM THUẬT TOÁN CHỐNG LẶP CÂU CHỬI QUÁ 2 LẦN ---
def get_unique_chui(chat_id, danh_sach):
    if chat_id not in history_chui: 
        history_chui[chat_id] = []
    
    available = [c for c in danh_sach if history_chui[chat_id].count(c) < 2]
    if not available:
        available = danh_sach
        history_chui[chat_id] = []
        
    cau_chon = random.choice(available)
    history_chui[chat_id].append(cau_chon)
    if len(history_chui[chat_id]) > 4: 
        history_chui[chat_id].pop(0)
    return cau_chon
# --- HÀM DỰNG MENU NÚT BẤM (INLINE KEYBOARD) ---
def build_menu_keyboard(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    
    txt_add = "✅ Đã Add (Bấm để Xadd)" if chat_id in activated_chats else "❌ Chưa Add (Bấm để Add)"
    txt_onchat = "🔥 Chửi Hài: BẬT" if onchat_status.get(chat_id, False) else "🍀 Chửi Hài: TẮT"
    txt_cc = "💀 Chửi Thấm: BẬT" if cc_status.get(chat_id, False) else "💤 Chửi Thấm: TẮT"
    txt_bot = "💤 Trạng thái: ĐANG NGỦ" if not bot_active else "🟢 Trạng thái: ĐANG THỨC"

    btn_add = InlineKeyboardButton(txt_add, callback_data="btn_toggle_add")
    btn_onchat = InlineKeyboardButton(txt_onchat, callback_data="btn_toggle_onchat")
    btn_cc = InlineKeyboardButton(txt_cc, callback_data="btn_toggle_cc")
    
    btn_mute = InlineKeyboardButton("🤫 Mute 36m", callback_data="btn_action_mute")
    btn_ban = InlineKeyboardButton("🔨 Ban Member", callback_data="btn_action_ban")
    btn_bv = InlineKeyboardButton("🛡️ Bảo Vệ (Bv)", callback_data="btn_action_bv")
    
    btn_sleep = InlineKeyboardButton(txt_bot, callback_data="btn_toggle_sleep")

    markup.add(btn_add)
    markup.add(btn_onchat, btn_cc)
    markup.add(btn_mute, btn_ban)
    markup.add(btn_bv, btn_sleep)
    return markup

# --- TRÌNH CHẶN/XỬ LÝ TIN NHẮN TOÀN CỤC ---
@bot.message_handler(func=lambda msg: True, content_types=['text', 'command'])
def main_handler(message):
    global bot_active
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text if message.text else ""

    if text.startswith('/start') and chat_id > 0:
        user_name = message.from_user.first_name
        bot.reply_to(message, f"Xin chào {user_name} đến với channel của @DCMMTCD")
        return

    if not bot_active:
        if text == '/menu' and user_id == OWNER_ID:
            bot.reply_to(message, "🛠️ Bảng điều khiển hệ thống của Đại ca:", reply_markup=build_menu_keyboard(chat_id))
        return

    if text == '/menu':
        if chat_id < 0 and chat_id not in activated_chats and not is_chat_admin(chat_id, user_id):
            return 
        bot.reply_to(message, "⚙️ **BẢNG ĐIỀU KHIỂN CHỨC NĂNG BOT**\n*(Hãy bấm nút bên dưới để sử dụng)*", parse_mode="Markdown", reply_markup=build_menu_keyboard(chat_id))
        return

    if chat_id < 0 and chat_id not in activated_chats:
        return

    if chat_id < 0 and chat_id in muted_users and user_id in muted_users[chat_id]:
        if time.time() < muted_users[chat_id][user_id]:
            try: bot.delete_message(chat_id, message.message_id)
            except: pass
            return
        else:
            del muted_users[chat_id][user_id]

    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)
    is_protected = (user_id == OWNER_ID or is_chat_admin(chat_id, user_id) or 
                    (chat_id in protected_users and user_id in protected_users[chat_id]))

    if is_reply_to_bot and not is_protected:
        try: bot.delete_message(chat_id, message.message_id)
        except: pass
        return

    if not is_protected:
        if cc_status.get(chat_id, False):
            bot.reply_to(message, get_unique_chui(chat_id, CHUI_MAT_DAY))
        elif onchat_status.get(chat_id, False):
            bot.reply_to(message, get_unique_chui(chat_id, CHUI_HAI_HUOC))

# --- XỬ LÝ SỰ KIỆN KHI ẤN NÚT TRÊN GIAO DIỆN MENU (CALLBACK QUERY) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_menu_click(call):
    global bot_active
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    is_admin = is_chat_admin(chat_id, user_id)
    is_owner = (user_id == OWNER_ID)

    if not is_admin and not is_owner:
        bot.answer_callback_query(call.id, "⚠️ Bạn không có quyền sử dụng bảng điều khiển này!", show_alert=True)
        return

    if call.data == "btn_toggle_sleep":
        if is_owner:
            bot_active = not bot_active
            status_msg = "Sẵn sàng hoạt động!" if bot_active else "Đang ngủ say, cấm làm phiền..."
            bot.answer_callback_query(call.id, f"Trạng thái bot: {status_msg}", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "⚠️ Chỉ duy nhất Chủ sở hữu mới được tắt/mở nguồn bot!", show_alert=True)
            return

    if not bot_active and call.data != "btn_toggle_sleep":
        bot.answer_callback_query(call.id, "😴 Bot hiện tại đang ngủ, không thể cấu hình nhóm lúc này!", show_alert=True)
        return

    if call.data == "btn_toggle_add":
        if chat_id in activated_chats:
            activated_chats.remove(chat_id)
            bot.answer_callback_query(call.id, "❌ Đã hủy kích hoạt nhóm (Xadd). Bot dừng hoạt động!", show_alert=True)
        else:
            activated_chats.add(chat_id)
            bot.answer_callback_query(call.id, "✅ Kích hoạt nhóm thành công (Add)!", show_alert=True)

    elif call.data == "btn_toggle_onchat":
        onchat_status[chat_id] = not onchat_status.get(chat_id, False)
        if not onchat_status[chat_id]: cc_status[chat_id] = False 
        bot.answer_callback_query(call.id, "Đã cập nhật chế độ Chửi Hài Hước!")

    elif call.data == "btn_toggle_cc":
        cc_status[chat_id] = not cc_status.get(chat_id, False)
        if cc_status[chat_id]: onchat_status[chat_id] = True 
        bot.answer_callback_query(call.id, "Đã cập nhật chế độ Chửi Siêu Thấm (/cc)!")

    elif call.data in ["btn_action_mute", "btn_action_ban", "btn_action_bv"]:
        reply_msg = call.message.reply_to_message
        if not reply_msg:
            bot.answer_callback_query(call.id, "⚠️ Hãy REPLY (trả lời) tin nhắn của mục tiêu trước khi bấm nút này!", show_alert=True)
            return
            
        target_id = reply_msg.from_user.id
        if target_id == OWNER_ID or is_chat_admin(chat_id, target_id):
            bot.answer_callback_query(call.id, "❌ Không thể áp dụng lên Chủ sở hữu hoặc Admin khác!", show_alert=True)
            return

        if call.data == "btn_action_mute":
            if chat_id not in muted_users: muted_users[chat_id] = {}
            muted_users[chat_id][target_id] = time.time() + (36 * 60)
            bot.answer_callback_query(call.id, "🤐 Đã khóa mõm người này 36 phút thành công!", show_alert=True)

        elif call.data == "btn_action_ban":
            try:
                bot.ban_chat_member(chat_id, target_id)
                bot.answer_callback_query(call.id, "🔨 Đã kích/ban thành viên khỏi nhóm vĩnh viễn!", show_alert=True)
            except:
                bot.answer_callback_query(call.id, "⚠️ Bot thiếu quyền Admin nhóm để Ban người này!", show_alert=True)

        elif call.data == "btn_action_bv":
            if chat_id not in protected_users: protected_users[chat_id] = set()
            protected_users[chat_id].add(target_id)
            bot.answer_callback_query(call.id, "🛡️ Đã thêm người này vào danh sách được bảo vệ thành công!", show_alert=True)

    try: bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_menu_keyboard(chat_id))
    except: pass

# ==================== PHẦN KẾT: XỬ LÝ KHI TẮT BOT ĐỘT NGỘT ====================
def signal_handler(sig, frame):
    print("\n[HỆ THỐNG] Đang tiến hành ngắt kết nối và tắt bot...")
    try:
        bot.send_message(OWNER_ID, "🛑 **[BÁO CÁO HỆ THỐNG]**\nBot đã được tắt nguồn an toàn bởi máy chủ. Hẹn gặp lại đại ca!")
    except Exception as e:
        print(f"Không thể gửi tin nhắn tắt nguồn: {e}")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ==================== PHẦN ĐẦU: XỬ LÝ KHI BẬT NGUỒN BOT ====================
import os
import uvicorn
import threading # Thêm thư viện này để chạy đa luồng

# Hàm phụ để chạy Uvicorn server ở một luồng riêng
def run_uvicorn():
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    # 1. Khởi hành luồng phụ để mở Port cho Render quét
    web_thread = threading.Thread(target=run_uvicorn)
    web_thread.daemon = True # Đảm bảo luồng này tắt khi luồng chính tắt
    web_thread.start()

    # 2. Các lệnh chạy Bot của bạn ở luồng chính (giữ nguyên từ dòng 257)
    print("[HỆ THỐNG] Bot đang chuẩn bị khởi động...")
    try:
        bot.send_message(OWNER_ID, "⚡ **[BÁO CÁO HỆ THỐNG]**\nBot đã khởi động thành công...")
    except Exception as e:
        print(f"Lưu ý: Chưa gửi được tin nhắn khởi động cho Owner: {e}")
        
    print("Siêu Bot tổng hợp đang vận hành ổn định...")
    bot.remove_webhook()
    
    # 3. Chạy vòng lặp vô hạn của Bot để duy trì ứng dụng
    bot.infinity_polling()

