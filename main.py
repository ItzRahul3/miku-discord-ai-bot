import os
import re
import io
import asyncio
import logging
import urllib.parse
 
import aiohttp
import discord
from discord.ext import commands
from openai import OpenAI
from dotenv import load_dotenv
 
load_dotenv()
 
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct:free")
BOT_NAME = os.getenv("BOT_NAME", "Miku")
STATUS_TEXT = os.getenv("STATUS_TEXT", "Waiting for u 💭")
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "20"))
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("miku-bot")
 
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    max_retries=0,  # we handle retries/fallback ourselves across multiple free models
    timeout=20.0,   # give up on a slow/stuck model quickly and move to the next fallback
)
 
# If the primary free model is busy/rate-limited upstream, try these next, in order.
# Verified live against https://openrouter.ai/api/v1/models on 2026-07-11.
# "openrouter/free" is OpenRouter's own auto-router: it automatically picks
# *any* currently-available free model, so it acts as a strong safety net.
FALLBACK_MODELS = list(dict.fromkeys([
    CHAT_MODEL_NAME,
    "meta-llama/llama-3.3-70b-instruct:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter/free",  # auto-router, last resort — picks any available free model
]))
 
SYSTEM_PROMPT = f"""
তুমি হচ্ছো {BOT_NAME} — একজন বন্ধুত্বপূর্ণ, স্মার্ট AI অ্যাসিস্ট্যান্ট যে একটি Discord সার্ভারে থাকো।
 
নিয়মাবলী:
- ব্যবহারকারী যে ভাষায় কথা বলবে (বাংলা, ইংরেজি, বা মিশ্র বাংলিশ), তুমি স্বাভাবিকভাবে সেই ভাষাতেই reply দিবে।
- তুমি সাধারণ কথাবার্তা বলতে পারো, প্রশ্নের উত্তর দিতে পারো, এবং প্রয়োজনে ভালোভাবে ব্যাখ্যা করে কোড লিখে দিতে পারো
  (Markdown code block ব্যবহার করে, ভাষার নাম উল্লেখ করে, যেমন ```python ... ```)।
- তুমি বন্ধুর মতো হালকা মজার এবং সহায়ক টোনে কথা বলবে, তবে দরকারে সিরিয়াস ও প্রফেশনাল হতে পারবে।
- উত্তর প্রাসঙ্গিক ও যথাসম্ভব সংক্ষিপ্ত রাখবে, তবে জটিল প্রশ্ন বা কোডের ক্ষেত্রে বিস্তারিত ব্যাখ্যা দেবে।
- তুমি নিজেকে {BOT_NAME} নামে পরিচয় দাও। Google, OpenAI বা কোনো AI provider-এর নাম উল্লেখ করার দরকার নেই।
- বাংলা লেখার সময় সবসময় শুদ্ধ, স্বাভাবিক বাংলা বানান ব্যবহার করবে। কোনো বাংলা শব্দ/বানান নিয়ে অনিশ্চিত হলে, ভাঙা/অস্পষ্ট বাংলার বদলে সহজ বাংলা বা ইংরেজি শব্দ ব্যবহার করবে।
"""
 
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
 
bot = commands.Bot(command_prefix="!", intents=intents)
 
# channel_id -> list of {"role": ..., "content": ...} (OpenAI-style chat history)
chat_histories: dict[int, list] = {}
 
 
def get_history(channel_id: int) -> list:
    if channel_id not in chat_histories:
        chat_histories[channel_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return chat_histories[channel_id]
 
 
def trim_history(channel_id: int):
    """Keep memory/token usage bounded, always preserving the system prompt."""
    history = chat_histories.get(channel_id)
    if history and len(history) > MAX_HISTORY_TURNS * 2 + 1:
        chat_histories[channel_id] = [history[0]] + history[-(MAX_HISTORY_TURNS * 2):]
 
 
async def ask_ai(channel_id: int, user_text: str) -> str:
    history = get_history(channel_id)
    history.append({"role": "user", "content": user_text})
 
    last_error = None
    for model_name in FALLBACK_MODELS:
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model_name,
                messages=history,
                max_tokens=700,  # keep replies snappy; free models are slower on long outputs
                extra_headers={
                    "HTTP-Referer": "https://discord.com",
                    "X-Title": BOT_NAME,
                },
            )
            reply = response.choices[0].message.content
            if not reply:
                raise ValueError("empty response from model")
            history.append({"role": "assistant", "content": reply})
            trim_history(channel_id)
            return reply
        except Exception as e:
            logger.warning(f"Model {model_name} failed ({e}); trying next fallback...")
            last_error = e
            continue
 
    # every model failed
    history.pop()  # remove the user message we couldn't get a reply for
    raise last_error
 
 
IMAGE_KEYWORDS = [
    "draw", "generate image", "generate an image", "make an image", "create an image",
    "picture of", "image of", "an image", "a picture", "generate a picture",
    "ছবি আঁক", "ছবি বানা", "ছবি তৈরি", "ইমেজ বানা", "ইমেজ তৈরি", "ইমেজ জেনারেট",
    "আঁকো", "আঁকতে", "chobi", "chobi ako", "chobi banao", "chobi toiri",
]
 
 
def wants_image(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in IMAGE_KEYWORDS)
 
 
def is_triggered(message: discord.Message) -> bool:
    if bot.user in message.mentions:
        return True
    content_lower = message.content.lower()
    return bool(re.search(r"\bmiku\b", content_lower))
 
 
def strip_trigger(text: str) -> str:
    text = re.sub(r"<@!?\d+>", "", text)
    text = re.sub(r"\bmiku\b", "", text, flags=re.IGNORECASE)
    return text.strip(" ,:।-")
 
 
async def generate_image(prompt: str) -> bytes | None:
    """Pollinations.ai is a free, keyless image generation endpoint."""
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                return await resp.read()
    return None
 
 
async def send_long_reply(message: discord.Message, text: str):
    if not text:
        return
    chunks = [text[i: i + 1900] for i in range(0, len(text), 1900)]
    first = True
    for chunk in chunks:
        if first:
            await message.reply(chunk)
            first = False
        else:
            await message.channel.send(chunk)
 
 
@bot.event
async def on_ready():
    logger.info(f"{bot.user} is online and ready!")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.CustomActivity(name=STATUS_TEXT),
    )
 
 
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
 
    await bot.process_commands(message)
 
    if message.content.startswith("!"):
        return
 
    if not is_triggered(message):
        return
 
    user_text = strip_trigger(message.content)
    if not user_text:
        user_text = "হ্যালো"
 
    async with message.channel.typing():
        try:
            if wants_image(user_text):
                image_bytes = await generate_image(user_text)
                if image_bytes:
                    file = discord.File(io.BytesIO(image_bytes), filename="miku_image.png")
                    await message.reply("এই নাও তোমার ছবি! 🎨", file=file)
                else:
                    await message.reply(
                        "দুঃখিত, ছবিটা বানাতে পারলাম না। প্রম্পটটা একটু ভিন্নভাবে বলে আবার চেষ্টা করো।"
                    )
            else:
                reply = await ask_ai(message.channel.id, user_text)
                await send_long_reply(message, reply)
        except Exception as e:
            logger.exception("Error handling message")
            await message.reply(f"একটা সমস্যা হয়েছে 😅: `{e}`")
 
 
@bot.command(name="reset")
async def reset_chat(ctx: commands.Context):
    chat_histories.pop(ctx.channel.id, None)
    await ctx.send("Chat history reset হয়ে গেছে! নতুন করে কথা শুরু করো। 🔄")
 
 
@bot.command(name="miku_help")
async def miku_help(ctx: commands.Context):
    await ctx.send(
        f"হাই! আমি **{BOT_NAME}** 👋\n"
        f"- আমাকে mention করো অথবা মেসেজে `miku` লিখলেই আমি reply দিব।\n"
        f"- বাংলা বা ইংরেজি, দুই ভাষাতেই কথা বলতে পারি।\n"
        f"- কোড লিখতে বললে কোড লিখে দিব।\n"
        f"- ছবি আঁকতে/বানাতে বললে (e.g. `miku draw a cat` বা `miku ছবি বানাও...`) আমি image generate করব।\n"
        f"- `!reset` দিলে এই চ্যানেলের কথোপকথনের history মুছে যাবে।"
    )
 
 
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN .env ফাইলে সেট করো!")
    if not OPENROUTER_API_KEY:
        raise SystemExit("OPENROUTER_API_KEY .env ফাইলে সেট করো!")
    bot.run(DISCORD_TOKEN)
