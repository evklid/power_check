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
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return chrome_options

def select_from_dropdown(driver, wait, field_id, value):
    """Надійна логіка вибору з випадаючого списку"""
    # 1. Чекаємо, поки поле стане доступним 
    element = wait.until(EC.element_to_be_clickable((By.ID, field_id)))
    
    # 2. Клікаємо та очищуємо через JS для надійності
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    element.click()
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.BACKSPACE)
    
    # 3. Посимвольне введення (імітація людини для спрацювання JS-фільтрів)
    for char in value:
        element.send_keys(char)
        time.sleep(0.1)
    
    # 4. Чекаємо появи списку та вибираємо перший варіант клавішами
    time.sleep(2) # Час на появу dropdown
    element.send_keys(Keys.ARROW_DOWN)
    time.sleep(0.5)
    element.send_keys(Keys.ENTER)
    time.sleep(1.5) # Пауза для активації наступного поля

@app.route('/check')
def check_outage():
    city = request.args.get('city', 'Одеса')
    street = request.args.get('street', 'Марсельська')
    building = request.args.get('building', '60')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=get_chrome_options())
        wait = WebDriverWait(driver, 20)
        
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        
        # Обробка попапу через примусове натискання ESC декілька разів
        time.sleep(5) 
        for _ in range(3):
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.5)

        # Почергове заповнення полів за їх реальними ID
        select_from_dropdown(driver, wait, "city", city)
        select_from_dropdown(driver, wait, "street", street)
        select_from_dropdown(driver, wait, "house_num", building)

        # Очікування результату
        time.sleep(5)
        
        # Шукаємо текст результату
        try:
            # Шукаємо за класом, який з'являється при видачі результату
            res_element = driver.find_element(By.CSS_SELECTOR, ".shutdown-search-result, .is-open")
            full_text = res_element.text
        except:
            # Якщо блок не знайдено, беремо текст всієї сторінки
            full_text = driver.find_element(By.TAG_NAME, "body").text

        # Логіка визначення статусу
        is_off = any(word in full_text for word in ["відсутня електроенергія", "Екстрені відключення"])
        
        return jsonify({
            "success": True,
            "status": "OFF" if is_off else "ON",
            "address": f"{city}, {street}, {building}",
            "info": full_text.strip()[:1000],
            "timestamp": time.strftime("%H:%M:%S")
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
