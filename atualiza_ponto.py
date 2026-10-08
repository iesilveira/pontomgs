"""
Atualização: cálculo automático do saldo nas importações do Banco de Horas.

- Corrige a importação histórica para gravar o saldo calculado.
- Recalcula o saldo dos dias existentes ao reimportar um mês.
- Preenche saldo para todos os dias garantidos do período.
- Preserva dias/horários manuais durante a importação e recálculo.
- Recalcula uma vez os saldos já existentes no banco.
- Não cria backups, relatórios de atualização ou logs de depuração.

Execute na pasta do projeto: py atualiza_ponto.py
"""

import os
import sys
import importlib
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

NOVA_FUNCAO_GARANTIR_DIAS = r'''def garantir_dias_mes_banco(mes_ano):
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
'''

NOVA_FUNCAO_IMPORTAR_MARCACOES = r'''def importar_marcacoes_relatorio(data, marcacoes):
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
'''

NOVA_FUNCAO_RECALCULAR_EXISTENTES = r'''def recalcular_saldos_existentes():
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
'''


def localizar_arquivo(*nomes):
    for nome in nomes:
        caminho = BASE_DIR / nome
        if caminho.is_file():
            return caminho
    return None


def ler_arquivo(caminho):
    dados = caminho.read_bytes()
    possui_bom = dados.startswith(bytes((239, 187, 191)))
    try:
        texto = dados.decode("utf-8-sig")
        codificacao = "utf-8"
    except UnicodeDecodeError:
        texto = dados.decode("latin-1")
        codificacao = "latin-1"
        possui_bom = False
    quebra = "\r\n" if "\r\n" in texto else "\n"
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return texto, codificacao, possui_bom, quebra


def localizar_funcao(texto, nome):
    linhas = texto.splitlines(keepends=True)
    inicio = None
    prefixo = "def " + nome + "("
    for indice, linha in enumerate(linhas):
        if linha.startswith(prefixo):
            inicio = indice
            break
    if inicio is None:
        return None

    fim = len(linhas)
    for indice in range(inicio + 1, len(linhas)):
        linha = linhas[indice]
        if linha.startswith("def ") or linha.startswith("class "):
            fim = indice
            break
    return linhas, inicio, fim


def substituir_funcao(texto, nome, codigo):
    localizacao = localizar_funcao(texto, nome)
    codigo = codigo.strip("\n") + "\n\n"

    if localizacao:
        linhas, inicio, fim = localizacao
        return "".join(linhas[:inicio]) + codigo + "".join(linhas[fim:])

    marcador = "def delete_mes_banco("
    posicao = texto.find(marcador)
    if posicao < 0:
        return texto.rstrip() + "\n\n" + codigo
    return texto[:posicao] + codigo + texto[posicao:]


def atualizar_database(texto):
    for obrigatorio in (
        "def calcular_saldo_dia(",
        "def garantir_dias_mes_banco(",
        "def importar_marcacoes_relatorio("
    ):
        if obrigatorio not in texto:
            raise RuntimeError("Função esperada não encontrada no database.py: " + obrigatorio)

    texto = substituir_funcao(
        texto,
        "garantir_dias_mes_banco",
        NOVA_FUNCAO_GARANTIR_DIAS
    )
    texto = substituir_funcao(
        texto,
        "importar_marcacoes_relatorio",
        NOVA_FUNCAO_IMPORTAR_MARCACOES
    )
    texto = substituir_funcao(
        texto,
        "recalcular_saldos_existentes",
        NOVA_FUNCAO_RECALCULAR_EXISTENTES
    )

    compile(texto, "database.py", "exec")
    return texto


def gravar_atomico(caminho, texto, codificacao, possui_bom, quebra):
    if quebra != "\n":
        texto = texto.replace("\n", quebra)
    dados = texto.encode(codificacao)
    if codificacao == "utf-8" and possui_bom:
        dados = bytes((239, 187, 191)) + dados
    temporario = caminho.with_name(caminho.name + ".tmp")
    try:
        temporario.write_bytes(dados)
        os.replace(str(temporario), str(caminho))
    finally:
        if temporario.exists():
            try:
                temporario.unlink()
            except OSError:
                pass


def main():
    caminho = localizar_arquivo("database.py", "database.pyw")
    if caminho is None:
        raise FileNotFoundError("Não encontrei database.py ou database.pyw na pasta do atualizador.")

    dados_originais = caminho.read_bytes()
    texto_original, codificacao, possui_bom, quebra = ler_arquivo(caminho)
    compile(texto_original, caminho.name, "exec")
    texto_atualizado = atualizar_database(texto_original)
    compile(texto_atualizado, caminho.name, "exec")

    try:
        gravar_atomico(caminho, texto_atualizado, codificacao, possui_bom, quebra)
        texto_confirmacao, _, _, _ = ler_arquivo(caminho)
        compile(texto_confirmacao, caminho.name, "exec")
    except Exception:
        try:
            caminho.write_bytes(dados_originais)
        except Exception:
            pass
        raise

    # Atualiza saldos já importados sem tocar nos registros manuais.
    sys.path.insert(0, str(BASE_DIR))
    import database
    importlib.reload(database)
    quantidade = database.recalcular_saldos_existentes()

    print("Cálculo automático de saldo aplicado às importações.")
    print("Saldos existentes recalculados: " + str(quantidade))
    print("Dias manuais foram preservados.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as erro:
        print("Falha ao aplicar atualização: " + type(erro).__name__ + ": " + str(erro))
        traceback.print_exc()
        sys.exit(1)
