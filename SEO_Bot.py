import http.client
import json
import os
import requests
from bs4 import BeautifulSoup
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import google.generativeai as genai

BOT_TOKEN = '8362414405:AAHj7sZ1BsHjKEng1BT-4ERY3KbqY7LCBCs'
GEMINI_API_KEY = 'AIzaSyCBpyux-5yUYURCMHFB_MuFDxw-5BVZKVk'

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

main_menu = ReplyKeyboardMarkup(
    [["/start", "🔍 Search Keyword"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Choose an option from the menu below 👇",
        reply_markup=main_menu
    )

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "🔍 Search Keyword":
        await update.message.reply_text(
            "Please enter a Primary Keyword (PKW) to search on Google:",
            reply_markup=main_menu
        )
    else:
        await handle_keyword(update, context)

async def handle_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    if keyword == "🔍 Search Keyword":
        return

    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({
        "q": keyword,
        "gl": "ir",
        "hl": "fa"
    })
    headers = {
        'X-API-KEY': '3d1d120e400f78f41bd37d4bb621069f6ee9e593',
        'Content-Type': 'application/json'
    }

    try:
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = res.read()
        response_data = json.loads(data.decode("utf-8"))
        results = response_data.get("organic", [])

        if not results:
            await update.message.reply_text(
                "Search completed, but no results found.",
                reply_markup=main_menu
            )
            return

        for i, item in enumerate(results[:3], start=1):
            url = item.get("link", "")
            try:
                page = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(page.content, "html.parser")

                headings = []
                for level in range(1, 7):
                    tags = soup.find_all(f"h{level}")
                    for tag in tags:
                        text = tag.get_text(strip=True)
                        if text:
                            headings.append(f"h{level}: {text}")

                file_name = f"headings_{i}.txt"
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(f"Source: {url}\n\n")
                    for line in headings:
                        f.write(line + "\n")

            except Exception as e:
                print(f"[ERROR] Failed to fetch headings from {url} - {e}")

        await update.message.reply_text(
            "✅ Competitor headings were successfully extracted for your query.",
            reply_markup=main_menu
        )

        # Now use Gemini to generate new headings
        all_headings = ""
        for i in range(1, 4):
            file_name = f"headings_{i}.txt"
            if os.path.exists(file_name):
                with open(file_name, "r", encoding="utf-8") as f:
                    all_headings += f.read() + "\n"

        prompt = f"""فرض کن که یک متخصص "{keyword}" هستی و توی این زمینه تحربه زیادی داری و تمام مطالب و کتاب های مربوط به این موضوع رو مطالعه کردی؛ و می‌خوای که برای وبسایتت یه مقاله در مورد موضوع "{keyword}" بنویسی. 
خب حالا با توجه به پرسونا کاربری که سرچ می‌کنه "{keyword}" و سوالاتی که براش پیش میاد و با استفاده از تحلیل دقیق هدینگ‌هایی که رقبا نوشتن؛ زیرعناوین این محتوا رو برام مشخص کن.
محتوا عمق کافی داشته باشه ولی حاشیه‌پردازی نکرده باشه و به مطالب بی‌ربط نپرداخته باشه.
هدینگ‌ها فقط مربوط به "{keyword}" باشن و حاشیه نداشته باشن.
برای نوشتن هدینگ‌ها حتما از این هدینگ‌ها استفاده کن و سعی کن حتما هدینگ‌های مشابه‌ش رو داشته باشیم و کپی هم نباشه:

{all_headings}
تعداد هدینگ های مرتبط با "{keyword}" نهایتا 10 تا باشه و از نوشتن هدینگ های بسیار زیاد برای موضوع خودداری کن.
قبل از هر هدینگ با نوشتن H1 یا H2 یا H3 و... مشخص کن که هر هدینگ در چه سطحی قرار داره.


نکته مهم: توی خروجی فقط هدینگ‌ها رو بنویس و هیچ توضیح یا متن اضافه‌ای نده.
"""

        try:
            response = model.generate_content(prompt)
            headings_output = response.text.strip()

            await update.message.reply_text(
                f"🧠 Suggested Headings:\n\n{headings_output}",
                reply_markup=main_menu
            )

        except Exception as e:
            await update.message.reply_text(
                "⚠️ Failed to generate headings with Gemini.",
                reply_markup=main_menu
            )
            print(f"[ERROR] Gemini: {e}")

    except Exception as e:
        await update.message.reply_text(
            "Failed to search. Please try again later.",
            reply_markup=main_menu
        )
        print(f"[ERROR] {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_selection))
    app.run_polling()

if __name__ == '__main__':
    main()
