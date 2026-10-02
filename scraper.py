import json
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select, Select, Select, Select
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



def sync_mes_anterior_scraper(matricula, senha, mes_ano):
    """Importa automaticamente um mês anterior pelo Relatório de Ponto."""
    import calendar
    import datetime as _datetime
    import re as _re
    import time as _time
    from selenium import webdriver as _webdriver
    from selenium.webdriver.common.by import By as _By
    from selenium.webdriver.chrome.options import Options as _Options
    from selenium.webdriver.support.ui import WebDriverWait as _Wait, Select as _Select
    from selenium.webdriver.support import expected_conditions as _EC

    try:
        mes, ano = [int(valor) for valor in str(mes_ano).split("/")]
    except (TypeError, ValueError):
        raise ValueError("Período inválido: use MM/AAAA.")

    nomes = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
             "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
    periodo_texto = nomes[mes - 1] + "/" + str(ano)

    opcoes = _Options()
    opcoes.add_argument("--start-maximized")
    opcoes.add_argument("--disable-notifications")
    driver = _criar_driver_chrome(opcoes)
    espera = _Wait(driver, 30)

    try:
        # A URL do portal é aproveitada quando já existir no scraper.
        url_portal = globals().get("URL_LOGIN") or globals().get("URL_PORTAL")
        if not url_portal:
            raise RuntimeError("URL_LOGIN ou URL_PORTAL não foi encontrada no scraper.")

        driver.get(url_portal)

        # Seletores tolerantes para a tela de login do Portal MGS.
        usuario = None
        for seletor in ["#matricula", "#Matricula", "input[name='matricula']", "input[name='usuario']", "input[type='text']"]:
            encontrados = driver.find_elements(_By.CSS_SELECTOR, seletor)
            if encontrados:
                usuario = encontrados[0]
                break
        senha_input = None
        for seletor in ["#senha", "#Senha", "input[name='senha']", "input[type='password']"]:
            encontrados = driver.find_elements(_By.CSS_SELECTOR, seletor)
            if encontrados:
                senha_input = encontrados[0]
                break
        if usuario is None or senha_input is None:
            raise RuntimeError("Campos de login não encontrados no Portal MGS.")

        usuario.clear()
        usuario.send_keys(matricula)
        senha_input.clear()
        senha_input.send_keys(senha)
        botoes = driver.find_elements(_By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        if not botoes:
            raise RuntimeError("Botão de login não encontrado no Portal MGS.")
        botoes[0].click()

        espera.until(lambda d: len(d.window_handles) >= 1)
        espera.until(lambda d: "login" not in d.current_url.lower() or len(d.window_handles) > 1)

        # Ponto WEB abre a apuração em outra aba.
        abas_antes = set(driver.window_handles)
        ponto_web = espera.until(_EC.element_to_be_clickable((_By.XPATH,
            "//*[self::a or self::button][contains(translate(normalize-space(.), "
            "'abcdefghijklmnopqrstuvwxyzáàâãçéêíóôõúü', "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZAAACEEIOOOUU'), 'PONTO WEB')]")))
        driver.execute_script("arguments[0].click();", ponto_web)
        espera.until(lambda d: len(d.window_handles) > len(abas_antes))
        nova_aba = next(aba for aba in driver.window_handles if aba not in abas_antes)
        driver.switch_to.window(nova_aba)
        espera.until(lambda d: d.execute_script("return document.readyState") == "complete")

        driver.get("https://sistemas.mgs.srv.br:8082/relatorios")
        seletor_periodo = espera.until(_EC.presence_of_element_located((_By.ID, "periodo-select")))
        combo = _Select(seletor_periodo)
        opcao = next((item for item in combo.options if item.text.strip().upper() == periodo_texto), None)
        if opcao is None:
            raise RuntimeError("Período " + periodo_texto + " não encontrado no Relatório de Ponto.")
        combo.select_by_visible_text(opcao.text)
        espera.until(_EC.presence_of_element_located((_By.ID, "marcacoesRelatorioTableBody")))
        _time.sleep(2)

        database.garantir_dias_mes_banco(mes_ano)
        linhas = driver.find_elements(_By.CSS_SELECTOR, "#marcacoesRelatorioTableBody tr")
        importados = 0
        for linha in linhas:
            colunas = linha.find_elements(_By.TAG_NAME, "td")
            if len(colunas) < 2:
                continue
            data_encontrada = _re.search(r"\b(\d{2})/(\d{2})(?:/(\d{4}))?\b", colunas[0].text)
            if not data_encontrada:
                continue
            dia, mes_linha, ano_linha = data_encontrada.groups()
            ano_linha = ano_linha or str(ano)
            if int(mes_linha) != mes or int(ano_linha) != ano:
                continue
            data = dia + "/" + mes_linha + "/" + ano_linha
            horarios = _re.findall(r"\b\d{2}:\d{2}\b", colunas[1].text)
            database.importar_marcacoes_relatorio(data, horarios[:4])
            importados += 1

        return True, "Importação concluída. Dias com marcação importados: " + str(importados)

    except Exception as erro:
        return False, "Erro na importação histórica: " + str(erro)
    finally:
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


# ============================================================================
# Driver Chrome resiliente - instalado pelo atualizador 2026.10.02-driver-debug
# ============================================================================
def criar_driver_chrome(options):
    """Cria ChromeDriver com alternativas para evitar Selenium Manager falhar."""
    import glob
    import shutil as _shutil
    from selenium import webdriver as _webdriver
    from selenium.webdriver.chrome.service import Service

    erros = []
    candidatos = []

    variavel = os.environ.get("CHROMEDRIVER")
    if variavel:
        candidatos.append(variavel)

    raiz = os.path.dirname(os.path.abspath(__file__))
    candidatos.extend([
        os.path.join(raiz, "chromedriver.exe"),
        os.path.join(raiz, "chromedriver"),
        _shutil.which("chromedriver"),
    ])

    candidatos.extend(glob.glob(os.path.expanduser(
        "~/.wdm/drivers/chromedriver/**/chromedriver.exe"
    ), recursive=True))

    vistos = set()
    for candidato in candidatos:
        if not candidato or candidato in vistos:
            continue
        vistos.add(candidato)
        if not os.path.isfile(candidato):
            continue
        try:
            return _webdriver.Chrome(
                service=Service(candidato),
                options=options
            )
        except Exception as erro:
            erros.append(f"{candidato}: {erro}")

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        caminho = ChromeDriverManager().install()
        return _webdriver.Chrome(
            service=Service(caminho),
            options=options
        )
    except Exception as erro:
        erros.append(f"webdriver-manager: {erro}")

    try:
        return _webdriver.Chrome(options=options)
    except Exception as erro:
        erros.append(f"Selenium Manager: {erro}")

    raise RuntimeError(
        "Não foi possível criar o ChromeDriver. Caminhos e métodos testados:\n- "
        + "\n- ".join(erros)
        + "\n\nInstale/atualize o Google Chrome ou coloque chromedriver.exe "
        "na mesma pasta do scraper.py."
    )
