from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time
import os
import re

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

def fill_field_and_select(driver, field, value, wait):
    """Заповнює поле та вибирає варіант з autocomplete"""
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

def get_power_outage_info(city="Одеса", street="Марсельська", building="60"):
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
            return {"success": False, "error": "Не вдалось вибрати місто"}
        
        if not fill_field_and_select(driver, street_field, street, wait):
            return {"success": False, "error": "Не вдалось вибрати вулицю"}
        
        if not fill_field_and_select(driver, building_field, building, wait):
            return {"success": False, "error": "Не вдалось вибрати будинок"}
        
        time.sleep(3)
        
        try:
            result_div = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#showCurOutage.active, div.active"))
            )
            
            full_text = result_div.text
            
            restoration_line = ""
            lines = full_text.split('\n')
            
            for line in lines:
                if "Орієнтовний час відновлення" in line and "до" in line:
                    restoration_line = line.strip()
                    break
            
            if not restoration_line:
                for line in lines:
                    if "до" in line and any(char.isdigit() for char in line):
                        restoration_line = line.strip()
                        break
            
            return {
                "success": True,
                "restoration_time": restoration_line if restoration_line else "Інформація про час відновлення не знайдена",
                "full_info": full_text,
                "address": f"м. {city}, вул. {street}, {building}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except TimeoutException:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "відсутня електроенергія" in body_text or "відключення" in body_text:
                lines = body_text.split('\n')
                for line in lines:
                    if "Орієнтовний час" in line or ("до" in line and ":" in line):
                        return {
                            "success": True,
                            "restoration_time": line.strip(),
                            "full_info": "Інформація знайдена",
                            "address": f"м. {city}, вул. {street}, {building}",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
            
            return {
                "success": False,
                "error": "Результат не з'явився. Можливо адреса некоректна.",
                "address": f"м. {city}, вул. {street}, {building}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "address": f"м. {city}, вул. {street}, {building}"
        }
    finally:
        if driver:
            driver.quit()

@app.route('/')
def home():
    return jsonify({
        "message": "DTEK Power Outage API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "/health": "Health check",
            "/check": "Check power outage (params: city, street, building)"
        },
        "example": "/check?city=Одеса&street=Марсельська&building=60"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/check')
def check_outage():
    city = request.args.get('city', 'Одеса')
    street = request.args.get('street', 'Марсельська')
    building = request.args.get('building', '60')
    
    result = get_power_outage_info(city, street, building)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
