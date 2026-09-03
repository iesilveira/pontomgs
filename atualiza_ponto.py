"""
Autor: Ismael Elói da Silveira Silva
Descrição: Atualiza a identificação de marcações e o relatório mensal.
Versão: 2026.09.03-07

Alterações:
- Exibe somente * nos horários realmente inseridos manualmente.
- Não usa R ou I nos horários obtidos do sistema.
- Compara os horários atuais com todas as marcações originais do dia,
  independentemente da posição, consumindo cada ocorrência uma única vez.
- Aplica a mesma classificação na tela Banco de Horas e no PDF.
- No PDF, a justificativa fica na mesma linha do dia, centralizada, ocupando
  a área mesclada das quatro marcações.
- Move a legenda de marcação manual para baixo da tabela.
- Converte todo o relatório para preto, branco e tons de cinza, inclusive
  saldos positivos, negativos e totais.
- Mantém A4 retrato, uma única página e totais em horas e minutos.
"""

import os
import re
import sys
import shutil
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

VERSAO = "2026.09.03-07"
BASE_DIR = Path(__file__).resolve().parent
AGORA = datetime.now()
ID_EXECUCAO = AGORA.strftime("%Y%m%d_%H%M%S")
PASTA_BACKUP = BASE_DIR / f"backup_atualizacao_{ID_EXECUCAO}"
ARQUIVO_RELATORIO = BASE_DIR / f"relatorio_atualizacao_{ID_EXECUCAO}.txt"


@dataclass
class ArquivoPreparado:
    caminho: Path
    original: str
    atualizado: str
    encoding: str
    bom: bool
    newline: str
    novo: bool = False
    backup: Path = None


resultados = []


NOVO_GET_BANCO_HORAS = r'''
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
'''


NOVO_ATUALIZAR_LISTA_BANCO = r'''
    def atualizar_lista_banco(self):
        """
        Atualiza a tela Banco de Horas.

        Somente horários que não correspondem a uma ocorrência original do
        dia recebem *. A posição da marcação não interfere na comparação.
        """
        from collections import Counter

        for item in self.tree_banco.get_children():
            self.tree_banco.delete(item)

        mes_sel = self.mes_selecionado_var.get()
        if not mes_sel:
            return

        def normalizar(valor):
            if valor is None:
                return ""
            texto = str(valor).strip()
            if texto.lower() in ("", "-", "--:--", "none", "null"):
                return ""
            return texto

        try:
            registros = database.get_banco_horas(mes_sel)

            for registro in registros:
                atuais = list(registro[1:5])
                originais = list(registro[8:12]) if len(registro) >= 12 else []
                manual_linha = bool(registro[6]) if len(registro) > 6 else False

                contador = Counter(
                    normalizar(valor)
                    for valor in originais
                    if normalizar(valor)
                )
                existem_originais = bool(contador)
                horarios_exibicao = []
                possui_inserido = False

                for valor in atuais:
                    horario = normalizar(valor)
                    if not horario:
                        horarios_exibicao.append("")
                        continue

                    if contador[horario] > 0:
                        contador[horario] -= 1
                        horarios_exibicao.append(horario)
                    elif not existem_originais and not manual_linha:
                        # Compatibilidade com registros antigos que ainda não
                        # possuam cópia das marcações originais.
                        horarios_exibicao.append(horario)
                    else:
                        horarios_exibicao.append(f"* {horario}")
                        possui_inserido = True

                dia_str = database.get_dia_semana(registro[0])
                valores = (
                    registro[0],
                    dia_str,
                    horarios_exibicao[0],
                    horarios_exibicao[1],
                    horarios_exibicao[2],
                    horarios_exibicao[3],
                    registro[5],
                    registro[7],
                    registro[6]
                )

                tags = ("possui_inserido",) if possui_inserido else ()
                self.tree_banco.insert(
                    "",
                    "end",
                    values=valores,
                    tags=tags
                )

            self.atualizar_resumo_mes()

        except Exception as erro:
            messagebox.showerror(
                "Banco de Horas",
                f"Não foi possível carregar as marcações: {erro}"
            )
'''


METODO_LIMPAR_INDICADOR = r'''
    def limpar_indicador_origem(self, valor):
        """Remove o asterisco visual antes de carregar o horário na edição."""
        if valor is None:
            return ""

        texto = str(valor).strip()
        if texto.lower() in ("", "-", "--:--", "none", "null"):
            return ""

        return re.sub(
            r"^(?:\*|R|I)\s*",
            "",
            texto
        ).strip()
'''


NOVO_CARREGAR_EDICAO_BANCO = r'''
    def carregar_edicao_banco(self, event=None):
        selected = self.tree_banco.selection()
        if not selected:
            return

        item_values = self.tree_banco.item(
            selected[0],
            "values"
        )

        self.ent_banco_data.config(state=tk.NORMAL)
        self.ent_banco_data.delete(0, tk.END)
        self.ent_banco_data.insert(0, item_values[0])
        self.ent_banco_data.config(state="readonly")

        self.banco_m1_var.set(
            self.limpar_indicador_origem(item_values[2])
        )
        self.banco_m2_var.set(
            self.limpar_indicador_origem(item_values[3])
        )
        self.banco_m3_var.set(
            self.limpar_indicador_origem(item_values[4])
        )
        self.banco_m4_var.set(
            self.limpar_indicador_origem(item_values[5])
        )

        self.ent_banco_justificativa.delete(0, tk.END)
        if len(item_values) > 7 and item_values[7] != "None":
            self.ent_banco_justificativa.insert(0, item_values[7])

        self.btn_cancelar_banco.pack(side=tk.LEFT, padx=10)
        self.btn_restaurar_banco.pack(side=tk.LEFT, padx=10)
'''


CONTEUDO_RELATORIO = r'''"""
Autor: Ismael Elói da Silveira Silva
Descrição: Relatório mensal do Banco de Horas em PDF.

- A4 retrato.
- Uma única página.
- Somente * identifica horário inserido manualmente.
- Horários obtidos do sistema não recebem prefixo.
- A classificação independe da posição da marcação.
- Justificativas ocupam, na mesma linha do dia, a área mesclada dos horários.
- Relatório integralmente em preto, branco e tons de cinza.
"""

import datetime
from collections import Counter

COR_PRETO = "#000000"
COR_BRANCO = "#FFFFFF"
COR_CINZA_CLARO = "#F2F2F2"
COR_CINZA_MEDIO = "#B8B8B8"
COR_CINZA_ESCURO = "#404040"
COR_CABECALHO = "#202020"
COR_BORDA = "#505050"


def normalizar_horario(valor):
    if valor is None:
        return ""
    texto = str(valor).strip()
    if texto.lower() in ("", "-", "--:--", "none", "null"):
        return ""
    return texto


def formatar_valor(valor, vazio="-"):
    texto = normalizar_horario(valor)
    return texto if texto else vazio


def classificar_origem_marcacoes(atuais, originais, registro_manual=False):
    """
    Classifica cada horário atual como sistema, manual ou vazio.

    Cada ocorrência original pode validar uma única ocorrência atual. Dessa
    forma, horários registrados continuam sendo reconhecidos mesmo depois de
    mudarem de M2 para M3 ou de M3 para M4.
    """
    contador = Counter(
        normalizar_horario(valor)
        for valor in originais
        if normalizar_horario(valor)
    )
    existem_originais = bool(contador)
    resultado = []

    for valor in atuais:
        horario = normalizar_horario(valor)
        if not horario:
            resultado.append("vazio")
        elif contador[horario] > 0:
            contador[horario] -= 1
            resultado.append("sistema")
        elif not existem_originais and not registro_manual:
            resultado.append("sistema")
        else:
            resultado.append("manual")

    return resultado


def saldo_para_minutos(saldo):
    texto = str(saldo or "").strip()
    if not texto:
        return 0

    sinal = -1 if texto.startswith("-") else 1
    partes = texto.replace("+", "").replace("-", "").split(":")
    if len(partes) != 2:
        return 0

    try:
        return sinal * (int(partes[0]) * 60 + int(partes[1]))
    except (TypeError, ValueError):
        return 0


def minutos_para_horas(total):
    total = int(total or 0)
    sinal = "+" if total >= 0 else "-"
    horas, minutos = divmod(abs(total), 60)
    return f"{sinal}{horas:02d}:{minutos:02d}"


def minutos_com_sinal(total):
    total = int(total or 0)
    sinal = "+" if total >= 0 else "-"
    return f"{sinal}{abs(total)} min"


def calcular_totais_saldo(registros):
    positivos = 0
    negativos = 0

    for registro in registros:
        minutos = saldo_para_minutos(
            registro[5] if len(registro) > 5 else ""
        )
        if minutos > 0:
            positivos += minutos
        elif minutos < 0:
            negativos += minutos

    return positivos, negativos, positivos + negativos


def obter_dia_semana(data):
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    try:
        objeto = datetime.datetime.strptime(str(data), "%d/%m/%Y")
        return dias[objeto.weekday()]
    except (TypeError, ValueError):
        return ""


def quebrar_texto(texto, largura, fonte, tamanho, max_linhas=2):
    from reportlab.pdfbase.pdfmetrics import stringWidth

    palavras = str(texto or "").replace("\n", " ").split()
    if not palavras:
        return [""]

    linhas = []
    atual = ""
    for palavra in palavras:
        candidato = palavra if not atual else atual + " " + palavra
        if stringWidth(candidato, fonte, tamanho) <= largura:
            atual = candidato
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
            if len(linhas) >= max_linhas:
                break

    if atual and len(linhas) < max_linhas:
        linhas.append(atual)

    original = " ".join(palavras)
    if linhas and " ".join(linhas) != original:
        ultima = linhas[-1]
        while ultima:
            candidato = ultima.rstrip() + "..."
            if stringWidth(candidato, fonte, tamanho) <= largura:
                linhas[-1] = candidato
                break
            ultima = ultima[:-1]
        if not ultima:
            linhas[-1] = "..."

    return linhas[:max_linhas]


def desenhar_celula(
    pdf,
    x,
    y,
    largura,
    altura,
    texto,
    tamanho,
    cor_texto=COR_PRETO,
    cor_fundo=COR_BRANCO,
    negrito=False,
    alinhamento="center",
    max_linhas=1,
    borda=0.45
):
    from reportlab.lib import colors

    pdf.setFillColor(colors.HexColor(cor_fundo))
    pdf.rect(x, y, largura, altura, stroke=0, fill=1)
    pdf.setStrokeColor(colors.HexColor(COR_BORDA))
    pdf.setLineWidth(borda)
    pdf.rect(x, y, largura, altura, stroke=1, fill=0)

    fonte = "Helvetica-Bold" if negrito else "Helvetica"
    pdf.setFont(fonte, tamanho)
    pdf.setFillColor(colors.HexColor(cor_texto))

    linhas = quebrar_texto(
        texto,
        max(1, largura - 6),
        fonte,
        tamanho,
        max_linhas
    )
    entrelinha = tamanho + 0.7
    inicio_y = (
        y + altura / 2 + (len(linhas) - 1) * entrelinha / 2 - tamanho * 0.35
    )

    for indice, linha in enumerate(linhas):
        linha_y = inicio_y - indice * entrelinha
        if alinhamento == "left":
            pdf.drawString(x + 3, linha_y, linha)
        elif alinhamento == "right":
            pdf.drawRightString(x + largura - 3, linha_y, linha)
        else:
            pdf.drawCentredString(x + largura / 2, linha_y, linha)


def desenhar_total(pdf, x, y, largura, altura, titulo, minutos):
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth

    pdf.setFillColor(colors.HexColor(COR_CINZA_CLARO))
    pdf.setStrokeColor(colors.HexColor(COR_BORDA))
    pdf.setLineWidth(0.7)
    pdf.roundRect(x, y, largura, altura, 3, stroke=1, fill=1)

    pdf.setFillColor(colors.HexColor(COR_PRETO))
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(x + 5, y + altura - 10, titulo)

    horas = minutos_para_horas(minutos)
    texto_minutos = f"({minutos_com_sinal(minutos)})"
    largura_horas = stringWidth(horas, "Helvetica-Bold", 11)
    largura_minutos = stringWidth(texto_minutos, "Helvetica", 7)
    inicio = x + (largura - largura_horas - largura_minutos - 5) / 2

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(inicio, y + 7, horas)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(inicio + largura_horas + 5, y + 8, texto_minutos)


def gerar_pdf(
    caminho_arquivo,
    mes_ano,
    registros,
    saldo_mes=None,
    matricula=""
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas

    if not registros:
        raise ValueError("Não existem registros para gerar o relatório.")

    largura_pagina, altura_pagina = A4
    pdf = pdf_canvas.Canvas(
        str(caminho_arquivo),
        pagesize=A4,
        pageCompression=1
    )
    pdf.setTitle(f"Banco de Horas - {mes_ano}")
    pdf.setAuthor("Assistente do PontoWeb MGS")

    margem_x = 8 * mm
    margem_topo = 8 * mm
    margem_base = 8 * mm
    largura_util = largura_pagina - 2 * margem_x
    centro = largura_pagina / 2

    y = altura_pagina - margem_topo
    pdf.setFillColor(colors.HexColor(COR_PRETO))
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(centro, y - 10, "Relatório de Banco de Horas")
    y -= 24

    informacoes = [f"Período: {mes_ano}"]
    if matricula:
        informacoes.append(f"Matrícula: {matricula}")
    informacoes.append(
        "Emissão: " + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    )
    pdf.setFont("Helvetica", 7.5)
    pdf.drawCentredString(centro, y, "    |    ".join(informacoes))
    y -= 12

    altura_totais = 18 * mm
    altura_legenda = 9 * mm
    altura_rodape = 7 * mm
    limite_tabela = (
        margem_base + altura_rodape + altura_totais + altura_legenda + 5 * mm
    )
    topo_tabela = y
    altura_disponivel = topo_tabela - limite_tabela
    quantidade_linhas = len(registros) + 1
    altura_linha = altura_disponivel / quantidade_linhas
    fonte_corpo = min(7.2, max(4.2, altura_linha * 0.34))
    fonte_cabecalho = min(6.7, max(4.1, altura_linha * 0.31))

    proporcoes = [0.15, 0.08, 0.14, 0.16, 0.16, 0.14, 0.17]
    larguras = [largura_util * valor for valor in proporcoes]
    cabecalhos = [
        "Data",
        "Dia",
        "Entrada",
        "Saída Almoço",
        "Retorno Almoço",
        "Saída",
        "Saldo Dia"
    ]

    linha_y = topo_tabela - altura_linha
    x = margem_x
    for indice, cabecalho in enumerate(cabecalhos):
        desenhar_celula(
            pdf,
            x,
            linha_y,
            larguras[indice],
            altura_linha,
            cabecalho,
            fonte_cabecalho,
            cor_texto=COR_BRANCO,
            cor_fundo=COR_CABECALHO,
            negrito=True,
            max_linhas=2
        )
        x += larguras[indice]

    for indice_registro, registro in enumerate(registros):
        linha_y -= altura_linha
        fundo_linha = (
            COR_BRANCO if indice_registro % 2 == 0 else COR_CINZA_CLARO
        )

        data = formatar_valor(registro[0] if len(registro) > 0 else "")
        atuais = [
            registro[1] if len(registro) > 1 else "",
            registro[2] if len(registro) > 2 else "",
            registro[3] if len(registro) > 3 else "",
            registro[4] if len(registro) > 4 else ""
        ]
        saldo = formatar_valor(
            registro[5] if len(registro) > 5 else "",
            ""
        )
        manual_linha = bool(registro[6]) if len(registro) > 6 else False
        justificativa = normalizar_horario(
            registro[7] if len(registro) > 7 else ""
        )
        originais = [
            registro[8] if len(registro) > 8 else "",
            registro[9] if len(registro) > 9 else "",
            registro[10] if len(registro) > 10 else "",
            registro[11] if len(registro) > 11 else ""
        ]
        origens = classificar_origem_marcacoes(
            atuais,
            originais,
            manual_linha
        )

        # Data e dia sempre permanecem visíveis.
        desenhar_celula(
            pdf, margem_x, linha_y, larguras[0], altura_linha,
            data, fonte_corpo, cor_fundo=fundo_linha
        )
        desenhar_celula(
            pdf, margem_x + larguras[0], linha_y, larguras[1], altura_linha,
            obter_dia_semana(data), fonte_corpo, cor_fundo=fundo_linha
        )

        inicio_horarios = margem_x + larguras[0] + larguras[1]
        largura_horarios = sum(larguras[2:6])

        if justificativa:
            # A justificativa substitui visualmente as quatro marcações,
            # permanecendo na mesma linha do dia e centralizada.
            desenhar_celula(
                pdf,
                inicio_horarios,
                linha_y,
                largura_horarios,
                altura_linha,
                justificativa,
                fonte_corpo,
                cor_texto=COR_PRETO,
                cor_fundo=fundo_linha,
                negrito=True,
                alinhamento="center",
                max_linhas=2,
                borda=0.65
            )
        else:
            x = inicio_horarios
            for indice, valor in enumerate(atuais):
                horario = normalizar_horario(valor)
                origem = origens[indice]
                texto = horario if horario else "-"
                cor_fundo = fundo_linha
                cor_texto = COR_PRETO
                negrito = False

                if origem == "manual":
                    texto = f"* {horario}"
                    cor_fundo = COR_CINZA_ESCURO
                    cor_texto = COR_BRANCO
                    negrito = True

                desenhar_celula(
                    pdf,
                    x,
                    linha_y,
                    larguras[indice + 2],
                    altura_linha,
                    texto,
                    fonte_corpo,
                    cor_texto=cor_texto,
                    cor_fundo=cor_fundo,
                    negrito=negrito
                )
                x += larguras[indice + 2]

        # Saldo também permanece em preto e branco, sem verde ou vermelho.
        desenhar_celula(
            pdf,
            inicio_horarios + largura_horarios,
            linha_y,
            larguras[6],
            altura_linha,
            saldo,
            fonte_corpo,
            cor_texto=COR_PRETO,
            cor_fundo=fundo_linha,
            negrito=True
        )

    # Legenda posicionada imediatamente abaixo da tabela.
    legenda_y = linha_y - 5 * mm
    pdf.setFillColor(colors.HexColor(COR_CINZA_ESCURO))
    pdf.setStrokeColor(colors.HexColor(COR_PRETO))
    pdf.rect(margem_x, legenda_y, 8, 8, stroke=1, fill=1)
    pdf.setFillColor(colors.HexColor(COR_BRANCO))
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawCentredString(margem_x + 4, legenda_y + 1.5, "*")
    pdf.setFillColor(colors.HexColor(COR_PRETO))
    pdf.setFont("Helvetica", 7)
    pdf.drawString(
        margem_x + 12,
        legenda_y + 1.5,
        "Horário inserido ou alterado manualmente"
    )

    positivos, negativos, resultado = calcular_totais_saldo(registros)
    y_totais = margem_base + altura_rodape + 2 * mm
    espaco = 3 * mm
    largura_caixa = (largura_util - 2 * espaco) / 3

    desenhar_total(
        pdf, margem_x, y_totais, largura_caixa, altura_totais,
        "Horas positivas", positivos
    )
    desenhar_total(
        pdf, margem_x + largura_caixa + espaco, y_totais,
        largura_caixa, altura_totais, "Horas negativas", negativos
    )
    desenhar_total(
        pdf, margem_x + 2 * (largura_caixa + espaco), y_totais,
        largura_caixa, altura_totais, "Resultado final", resultado
    )

    pdf.setStrokeColor(colors.HexColor(COR_BORDA))
    pdf.setLineWidth(0.4)
    pdf.line(margem_x, margem_base + 6, largura_pagina - margem_x, margem_base + 6)
    pdf.setFillColor(colors.HexColor(COR_PRETO))
    pdf.setFont("Helvetica", 6)
    pdf.drawString(margem_x, margem_base, "Assistente do PontoWeb MGS")
    pdf.drawRightString(
        largura_pagina - margem_x,
        margem_base,
        "Página 1 de 1"
    )

    pdf.showPage()
    pdf.save()
    return str(caminho_arquivo)
'''


def localizar_arquivo(*nomes):
    for nome in nomes:
        caminho = BASE_DIR / nome
        if caminho.exists() and caminho.is_file():
            return caminho
    return None


def ler_arquivo(caminho):
    dados = caminho.read_bytes()
    bom = dados.startswith(b"\xef\xbb\xbf")

    try:
        texto = dados.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        texto = dados.decode("latin-1")
        encoding = "latin-1"
        bom = False

    newline = "\r\n" if "\r\n" in texto else "\n"
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return texto, encoding, bom, newline


def converter_bytes(texto, encoding, bom, newline):
    saida = texto if newline == "\n" else texto.replace("\n", newline)
    dados = saida.encode(encoding)
    if encoding == "utf-8" and bom:
        dados = b"\xef\xbb\xbf" + dados
    return dados


def escrever_atomico(caminho, texto, encoding, bom, newline):
    temporario = caminho.with_name(caminho.name + ".atualizando")
    try:
        temporario.write_bytes(
            converter_bytes(texto, encoding, bom, newline)
        )
        os.replace(str(temporario), str(caminho))
    finally:
        if temporario.exists():
            try:
                temporario.unlink()
            except OSError:
                pass


def validar(texto, nome):
    try:
        compile(texto, nome, "exec")
    except SyntaxError as erro:
        raise RuntimeError(
            f"Erro de sintaxe em {nome}, linha {erro.lineno}, "
            f"coluna {erro.offset}: {erro.msg}"
        ) from erro


def localizar_bloco(texto, nome, indentacao):
    prefixo = " " * indentacao
    inicio_match = re.search(
        rf"(?m)^{re.escape(prefixo)}def {re.escape(nome)}\s*\(",
        texto
    )
    if not inicio_match:
        return None

    inicio = inicio_match.start()
    trecho = texto[inicio_match.end():]

    if indentacao == 0:
        fim_match = re.search(
            r"(?m)^(?:def |class |if __name__)",
            trecho
        )
    else:
        fim_match = re.search(
            r"(?m)^(?:    def |class |if __name__)",
            trecho
        )

    fim = (
        inicio_match.end() + fim_match.start()
        if fim_match
        else len(texto)
    )
    return inicio, fim


def substituir_bloco(texto, nome, indentacao, novo_codigo):
    local = localizar_bloco(texto, nome, indentacao)
    if not local:
        raise RuntimeError(f"Não foi possível localizar {nome}.")

    inicio, fim = local
    return texto[:inicio] + novo_codigo.strip("\n") + "\n\n" + texto[fim:]


def inserir_metodo_antes(texto, nome_referencia, novo_codigo):
    local = localizar_bloco(texto, nome_referencia, 4)
    if not local:
        raise RuntimeError(
            f"Não foi possível localizar o método {nome_referencia}."
        )

    inicio, _ = local
    return texto[:inicio] + novo_codigo.strip("\n") + "\n\n" + texto[inicio:]


def remover_legendas_antigas(texto):
    # Remove o bloco de legenda criado pela versão 06, caso já tenha sido
    # aplicado. O padrão termina no fechamento de pack(pady=(0, 2)).
    texto = re.sub(
        r'''(?ms)\n\s*# LEGENDA_ORIGEM_MARCACOES_V2\n'''
        r'''\s*tk\.Label\(.*?\)\.pack\(\s*pady=\(0, 2\)\s*\)''',
        "",
        texto,
        count=1
    )

    # Remove eventual legenda V3 para permitir atualização idempotente.
    texto = re.sub(
        r'''(?ms)\n\s*# LEGENDA_ORIGEM_MARCACOES_V3\n'''
        r'''\s*tk\.Label\(.*?\)\.pack\(\s*pady=\(0, 2\)\s*\)''',
        "",
        texto,
        count=1
    )
    return texto


def atualizar_database(texto):
    return substituir_bloco(
        texto,
        "get_banco_horas",
        0,
        NOVO_GET_BANCO_HORAS
    )


def atualizar_main(texto):
    texto = substituir_bloco(
        texto,
        "atualizar_lista_banco",
        4,
        NOVO_ATUALIZAR_LISTA_BANCO
    )

    if localizar_bloco(texto, "limpar_indicador_origem", 4):
        texto = substituir_bloco(
            texto,
            "limpar_indicador_origem",
            4,
            METODO_LIMPAR_INDICADOR
        )
    else:
        texto = inserir_metodo_antes(
            texto,
            "carregar_edicao_banco",
            METODO_LIMPAR_INDICADOR
        )

    texto = substituir_bloco(
        texto,
        "carregar_edicao_banco",
        4,
        NOVO_CARREGAR_EDICAO_BANCO
    )

    texto = texto.replace(
        'self.tree_banco.tag_configure("manual", foreground=settings.COLOR_YELLOW)',
        'self.tree_banco.tag_configure("possui_inserido", background="#F0F0F0")'
    )
    texto = texto.replace(
        'self.tree_banco.tag_configure("possui_inserido", background="#E2E2E2")',
        'self.tree_banco.tag_configure("possui_inserido", background="#F0F0F0")'
    )

    texto = remover_legendas_antigas(texto)
    marcador = "# LEGENDA_ORIGEM_MARCACOES_V3"

    if marcador not in texto:
        alvo = (
            '        self.tree_banco.bind("<<TreeviewSelect>>", '
            'self.carregar_edicao_banco)'
        )
        if alvo not in texto:
            raise RuntimeError(
                "Não foi possível localizar o vínculo da tabela Banco de Horas."
            )

        legenda = alvo + r'''

        # LEGENDA_ORIGEM_MARCACOES_V3
        tk.Label(
            self.win_banco,
            text="* Horário inserido ou alterado manualmente",
            bg=settings.COLOR_BG,
            fg="#303030",
            font=("Segoe UI", 9, "bold")
        ).pack(
            pady=(0, 2)
        )'''
        texto = texto.replace(alvo, legenda, 1)

    return texto


def preparar_existente(nomes, transformador):
    caminho = localizar_arquivo(*nomes)
    if not caminho:
        raise RuntimeError("Arquivo não encontrado: " + " / ".join(nomes))

    original, encoding, bom, newline = ler_arquivo(caminho)
    validar(original, caminho.name)
    atualizado = transformador(original)
    validar(atualizado, caminho.name)

    return ArquivoPreparado(
        caminho=caminho,
        original=original,
        atualizado=atualizado,
        encoding=encoding,
        bom=bom,
        newline=newline
    )


def preparar_relatorio():
    caminho = localizar_arquivo("relatorio.py", "relatorio.pyw")
    validar(CONTEUDO_RELATORIO, "relatorio.py")

    if caminho:
        original, encoding, bom, newline = ler_arquivo(caminho)
        validar(original, caminho.name)
        return ArquivoPreparado(
            caminho=caminho,
            original=original,
            atualizado=CONTEUDO_RELATORIO,
            encoding=encoding,
            bom=bom,
            newline=newline
        )

    return ArquivoPreparado(
        caminho=BASE_DIR / "relatorio.py",
        original="",
        atualizado=CONTEUDO_RELATORIO,
        encoding="utf-8",
        bom=False,
        newline="\n",
        novo=True
    )


def aplicar(arquivos):
    alterados = [
        arquivo for arquivo in arquivos
        if arquivo.original != arquivo.atualizado
    ]

    if not alterados:
        resultados.append("Todos os arquivos já estão atualizados.")
        return True

    PASTA_BACKUP.mkdir(parents=True, exist_ok=True)

    try:
        for arquivo in alterados:
            if not arquivo.novo:
                arquivo.backup = PASTA_BACKUP / arquivo.caminho.name
                shutil.copy2(arquivo.caminho, arquivo.backup)

        for arquivo in alterados:
            escrever_atomico(
                arquivo.caminho,
                arquivo.atualizado,
                arquivo.encoding,
                arquivo.bom,
                arquivo.newline
            )
            confirmacao, _, _, _ = ler_arquivo(arquivo.caminho)
            validar(confirmacao, arquivo.caminho.name)

            if confirmacao != arquivo.atualizado:
                raise RuntimeError(
                    f"Falha ao confirmar {arquivo.caminho.name}."
                )

        for arquivo in arquivos:
            if arquivo.original == arquivo.atualizado:
                status = "JÁ ATUALIZADO"
            elif arquivo.novo:
                status = "CRIADO"
            else:
                status = "ATUALIZADO"
            resultados.append(f"{arquivo.caminho.name}: {status}")

        return True

    except Exception as erro:
        for arquivo in alterados:
            try:
                if arquivo.novo:
                    if arquivo.caminho.exists():
                        arquivo.caminho.unlink()
                elif arquivo.backup and arquivo.backup.exists():
                    shutil.copy2(arquivo.backup, arquivo.caminho)
            except Exception:
                pass

        resultados.append(
            f"FALHA: {type(erro).__name__}: {erro}"
        )
        return False


def montar_relatorio(sucesso):
    linhas = [
        "=" * 78,
        "ATUALIZAÇÃO DO RELATÓRIO E DAS MARCAÇÕES MANUAIS",
        "=" * 78,
        f"Versão: {VERSAO}",
        "Data: " + AGORA.strftime("%d/%m/%Y %H:%M:%S"),
        f"Diretório: {BASE_DIR}",
        ""
    ]
    linhas.extend(resultados)
    linhas.extend([
        "",
        "Resultado: " + ("SUCESSO" if sucesso else "FALHA"),
        "=" * 78
    ])
    return "\n".join(linhas)


def main():
    print("Preparando a atualização 2026.09.03-07...")
    arquivos = []

    try:
        arquivos.append(
            preparar_existente(
                ("database.py", "database.pyw"),
                atualizar_database
            )
        )
        arquivos.append(
            preparar_existente(
                ("main.pyw", "main.py"),
                atualizar_main
            )
        )
        arquivos.append(preparar_relatorio())
        sucesso = aplicar(arquivos)

    except Exception as erro:
        sucesso = False
        resultados.append(
            f"FALHA NA PREPARAÇÃO: {type(erro).__name__}: {erro}"
        )

    relatorio_execucao = montar_relatorio(sucesso)
    print()
    print(relatorio_execucao)

    try:
        ARQUIVO_RELATORIO.write_text(
            relatorio_execucao,
            encoding="utf-8"
        )
        print()
        print(f"Relatório salvo em: {ARQUIVO_RELATORIO.name}")
    except Exception as erro:
        print(f"Não foi possível salvar o relatório: {erro}")

    return 0 if sucesso else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Atualização cancelada pelo usuário.")
        sys.exit(130)
    except Exception as erro:
        print(f"Falha inesperada: {type(erro).__name__}: {erro}")
        traceback.print_exc()
        sys.exit(1)
