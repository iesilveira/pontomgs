"""
Autor: Ismael Elói da Silveira Silva
Descrição: Módulo de automação com Selenium (Raspagem de Dados) e PyAutoGUI (Ação de Registro).
"""
import os
import time
import datetime
import re
import pyautogui
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import database

def buscar_marcacoes_selenium(matricula, senha):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    try:
        chromedriver_path = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
            
        driver.set_page_load_timeout(30)
        driver.get("http://areaempregado.mgs.srv.br/login")
        login_url = driver.current_url

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "fMat"))).send_keys(matricula)
        driver.find_element(By.NAME, "fPass").send_keys(senha)
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        try:
            WebDriverWait(driver, 15).until(lambda d: d.current_url != login_url or len(d.find_elements(By.XPATH, "//div[@role=\'dialog\']//button[text()=\'OK\']")) > 0)
            error_dialog = driver.find_elements(By.XPATH, "//div[@role=\'dialog\']//button[text()=\'OK\']")
            if error_dialog:
                error_dialog[0].click()
                time.sleep(1)
                return "Erro: Usuário ou senha incorreta."
        except Exception:
            pass

        driver.get("http://areaempregado.mgs.srv.br/Empregado/MarcacoesPonto")
        
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".k-grid-content table, .k-table")))
            time.sleep(3)
        except:
            pass
        
        soup_ponto = BeautifulSoup(driver.page_source, 'html.parser')
        
        rows = soup_ponto.find_all("tr", class_=lambda c: c and "k-master-row" in c.split())
        if not rows:
            table = soup_ponto.find("div", class_="k-grid-content")
            if table:
                rows = table.find_all("tr")
        
        marcacoes_texto = "Sem marcações"
        hoje_str = datetime.datetime.now().strftime("%d/%m/%Y")
        
        encontrou_hoje = False
        if rows:
            for row in reversed(rows):
                tds = row.find_all("td")
                if len(tds) >= 2:
                    data_texto = tds[0].text.strip()
                    marcacoes = tds[1].text.strip()
                    
                    if hoje_str in data_texto:
                        if marcacoes:
                            marcacoes_texto = marcacoes
                        encontrou_hoje = True
                        break
            
            if not encontrou_hoje:
                last_row = rows[-1]
                tds = last_row.find_all("td")
                if len(tds) >= 2:
                    marcacoes = tds[1].text.strip()
                    if marcacoes:
                        marcacoes_texto = f"Última ({tds[0].text.strip()}): {marcacoes}"

        return marcacoes_texto

    except Exception:
        return "Erro ao buscar marcações"
    finally:
        if driver:
            driver.quit()

def sync_mes_scraper(matricula, senha):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    try:
        chromedriver_path = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
            
        driver.set_page_load_timeout(30)
        driver.get("http://areaempregado.mgs.srv.br/login")
        login_url = driver.current_url

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "fMat"))).send_keys(matricula)
        driver.find_element(By.NAME, "fPass").send_keys(senha)
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        try:
            WebDriverWait(driver, 15).until(lambda d: d.current_url != login_url or len(d.find_elements(By.XPATH, "//div[@role=\'dialog\']//button[text()=\'OK\']")) > 0)
            error_dialog = driver.find_elements(By.XPATH, "//div[@role=\'dialog\']//button[text()=\'OK\']")
            if error_dialog:
                return False
        except Exception:
            pass

        driver.get("http://areaempregado.mgs.srv.br/Empregado/MarcacoesPonto")
        
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".k-grid-content table, .k-table")))
            time.sleep(3)
        except:
            pass
        
        soup_ponto = BeautifulSoup(driver.page_source, 'html.parser')
        
        rows = soup_ponto.find_all("tr", class_=lambda c: c and "k-master-row" in c.split())
        if not rows:
            table = soup_ponto.find("div", class_="k-grid-content")
            if table:
                rows = table.find_all("tr")
        
        if rows:
            hoje_str = datetime.datetime.now().strftime("%d/%m/%Y")
            
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 2:
                    data_texto = tds[0].text.strip()
                    marcacoes_texto = tds[1].text.strip()
                    
                    match_data = re.search(r'\d{2}/\d{2}/\d{4}', data_texto)
                    if match_data:
                        data_formatada = match_data.group(0)
                        
                        if data_formatada != hoje_str and database.check_dia_completo(data_formatada):
                            continue
                        
                        tempos = re.findall(r'\d{2}:\d{2}', marcacoes_texto)
                        m1 = tempos[0] if len(tempos) > 0 else ""
                        m2 = tempos[1] if len(tempos) > 1 else ""
                        m3 = tempos[2] if len(tempos) > 2 else ""
                        m4 = tempos[3] if len(tempos) > 3 else ""
                        
                        database.update_dia_banco(data_formatada, m1, m2, m3, m4, is_manual=False)
        return True
    except Exception as e:
        raise Exception(f"Erro na sincronização: {e}")
    finally:
        if driver:
            driver.quit()

def realizar_registro_ponto(matricula, senha):
    desktop_public = os.path.join(os.environ['PUBLIC'], 'Desktop')
    desktop_user = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    atalho_nome = "Registro de Ponto.appref-ms"
    
    caminho_atalho = os.path.join(desktop_user, atalho_nome)
    if not os.path.exists(caminho_atalho):
        caminho_atalho = os.path.join(desktop_public, atalho_nome)
        
    if os.path.exists(caminho_atalho):
        os.startfile(caminho_atalho)
    else:
        return False, f"Atalho '{atalho_nome}' não encontrado na Área de Trabalho."

    time.sleep(1) 
    pyautogui.write(matricula)
    pyautogui.press('tab')
    pyautogui.write(senha)
    pyautogui.press('tab')
    return True, ""