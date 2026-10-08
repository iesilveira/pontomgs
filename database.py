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
    """Retorna os meses do Banco de Horas em ordem decrescente.

    Mantém períodos limpos disponíveis e inclui todos os meses entre
    o primeiro período conhecido e o mês corrente.
    """
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banco_horas_periodos (
            mes_ano TEXT PRIMARY KEY
        )
    """)

    # Registra os períodos que ainda existem na tabela principal.
    cursor.execute("SELECT DISTINCT data FROM banco_horas WHERE data IS NOT NULL")
    datas = cursor.fetchall()
    periodos = set()
    for (data_texto,) in datas:
        try:
            data_obj = datetime.datetime.strptime(str(data_texto), "%d/%m/%Y")
            periodo = data_obj.strftime("%m/%Y")
            periodos.add(periodo)
            cursor.execute(
                "INSERT OR IGNORE INTO banco_horas_periodos (mes_ano) VALUES (?)",
                (periodo,)
            )
        except (TypeError, ValueError):
            continue

    cursor.execute("SELECT mes_ano FROM banco_horas_periodos")
    for (periodo,) in cursor.fetchall():
        try:
            datetime.datetime.strptime(periodo, "%m/%Y")
            periodos.add(periodo)
        except (TypeError, ValueError):
            continue

    agora = datetime.datetime.now()
    periodo_atual = (agora.year, agora.month)
    chaves = []
    for periodo in periodos:
        try:
            dt = datetime.datetime.strptime(periodo, "%m/%Y")
            chaves.append((dt.year, dt.month))
        except (TypeError, ValueError):
            pass

    if chaves:
        primeiro = min(chaves)
        ano, mes = primeiro
        while (ano, mes) <= periodo_atual:
            periodos.add(f"{mes:02d}/{ano:04d}")
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
    else:
        periodos.add(agora.strftime("%m/%Y"))

    conn.commit()
    conn.close()

    def chave_periodo(texto):
        try:
            dt = datetime.datetime.strptime(texto, "%m/%Y")
            return (dt.year, dt.month)
        except (TypeError, ValueError):
            return (0, 0)

    return sorted(periodos, key=chave_periodo, reverse=True)

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

def recalcular_saldos_existentes():
    """Recalcula os saldos gravados, sem alterar linhas marcadas como manuais."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    alterados = 0

    try:
        cursor.execute(
            """
            SELECT data, m1, m2, m3, m4, manual, justificativa, saldo
            FROM banco_horas
            """
        )
        registros = cursor.fetchall()

        for data, m1, m2, m3, m4, manual, justificativa, saldo_anterior in registros:
            if bool(manual):
                continue

            saldo_calculado = calcular_saldo_dia(
                data, m1, m2, m3, m4, justificativa or ""
            )

            if saldo_calculado != (saldo_anterior or ""):
                cursor.execute(
                    "UPDATE banco_horas SET saldo = ? WHERE data = ?",
                    (saldo_calculado, data)
                )
                alterados += 1

        conn.commit()
        return alterados

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def delete_mes_banco(mes_ano):
    """Limpa as marcações de um mês sem apagar seus dias/período.

    O mês permanece no seletor e a tabela continua contendo todos os dias.
    Em fins de semana, as marcações atuais são apresentadas como "-";
    nos dias úteis, os campos ficam vazios. As marcações originais são
    apagadas porque esta operação representa uma limpeza explícita do mês.
    """
    init_db()

    texto = str(mes_ano or "").strip()
    try:
        partes = texto.split("/")
        if len(partes) != 2:
            raise ValueError("Período deve estar no formato MM/AAAA")
        mes = int(partes[0])
        ano = int(partes[1])
        if ano < 100:
            ano += 2000
        if mes < 1 or mes > 12:
            raise ValueError("Mês inválido")
        primeiro_dia = datetime.date(ano, mes, 1)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"Período inválido: {mes_ano!r}") from erro

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banco_horas_periodos (
            mes_ano TEXT PRIMARY KEY
        )
    """)

    periodo_normalizado = f"{mes:02d}/{ano:04d}"
    cursor.execute(
        "INSERT OR IGNORE INTO banco_horas_periodos (mes_ano) VALUES (?)",
        (periodo_normalizado,)
    )

    data_obj = primeiro_dia
    while data_obj.month == mes:
        data_str = data_obj.strftime("%d/%m/%Y")
        if data_obj.weekday() >= 5:
            valores = ("-", "-", "-", "-")
        else:
            valores = ("", "", "", "")

        cursor.execute(
            "SELECT 1 FROM banco_horas WHERE data = ?",
            (data_str,)
        )
        existe = cursor.fetchone() is not None

        if existe:
            cursor.execute("""
                UPDATE banco_horas
                SET m1 = ?, m2 = ?, m3 = ?, m4 = ?,
                    saldo = '', manual = 0, justificativa = '',
                    orig_m1 = '', orig_m2 = '', orig_m3 = '', orig_m4 = ''
                WHERE data = ?
            """, (*valores, data_str))
        else:
            cursor.execute("""
                INSERT INTO banco_horas (
                    data, m1, m2, m3, m4, saldo, manual, justificativa,
                    orig_m1, orig_m2, orig_m3, orig_m4
                ) VALUES (?, ?, ?, ?, ?, '', 0, '', '', '', '', '')
            """, (data_str, *valores))

        # Também registra o período para sobreviver a futuras limpezas.
        cursor.execute(
            "INSERT OR IGNORE INTO banco_horas_periodos (mes_ano) VALUES (?)",
            (periodo_normalizado,)
        )
        data_obj += datetime.timedelta(days=1)

    conn.commit()
    conn.close()

def garantir_dias_mes_banco(mes_ano):
    """Garante todas as datas do mês e calcula os saldos não manuais."""
    import calendar
    import datetime as _datetime

    try:
        mes, ano = [int(item) for item in str(mes_ano).strip().split("/")]
    except (TypeError, ValueError):
        raise ValueError("Período inválido: use MM/AAAA.")

    if mes < 1 or mes > 12 or ano < 1900:
        raise ValueError("Período inválido: use MM/AAAA.")

    init_db()
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        for dia in range(1, ultimo_dia + 1):
            data = _datetime.date(ano, mes, dia).strftime("%d/%m/%Y")
            cursor.execute(
                "SELECT 1 FROM banco_horas WHERE data = ?",
                (data,)
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO banco_horas (
                        data, m1, m2, m3, m4, saldo, manual, justificativa
                    ) VALUES (?, '', '', '', '', '', 0, '')
                    """,
                    (data,)
                )

        mes_ano_normalizado = f"{mes:02d}/{ano:04d}"
        cursor.execute(
            """
            SELECT data, m1, m2, m3, m4, manual, justificativa
            FROM banco_horas
            WHERE data LIKE ?
            """,
            (f"%/{mes_ano_normalizado}",)
        )

        atualizados = []
        for data, m1, m2, m3, m4, manual, justificativa in cursor.fetchall():
            if bool(manual):
                continue
            saldo = calcular_saldo_dia(
                data, m1, m2, m3, m4, justificativa or ""
            )
            atualizados.append((saldo, data))

        cursor.executemany(
            "UPDATE banco_horas SET saldo = ? WHERE data = ?",
            atualizados
        )
        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def importar_marcacoes_relatorio(data, marcacoes):
    """Importa as marcações e calcula o saldo sem apagar ajustes manuais."""
    init_db()

    valores = list(marcacoes or [])[:4]
    valores += [""] * (4 - len(valores))
    m1, m2, m3, m4 = valores

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT manual, justificativa
            FROM banco_horas
            WHERE data = ?
            """,
            (data,)
        )
        existente = cursor.fetchone()

        if existente is None:
            justificativa = ""
            saldo = calcular_saldo_dia(
                data, m1, m2, m3, m4, justificativa
            )
            cursor.execute(
                """
                INSERT INTO banco_horas (
                    data, m1, m2, m3, m4, saldo, manual, justificativa,
                    orig_m1, orig_m2, orig_m3, orig_m4
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
                """,
                (
                    data, m1, m2, m3, m4, saldo, justificativa,
                    m1, m2, m3, m4
                )
            )
        else:
            manual = bool(existente[0])
            justificativa = existente[1] or ""

            # Sempre atualiza a cópia original recebida do sistema.
            cursor.execute(
                """
                UPDATE banco_horas
                SET orig_m1 = ?, orig_m2 = ?, orig_m3 = ?, orig_m4 = ?
                WHERE data = ?
                """,
                (m1, m2, m3, m4, data)
            )

            # Uma linha manual mantém os horários e saldo ajustados pelo usuário.
            if not manual:
                saldo = calcular_saldo_dia(
                    data, m1, m2, m3, m4, justificativa
                )
                cursor.execute(
                    """
                    UPDATE banco_horas
                    SET m1 = ?, m2 = ?, m3 = ?, m4 = ?, saldo = ?
                    WHERE data = ?
                    """,
                    (m1, m2, m3, m4, saldo, data)
                )

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

