from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import os

app = Flask(__name__)

def get_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return chrome_options

def get_power_outage_info(city="Одеса", street="Марсельська", building="60"):
    driver = None
    try:
        chrome_options = get_chrome_options()
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 20) 
        
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        time.sleep(7)
        
        # Закриваємо popup через ESC
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
        fields = [
            ("city", city, "місто"),
            ("street", street, "вулиця"),
            ("house_num", building, "будинок")
        ]
        
        for field_id, value, name in fields:
            # Чекаємо, поки поле стане активним (enabled: true)
            # Це виправляє помилку "Element is not currently interactable"
            field = wait.until(EC.element_to_be_clickable((By.ID, field_id)))
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
            field.clear()
            
            # Вводимо текст посимвольно
            for char in value:
                field.send_keys(char)
                time.sleep(0.1)
            
            time.sleep(2.5) # Чекаємо на dropdown список
            field.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.5)
            field.send_keys(Keys.ENTER)
            time.sleep(1.5) # Пауза, щоб сайт активував наступне поле

        # Чекаємо на фінальний результат
        time.sleep(6)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Пошук ключових слів
        is_outage = any(kw in body_text for kw in ["відсутня електроенергія", "Екстрені відключення", "Орієнтовний час"])
        
        return {
            "success": True,
            "is_outage": is_outage,
            "address": f"{city}, {street}, {building}",
            "info": body_text[:800] if is_outage else "Відключень не знайдено"
        }
            
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if driver:
            driver.quit()

@app.route('/')
def home():
    return jsonify({"status": "DTEK API is running", "version": "2.0.1"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/check')
def check_outage():
    city = request.args.get('city', 'Одеса')
    street = request.args.get('street', 'Марсельська')
    building = request.args.get('building', '60')
    return jsonify(get_power_outage_info(city, street, building))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
