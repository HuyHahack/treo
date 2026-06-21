import os
import audioop
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask, jsonify
import threading

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("Chưa set DISCORD_TOKEN trong environment!")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

class VoiceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.treo_owner = {}  # Lưu user_id đã treo (chỉ để tham khảo)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Đã sync slash commands!")

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f"✅ {bot.user} đã sẵn sàng!")

# Xóa owner khi bot rời voice (do bị kick hoặc lỗi)
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and after.channel is None:
        if bot.treo_owner:
            bot.treo_owner.clear()
            print("🗑️ Đã xóa toàn bộ owner do bot rời voice.")

# ----- LỆNH /treo (chỉ 1 lần, lưu owner) -----
@bot.tree.command(name="treo", description="Treo bot vào voice channel của bạn")
async def treo(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Bạn phải ở trong voice channel để dùng lệnh này!")
        return

    guild = interaction.guild
    voice_client = guild.voice_client

    if voice_client is not None:
        await interaction.response.send_message("❌ Bot đã được treo ở một voice channel rồi!")
        return

    if interaction.user.id in bot.treo_owner:
        await interaction.response.send_message("❌ Bạn đã treo bot trước đó! Dùng /thoat để thả bot ra.")
        return

    channel = interaction.user.voice.channel
    try:
        await channel.connect(timeout=30, reconnect=False)
        bot.treo_owner[interaction.user.id] = channel.id
        await interaction.response.send_message(f"✅ Đã treo bot vào voice **{channel.name}** thành công!")
    except Exception as e:
        # Nếu bot vẫn kết nối được dù có exception, coi như thành công
        if guild.voice_client is not None:
            bot.treo_owner[interaction.user.id] = channel.id
            await interaction.response.send_message(f"✅ Đã treo bot vào voice **{channel.name}** thành công!")
        else:
            await interaction.response.send_message(f"❌ Lỗi khi treo bot: {e}")

# ----- LỆNH /thoat (ai cũng dùng được, bỏ kiểm tra owner) -----
@bot.tree.command(name="thoat", description="Cho bot rời khỏi voice channel (ai cũng có thể dùng)")
async def thoat(interaction: discord.Interaction):
    guild = interaction.guild
    voice_client = guild.voice_client

    if voice_client is None:
        await interaction.response.send_message("❌ Bot hiện không ở trong voice channel nào!")
        return

    # Không cần kiểm tra quyền sở hữu nữa
    # Tuy nhiên, để an toàn, vẫn yêu cầu người dùng ở cùng voice với bot
    if not interaction.user.voice or interaction.user.voice.channel.id != voice_client.channel.id:
        await interaction.response.send_message("❌ Bạn phải ở cùng voice channel với bot để thả bot ra!")
        return

    try:
        await voice_client.disconnect()
        # Xóa owner tương ứng (nếu có)
        if interaction.user.id in bot.treo_owner:
            del bot.treo_owner[interaction.user.id]
        # Nếu không có owner cụ thể, nhưng bot rời, ta vẫn clear toàn bộ để reset
        else:
            bot.treo_owner.clear()
        await interaction.response.send_message("✅ Bot đã rời voice channel!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi khi thả bot: {e}")

# ------------------- WEB SERVER -------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord đang chạy!"

@app.route('/ping')
def ping():
    return jsonify({"status": "pong", "bot": str(bot.user) if bot.user else "Unknown"})

def run_webserver():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ------------------- KHỞI ĐỘNG -------------------
if __name__ == "__main__":
    threading.Thread(target=run_webserver, daemon=True).start()
    bot.run(TOKEN)
