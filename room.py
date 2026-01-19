import discord
import os  # 追加: 環境変数を読み込むためのライブラリ
from discord.ext import commands
from discord.ui import View, Button, Select

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- 部屋作成用のメニューView ---
class RoomCreationView(View):
    def __init__(self, author, initial_members):
        super().__init__(timeout=180) 
        self.author = author
        self.members = set(initial_members)
        self.members.add(author)
        self.channel_type = discord.ChannelType.text

    @discord.ui.select(
        placeholder="チャンネルの種類を選択 (デフォルト: チャット)",
        options=[
            discord.SelectOption(label="チャット (Text)", value="text", description="テキストチャンネルを作成"),
            discord.SelectOption(label="通話 (Voice)", value="voice", description="ボイスチャンネルを作成"),
        ]
    )
    async def select_type(self, interaction: discord.Interaction, select: Select):
        if interaction.user != self.author:
            return await interaction.response.send_message("設定を変更できるのはコマンド実行者のみです。", ephemeral=True)
        
        selected_value = select.values[0]
        if selected_value == "voice":
            self.channel_type = discord.ChannelType.voice
            await interaction.response.send_message("ボイスチャンネルを作成します。", ephemeral=True)
        else:
            self.channel_type = discord.ChannelType.text
            await interaction.response.send_message("テキストチャンネルを作成します。", ephemeral=True)

    @discord.ui.button(label="参加する", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user in self.members:
            return await interaction.response.send_message("既に参加リストに入っています。", ephemeral=True)
        
        self.members.add(interaction.user)
        await interaction.response.send_message(f"{interaction.user.mention} が参加リストに追加されました！", ephemeral=False)

    @discord.ui.button(label="開始 (部屋を作成)", style=discord.ButtonStyle.blurple)
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("部屋を作成できるのはコマンド実行者のみです。", ephemeral=True)

        await interaction.response.defer()
        
        guild = interaction.guild
        category = interaction.channel.category

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, connect=True, manage_channels=True)
        }

        for member in self.members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, connect=True, speak=True)

        room_name = f"🔒-{self.author.display_name}の部屋"

        try:
            if self.channel_type == discord.ChannelType.text:
                created_channel = await guild.create_text_channel(name=room_name, overwrites=overwrites, category=category)
                await created_channel.send(f"{self.author.mention} 部屋を作成しました！\nメンバー: {', '.join([m.mention for m in self.members])}\n\nこの部屋を消すには `!erace` と入力してください。")
            else:
                created_channel = await guild.create_voice_channel(name=room_name, overwrites=overwrites, category=category)
                await interaction.followup.send(f"ボイスチャンネルを作成しました: {created_channel.mention}\nメンバー: {', '.join([m.mention for m in self.members])}")

            self.stop()
            await interaction.followup.send("部屋の作成が完了しました。")
            
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

# --- コマンド実装 ---

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def create(ctx):
    initial_members = ctx.message.mentions
    view = RoomCreationView(ctx.author, initial_members)
    
    mention_str = "なし"
    if initial_members:
        mention_str = ", ".join([m.display_name for m in initial_members])

    embed = discord.Embed(title="会議室作成メニュー", description="設定を選んで「開始」を押してください。", color=discord.Color.blue())
    embed.add_field(name="初期メンバー", value=mention_str, inline=False)
    embed.add_field(name="使い方", value="1. 必要なら「参加する」ボタンを押してもらう\n2. メニューでVCかチャットか選択\n3. 「開始」で部屋作成", inline=False)

    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['erase'])
async def erace(ctx):
    channel = ctx.channel
    await ctx.send("この部屋を削除します...")
    await channel.delete()

# --- 変更点: 環境変数からトークンを取得 ---
token = os.getenv("DISCORD_TOKEN")

if token is None:
    print("エラー: 環境変数 DISCORD_TOKEN が設定されていません。")
else:
    bot.run(token)