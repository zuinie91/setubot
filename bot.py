import os
import random
import time
import json
import threading
from datetime import datetime
import telebot

# ===== 配置区域 - 使用环境变量 =====
BOT_TOKEN = os.getenv('BOT_TOKEN', '7536812234:AAG7MIHquaQZdjnIZ3okEIx-Zc7kvaLhR7o')
ADMIN_ID = int(os.getenv('ADMIN_ID', '8120969259'))
IMAGES_DIR = os.getenv('IMAGES_DIR', 'downloaded_images')
STATS_FILE = os.getenv('STATS_FILE', 'bot_stats.json')
GROUP_SETTINGS_FILE = os.getenv('GROUP_SETTINGS_FILE', 'group_settings.json')
# =================================

# 创建必要目录
os.makedirs(IMAGES_DIR, exist_ok=True)

# 初始化日志
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

# 初始化数据存储
def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                return json.load(f)
        except Exception as e:
            log(f"加载 {file} 失败: {e}", "ERROR")
    return default

def save_json(data, file):
    try:
        with open(file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存 {file} 失败: {e}", "ERROR")

# 加载数据
def load_data():
    global stats, group_settings
    
    stats = load_json(STATS_FILE, {
        "total_users": set(),
        "group_chats": set(),
        "command_count": {"start": 0, "setu": 0, "gb": 0, "tj": 0, "autopic": 0},
        "last_reset": str(datetime.now())
    })
    
    # 转换 set 类型
    stats["total_users"] = set(stats.get("total_users", []))
    stats["group_chats"] = set(stats.get("group_chats", []))
    
    group_settings = load_json(GROUP_SETTINGS_FILE, {})
    
    log(f"已加载 {len(group_settings)} 个群组设置")
    log(f"已存储 {len(os.listdir(IMAGES_DIR))} 张图片")

# 保存数据
def save_data():
    # 转换为可序列化的列表
    stats_to_save = stats.copy()
    stats_to_save["total_users"] = list(stats_to_save["total_users"])
    stats_to_save["group_chats"] = list(stats_to_save["group_chats"])
    
    save_json(stats_to_save, STATS_FILE)
    save_json(group_settings, GROUP_SETTINGS_FILE)

# 初始化机器人
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ===== 数据自动保存线程 =====
def auto_save_thread():
    while True:
        time.sleep(1800)  # 每30分钟保存一次
        save_data()
        log("数据自动保存完成")

# ===== 群组图片功能 =====
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    try:
        if bot.get_me().id in [user.id for user in message.new_chat_members]:
            chat_id = message.chat.id
            stats["group_chats"].add(chat_id)
            if str(chat_id) not in group_settings:
                group_settings[str(chat_id)] = {"auto_pic": False}
            save_data()
            bot.reply_to(message, "👋 感谢添加！使用 /autopic 开启/关闭自动发图功能")
    except Exception as e:
        log(f"处理新成员出错: {e}", "ERROR")

@bot.message_handler(commands=['autopic'])
def toggle_auto_pic(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # 检查权限
        if message.chat.type in ["group", "supergroup"]:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status not in ["administrator", "creator"]:
                bot.reply_to(message, "❌ 仅群组管理员可操作")
                return
        
        # 切换设置
        if str(chat_id) not in group_settings:
            group_settings[str(chat_id)] = {"auto_pic": True}
        else:
            current = group_settings[str(chat_id)].get("auto_pic", False)
            group_settings[str(chat_id)]["auto_pic"] = not current
        
        status = "✅ 已开启" if group_settings[str(chat_id)]["auto_pic"] else "❌ 已关闭"
        bot.reply_to(message, f"{status}自动发图功能")
        stats["command_count"]["autopic"] += 1
        save_data()
    except Exception as e:
        log(f"切换自动发图出错: {e}", "ERROR")

@bot.message_handler(func=lambda msg: str(msg.chat.id) in group_settings and 
                    group_settings[str(msg.chat.id)].get("auto_pic", False) and
                    random.random() < 0.05)
def send_random_group_pic(message):
    try:
        images = os.listdir(IMAGES_DIR)
        if images:
            selected = random.choice(images)
            with open(os.path.join(IMAGES_DIR, selected), 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="❤ 色图来喽！")
                log(f"向群组 {message.chat.id} 发送图片: {selected}")
    except Exception as e:
        log(f"群组发图失败: {str(e)}", "ERROR")

# ===== 原有功能增强 =====
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # 区分私聊和群组
        if message.chat.type == "private":
            stats["total_users"].add(user_id)
        else:
            stats["group_chats"].add(chat_id)
        
        stats["command_count"]["start"] += 1
        save_data()
        
        text = """
✨ *欢迎使用色图机器人！* ✨

• /se /setu - 获取随机色图
• /autopic - 群组自动发图开关
• /help - 查看帮助指南

客服 @naicha35
        """
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        log(f"发送欢迎消息出错: {e}", "ERROR")

@bot.message_handler(commands=['se', 'setu'])
def send_random_image(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name
        stats["command_count"]["setu"] += 1
        save_data()
        
        images = os.listdir(IMAGES_DIR)
        if images:
            selected = random.choice(images)
            with open(os.path.join(IMAGES_DIR, selected), 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=f"{username}，你的色图来了！ ❤")
                log(f"向用户 {user_id} 发送图片: {selected}")
        else:
            bot.reply_to(message, "🛑 图片库为空")
    except Exception as e:
        log(f"发送随机图片出错: {e}", "ERROR")
        bot.reply_to(message, "❌ 发送失败，请稍后再试")

# ===== 管理员命令 =====
def is_admin(user_id):
    return user_id == ADMIN_ID

@bot.message_handler(func=lambda msg: is_admin(msg.from_user.id) and msg.text.startswith('/gb'))
def broadcast_message(message):
    try:
        if " " not in message.text:
            bot.reply_to(message, "⚠️ 格式错误：/gb 广播内容")
            return
            
        content = message.text.split(' ', 1)[1]
        users = list(stats["total_users"])
        groups = list(stats["group_chats"])
        success = 0
        
        # 向所有用户发送
        for user_id in users:
            try:
                bot.send_message(user_id, f"【管理员广播】\n{content}")
                success += 1
            except Exception as e:
                log(f"用户 {user_id} 广播失败: {e}", "WARNING")
        
        # 向所有群组发送
        for group_id in groups:
            try:
                bot.send_message(group_id, f"【管理员广播】\n{content}")
                success += 1
            except Exception as e:
                log(f"群组 {group_id} 广播失败: {e}", "WARNING")
        
        stats["command_count"]["gb"] += 1
        save_data()
        bot.reply_to(message, f"📢 广播发送完成！\n成功接收: {success}/{len(users)+len(groups)}")
        log(f"管理员广播: {content[:50]}..., 成功率: {success}/{len(users)+len(groups)}")
    except Exception as e:
        log(f"广播消息出错: {e}", "ERROR")

@bot.message_handler(func=lambda msg: is_admin(msg.from_user.id) and msg.text == '/tj')
def show_stats(message):
    try:
        stats["command_count"]["tj"] += 1
        save_data()
        
        report = f"""
📊 *机器人使用统计*
- 累计用户: {len(stats["total_users"])}
- 群组数量: {len(stats["group_chats"])}
- 图片请求: {stats["command_count"]["setu"]}
- 广播发送: {stats["command_count"]["gb"]}
- 自动发图: {stats["command_count"]["autopic"]}
- 上次重置: {stats["last_reset"]}
        """
        bot.reply_to(message, report.strip(), parse_mode="Markdown")
    except Exception as e:
        log(f"生成统计报告出错: {e}", "ERROR")

# ===== 启动机器人 =====
def run_bot():
    while True:
        try:
            log("===== 机器人启动 =====")
            load_data()
            # 启动自动保存线程
            threading.Thread(target=auto_save_thread, daemon=True).start()
            
            log("开始轮询消息...")
            bot.infinity_polling()
        except Exception as e:
            log(f"机器人崩溃: {str(e)}", "CRITICAL")
            save_data()  # 尝试在崩溃前保存数据
            log("5秒后尝试重启...")
            time.sleep(5)

if __name__ == '__main__':
    run_bot()
