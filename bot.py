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
        self.treo_owner = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Đã sync slash commands!")

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f"✅ {bot.user} đã sẵn sàng!")

# ----- LỆNH SLASH -----
@bot.tree.command(name="treo", description="Treo bot vào voice channel của bạn")
async def treo(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Bạn phải ở trong voice channel để dùng lệnh này!", ephemeral=True)
        return

    guild = interaction.guild
    if guild.voice_client is not None:
        await interaction.response.send_message("❌ Bot đã được treo ở một voice channel rồi!", ephemeral=True)
        return

    if interaction.user.id in bot.treo_owner:
        await interaction.response.send_message("❌ Bạn đã treo bot trước đó! Dùng /thoat để thả bot ra.", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    try:
        await channel.connect()
        bot.treo_owner[interaction.user.id] = channel.id
        await interaction.response.send_message(f"✅ Đã treo bot vào voice **{channel.name}** thành công!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi khi treo bot: {e}", ephemeral=True)

@bot.tree.command(name="thoat", description="Cho bot rời khỏi voice channel")
async def thoat(interaction: discord.Interaction):
    guild = interaction.guild
    voice_client = guild.voice_client

    if voice_client is None:
        await interaction.response.send_message("❌ Bot hiện không ở trong voice channel nào!", ephemeral=True)
        return

    if interaction.user.id not in bot.treo_owner:
        await interaction.response.send_message("❌ Bạn không có quyền thả bot ra! Chỉ người đã dùng /treo mới được dùng /thoat.", ephemeral=True)
        return

    if not interaction.user.voice or interaction.user.voice.channel.id != voice_client.channel.id:
        await interaction.response.send_message("❌ Bạn phải ở cùng voice channel với bot để thả bot ra!", ephemeral=True)
        return

    try:
        await voice_client.disconnect()
        del bot.treo_owner[interaction.user.id]
        await interaction.response.send_message("✅ Bot đã rời voice channel!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi khi thả bot: {e}", ephemeral=True)

# ------------------- WEB SERVER (cho Render) -------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord đang chạy!"

@app.route('/ping')
def ping():
    return jsonify({"status": "pong", "bot": str(bot.user)})

def run_webserver():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ------------------- KHỞI ĐỘNG -------------------
if __name__ == "__main__":
    # Chạy web server trong luồng riêng
    threading.Thread(target=run_webserver, daemon=True).start()
    # Chạy bot Discord
    bot.run(TOKEN)
