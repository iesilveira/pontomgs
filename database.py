"""
Autor: Ismael Elói da Silveira Silva
Descrição: Módulo de banco de dados SQLite para armazenamento local das credenciais e lembretes.
"""
import sqlite3
import os
import datetime
from settings import APP_DIR, DB_FILE

def init_db():
    if not os.path.exists(APP_DIR):
        os.makedirs(APP_DIR)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Tabela de Credenciais
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT NOT NULL,
            senha TEXT NOT NULL,
            saida_almoco TEXT DEFAULT '12:00',
            intervalo_atualizacao INTEGER DEFAULT 10
        )
    ''')

    try:
        cursor.execute(
            'ALTER TABLE credentials '
            'ADD COLUMN saida_almoco TEXT DEFAULT "12:00"'
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            'ALTER TABLE credentials '
            'ADD COLUMN intervalo_atualizacao INTEGER DEFAULT 10'
        )
    except sqlite3.OperationalError:
        pass

    # Tabela de Lembretes Dinâmicos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lembretes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            evento TEXT NOT NULL,
            tempo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            mensagem TEXT DEFAULT ''
        )
    ''')

    try:
        cursor.execute(
            'ALTER TABLE lembretes '
            'ADD COLUMN mensagem TEXT DEFAULT ""'
        )
    except sqlite3.OperationalError:
        pass

    # Tabela de Banco de Horas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banco_horas (
            data TEXT PRIMARY KEY,
            m1 TEXT,
            m2 TEXT,
            m3 TEXT,
            m4 TEXT,
            saldo TEXT,
            manual INTEGER DEFAULT 0,
            justificativa TEXT DEFAULT ''
        )
    ''')

    try:
        cursor.execute(
            'ALTER TABLE banco_horas '
            'ADD COLUMN manual INTEGER DEFAULT 0'
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            'ALTER TABLE banco_horas '
            'ADD COLUMN justificativa TEXT DEFAULT ""'
        )
    except sqlite3.OperationalError:
        pass

    # Cópia das marcações originais do sistema
    for col in [
        'orig_m1',
        'orig_m2',
        'orig_m3',
        'orig_m4'
    ]:
        try:
            cursor.execute(
                f'ALTER TABLE banco_horas '
                f'ADD COLUMN {col} TEXT DEFAULT ""'
            )
        except sqlite3.OperationalError:
            pass

    # Lembretes iniciais
    cursor.execute(
        "SELECT COUNT(*) FROM lembretes"
    )

    if cursor.fetchone()[0] == 0:
        cursor.execute(
            '''
            INSERT INTO lembretes (
                nome,
                evento,
                tempo,
                tipo,
                mensagem
            )
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                'Lembrete Almoço',
                'Horário previsto de almoço',
                '00:02',
                'Antes',
                'Seu almoço está previsto para as {}'
            )
        )

        cursor.execute(
            '''
            INSERT INTO lembretes (
                nome,
                evento,
                tempo,
                tipo,
                mensagem
            )
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                'Lembrete Retorno',
                'Horário previsto de fim do almoço',
                '00:02',
                'Antes',
                'Seu retorno está previsto para as {}'
            )
        )

    conn.commit()
    conn.close()

def get_credentials():
    init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            matricula,
            senha,
            saida_almoco,
            intervalo_atualizacao
        FROM credentials
        ORDER BY id DESC
        LIMIT 1
    ''')

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
        'DELETE FROM credentials'
    )

    cursor.execute('''
        INSERT INTO credentials (
            matricula,
            senha,
            saida_almoco,
            intervalo_atualizacao
        )
        VALUES (?, ?, ?, ?)
    ''', (
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
    cursor.execute('''
        UPDATE lembretes 
        SET nome = ?, evento = ?, tempo = ?, tipo = ?, mensagem = ? 
        WHERE id = ?
    ''', (nome, evento, tempo, tipo, mensagem, lembrete_id))
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

def get_meses_disponiveis():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT substr(data, 4, 7) FROM banco_horas ORDER BY substr(data, 7, 4) DESC, substr(data, 4, 2) DESC')
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
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT data, m1, m2, m3, m4, saldo, manual, justificativa 
        FROM banco_horas 
        WHERE data LIKE ?
        ORDER BY substr(data, 7, 4) || substr(data, 4, 2) || substr(data, 1, 2) ASC
    ''', (f"%/{mes_ano}",))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_banco_horas_relatorio(mes_ano):
    """
    Retorna os dados mensais utilizados pelo relatório em PDF.

    Além dos valores atuais, retorna as marcações originais
    para permitir a identificação individual de alterações manuais.
    """

    init_db()

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
    
    cursor.execute('''
        UPDATE banco_horas 
        SET m1 = ?, m2 = ?, m3 = ?, m4 = ?, saldo = ?, manual = ?, justificativa = ?, orig_m1 = ?, orig_m2 = ?, orig_m3 = ?, orig_m4 = ?
        WHERE data = ?
    ''', (m1, m2, m3, m4, saldo, flag_manual, justificativa, orig_m1, orig_m2, orig_m3, orig_m4, data))
    
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT INTO banco_horas (data, m1, m2, m3, m4, saldo, manual, justificativa, orig_m1, orig_m2, orig_m3, orig_m4) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data, m1, m2, m3, m4, saldo, flag_manual, justificativa, orig_m1, orig_m2, orig_m3, orig_m4))
        
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
        cursor.execute('''
            UPDATE banco_horas 
            SET m1 = ?, m2 = ?, m3 = ?, m4 = ?, saldo = ?, manual = 0, justificativa = ''
            WHERE data = ?
        ''', (m1, m2, m3, m4, saldo, data))
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
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM banco_horas WHERE data LIKE ?', (f"%/{mes_ano}",))
    conn.commit()
    conn.close()