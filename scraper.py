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

def _criar_driver_chrome(options=None, **kwargs):
    """Cria o ChromeDriver com fallback para Selenium Manager.

    Parâmetros opcionais aceitos:
        options: ChromeOptions já configuradas.
        visivel / visible: True para abrir o Chrome visivelmente.
        headless: True para solicitar execução sem janela.
        driver_path / executable_path: caminho explícito do chromedriver.

    Se nenhuma opção de visibilidade for informada, mantém as opções
    recebidas. Assim, opções headless já existentes continuam headless,
    enquanto a rotina histórica sem --headless permanece visível.
    """
    import os
    from pathlib import Path
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    if options is None:
        options = kwargs.pop("chrome_options", None)
    if options is None:
        options = kwargs.pop("opcoes", None)
    if options is None:
        options = webdriver.ChromeOptions()

    visivel = kwargs.pop("visivel", kwargs.pop("visible", None))
    headless = kwargs.pop("headless", None)
    if visivel is None and headless is not None:
        visivel = not bool(headless)

    argumentos = list(getattr(options, "arguments", []))
    if visivel is True:
        for argumento in argumentos:
            if argumento.startswith("--headless"):
                try:
                    options.arguments.remove(argumento)
                except (AttributeError, ValueError):
                    pass
    elif visivel is False:
        if not any(arg.startswith("--headless") for arg in argumentos):
            options.add_argument("--headless=new")

    caminho_explicito = (
        kwargs.pop("driver_path", None)
        or kwargs.pop("executable_path", None)
        or os.environ.get("CHROMEDRIVER_PATH")
        or os.environ.get("CHROMEDRIVER")
    )

    caminhos = []
    if caminho_explicito:
        caminhos.append(Path(caminho_explicito))

    caminho_local = Path(__file__).resolve().parent / "chromedriver.exe"
    if caminho_local not in caminhos and caminho_local.exists():
        caminhos.append(caminho_local)

    erros = []
    for caminho in caminhos:
        if not caminho.exists():
            erros.append(f"Driver não encontrado: {caminho}")
            continue
        try:
            return webdriver.Chrome(
                service=Service(executable_path=str(caminho)),
                options=options
            )
        except Exception as erro:
            erros.append(
                f"Falha usando {caminho}: {type(erro).__name__}: {erro}"
            )

    # Selenium Manager procura/baixa automaticamente um driver compatível.
    try:
        return webdriver.Chrome(options=options)
    except Exception as erro:
        erros.append(
            "Falha usando Selenium Manager: "
            f"{type(erro).__name__}: {erro}"
        )

    detalhes = "\n".join(erros) if erros else "Nenhum método de inicialização disponível."
    raise RuntimeError(
        "Não foi possível iniciar o ChromeDriver. Verifique se o Chrome está "
        "instalado e se a versão do Selenium consegue obter um driver compatível.\n"
        + detalhes
    )

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



# Controle manual da janela do Chrome na importação histórica.
# True = visível; False = oculto.
CHROME_VISIVEL_IMPORTACAO_HISTORICA = False

def sync_mes_anterior_scraper(matricula, senha, mes_ano, modo_debug=True):
    """Importa mês anterior pelo relatório do Ponto WEB, usando o fluxo mapeado."""
    import calendar as _calendar
    import datetime as _datetime
    import os as _os
    import re as _re
    import sqlite3 as _sqlite3
    import time as _time
    import traceback as _traceback
    from selenium import webdriver as _webdriver
    from selenium.webdriver.common.by import By as _By
    from selenium.webdriver.support.ui import WebDriverWait as _Wait
    from selenium.webdriver.support.ui import Select as _Select
    from selenium.webdriver.support import expected_conditions as _EC

    try:
        mes_texto, ano_texto = str(mes_ano).strip().split("/")
        mes = int(mes_texto)
        ano = int(ano_texto)
        if not 1 <= mes <= 12 or len(ano_texto) != 4:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Período inválido. Use o formato MM/AAAA.")

    mes_ano = f"{mes:02d}/{ano:04d}"
    nomes_meses = [
        "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
        "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
    ]
    periodo_portal = nomes_meses[mes - 1] + "/" + str(ano)

    driver = None

    def registrar(etapa):
        return None

    def garantir_dias_do_mes():
        """Garante todas as datas, inclusive fins de semana, sem apagar registros existentes."""
        garantir = getattr(database, "garantir_dias_mes_banco", None)
        if callable(garantir):
            garantir(mes_ano)
            return

        database.init_db()
        arquivo_db = getattr(database, "DB_FILE", None)
        if not arquivo_db:
            registrar("Aviso: database.DB_FILE não está disponível; não foi possível pré-criar dias vazios.")
            return

        conexao = _sqlite3.connect(arquivo_db)
        cursor = conexao.cursor()
        ultimo_dia = _calendar.monthrange(ano, mes)[1]
        for dia_numero in range(1, ultimo_dia + 1):
            data = f"{dia_numero:02d}/{mes:02d}/{ano:04d}"
            cursor.execute("SELECT 1 FROM banco_horas WHERE data = ?", (data,))
            if cursor.fetchone():
                continue
            data_obj = _datetime.date(ano, mes, dia_numero)
            marca_vazia = "-" if data_obj.weekday() >= 5 else ""
            cursor.execute(
                """
                INSERT INTO banco_horas
                    (data, m1, m2, m3, m4, saldo, manual, justificativa,
                     orig_m1, orig_m2, orig_m3, orig_m4)
                VALUES (?, ?, ?, ?, ?, ?, 0, '', '', '', '', '')
                """,
                (data, marca_vazia, marca_vazia, marca_vazia, marca_vazia, "")
            )
        conexao.commit()
        conexao.close()

    def abrir_pagina_controle_ponto(wait, aba_original):
        """Abre Ponto WEB e acompanha a nova aba, com fallback pela URL mapeada."""
        abas_antes = set(driver.window_handles)
        elemento_ponto_web = None

        try:
            elemento_ponto_web = wait.until(
                _EC.element_to_be_clickable((_By.ID, "navbarDropdown_3600360036003300"))
            )
        except Exception:
            candidatos = driver.find_elements(
                _By.XPATH,
                "//a[contains(translate(normalize-space(.), "
                "'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PONTO WEB')]"
            )
            if candidatos:
                elemento_ponto_web = candidatos[0]

        if elemento_ponto_web is not None:
            registrar("Clicando no menu PONTO WEB.")
            try:
                elemento_ponto_web.click()
            except Exception:
                driver.execute_script("arguments[0].click();", elemento_ponto_web)

        # Em algumas sessões o clique abre diretamente a nova aba; em outras,
        # primeiro abre o submenu e é necessário clicar em Controle de Ponto.
        try:
            _Wait(driver, 5).until(lambda d: len(d.window_handles) > len(abas_antes))
        except Exception:
            controle = None
            try:
                controle = _Wait(driver, 8).until(
                    _EC.element_to_be_clickable((
                        _By.XPATH,
                        "//*[self::a or self::button][contains(translate(normalize-space(.), "
                        "'abcdefghijklmnopqrstuvwxyzáàâãçéêíóôõúü', "
                        "'ABCDEFGHIJKLMNOPQRSTUVWXYZAAACEEIOOOUU'), 'CONTROLE DE PONTO')]"
                    ))
                )
            except Exception:
                pass

            if controle is not None:
                registrar("Submenu aberto; clicando em Controle de Ponto.")
                try:
                    controle.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", controle)

            try:
                _Wait(driver, 12).until(lambda d: len(d.window_handles) > len(abas_antes))
            except Exception:
                pass

        novas_abas = [aba for aba in driver.window_handles if aba not in abas_antes]
        if novas_abas:
            aba_alvo = novas_abas[-1]
            driver.switch_to.window(aba_alvo)
            _Wait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
            )
            registrar("Controle de Ponto aberto em nova aba; Selenium trocou para ela.")
            return

        # URL confirmada pelo mapeamento fornecido pelo usuário.
        registrar("A nova aba não surgiu pelo clique; abrindo a rota mapeada de Controle de Ponto.")
        driver.execute_script(
            "window.open(arguments[0], '_blank');",
            "https://sistemas.mgs.srv.br:8082/ocorrencia-ponto"
        )
        _Wait(driver, 15).until(lambda d: len(d.window_handles) > len(abas_antes))
        novas_abas = [aba for aba in driver.window_handles if aba not in abas_antes]
        if not novas_abas:
            raise RuntimeError("O portal não abriu uma nova aba de Controle de Ponto.")
        driver.switch_to.window(novas_abas[-1])
        _Wait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
        )
        registrar("Aba de Controle de Ponto aberta pela rota mapeada.")

    registrar("Início da importação histórica: " + mes_ano + "; período do portal: " + periodo_portal)

    try:
        opcoes = webdriver.ChromeOptions()
        # CONTROLE DE VISIBILIDADE DO CHROME
        # True mostra a janela; False executa o Chrome oculto.
        for _chrome_argument in list(opcoes.arguments):
            if str(_chrome_argument).lower().startswith("--headless"):
                opcoes.arguments.remove(_chrome_argument)
        if CHROME_VISIVEL_IMPORTACAO_HISTORICA:
            opcoes.add_argument("--start-maximized")
        else:
            opcoes.add_argument("--headless=new")
            opcoes.add_argument("--window-size=1920,1080")
        opcoes.add_argument("--disable-notifications")

        criar_driver = globals().get("criar_driver_chrome") or globals().get("_criar_driver_chrome")
        if callable(criar_driver):
            driver = criar_driver(opcoes)
        else:
            registrar("Helper de ChromeDriver ausente; usando Selenium Manager.")
            driver = _webdriver.Chrome(options=opcoes)

        driver.maximize_window()
        driver.set_page_load_timeout(45)
        wait = _Wait(driver, 30)

        url_login = "http://areaempregado.mgs.srv.br/login"
        registrar("Abrindo tela de login do Portal MGS.")
        driver.get(url_login)
        url_tela_login = driver.current_url

        campo_matricula = wait.until(
            _EC.presence_of_element_located((_By.NAME, "fMat"))
        )
        campo_senha = wait.until(
            _EC.presence_of_element_located((_By.NAME, "fPass"))
        )
        campo_matricula.clear()
        campo_matricula.send_keys(matricula)
        campo_senha.clear()
        campo_senha.send_keys(senha)
        registrar("Credenciais preenchidas; enviando login.")

        botao_login = driver.find_element(_By.CSS_SELECTOR, "input[type='submit']")
        botao_login.click()

        try:
            wait.until(
                lambda d: d.current_url != url_tela_login
                or len(d.window_handles) > 1
                or bool(d.find_elements(_By.XPATH, "//div[@role='dialog']//button[normalize-space()='OK']"))
            )
        except Exception:
            pass

        erro_login = driver.find_elements(
            _By.XPATH,
            "//div[@role='dialog']//button[normalize-space()='OK']"
        )
        if erro_login:
            raise RuntimeError("O Portal MGS exibiu erro de login. Verifique matrícula e senha.")

        if "login" in driver.current_url.lower():
            raise RuntimeError("O login não foi confirmado; a página ainda está na tela de autenticação.")
        registrar("Login concluído: " + str(driver.current_url))

        aba_original = driver.current_window_handle
        wait_portal = _Wait(driver, 20)
        abrir_pagina_controle_ponto(wait_portal, aba_original)

        url_relatorios = "https://sistemas.mgs.srv.br:8082/relatorios"
        registrar("Abrindo Relatórios de Ponto.")
        driver.get(url_relatorios)
        seletor_periodo = _Wait(driver, 30).until(
            _EC.presence_of_element_located((_By.ID, "periodo-select"))
        )
        combo = _Select(seletor_periodo)
        opcao = None
        for item in combo.options:
            if item.text.strip().upper() == periodo_portal:
                opcao = item
                break
        if opcao is None:
            disponiveis = [item.text.strip() for item in combo.options]
            raise RuntimeError(
                "Período " + periodo_portal + " não encontrado. Opções disponíveis: "
                + ", ".join(disponiveis[:12])
            )

        registrar("Selecionando período " + periodo_portal + ".")
        combo.select_by_visible_text(opcao.text)
        _Wait(driver, 30).until(lambda d: "periodoId=" in d.current_url)
        corpo = _Wait(driver, 30).until(
            _EC.presence_of_element_located((_By.ID, "marcacoesRelatorioTableBody"))
        )
        _time.sleep(1)
        registrar("Tabela Marcações carregada; garantindo todos os dias do mês.")
        garantir_dias_do_mes()

        linhas = corpo.find_elements(_By.CSS_SELECTOR, "tr")
        importados = 0
        linhas_lidas = 0
        for linha in linhas:
            colunas = linha.find_elements(_By.TAG_NAME, "td")
            if len(colunas) < 2:
                continue
            texto_data = colunas[0].text.strip()
            correspondencia = _re.search(r"(\d{2})/(\d{2})(?:/(\d{4}))?", texto_data)
            if not correspondencia:
                continue
            dia, mes_linha, ano_linha = correspondencia.groups()
            ano_linha = ano_linha or str(ano)
            if int(mes_linha) != mes or int(ano_linha) != ano:
                continue
            linhas_lidas += 1
            data = f"{dia}/{mes:02d}/{ano:04d}"
            horarios = _re.findall(r"\d{2}:\d{2}", colunas[1].text)
            if not horarios:
                continue

            horarios = horarios[:4]
            importar = getattr(database, "importar_marcacoes_relatorio", None)
            if callable(importar):
                importar(data, horarios)
            else:
                valores = horarios + [""] * (4 - len(horarios))
                database.update_dia_banco(
                    data,
                    valores[0],
                    valores[1],
                    valores[2],
                    valores[3],
                    is_manual=False
                )
            importados += 1

        registrar(
            "Extração concluída: " + str(linhas_lidas)
            + " linha(s) do mês; " + str(importados)
            + " dia(s) com marcações importados."
        )
        return True, (
            "Importação histórica concluída para " + mes_ano + ". "
            + str(importados) + " dia(s) com marcações importados."
        )

    except Exception as erro:
        registrar("FALHA: " + type(erro).__name__ + ": " + str(erro))
        registrar(_traceback.format_exc())
        if driver is not None:
            registrar("Chrome permanecerá aberto por 60 segundos para inspeção.")
        return False, "Erro na importação histórica: " + str(erro)

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

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

