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
    chrome_options.add_argument("--window-size=1920,1080")
    return chrome_options

def get_power_outage_info(city, street, building):
    driver = None
    try:
        driver = webdriver.Chrome(options=get_chrome_options())
        wait = WebDriverWait(driver, 15)
        
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        time.sleep(5)
        
        # Закриваємо попап (ESC)
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        
        # Список полів для заповнення з їх реальними ID
        steps = [
            ("city", city),
            ("street", street),
            ("house_num", building)
        ]
        
        for field_id, value in steps:
            # ЧЕКАЄМО, поки поле стане активним (enabled: true)
            el = wait.until(EC.element_to_be_clickable((By.ID, field_id)))
            
            el.clear()
            for char in value:
                el.send_keys(char)
                time.sleep(0.1)
            
            time.sleep(2) # Час на появу списку
            el.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.5)
            el.send_keys(Keys.ENTER)
            time.sleep(1) # Пауза для активації наступного поля сайтом

        # Очікуємо появу результату (жовтий блок)
        time.sleep(5)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        is_off = "відсутня електроенергія" in body_text or "Екстрені відключення" in body_text
        
        return {
            "success": True,
            "status": "OFF" if is_off else "ON",
            "address": f"{city}, {street}, {building}",
            "info": body_text[:500]
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
