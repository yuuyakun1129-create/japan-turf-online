import os, asyncio, aiohttp, discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN=os.environ["DISCORD_BOT_TOKEN"]
API_KEY=os.getenv("PIXAI_API_KEY","")
MODEL=os.getenv("PIXAI_MODEL_VERSION_ID","")
CHANNEL_ID=int(os.getenv("NOTIFY_CHANNEL_ID","0") or 0)
USER_ID=int(os.getenv("NOTIFY_USER_ID","0") or 0)
ALLOWED={int(x) for x in os.getenv("ALLOWED_USER_IDS","").split(",") if x.strip().isdigit()}
API="https://api.pixai.art"
JST=ZoneInfo("Asia/Tokyo")
bot=commands.Bot(command_prefix="!", intents=discord.Intents.default())
_last_notice=None

def ok(uid): return not ALLOWED or uid in ALLOWED

async def generate(prompt, negative, ratio):
    if not API_KEY or not MODEL: raise RuntimeError("PIXAI_API_KEY / PIXAI_MODEL_VERSION_ID が未設定です")
    headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"}
    data={"modelVersionId":MODEL,"prompt":prompt,"aspectRatio":ratio,"mode":"standard","batchSize":1}
    if negative: data["negativePrompt"]=negative
    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.post(API+"/v2/image/create",json=data) as r:
            if r.status not in (200,201): raise RuntimeError((await r.text())[:500])
            job=await r.json()
        tid=job["id"]
        for _ in range(150):
            await asyncio.sleep(2)
            async with s.get(API+f"/v1/task/{tid}") as r:
                if r.status!=200: continue
                job=await r.json()
            status=str(job.get("status","")).lower()
            if status in ("completed","success","succeeded"):
                urls=(job.get("outputs") or {}).get("mediaUrls") or []
                if not urls: raise RuntimeError("画像URLを取得できませんでした")
                return urls[0]
            if status in ("failed","error","cancelled","canceled"): raise RuntimeError("PixAI生成に失敗しました")
    raise RuntimeError("生成がタイムアウトしました")

@bot.tree.command(name="pixai_generate",description="PixAIで画像を生成")
async def cmd_generate(i:discord.Interaction,prompt:str,negative_prompt:str="",aspect_ratio:str="1:1"):
    if not ok(i.user.id): return await i.response.send_message("権限がありません",ephemeral=True)
    await i.response.defer(thinking=True)
    try:
        url=await generate(prompt,negative_prompt,aspect_ratio)
        e=discord.Embed(title="PixAI 生成完了",description=prompt[:1000]); e.set_image(url=url)
        await i.followup.send(embed=e)
    except Exception as e: await i.followup.send(f"❌ {e}",ephemeral=True)

@bot.tree.command(name="pixai_claim",description="PixAIのデイリー報酬ページを案内")
async def claim(i:discord.Interaction):
    await i.response.send_message("🎁 PixAIのデイリー報酬が更新されています。PixAIを開いて受け取ってください。\nhttps://pixai.art/",ephemeral=True)

@tasks.loop(minutes=5)
async def notice():
    global _last_notice
    now=datetime.now(JST)
    # PixAI daily credits reset at 09:00 JST. Notify once after reset.
    day=now.date().isoformat()
    if now.hour>=9 and _last_notice!=day and CHANNEL_ID and USER_ID:
        ch=bot.get_channel(CHANNEL_ID)
        if ch:
            await ch.send(f"<@{USER_ID}> 🎁 PixAIのデイリー報酬が更新されたよ！ `/pixai_claim` から確認できます。")
            _last_notice=day

@notice.before_loop
async def before_notice(): await bot.wait_until_ready()

@bot.event
async def on_ready():
    await bot.tree.sync()
    if not notice.is_running(): notice.start()
    print("ready:",bot.user)

bot.run(TOKEN)
