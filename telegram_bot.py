import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

CITY, STREET, BUILDING = range(3)

def get_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return chrome_options

def fill_field_and_select(driver, field, value, wait):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
    time.sleep(0.3)
    
    driver.execute_script("arguments[0].focus();", field)
    time.sleep(0.2)
    
    field.clear()
    time.sleep(0.2)
    
    for char in value:
        field.send_keys(char)
        time.sleep(0.08)
    
    time.sleep(2)
    
    try:
        autocomplete_items = wait.until(
            EC.presence_of_all_elements_located((
                By.CSS_SELECTOR,
                "#cityautocomplete-list div, .autocomplete-items div, [role='option']"
            ))
        )
        
        if autocomplete_items:
            for item in autocomplete_items:
                if item.is_displayed() and value.lower() in item.text.lower():
                    item.click()
                    time.sleep(1)
                    return True
            
            if autocomplete_items[0].is_displayed():
                autocomplete_items[0].click()
                time.sleep(1)
                return True
    except TimeoutException:
        pass
    
    field.send_keys(Keys.ARROW_DOWN)
    time.sleep(0.3)
    field.send_keys(Keys.ENTER)
    time.sleep(1)
    return True

def check_power_outage(city, street, building):
    driver = None
    try:
        chrome_options = get_chrome_options()
        driver = webdriver.Chrome(options=chrome_options)
        
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        wait = WebDriverWait(driver, 30)
        
        time.sleep(5)
        
        from selenium.webdriver.common.action_chains import ActionChains
        for _ in range(3):
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.3)
        
        time.sleep(1)
        
        try:
            close_buttons = driver.find_elements(By.CSS_SELECTOR, "button.close, [aria-label='Close'], .modal-close")
            for btn in close_buttons:
                if btn.is_displayed():
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except:
                        pass
        except:
            pass
        
        time.sleep(2)
        
        city_field = wait.until(EC.presence_of_element_located((By.ID, "city")))
        street_field = driver.find_element(By.ID, "street")
        building_field = driver.find_element(By.ID, "house_num")
        
        if not fill_field_and_select(driver, city_field, city, wait):
            return {"success": False, "error": "address_not_found"}
        
        if not fill_field_and_select(driver, street_field, street, wait):
            return {"success": False, "error": "address_not_found"}
        
        if not fill_field_and_select(driver, building_field, building, wait):
            return {"success": False, "error": "address_not_found"}
        
        time.sleep(3)
        
        try:
            result_div = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#showCurOutage.active, div.active"))
            )
            
            full_text = result_div.text
            
            if "відсутня електроенергія" in full_text or "відключення" in full_text.lower():
                lines = full_text.split('\n')
                
                cause = ""
                start_time = ""
                restoration_time = ""
                
                for i, line in enumerate(lines):
                    if "Причина:" in line and i + 1 < len(lines):
                        cause = lines[i + 1].strip()
                    
                    if "Час початку" in line:
                        match = re.search(r'(\d{2}:\d{2}\s+\d{2}\.\d{2}\.\d{4})', line)
                        if match:
                            start_time = match.group(1)
                    
                    if "Орієнтовний час відновлення" in line:
                        match = re.search(r'до\s+(\d{2}:\d{2}\s+\d{2}\.\d{2}\.\d{4})', line)
                        if match:
                            restoration_time = match.group(1)
                
                return {
                    "success": True,
                    "has_outage": True,
                    "address": f"м. {city}, вул. {street}, {building}",
                    "cause": cause if cause else "Не вказано",
                    "start_time": start_time if start_time else "Не вказано",
                    "restoration_time": restoration_time if restoration_time else "Не вказано"
                }
            else:
                return {
                    "success": True,
                    "has_outage": False,
                    "address": f"м. {city}, вул. {street}, {building}"
                }
            
        except TimeoutException:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "не знайдено" in body_text.lower() or "некоректн" in body_text.lower():
                return {"success": False, "error": "address_not_found"}
            
            return {"success": False, "error": "unknown"}
            
    except Exception as e:
        logger.error(f"Error checking outage: {e}")
        return {"success": False, "error": "unknown"}
    finally:
        if driver:
            driver.quit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Вітаю! Я бот для перевірки відключень електроенергії ДТЕК.\n\n"
        "Я допоможу вам дізнатись чи є відключення за вашою адресою.\n\n"
        "Команди:\n"
        "/check - Перевірити відключення\n"
        "/cancel - Скасувати поточну дію"
    )
    return ConversationHandler.END

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📍 Введіть назву міста:\n"
        "(Наприклад: Одеса, Київ, Дніпро)"
    )
    return CITY

async def city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    context.user_data['city'] = city
    
    await update.message.reply_text(
        f"🏙 Місто: {city}\n\n"
        f"🛣 Тепер введіть назву вулиці:\n"
        f"(Наприклад: Марсельська, Хрещатик)"
    )
    return STREET

async def street_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    street = update.message.text.strip()
    context.user_data['street'] = street
    
    await update.message.reply_text(
        f"🏙 Місто: {context.user_data['city']}\n"
        f"🛣 Вулиця: {street}\n\n"
        f"🏠 Введіть номер будинку:\n"
        f"(Наприклад: 60, 15А)"
    )
    return BUILDING

async def building_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    building = update.message.text.strip()
    
    city = context.user_data['city']
    street = context.user_data['street']
    
    context.user_data['building'] = building
    context.user_data['last_city'] = city
    context.user_data['last_street'] = street
    context.user_data['last_building'] = building
    
    await update.message.reply_text(
        f"⏳ Перевіряю інформацію про відключення для адреси:\n"
        f"📍 м. {city}, вул. {street}, {building}\n\n"
        f"Це може зайняти до 1 хвилини..."
    )
    
    await perform_check_and_reply(update, context, city, street, building)
    
    return ConversationHandler.END

async def perform_check_and_reply(update, context, city, street, building):
    result = check_power_outage(city, street, building)
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Перевірити знову", callback_data='repeat_check'),
            InlineKeyboardButton("📝 Змінити адресу", callback_data='new_check')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if result['success']:
        if result['has_outage']:
            message = (
                f"🪫 За адресою *м. {city}, вул. {street}, {building}* зафіксовано відключення.\n\n"
                f"Причина: {result['cause']}.\n\n"
                f"🕦 Час початку: {result['start_time']}.\n"
                f"🕦 Орієнтовний час відновлення електроенергії: {result['restoration_time']}."
            )
        else:
            message = (
                f"⚡️ На даний момент відключень світла за вашою адресою не зафіксовано.\n\n"
                f"📍 м. {city}, вул. {street}, {building}"
            )
        
        if update.callback_query:
            await update.callback_query.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    else:
        if result.get('error') == 'address_not_found':
            message = (
                f"❗️ На жаль, такої адреси не знайдено.\n\n"
                f"Перевірте правильність введених даних:\n"
                f"📍 м. {city}, вул. {street}, {building}\n\n"
                f"Спробуйте ще раз: /check"
            )
        else:
            message = (
                f"❌ Виникла помилка при перевірці.\n\n"
                f"Спробуйте пізніше або зверніться до підтримки.\n\n"
                f"Повторити: /check"
            )
        
        if update.callback_query:
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'repeat_check':
        if 'last_city' in context.user_data:
            city = context.user_data['last_city']
            street = context.user_data['last_street']
            building = context.user_data['last_building']
            
            await query.message.reply_text(
                f"⏳ Перевіряю інформацію про відключення для адреси:\n"
                f"📍 м. {city}, вул. {street}, {building}\n\n"
                f"Це може зайняти до 1 хвилини..."
            )
            
            await perform_check_and_reply(update, context, city, street, building)
        else:
            await query.message.reply_text(
                "❌ Немає збереженої адреси.\n\n"
                "Використайте /check для нової перевірки."
            )
    
    elif query.data == 'new_check':
        await query.message.reply_text(
            "📍 Введіть назву міста:\n"
            "(Наприклад: Одеса, Київ, Дніпро)"
        )
        return CITY
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Перевірку скасовано.\n\n"
        "Для нової перевірки використайте /check"
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('check', check_command),
            CallbackQueryHandler(button_callback, pattern='^new_check$')
        ],
        states={
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_input)],
            STREET: [MessageHandler(filters.TEXT & ~filters.COMMAND, street_input)],
            BUILDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, building_input)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^repeat_check$'))
    
    logger.info("Бот запущено!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
