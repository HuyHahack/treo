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
        self.treo_owner = {}  # user_id -> channel_id

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Đã sync slash commands!")

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f"✅ {bot.user} đã sẵn sàng!")

# ----- SỰ KIỆN TỰ ĐỘNG XÓA OWNER KHI BOT RỜI VOICE (do bị kick hoặc lỗi) -----
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and after.channel is None:
        if bot.treo_owner:
            bot.treo_owner.clear()
            print("🗑️ Đã xóa toàn bộ owner do bot rời voice.")

# ----- LỆNH /treo (public) -----
@bot.tree.command(name="treo", description="Treo bot vào voice channel của bạn")
async def treo(interaction: discord.Interaction):
    # 1. Kiểm tra user có ở voice không
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Bạn phải ở trong voice channel để dùng lệnh này!")
        return

    guild = interaction.guild
    voice_client = guild.voice_client

    # 2. Nếu bot đã ở voice → báo lỗi
    if voice_client is not None:
        await interaction.response.send_message("❌ Bot đã được treo ở một voice channel rồi!")
        return

    # 3. Kiểm tra user này đã treo trước đó chưa
    if interaction.user.id in bot.treo_owner:
        await interaction.response.send_message("❌ Bạn đã treo bot trước đó! Dùng /thoat để thả bot ra.")
        return

    channel = interaction.user.voice.channel
    try:
        # KHÔNG dùng reconnect=True để tránh tự động kết nối lại sau restart
        await channel.connect(timeout=30, reconnect=False)
        bot.treo_owner[interaction.user.id] = channel.id
        await interaction.response.send_message(f"✅ Đã treo bot vào voice **{channel.name}** thành công!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi khi treo bot: {e}")

# ----- LỆNH /thoat (public) -----
@bot.tree.command(name="thoat", description="Cho bot rời khỏi voice channel")
async def thoat(interaction: discord.Interaction):
    guild = interaction.guild
    voice_client = guild.voice_client

    if voice_client is None:
        await interaction.response.send_message("❌ Bot hiện không ở trong voice channel nào!")
        return

    if interaction.user.id not in bot.treo_owner:
        await interaction.response.send_message("❌ Bạn không có quyền thả bot! Chỉ người đã dùng /treo mới được /thoat.")
        return

    if not interaction.user.voice or interaction.user.voice.channel.id != voice_client.channel.id:
        await interaction.response.send_message("❌ Bạn phải ở cùng voice channel với bot để thả bot ra!")
        return

    try:
        await voice_client.disconnect()
        if interaction.user.id in bot.treo_owner:
            del bot.treo_owner[interaction.user.id]
        await interaction.response.send_message("✅ Bot đã rời voice channel!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi khi thả bot: {e}")

# ------------------- WEB SERVER (cho Render, giữ cổng) -------------------
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
