"""
Autor: Ismael Elói da Silveira Silva
Descrição: Atualizador do Assistente do PontoWeb MGS.

Versão da atualização: 2026.10.02-01

Alterações desta versão:

- Corrige o comando "Limpar Mês" no Banco de Horas.
- "Limpar Mês" deixa de apagar as linhas do mês inteiro.
- Agora ele apenas reseta marcações, saldo, manual, justificativa
  e marcações originais de cada dia do mês selecionado.
- Garante que TODOS os dias do mês existam na tabela banco_horas,
  inclusive sábados e domingos, com a identificação já usada
  pela própria tela (traço "-" nos finais de semana sem marcação).
- Cria uma tabela de histórico de períodos (historico_periodos),
  para que um mês já utilizado nunca mais desapareça do seletor,
  mesmo depois de ser limpo.
- Ajusta get_meses_disponiveis() para combinar os meses existentes
  em banco_horas com os meses já registrados no histórico.
- Garante os dias do mês automaticamente ao consultar o Banco de
  Horas (tela) e ao gerar o relatório em PDF.

Funcionamento do atualizador:

- Procura exclusivamente arquivos .py ou .pyw.
- Cria backup antes de modificar o arquivo.
- Valida a sintaxe antes e depois da atualização.
- Utiliza gravação atômica.
- Restaura o arquivo original em caso de falha.
- Exibe um relatório no terminal.
- Salva uma cópia do relatório em arquivo TXT.
"""

import os
import sys
import shutil
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# =============================================================================
# CONFIGURAÇÕES DO ATUALIZADOR
# =============================================================================

VERSAO_ATUALIZACAO = "2026.10.02-01"
NOME_APLICACAO = "Assistente do PontoWeb MGS"

BASE_DIR = Path(__file__).resolve().parent
DATA_EXECUCAO = datetime.now()

IDENTIFICADOR_EXECUCAO = DATA_EXECUCAO.strftime(
    "%Y%m%d_%H%M%S"
)

PASTA_BACKUP = BASE_DIR / (
    "backup_atualizacao_"
    + IDENTIFICADOR_EXECUCAO
)

CAMINHO_RELATORIO = BASE_DIR / (
    "relatorio_atualizacao_ponto_"
    + IDENTIFICADOR_EXECUCAO
    + ".txt"
)


# =============================================================================
# ESTRUTURAS
# =============================================================================

@dataclass
class ResultadoAtualizacao:
    arquivo: str
    status: str
    detalhes: str
    backup: str = ""


resultados = []


# =============================================================================
# NOVO CONTEÚDO COMPLETO DO DATABASE.PY
# =============================================================================

NOVO_DATABASE_PY = r'''"""
Autor: Ismael Elói da Silveira Silva
Descrição: Módulo de banco de dados SQLite para armazenamento local das credenciais e lembretes.
"""
import sqlite3
import os
import calendar
import datetime
from settings import APP_DIR, DB_FILE

def init_db():
    if not os.path.exists(APP_DIR):
        os.makedirs(APP_DIR)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Tabela de Credenciais
    cursor.execute(\'\'\'
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT NOT NULL,
            senha TEXT NOT NULL,
            saida_almoco TEXT DEFAULT \'12:00\',
            intervalo_atualizacao INTEGER DEFAULT 10
        )
    \'\'\')

    try:
        cursor.execute(
            \'ALTER TABLE credentials \'
            \'ADD COLUMN saida_almoco TEXT DEFAULT "12:00"\'
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            \'ALTER TABLE credentials \'
            \'ADD COLUMN intervalo_atualizacao INTEGER DEFAULT 10\'
        )
    except sqlite3.OperationalError:
        pass

    # Tabela de Lembretes Dinâmicos
    cursor.execute(\'\'\'
        CREATE TABLE IF NOT EXISTS lembretes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            evento TEXT NOT NULL,
            tempo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            mensagem TEXT DEFAULT \'\'
        )
    \'\'\')

    try:
        cursor.execute(
            \'ALTER TABLE lembretes \'
            \'ADD COLUMN mensagem TEXT DEFAULT ""\'
        )
    except sqlite3.OperationalError:
        pass

    # Tabela de Banco de Horas
    cursor.execute(\'\'\'
        CREATE TABLE IF NOT EXISTS banco_horas (
            data TEXT PRIMARY KEY,
            m1 TEXT,
            m2 TEXT,
            m3 TEXT,
            m4 TEXT,
            saldo TEXT,
            manual INTEGER DEFAULT 0,
            justificativa TEXT DEFAULT \'\'
        )
    \'\'\')

    try:
        cursor.execute(
            \'ALTER TABLE banco_horas \'
            \'ADD COLUMN manual INTEGER DEFAULT 0\'
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            \'ALTER TABLE banco_horas \'
            \'ADD COLUMN justificativa TEXT DEFAULT ""\'
        )
    except sqlite3.OperationalError:
        pass

    # Cópia das marcações originais do sistema
    for col in [
        \'orig_m1\',
        \'orig_m2\',
        \'orig_m3\',
        \'orig_m4\'
    ]:
        try:
            cursor.execute(
                f\'ALTER TABLE banco_horas \'
                f\'ADD COLUMN {col} TEXT DEFAULT ""\'
            )
        except sqlite3.OperationalError:
            pass

    # Tabela de histórico de períodos já utilizados.
    #
    # Garante que um mês já acessado ou limpo nunca mais desapareça
    # do seletor de meses, mesmo que todos os dias fiquem sem
    # nenhuma marcação lançada.
    cursor.execute(\'\'\'
        CREATE TABLE IF NOT EXISTS historico_periodos (
            mes_ano TEXT PRIMARY KEY
        )
    \'\'\')

    # Lembretes iniciais
    cursor.execute(
        "SELECT COUNT(*) FROM lembretes"
    )

    if cursor.fetchone()[0] == 0:
        cursor.execute(
            \'\'\'
            INSERT INTO lembretes (
                nome,
                evento,
                tempo,
                tipo,
                mensagem
            )
            VALUES (?, ?, ?, ?, ?)
            \'\'\',
            (
                \'Lembrete Almoço\',
                \'Horário previsto de almoço\',
                \'00:02\',
                \'Antes\',
                \'Seu almoço está previsto para as {}\'
            )
        )

        cursor.execute(
            \'\'\'
            INSERT INTO lembretes (
                nome,
                evento,
                tempo,
                tipo,
                mensagem
            )
            VALUES (?, ?, ?, ?, ?)
            \'\'\',
            (
                \'Lembrete Retorno\',
                \'Horário previsto de fim do almoço\',
                \'00:02\',
                \'Antes\',
                \'Seu retorno está previsto para as {}\'
            )
        )

    conn.commit()
    conn.close()

def get_credentials():
    init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(\'\'\'
        SELECT
            matricula,
            senha,
            saida_almoco,
            intervalo_atualizacao
        FROM credentials
        ORDER BY id DESC
        LIMIT 1
    \'\'\')

    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            intervalo = int(row[3])
        except (TypeError, ValueError, IndexError):
            intervalo = 10

        intervalo = max(
            0,
            min(intervalo, 3600)
        )

        return {
            "matricula": row[0] or "",
            "senha": row[1] or "",
            "saida_almoco": row[2] or "12:00",
            "intervalo_atualizacao": intervalo
        }

    return {
        "matricula": "",
        "senha": "",
        "saida_almoco": "12:00",
        "intervalo_atualizacao": 10
    }

def save_credentials(
    matricula,
    senha,
    saida_almoco,
    intervalo_atualizacao=10
):
    init_db()

    try:
        intervalo = int(intervalo_atualizacao)
    except (TypeError, ValueError):
        intervalo = 10

    intervalo = max(
        0,
        min(intervalo, 3600)
    )

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        \'DELETE FROM credentials\'
    )

    cursor.execute(\'\'\'
        INSERT INTO credentials (
            matricula,
            senha,
            saida_almoco,
            intervalo_atualizacao
        )
        VALUES (?, ?, ?, ?)
    \'\'\', (
        matricula,
        senha,
        saida_almoco,
        intervalo
    ))

    conn.commit()
    conn.close()

def get_lembretes():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, evento, tempo, tipo, mensagem FROM lembretes ORDER BY id ASC')
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_lembrete(nome, evento, tempo, tipo, mensagem):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO lembretes (nome, evento, tempo, tipo, mensagem) VALUES (?, ?, ?, ?, ?)', 
                   (nome, evento, tempo, tipo, mensagem))
    conn.commit()
    conn.close()

def update_lembrete(lembrete_id, nome, evento, tempo, tipo, mensagem):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(\'\'\'
        UPDATE lembretes 
        SET nome = ?, evento = ?, tempo = ?, tipo = ?, mensagem = ? 
        WHERE id = ?
    \'\'\', (nome, evento, tempo, tipo, mensagem, lembrete_id))
    conn.commit()
    conn.close()

def delete_lembrete(lembrete_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM lembretes WHERE id = ?', (lembrete_id,))
    conn.commit()
    conn.close()

# --- Funções para Banco de Horas ---
def get_dia_semana(data_str):
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    try:
        dt = datetime.datetime.strptime(data_str, "%d/%m/%Y")
        return dias[dt.weekday()]
    except:
        return ""

def _registrar_periodo(cursor, mes_ano):
    """
    Registra o período no histórico, garantindo que ele nunca
    mais desapareça do seletor de meses, mesmo que todos os dias
    fiquem sem nenhuma marcação.
    """

    try:
        cursor.execute(
            "INSERT OR IGNORE INTO historico_periodos (mes_ano) VALUES (?)",
            (mes_ano,)
        )
    except sqlite3.OperationalError:
        pass

def registrar_periodo_utilizado(mes_ano):
    """
    Versão pública de _registrar_periodo, utilizável por outros
    módulos (telinha, banco de horas, importação histórica).
    """

    if not mes_ano:
        return

    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    _registrar_periodo(cursor, mes_ano)
    conn.commit()
    conn.close()

def garantir_dias_mes(mes_ano):
    """
    Garante que todos os dias do mês informado existam na tabela
    banco_horas, inclusive sábados e domingos, utilizando a mesma
    identificação já usada pela tela (traço "-" para finais de
    semana sem marcação).

    Também registra o período no histórico de meses utilizados,
    para que ele continue aparecendo no seletor mesmo depois de
    o mês ser limpo.
    """

    if not mes_ano or "/" not in mes_ano:
        return

    try:
        mes_str, ano_str = mes_ano.split("/")
        mes = int(mes_str)
        ano = int(ano_str)
    except (TypeError, ValueError):
        return

    if mes < 1 or mes > 12:
        return

    try:
        dias_no_mes = calendar.monthrange(ano, mes)[1]
    except (calendar.IllegalMonthError, ValueError):
        return

    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    _registrar_periodo(cursor, mes_ano)

    for dia in range(1, dias_no_mes + 1):
        data_str = f"{dia:02d}/{mes:02d}/{ano}"

        cursor.execute(
            "SELECT 1 FROM banco_horas WHERE data = ?",
            (data_str,)
        )

        if cursor.fetchone():
            continue

        try:
            dt = datetime.datetime(ano, mes, dia)
            wd = dt.weekday()
        except ValueError:
            wd = 0

        if wd in [5, 6]:
            m1 = m2 = m3 = m4 = "-"
        else:
            m1 = m2 = m3 = m4 = ""

        saldo = calcular_saldo_dia(data_str, m1, m2, m3, m4, "")

        cursor.execute(
            \'\'\'
            INSERT OR IGNORE INTO banco_horas (
                data, m1, m2, m3, m4, saldo, manual, justificativa,
                orig_m1, orig_m2, orig_m3, orig_m4
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, \'\', ?, ?, ?, ?)
            \'\'\',
            (data_str, m1, m2, m3, m4, saldo, m1, m2, m3, m4)
        )

    conn.commit()
    conn.close()

def get_meses_disponiveis():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        \'\'\'
        SELECT mes_ano FROM (
            SELECT DISTINCT substr(data, 4, 7) AS mes_ano
            FROM banco_horas
            UNION
            SELECT mes_ano FROM historico_periodos
        )
        WHERE mes_ano IS NOT NULL AND mes_ano != \'\'
        ORDER BY substr(mes_ano, 4, 4) DESC, substr(mes_ano, 1, 2) DESC
        \'\'\'
    )
    rows = cursor.fetchall()
    conn.close()
    
    meses = [row[0] for row in rows if row[0]]
    hoje_str = datetime.datetime.now().strftime("%m/%Y")
    if hoje_str not in meses:
        meses.insert(0, hoje_str)
    return meses

def calcular_saldo_dia(data, m1, m2, m3, m4, justificativa=""):
    def to_minutes(t_str):
        if not t_str or t_str.strip() in ["", "-", "None"]: 
            return None
        try:
            h, m = map(int, t_str.split(':'))
            return h * 60 + m
        except:
            return None
            
    t1 = to_minutes(m1)
    t2 = to_minutes(m2)
    t3 = to_minutes(m3)
    t4 = to_minutes(m4)
    
    is_future = False
    wd = 0
    try:
        dt = datetime.datetime.strptime(data, "%d/%m/%Y")
        wd = dt.weekday()
        hoje = datetime.datetime.now()
        hoje_dt = datetime.datetime(hoje.year, hoje.month, hoje.day)
        if dt > hoje_dt:
            is_future = True
    except:
        pass
        
    total_trabalhado = 0
    if t1 is not None and t2 is not None and t3 is not None and t4 is not None:
        total_trabalhado = (t4 - t3) + (t2 - t1)
        
    is_empty = (t1 is None and t2 is None and t3 is None and t4 is None)
    
    if wd in [5, 6]:
        if total_trabalhado > 0:
            h, m = divmod(total_trabalhado, 60)
            return f"+{h:02d}:{m:02d}"
        return ""
    else:
        if is_empty:
            if is_future:
                return ""
            if justificativa and justificativa.strip() != "":
                return "00:00"
            else:
                return "-08:00"
        else:
            if t1 is not None and t2 is not None and t3 is not None and t4 is not None:
                diff = total_trabalhado - 480
                if diff < 0 and justificativa and justificativa.strip() != "":
                    diff = 0
                sinal = "+" if diff >= 0 else "-"
                h, m = divmod(abs(diff), 60)
                return f"{sinal}{h:02d}:{m:02d}"
            else:
                return ""

def get_banco_horas(mes_ano):
    """
    Retorna os valores atuais e as marcações originais do período.

    Antes de consultar, garante que todos os dias do mês existam
    na tabela, inclusive sábados e domingos.

    Índices:
        0 data
        1 m1
        2 m2
        3 m3
        4 m4
        5 saldo
        6 manual
        7 justificativa
        8 orig_m1
        9 orig_m2
        10 orig_m3
        11 orig_m4
    """
    init_db()
    garantir_dias_mes(mes_ano)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            data,
            m1,
            m2,
            m3,
            m4,
            saldo,
            manual,
            justificativa,
            orig_m1,
            orig_m2,
            orig_m3,
            orig_m4
        FROM banco_horas
        WHERE data LIKE ?
        ORDER BY
            substr(data, 7, 4) ||
            substr(data, 4, 2) ||
            substr(data, 1, 2) ASC
        """,
        (f"%/{mes_ano}",)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_banco_horas_relatorio(mes_ano):
    """
    Retorna os dados mensais utilizados pelo relatório em PDF.

    Além dos valores atuais, retorna as marcações originais
    para permitir a identificação individual de alterações manuais.

    Antes de consultar, garante que todos os dias do mês existam
    na tabela, inclusive sábados e domingos.
    """

    init_db()
    garantir_dias_mes(mes_ano)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            data,
            m1,
            m2,
            m3,
            m4,
            saldo,
            manual,
            justificativa,
            orig_m1,
            orig_m2,
            orig_m3,
            orig_m4
        FROM banco_horas
        WHERE data LIKE ?
        ORDER BY
            substr(data, 7, 4) ||
            substr(data, 4, 2) ||
            substr(data, 1, 2) ASC
        """,
        (f"%/{mes_ano}",)
    )

    rows = cursor.fetchall()
    conn.close()

    return rows

def check_dia_completo(data):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT m1, m2, m3, m4, manual, justificativa FROM banco_horas WHERE data = ?', (data,))
    row = cursor.fetchone()
    conn.close()
    if row:
        m1, m2, m3, m4, manual, justif = row
        if manual == 1:
            return True
        if justif and justif.strip() != "":
            return True
        if m1 and m2 and m3 and m4 and m1 not in ["None", "-"] and m4 not in ["None", "-"]:
            return True
    return False

def update_dia_banco(data, m1, m2, m3, m4, justificativa="", is_manual=False):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Garante que o período do dia atualizado continue
    # disponível no histórico, mesmo que venha a ser limpo depois.
    try:
        partes_data = data.split("/")
        if len(partes_data) == 3:
            mes_ano_atual = f"{partes_data[1]}/{partes_data[2]}"
            _registrar_periodo(cursor, mes_ano_atual)
    except Exception:
        pass
    
    # Recupera originais em caso de edição manual ou atualização
    cursor.execute('SELECT manual, justificativa, orig_m1, orig_m2, orig_m3, orig_m4 FROM banco_horas WHERE data = ?', (data,))
    row = cursor.fetchone()
    
    if row and row[0] == 1 and not is_manual:
        conn.close()
        return
        
    if not is_manual and row and not justificativa:
        justificativa = row[1]
        
    orig_m1, orig_m2, orig_m3, orig_m4 = m1, m2, m3, m4
    if is_manual and row:
        orig_m1 = row[2] if row[2] is not None else ""
        orig_m2 = row[3] if row[3] is not None else ""
        orig_m3 = row[4] if row[4] is not None else ""
        orig_m4 = row[5] if row[5] is not None else ""
        
    try:
        dt = datetime.datetime.strptime(data, "%d/%m/%Y")
        wd = dt.weekday()
        if wd in [5, 6]:
            if not m1 or m1.strip() == "None": m1 = "-"
            if not m2 or m2.strip() == "None": m2 = "-"
            if not m3 or m3.strip() == "None": m3 = "-"
            if not m4 or m4.strip() == "None": m4 = "-"
    except:
        pass
        
    saldo = calcular_saldo_dia(data, m1, m2, m3, m4, justificativa)
    flag_manual = 1 if is_manual else 0
    
    cursor.execute(\'\'\'
        UPDATE banco_horas 
        SET m1 = ?, m2 = ?, m3 = ?, m4 = ?, saldo = ?, manual = ?, justificativa = ?, orig_m1 = ?, orig_m2 = ?, orig_m3 = ?, orig_m4 = ?
        WHERE data = ?
    \'\'\', (m1, m2, m3, m4, saldo, flag_manual, justificativa, orig_m1, orig_m2, orig_m3, orig_m4, data))
    
    if cursor.rowcount == 0:
        cursor.execute(\'\'\'
            INSERT INTO banco_horas (data, m1, m2, m3, m4, saldo, manual, justificativa, orig_m1, orig_m2, orig_m3, orig_m4) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        \'\'\', (data, m1, m2, m3, m4, saldo, flag_manual, justificativa, orig_m1, orig_m2, orig_m3, orig_m4))
        
    conn.commit()
    conn.close()

def restaurar_dia_original(data):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT orig_m1, orig_m2, orig_m3, orig_m4 FROM banco_horas WHERE data = ?', (data,))
    row = cursor.fetchone()
    
    if row:
        m1, m2, m3, m4 = row
        
        try:
            dt = datetime.datetime.strptime(data, "%d/%m/%Y")
            wd = dt.weekday()
            if wd in [5, 6]:
                if not m1 or m1.strip() == "None": m1 = "-"
                if not m2 or m2.strip() == "None": m2 = "-"
                if not m3 or m3.strip() == "None": m3 = "-"
                if not m4 or m4.strip() == "None": m4 = "-"
        except:
            pass
            
        saldo = calcular_saldo_dia(data, m1, m2, m3, m4, "")
        cursor.execute(\'\'\'
            UPDATE banco_horas 
            SET m1 = ?, m2 = ?, m3 = ?, m4 = ?, saldo = ?, manual = 0, justificativa = \'\'
            WHERE data = ?
        \'\'\', (m1, m2, m3, m4, saldo, data))
        conn.commit()
        
    conn.close()

def get_saldo_mes(mes_ano):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT saldo FROM banco_horas WHERE data LIKE ?", (f"%/{mes_ano}",))
    rows = cursor.fetchall()
    conn.close()
    
    total_mins = 0
    for r in rows:
        s = r[0]
        if s and len(s) >= 5:
            sinal = -1 if s.startswith('-') else 1
            try:
                h, m = map(int, s.replace('+', '').replace('-', '').split(':'))
                total_mins += sinal * (h * 60 + m)
            except:
                pass
                
    sinal_str = "+" if total_mins >= 0 else "-"
    h, m = divmod(abs(total_mins), 60)
    return f"{sinal_str}{h:02d}:{m:02d}", total_mins

def delete_mes_banco(mes_ano):
    """
    "Limpa" o mês informado sem removê-lo do Banco de Horas.

    Em vez de apagar as linhas (o que fazia o mês desaparecer do
    seletor e perder os dias já existentes), esta função:

    1. Garante que todos os dias do mês existam, inclusive
       sábados e domingos.
    2. Registra o período no histórico de meses utilizados.
    3. Reseta m1, m2, m3, m4, saldo, manual, justificativa e as
       marcações originais de cada dia do mês, preservando a
       própria linha do dia na tabela.
    """

    init_db()
    garantir_dias_mes(mes_ano)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    _registrar_periodo(cursor, mes_ano)

    cursor.execute(
        "SELECT data FROM banco_horas WHERE data LIKE ?",
        (f"%/{mes_ano}",)
    )
    linhas = cursor.fetchall()

    for (data_str,) in linhas:
        try:
            dt = datetime.datetime.strptime(data_str, "%d/%m/%Y")
            wd = dt.weekday()
        except (TypeError, ValueError):
            wd = 0

        if wd in [5, 6]:
            m1 = m2 = m3 = m4 = "-"
        else:
            m1 = m2 = m3 = m4 = ""

        saldo = calcular_saldo_dia(data_str, m1, m2, m3, m4, "")

        cursor.execute(
            \'\'\'
            UPDATE banco_horas
            SET m1 = ?, m2 = ?, m3 = ?, m4 = ?, saldo = ?,
                manual = 0, justificativa = \'\',
                orig_m1 = ?, orig_m2 = ?, orig_m3 = ?, orig_m4 = ?
            WHERE data = ?
            \'\'\',
            (m1, m2, m3, m4, saldo, m1, m2, m3, m4, data_str)
        )

    conn.commit()
    conn.close()
'''


# =============================================================================
# FUNÇÕES GERAIS DE ARQUIVO
# =============================================================================

def localizar_arquivo(*nomes):
    """
    Localiza o primeiro arquivo existente entre os nomes informados.
    """

    for nome in nomes:
        caminho = BASE_DIR / nome

        if caminho.exists() and caminho.is_file():
            return caminho

    return None


def ler_arquivo(caminho):
    """
    Lê um arquivo preservando codificação, BOM e quebra de linha.
    """

    dados = caminho.read_bytes()

    possui_bom = dados.startswith(
        b"\xef\xbb\xbf"
    )

    try:
        texto = dados.decode("utf-8-sig")
        codificacao = "utf-8"

    except UnicodeDecodeError:
        texto = dados.decode("latin-1")
        codificacao = "latin-1"
        possui_bom = False

    quebra_linha = (
        "\r\n"
        if "\r\n" in texto
        else "\n"
    )

    texto = texto.replace("\r\n", "\n")
    texto = texto.replace("\r", "\n")

    return (
        texto,
        codificacao,
        possui_bom,
        quebra_linha
    )


def converter_para_bytes(
    texto,
    codificacao,
    possui_bom,
    quebra_linha
):
    """
    Converte o texto para bytes preservando o padrão original.
    """

    texto_saida = texto

    if quebra_linha != "\n":
        texto_saida = texto_saida.replace(
            "\n",
            quebra_linha
        )

    if codificacao == "utf-8":
        dados = texto_saida.encode("utf-8")

        if possui_bom:
            dados = b"\xef\xbb\xbf" + dados

        return dados

    return texto_saida.encode(codificacao)


def gravar_arquivo_atomico(
    caminho,
    texto,
    codificacao,
    possui_bom,
    quebra_linha
):
    """
    Grava em um arquivo temporário antes de substituir o original.
    """

    dados = converter_para_bytes(
        texto,
        codificacao,
        possui_bom,
        quebra_linha
    )

    caminho_temporario = caminho.with_name(
        caminho.name + ".atualizando"
    )

    try:
        caminho_temporario.write_bytes(dados)

        os.replace(
            str(caminho_temporario),
            str(caminho)
        )

    finally:
        if caminho_temporario.exists():
            try:
                caminho_temporario.unlink()
            except OSError:
                pass


def criar_backup(caminho):
    """
    Cria uma cópia de segurança do arquivo antes da atualização.
    """

    PASTA_BACKUP.mkdir(
        parents=True,
        exist_ok=True
    )

    destino = PASTA_BACKUP / caminho.name

    shutil.copy2(
        str(caminho),
        str(destino)
    )

    return destino


def validar_sintaxe_python(texto, nome_arquivo):
    """
    Valida a sintaxe Python sem executar o módulo.
    """

    try:
        compile(
            texto,
            nome_arquivo,
            "exec"
        )

    except SyntaxError as erro:
        linha = erro.lineno or 0
        coluna = erro.offset or 0
        mensagem = erro.msg or "Erro desconhecido"

        raise RuntimeError(
            f"Erro de sintaxe em {nome_arquivo}, "
            f"linha {linha}, coluna {coluna}: {mensagem}"
        ) from erro


# =============================================================================
# ATUALIZAÇÃO DO DATABASE.PY
# =============================================================================

def atualizar_database():
    """
    Substitui database.py/database.pyw pela versão corrigida.
    """

    caminho = localizar_arquivo(
        "database.py",
        "database.pyw"
    )

    if caminho is None:
        resultados.append(
            ResultadoAtualizacao(
                arquivo="database.py / database.pyw",
                status="FALHA",
                detalhes=(
                    "Arquivo não encontrado na pasta do projeto."
                )
            )
        )
        return False

    (
        texto_original,
        codificacao,
        possui_bom,
        quebra_linha
    ) = ler_arquivo(caminho)

    try:
        validar_sintaxe_python(
            texto_original,
            caminho.name
        )
    except RuntimeError as erro:
        resultados.append(
            ResultadoAtualizacao(
                arquivo=caminho.name,
                status="FALHA",
                detalhes=(
                    "O arquivo atual já possui um erro de sintaxe "
                    f"e não foi modificado: {erro}"
                )
            )
        )
        return False

    validar_sintaxe_python(
        NOVO_DATABASE_PY,
        caminho.name
    )

    if texto_original == NOVO_DATABASE_PY:
        resultados.append(
            ResultadoAtualizacao(
                arquivo=caminho.name,
                status="JÁ ATUALIZADO",
                detalhes=(
                    "O arquivo já contém a correção do comando "
                    "Limpar Mês e o histórico de períodos."
                )
            )
        )
        return True

    backup = None

    try:
        backup = criar_backup(caminho)

        gravar_arquivo_atomico(
            caminho,
            NOVO_DATABASE_PY,
            codificacao,
            possui_bom,
            quebra_linha
        )

        (
            texto_confirmacao,
            _,
            _,
            _
        ) = ler_arquivo(caminho)

        if texto_confirmacao != NOVO_DATABASE_PY:
            raise RuntimeError(
                "O conteúdo gravado não corresponde ao conteúdo "
                "preparado pelo atualizador."
            )

        validar_sintaxe_python(
            texto_confirmacao,
            caminho.name
        )

        itens_obrigatorios = [
            "def garantir_dias_mes(",
            "def registrar_periodo_utilizado(",
            "historico_periodos",
            "def delete_mes_banco(",
            "import calendar"
        ]

        ausentes = [
            item
            for item in itens_obrigatorios
            if item not in texto_confirmacao
        ]

        if ausentes:
            raise RuntimeError(
                "A atualização ficou incompleta. Itens ausentes: "
                + ", ".join(ausentes)
            )

        resultados.append(
            ResultadoAtualizacao(
                arquivo=caminho.name,
                status="ATUALIZADO",
                detalhes=(
                    "Limpar Mês não apaga mais as linhas do mês; "
                    "todos os dias do mês passam a ser garantidos, "
                    "inclusive sábados e domingos; criado histórico "
                    "de períodos para que o mês nunca mais "
                    "desapareça do seletor."
                ),
                backup=str(backup)
            )
        )

        return True

    except Exception as erro:
        detalhes = f"{type(erro).__name__}: {erro}"

        if backup and backup.exists():
            try:
                shutil.copy2(
                    str(backup),
                    str(caminho)
                )
                detalhes += (
                    " O arquivo original foi restaurado "
                    "automaticamente."
                )
            except Exception as erro_restauracao:
                detalhes += (
                    " Também ocorreu uma falha ao restaurar o "
                    f"arquivo original: {type(erro_restauracao).__name__}: "
                    f"{erro_restauracao}"
                )

        resultados.append(
            ResultadoAtualizacao(
                arquivo=caminho.name,
                status="FALHA",
                detalhes=detalhes,
                backup=str(backup) if backup else ""
            )
        )

        return False


def registrar_arquivo_sem_alteracao(*nomes):
    """
    Registra módulos que não precisam ser modificados nesta versão.
    """

    caminho = localizar_arquivo(*nomes)

    if caminho:
        resultados.append(
            ResultadoAtualizacao(
                arquivo=caminho.name,
                status="SEM ALTERAÇÃO",
                detalhes=(
                    "Nenhuma modificação é necessária neste "
                    "arquivo para esta correção."
                )
            )
        )
    else:
        resultados.append(
            ResultadoAtualizacao(
                arquivo=" / ".join(nomes),
                status="NÃO ENCONTRADO",
                detalhes=(
                    "O arquivo não foi encontrado, mas não é "
                    "necessário para esta atualização."
                )
            )
        )


# =============================================================================
# RELATÓRIO DA ATUALIZAÇÃO
# =============================================================================

def montar_relatorio(sucesso):
    linhas = [
        "=" * 78,
        "RELATÓRIO DE ATUALIZAÇÃO",
        "=" * 78,
        f"Aplicação: {NOME_APLICACAO}",
        f"Versão da atualização: {VERSAO_ATUALIZACAO}",
        (
            "Data da execução: "
            + DATA_EXECUCAO.strftime("%d/%m/%Y %H:%M:%S")
        ),
        f"Diretório: {BASE_DIR}",
        ""
    ]

    for resultado in resultados:
        linhas.extend([
            "-" * 78,
            f"Arquivo: {resultado.arquivo}",
            f"Status: {resultado.status}",
            f"Detalhes: {resultado.detalhes}"
        ])

        if resultado.backup:
            linhas.append(f"Backup: {resultado.backup}")

    atualizados = sum(
        r.status == "ATUALIZADO" for r in resultados
    )
    ja_atualizados = sum(
        r.status == "JÁ ATUALIZADO" for r in resultados
    )
    sem_alteracao = sum(
        r.status == "SEM ALTERAÇÃO" for r in resultados
    )
    nao_encontrados = sum(
        r.status == "NÃO ENCONTRADO" for r in resultados
    )
    falhas = sum(
        r.status == "FALHA" for r in resultados
    )

    linhas.extend([
        "-" * 78,
        "",
        "RESUMO",
        f"Arquivos atualizados: {atualizados}",
        f"Arquivos já atualizados: {ja_atualizados}",
        f"Arquivos sem alteração necessária: {sem_alteracao}",
        f"Arquivos não encontrados: {nao_encontrados}",
        f"Falhas: {falhas}",
        ""
    ])

    if sucesso:
        linhas.append(
            "RESULTADO FINAL: ATUALIZAÇÃO CONCLUÍDA COM SUCESSO"
        )
    else:
        linhas.append(
            "RESULTADO FINAL: ATUALIZAÇÃO CONCLUÍDA COM FALHAS"
        )

    linhas.append("=" * 78)

    return "\n".join(linhas)


def salvar_relatorio(conteudo):
    try:
        CAMINHO_RELATORIO.write_text(
            conteudo,
            encoding="utf-8"
        )
        return True
    except Exception as erro:
        print()
        print("Não foi possível salvar o relatório:")
        print(f"{type(erro).__name__}: {erro}")
        return False


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    print("=" * 78)
    print(f"ATUALIZADOR - {NOME_APLICACAO}")
    print(f"Versão: {VERSAO_ATUALIZACAO}")
    print("=" * 78)
    print()
    print("Corrigindo o comando Limpar Mês do Banco de Horas...")
    print()

    sucesso_database = atualizar_database()

    registrar_arquivo_sem_alteracao("main.py", "main.pyw")
    registrar_arquivo_sem_alteracao("scraper.py", "scraper.pyw")
    registrar_arquivo_sem_alteracao("relatorio.py", "relatorio.pyw")
    registrar_arquivo_sem_alteracao("settings.py", "settings.pyw")

    sucesso_geral = (
        sucesso_database
        and not any(r.status == "FALHA" for r in resultados)
    )

    relatorio = montar_relatorio(sucesso_geral)

    print(relatorio)
    print()

    salvo = salvar_relatorio(relatorio)

    if salvo:
        print("Relatório salvo no arquivo:")
        print(CAMINHO_RELATORIO.name)
    else:
        print(
            "O relatório foi exibido no terminal, mas não pôde "
            "ser salvo em arquivo."
        )

    print()

    if sucesso_geral:
        print("A aplicação foi corrigida com sucesso.")
        return 0

    print(
        "A atualização terminou com falhas. Consulte o relatório "
        "apresentado acima."
    )
    return 1


if __name__ == "__main__":
    try:
        codigo_saida = main()

    except KeyboardInterrupt:
        print()
        print("Atualização cancelada pelo usuário.")
        codigo_saida = 130

    except Exception as erro_geral:
        print()
        print("Ocorreu uma falha inesperada no atualizador:")
        print(f"{type(erro_geral).__name__}: {erro_geral}")
        print()
        traceback.print_exc()
        codigo_saida = 1

    sys.exit(codigo_saida)
