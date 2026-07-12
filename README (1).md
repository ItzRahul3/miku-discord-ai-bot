# Miku — Discord AI Bot 🎤

Python (discord.py) দিয়ে বানানো একটা Discord AI বট, যেটা **OpenRouter** (চ্যাটের জন্য, ফ্রি, কোনো কার্ড লাগে না) আর **Pollinations.ai** (ছবি জেনারেশন, একদম keyless-ফ্রি) ব্যবহার করে:
- সাধারণ AI-এর মতো কথা বলে (বাংলা + English দুইটাতেই)
- কোড লিখে দিতে পারে
- ছবি generate করতে পারে
- বটকে **mention** করলে অথবা মেসেজে **"miku"** লিখলেই reply দেয়
- প্রতিটা চ্যানেলে আলাদা conversation memory রাখে (`!reset` দিয়ে মুছে ফেলা যায়)
- চালু হলে Discord-এ কাস্টম স্ট্যাটাস দেখায় ("Waiting for u 💭")

---

## ধাপ ১: Discord Bot বানানো

1. https://discord.com/developers/applications এ যাও → **New Application** → নাম দাও "Miku"।
2. বাম পাশে **Bot** ট্যাবে যাও → **Reset Token** করে token কপি করো (এটাই তোমার `DISCORD_TOKEN`)।
3. একই পেজে নিচে **Privileged Gateway Intents** সেকশনে গিয়ে **MESSAGE CONTENT INTENT** চালু (enable) করো — এটা must, নাহলে বট মেসেজ পড়তে পারবে না।
4. বাম পাশে **OAuth2 → URL Generator** এ যাও:
   - Scopes: `bot`
   - Bot Permissions: `Send Messages`, `Read Message History`, `Attach Files`, `Use Slash Commands`
   - নিচে যে URL তৈরি হবে সেটা ব্রাউজারে খুলে তোমার সার্ভারে বটটা invite করো।

## ধাপ ২: OpenRouter API Key নেওয়া

1. https://openrouter.ai এ গিয়ে সাইন-আপ করো (Google/GitHub দিয়েও করা যায়) — **কোনো কার্ড লাগবে না**।
2. https://openrouter.ai/keys এ গিয়ে **Create Key** করে key কপি করো (এটাই তোমার `OPENROUTER_API_KEY`)।
3. কোন কোন model ফ্রি সেটা দেখতে চাইলে: https://openrouter.ai/models?max_price=0 — model-এর নামের শেষে `:free` থাকলে সেটা ফ্রি।

## ধাপ ৩: প্রজেক্ট সেটআপ করা

```bash
cd miku-discord-bot
python -m venv venv
source venv/bin/activate      # Windows এ: venv\Scripts\activate
pip install -r requirements.txt
```

`.env.example` কপি করে `.env` বানাও:
```bash
cp .env.example .env
```

`.env` ফাইল ওপেন করে নিজের token আর key বসাও:
```
DISCORD_TOKEN=তোমার_discord_bot_token
OPENROUTER_API_KEY=তোমার_openrouter_api_key
```

## ধাপ ৪: বট চালানো

```bash
python main.py
```

কনসোলে `Miku is online and ready!` দেখালে বুঝবে বট চালু হয়ে গেছে।

---

## ব্যবহার

- `@Miku তুমি কেমন আছো?` — mention করে সাধারণ কথা বলা
- `miku, python এ একটা bubble sort লিখে দাও` — কোড চাওয়া
- `miku draw a cat wearing sunglasses` অথবা `miku একটা পাহাড়ের ছবি বানাও` — image generation
- `!reset` — চ্যানেলের চ্যাট history রিসেট করা
- `!miku_help` — সাহায্য মেনু

---

## Customize করা

- **বটের নাম / ব্যক্তিত্ব বদলাতে**: `.env` এ `BOT_NAME` বদলাও, এবং `main.py`-তে `SYSTEM_PROMPT` variable-টা নিজের মতো করে লেখো।
- **AI মডেল বদলাতে**: `.env` এ `CHAT_MODEL_NAME` বদলাও — OpenRouter-এর যেকোনো `:free` মডেলের নাম বসানো যাবে। এছাড়াও বটে built-in **fallback list** আছে (`main.py`-তে `FALLBACK_MODELS`: `meta-llama/llama-3.3-70b-instruct:free` → `nvidia/nemotron-3-ultra-550b-a55b:free` → `openrouter/free` (auto-router)) — primary model upstream-এ busy/rate-limited থাকলে বা deprecated/404 হয়ে গেলে বট automatically পরের model try করবে। ছোট/কোডিং-ফোকাসড ফ্রি মডেলগুলো (যেমন `cohere/north-mini-code:free`) ইচ্ছাকৃতভাবে বাদ দেওয়া হয়েছে কারণ সেগুলো বাংলা লেখায় দুর্বল এবং মাঝে মাঝে garbled/ভাঙা টেক্সট বের করে। মডেল লিস্ট মাঝেমধ্যে বদলায়, তাই কখনো সব model fail করলে https://openrouter.ai/models?max_price=0 চেক করে `FALLBACK_MODELS` আপডেট করে নিও, তবে নতুন মডেল যোগ করার আগে সেটা বাংলায় ভালো কিনা টেস্ট করে নিও।
- **Trigger keyword বদলাতে**: `main.py`-তে `is_triggered()` ফাংশনে `miku` শব্দটার জায়গায় অন্য কিছু বসাতে পারো।
- **কাস্টম স্ট্যাটাস বদলাতে**: `.env` এ `STATUS_TEXT` বদলাও।

## সমস্যা হলে (Troubleshooting)

- বট অনলাইনে আছে কিন্তু মেসেজে reply দিচ্ছে না → Discord Developer Portal-এ **MESSAGE CONTENT INTENT** enable করা আছে কিনা চেক করো।
- `401 Unauthorized` / `Invalid API key` → `.env`-এ `OPENROUTER_API_KEY` ঠিকমতো বসানো আছে কিনা চেক করো।
- বটের বাংলা রিপ্লাই মাঝে মাঝে ভাঙা/অস্পষ্ট (garbled) আসে → এটা সাধারণত fallback-এ কোনো ছোট/দুর্বল ফ্রি মডেল ব্যবহার হওয়ার কারণে হয় (সব ফ্রি মডেল বাংলায় সমান ভালো না)। বর্তমান `FALLBACK_MODELS` লিস্ট থেকে এমন মডেল বাদ দেওয়া হয়েছে, তবে যদি আবার হয় তাহলে যেই মডেলটা ব্যবহার হয়েছিল সেটা log-এ দেখে (`Model ... failed` বা successful reply-এর আগের log line) `FALLBACK_MODELS` থেকে বাদ দিয়ে দাও।
- বট রিপ্লাই দিতে সময় নিচ্ছে → ফ্রি মডেলগুলো paid মডেলের চেয়ে ধীর, এটা স্বাভাবিক। বট এখন প্রতিটা মডেলে বেশিক্ষণ (২০ সেকেন্ডের বেশি) আটকে না থেকে দ্রুত পরের fallback-এ চলে যায়, আর reply ছোট রাখার জন্য response length limit করা আছে। তারপরও স্লো লাগলে `FALLBACK_MODELS`-এর ক্রম পাল্টে ছোট/দ্রুত মডেল আগে বসাও, অথবা `client = OpenAI(..., timeout=20.0)`-এর সংখ্যাটা কমাও।
- চ্যাটে `429` error বারবার হলে → বট নিজে থেকেই fallback model-এ চলে যায়, কিন্তু যদি সব free model-ই একসাথে busy থাকে তাহলে একটু wait করো, বা `FALLBACK_MODELS` লিস্টে নিজের পছন্দের আরও `:free` model যোগ করো, অথবা https://openrouter.ai/settings/integrations এ গিয়ে নিজের rate limit বাড়াতে পারো।
- Image generation slow/fail হলে → Pollinations.ai মাঝে মাঝে busy থাকে, আবার চেষ্টা করো।
- **`429 Too Many Requests` / Cloudflare "Error 1015 rate limited" Discord login-এর সময়** → এটা সাধারণত crash-restart loop এর কারণে হয়। কিছুক্ষণ (৩০ মিনিট+) বট restart না করে wait করো, একই token দিয়ে একাধিক জায়গায় বট চালানো হচ্ছে না তো সেটাও চেক করো।
