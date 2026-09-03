"""
Autor: Ismael Elói da Silveira Silva
Descrição: Corrige a identificação individual das marcações originais e manuais.
Versão: 2026.09.03-06

Alterações:
- Usa orig_m1, orig_m2, orig_m3 e orig_m4 como fonte de verdade.
- Classifica horários independentemente da coluna em que aparecem.
- Consome cada ocorrência original somente uma vez, tratando duplicidades.
- Exibe R (registrado) e I (inserido) na tela Banco de Horas.
- Usa a mesma classificação no relatório PDF.
- Remove a coluna Justificativa do PDF.
- Exibe a justificativa em uma linha adicional, mesclando as quatro células de horários.
- Reforça o contraste para impressão em preto e branco.
- Mantém A4 retrato, uma única página e os totais em horas e minutos.
"""

import os
import re
import sys
import shutil
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

VERSAO = "2026.09.03-06"
BASE_DIR = Path(__file__).resolve().parent
AGORA = datetime.now()
IDENTIFICADOR = AGORA.strftime("%Y%m%d_%H%M%S")
PASTA_BACKUP = BASE_DIR / f"backup_atualizacao_{IDENTIFICADOR}"
RELATORIO_EXECUCAO = BASE_DIR / f"relatorio_atualizacao_{IDENTIFICADOR}.txt"


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
        Atualiza a tabela e identifica cada horário individualmente.

        R = marcação registrada pelo sistema.
        I = marcação inserida ou alterada manualmente.

        A comparação não depende da coluna. Assim, uma marcação original
        que foi deslocada de M2 para M3 continua sendo classificada como R.
        """

        for item in self.tree_banco.get_children():
            self.tree_banco.delete(item)

        mes_sel = self.mes_selecionado_var.get()
        if not mes_sel:
            return

        try:
            registros = database.get_banco_horas(mes_sel)

            for registro in registros:
                atuais = registro[1:5]
                originais = registro[8:12]

                origens = relatorio.classificar_origem_marcacoes(
                    atuais,
                    originais
                )

                horarios_exibicao = []

                for horario, origem in zip(atuais, origens):
                    valor = relatorio.normalizar_horario(horario)

                    if not valor:
                        horarios_exibicao.append("-")
                    elif origem == "sistema":
                        horarios_exibicao.append(f"R  {valor}")
                    else:
                        horarios_exibicao.append(f"I  {valor}")

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

                possui_inserido = "manual" in origens
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
        """Remove os prefixos visuais R e I antes da edição."""

        if valor is None:
            return ""

        texto = str(valor).strip()

        if texto in ("", "-", "None", "--:--"):
            return ""

        return re.sub(
            r"^[RI]\s+",
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
            self.ent_banco_justificativa.insert(
                0,
                item_values[7]
            )

        self.btn_cancelar_banco.pack(
            side=tk.LEFT,
            padx=10
        )
        self.btn_restaurar_banco.pack(
            side=tk.LEFT,
            padx=10
        )
'''


CONTEUDO_RELATORIO = r'''"""
Autor: Ismael Elói da Silveira Silva
Descrição: Relatório mensal do Banco de Horas em PDF.

- A4 retrato.
- Uma única página.
- R identifica marcação registrada pelo sistema.
- I identifica marcação inserida ou alterada manualmente.
- A classificação é independente da posição da marcação.
"""

import datetime
from collections import Counter

COR_PRETO = "#000000"
COR_BRANCO = "#FFFFFF"
COR_CINZA_1 = "#F0F0F0"
COR_CINZA_2 = "#D0D0D0"
COR_CINZA_3 = "#707070"
COR_CINZA_4 = "#303030"
COR_VERDE = "#166534"
COR_VERMELHO = "#991B1B"
COR_CABECALHO = "#111827"
COR_BORDA = "#404040"


def normalizar_horario(valor):
    """Normaliza horários vazios para comparação."""

    if valor is None:
        return ""

    texto = str(valor).strip()

    if texto.lower() in (
        "",
        "-",
        "--:--",
        "none",
        "null"
    ):
        return ""

    return texto


def formatar_valor(valor, vazio="-"):
    if valor is None:
        return vazio

    texto = str(valor).strip()

    if texto.lower() in ("", "none", "null"):
        return vazio

    return texto


def classificar_origem_marcacoes(
    marcacoes_atuais,
    marcacoes_originais
):
    """
    Classifica cada marcação atual como sistema, manual ou vazio.

    A posição não é considerada. Cada ocorrência original pode validar
    apenas uma ocorrência atual, inclusive quando há horários repetidos.

    Exemplo:
        originais = 09:00, 13:00, 18:00
        atuais    = 09:00, 12:00, 13:00, 18:00
        resultado = sistema, manual, sistema, sistema
    """

    disponiveis = Counter()

    for horario in marcacoes_originais:
        normalizado = normalizar_horario(horario)
        if normalizado:
            disponiveis[normalizado] += 1

    resultado = []

    for horario in marcacoes_atuais:
        normalizado = normalizar_horario(horario)

        if not normalizado:
            resultado.append("vazio")
        elif disponiveis[normalizado] > 0:
            resultado.append("sistema")
            disponiveis[normalizado] -= 1
        else:
            resultado.append("manual")

    return resultado


def horario_foi_alterado(
    horario_atual,
    marcacoes_originais,
    marcacoes_atuais=None
):
    """Compatibilidade: informa se um horário não existe nos originais."""

    atual = normalizar_horario(horario_atual)
    if not atual:
        return False

    originais = [
        normalizar_horario(item)
        for item in marcacoes_originais
    ]

    return atual not in originais


def saldo_para_minutos(saldo):
    if saldo is None:
        return 0

    texto = str(saldo).strip()
    if not texto:
        return 0

    sinal = -1 if texto.startswith("-") else 1
    texto = texto.replace("+", "").replace("-", "")
    partes = texto.split(":")

    if len(partes) != 2:
        return 0

    try:
        horas = int(partes[0])
        minutos = int(partes[1])
    except (TypeError, ValueError):
        return 0

    return sinal * (horas * 60 + minutos)


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
    reconstruido = " ".join(linhas)

    if linhas and reconstruido != original:
        ultima = linhas[-1]

        while ultima:
            candidato = ultima.rstrip() + "..."
            if stringWidth(candidato, fonte, tamanho) <= largura:
                linhas[-1] = candidato
                break
            ultima = ultima[:-1]

    return linhas[:max_linhas]


def desenhar_celula(
    pdf,
    x,
    y,
    largura,
    altura,
    texto,
    tamanho,
    cor_texto,
    cor_fundo,
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
        max(1, largura - 5),
        fonte,
        tamanho,
        max_linhas
    )

    entrelinha = tamanho + 0.8
    inicio_y = y + altura / 2 + (len(linhas) - 1) * entrelinha / 2 - tamanho * 0.35

    for indice, linha in enumerate(linhas):
        linha_y = inicio_y - indice * entrelinha

        if alinhamento == "left":
            pdf.drawString(x + 3, linha_y, linha)
        elif alinhamento == "right":
            pdf.drawRightString(x + largura - 3, linha_y, linha)
        else:
            pdf.drawCentredString(x + largura / 2, linha_y, linha)


def desenhar_total(
    pdf,
    x,
    y,
    largura,
    altura,
    titulo,
    minutos,
    cor
):
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth

    pdf.setFillColor(colors.HexColor(COR_CINZA_1))
    pdf.setStrokeColor(colors.HexColor(COR_BORDA))
    pdf.setLineWidth(0.7)
    pdf.roundRect(x, y, largura, altura, 3, stroke=1, fill=1)

    pdf.setFillColor(colors.HexColor(COR_PRETO))
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(x + 5, y + altura - 10, titulo)

    horas = minutos_para_horas(minutos)
    texto_minutos = f"({minutos_com_sinal(minutos)})"
    tam_horas = 11
    tam_minutos = 6.5
    espaco = 4

    largura_total = (
        stringWidth(horas, "Helvetica-Bold", tam_horas)
        + espaco
        + stringWidth(texto_minutos, "Helvetica", tam_minutos)
    )
    inicio = x + (largura - largura_total) / 2

    pdf.setFillColor(colors.HexColor(cor))
    pdf.setFont("Helvetica-Bold", tam_horas)
    pdf.drawString(inicio, y + 7, horas)

    pdf.setFillColor(colors.HexColor(COR_CINZA_4))
    pdf.setFont("Helvetica", tam_minutos)
    pdf.drawString(
        inicio + stringWidth(horas, "Helvetica-Bold", tam_horas) + espaco,
        y + 8.5,
        texto_minutos
    )


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
    from reportlab.pdfgen import canvas

    if not registros:
        raise ValueError("Não existem registros para gerar o relatório.")

    largura_pagina, altura_pagina = A4
    pdf = canvas.Canvas(str(caminho_arquivo), pagesize=A4, pageCompression=1)
    pdf.setTitle(f"Banco de Horas - {mes_ano}")
    pdf.setAuthor("Assistente do PontoWeb MGS")

    margem_x = 7 * mm
    margem_superior = 7 * mm
    margem_inferior = 7 * mm
    largura_util = largura_pagina - 2 * margem_x

    y = altura_pagina - margem_superior

    pdf.setFillColor(colors.HexColor(COR_CABECALHO))
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(largura_pagina / 2, y - 10, "Relatório de Banco de Horas")
    y -= 24

    info = [f"Período: {mes_ano}"]
    if matricula:
        info.append(f"Matrícula: {matricula}")
    info.append("Emissão: " + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    pdf.setFillColor(colors.HexColor(COR_PRETO))
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(largura_pagina / 2, y, "    |    ".join(info))
    y -= 12

    # Legenda de alto contraste para impressão em preto e branco.
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.setFillColor(colors.HexColor(COR_PRETO))
    pdf.drawString(margem_x, y, "R  Registrado pelo sistema")

    pdf.setFillColor(colors.HexColor(COR_CINZA_4))
    pdf.rect(margem_x + 61 * mm, y - 2, 8, 8, stroke=0, fill=1)
    pdf.setFillColor(colors.HexColor(COR_PRETO))
    pdf.drawString(margem_x + 61 * mm + 11, y, "I  Inserido ou alterado manualmente")
    y -= 12

    altura_totais = 18 * mm
    altura_rodape = 7 * mm
    limite_tabela = margem_inferior + altura_rodape + altura_totais + 4 * mm
    topo_tabela = y

    linhas_visuais = 1
    for registro in registros:
        linhas_visuais += 1
        justificativa = formatar_valor(
            registro[7] if len(registro) > 7 else "",
            ""
        )
        if justificativa:
            linhas_visuais += 1

    altura_disponivel = topo_tabela - limite_tabela
    altura_linha = altura_disponivel / max(1, linhas_visuais)
    fonte_corpo = min(7.0, max(3.8, altura_linha * 0.35))
    fonte_cabecalho = min(6.5, max(3.8, altura_linha * 0.33))

    proporcoes = [0.14, 0.07, 0.145, 0.16, 0.17, 0.145, 0.17]
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

    for indice, titulo in enumerate(cabecalhos):
        desenhar_celula(
            pdf, x, linha_y, larguras[indice], altura_linha,
            titulo, fonte_cabecalho, COR_BRANCO, COR_CABECALHO,
            negrito=True, max_linhas=2, borda=0.7
        )
        x += larguras[indice]

    for indice_registro, registro in enumerate(registros):
        linha_y -= altura_linha

        data = formatar_valor(registro[0] if len(registro) > 0 else "")
        atuais = [
            registro[1] if len(registro) > 1 else "",
            registro[2] if len(registro) > 2 else "",
            registro[3] if len(registro) > 3 else "",
            registro[4] if len(registro) > 4 else ""
        ]
        saldo = formatar_valor(registro[5] if len(registro) > 5 else "", "")
        justificativa = formatar_valor(registro[7] if len(registro) > 7 else "", "")
        originais = [
            registro[8] if len(registro) > 8 else "",
            registro[9] if len(registro) > 9 else "",
            registro[10] if len(registro) > 10 else "",
            registro[11] if len(registro) > 11 else ""
        ]

        origens = classificar_origem_marcacoes(atuais, originais)
        fundo_linha = COR_BRANCO if indice_registro % 2 == 0 else COR_CINZA_1
        valores = [data, obter_dia_semana(data)] + atuais + [saldo]
        x = margem_x

        for coluna, valor in enumerate(valores):
            texto = formatar_valor(valor)
            cor_fundo = fundo_linha
            cor_texto = COR_PRETO
            negrito = False

            if 2 <= coluna <= 5:
                origem = origens[coluna - 2]
                horario = normalizar_horario(valor)

                if not horario:
                    texto = "-"
                elif origem == "sistema":
                    texto = f"R  {horario}"
                    cor_fundo = COR_BRANCO
                    cor_texto = COR_PRETO
                    negrito = True
                else:
                    texto = f"I  {horario}"
                    cor_fundo = COR_CINZA_4
                    cor_texto = COR_BRANCO
                    negrito = True

            elif coluna == 6:
                minutos = saldo_para_minutos(valor)
                negrito = True
                if minutos > 0:
                    cor_texto = COR_VERDE
                elif minutos < 0:
                    cor_texto = COR_VERMELHO
                else:
                    cor_texto = COR_CINZA_4

            desenhar_celula(
                pdf, x, linha_y, larguras[coluna], altura_linha,
                texto, fonte_corpo, cor_texto, cor_fundo,
                negrito=negrito, max_linhas=1
            )
            x += larguras[coluna]

        if justificativa:
            linha_y -= altura_linha

            # Data e dia permanecem vazios; as quatro células de horários
            # são mescladas para receber a justificativa.
            desenhar_celula(
                pdf, margem_x, linha_y, larguras[0], altura_linha,
                "", fonte_corpo, COR_PRETO, COR_CINZA_2
            )
            desenhar_celula(
                pdf, margem_x + larguras[0], linha_y, larguras[1], altura_linha,
                "", fonte_corpo, COR_PRETO, COR_CINZA_2
            )

            x_just = margem_x + larguras[0] + larguras[1]
            largura_just = sum(larguras[2:6])

            desenhar_celula(
                pdf, x_just, linha_y, largura_just, altura_linha,
                "Justificativa: " + justificativa,
                fonte_corpo, COR_PRETO, COR_CINZA_2,
                negrito=True, alinhamento="left", max_linhas=2,
                borda=0.7
            )

            desenhar_celula(
                pdf, x_just + largura_just, linha_y, larguras[6], altura_linha,
                "", fonte_corpo, COR_PRETO, COR_CINZA_2
            )

    positivos, negativos, resultado = calcular_totais_saldo(registros)
    y_totais = margem_inferior + altura_rodape + 2 * mm
    espaco = 2.5 * mm
    largura_caixa = (largura_util - 2 * espaco) / 3

    desenhar_total(
        pdf, margem_x, y_totais, largura_caixa, altura_totais,
        "Horas positivas", positivos, COR_VERDE
    )
    desenhar_total(
        pdf, margem_x + largura_caixa + espaco, y_totais,
        largura_caixa, altura_totais,
        "Horas negativas", negativos, COR_VERMELHO
    )

    cor_resultado = COR_VERDE if resultado > 0 else COR_VERMELHO if resultado < 0 else COR_CINZA_4
    desenhar_total(
        pdf, margem_x + 2 * (largura_caixa + espaco), y_totais,
        largura_caixa, altura_totais,
        "Resultado final", resultado, cor_resultado
    )

    pdf.setStrokeColor(colors.HexColor(COR_BORDA))
    pdf.line(margem_x, margem_inferior + 5, largura_pagina - margem_x, margem_inferior + 5)
    pdf.setFillColor(colors.HexColor(COR_CINZA_4))
    pdf.setFont("Helvetica", 6)
    pdf.drawString(margem_x, margem_inferior, "Assistente do PontoWeb MGS")
    pdf.drawRightString(largura_pagina - margem_x, margem_inferior, "Página 1 de 1")

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


def escrever_atomico(caminho, texto, encoding, bom, newline):
    saida = texto if newline == "\n" else texto.replace("\n", newline)
    dados = saida.encode(encoding)

    if encoding == "utf-8" and bom:
        dados = b"\xef\xbb\xbf" + dados

    temporario = caminho.with_name(caminho.name + ".atualizando")

    try:
        temporario.write_bytes(dados)
        os.replace(str(temporario), str(caminho))
    finally:
        if temporario.exists():
            temporario.unlink()


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

    if indentacao == 0:
        fim_match = re.search(
            r"(?m)^(?:def |class |if __name__)",
            texto[inicio_match.end():]
        )
    else:
        fim_match = re.search(
            r"(?m)^(?:    def |class |if __name__)",
            texto[inicio_match.end():]
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

    # Substitui a configuração antiga de linha inteira.
    texto = texto.replace(
        'self.tree_banco.tag_configure("manual", foreground=settings.COLOR_YELLOW)',
        'self.tree_banco.tag_configure("possui_inserido", background="#E2E2E2")'
    )

    marcador_legenda = "# LEGENDA_ORIGEM_MARCACOES_V2"

    if marcador_legenda not in texto:
        alvo = (
            '        self.tree_banco.bind("<<TreeviewSelect>>", '
            'self.carregar_edicao_banco)'
        )

        if alvo not in texto:
            raise RuntimeError(
                "Não foi possível localizar o vínculo da tabela Banco de Horas."
            )

        legenda = alvo + r'''

        # LEGENDA_ORIGEM_MARCACOES_V2
        tk.Label(
            self.win_banco,
            text=(
                "R = registrado pelo sistema    |    "
                "I = inserido ou alterado manualmente"
            ),
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
        raise RuntimeError(
            "Arquivo não encontrado: " + " / ".join(nomes)
        )

    original, encoding, bom, newline = ler_arquivo(caminho)
    validar(original, caminho.name)
    atualizado = transformador(original)
    validar(atualizado, caminho.name)

    return ArquivoPreparado(
        caminho,
        original,
        atualizado,
        encoding,
        bom,
        newline
    )


def preparar_relatorio():
    caminho = localizar_arquivo("relatorio.py", "relatorio.pyw")

    if caminho:
        original, encoding, bom, newline = ler_arquivo(caminho)
        validar(original, caminho.name)
        novo = False
    else:
        caminho = BASE_DIR / "relatorio.py"
        original = ""
        encoding = "utf-8"
        bom = False
        newline = "\n"
        novo = True

    validar(CONTEUDO_RELATORIO, caminho.name)

    return ArquivoPreparado(
        caminho,
        original,
        CONTEUDO_RELATORIO,
        encoding,
        bom,
        newline,
        novo=novo
    )


def aplicar(arquivos):
    alterados = [a for a in arquivos if a.original != a.atualizado]

    if not alterados:
        for arquivo in arquivos:
            resultados.append(
                f"{arquivo.caminho.name}: JÁ ATUALIZADO"
            )
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
        "ATUALIZAÇÃO DA IDENTIFICAÇÃO DE MARCAÇÕES",
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
    print("Preparando a atualização...")

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

    relatorio = montar_relatorio(sucesso)
    print()
    print(relatorio)

    try:
        RELATORIO_EXECUCAO.write_text(relatorio, encoding="utf-8")
        print()
        print(f"Relatório salvo em: {RELATORIO_EXECUCAO.name}")
    except Exception as erro:
        print(f"Não foi possível salvar o relatório: {erro}")

    return 0 if sucesso else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as erro:
        traceback.print_exc()
        print(f"Falha inesperada: {erro}")
        sys.exit(1)
