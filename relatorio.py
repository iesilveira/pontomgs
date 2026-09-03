"""
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
