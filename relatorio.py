"""
Autor: Ismael Elói da Silveira Silva
Descrição: Geração do relatório mensal do Banco de Horas em PDF.

O relatório é gerado em folha A4 no formato retrato e ajustado
automaticamente para permanecer em uma única página.
"""

import datetime


# =============================================================================
# CORES DO RELATÓRIO
# =============================================================================

COR_AZUL_SISTEMA = "#00205B"
COR_FUNDO_SISTEMA = "#EAF2FF"

COR_TEXTO_MANUAL = "#8A3B00"
COR_FUNDO_MANUAL = "#FFE0B2"

COR_VERDE = "#1B7F3A"
COR_VERDE_CLARO = "#E5F5EA"

COR_VERMELHO = "#AE1917"
COR_VERMELHO_CLARO = "#FCE8E8"

COR_CINZA = "#6C757D"
COR_CINZA_CLARO = "#F2F4F7"

COR_BORDA = "#B8C2CC"
COR_CABECALHO = "#00205B"
COR_FUNDO_ALTERNADO = "#F7F9FC"
COR_BRANCO = "#FFFFFF"
COR_TEXTO = "#222222"


# =============================================================================
# FUNÇÕES DE TRATAMENTO DOS DADOS
# =============================================================================

def normalizar_horario(valor):
    """
    Normaliza um horário para comparação.

    Valores vazios, None e traços são considerados equivalentes.
    """

    if valor is None:
        return ""

    texto = str(valor).strip()

    if texto.lower() in (
        "",
        "-",
        "none",
        "null"
    ):
        return ""

    return texto


def formatar_valor(valor, vazio="-"):
    """
    Formata um valor para apresentação no relatório.
    """

    if valor is None:
        return vazio

    texto = str(valor).strip()

    if texto.lower() in (
        "",
        "none",
        "null"
    ):
        return vazio

    return texto


def horario_foi_alterado(
    horario_atual,
    horario_original,
    registro_manual
):
    """
    Identifica individualmente se um horário foi modificado.

    O registro precisa estar marcado como manual e o valor atual
    precisa ser diferente do valor originalmente obtido do sistema.
    """

    if not registro_manual:
        return False

    atual = normalizar_horario(
        horario_atual
    )

    original = normalizar_horario(
        horario_original
    )

    return atual != original


def saldo_para_minutos(saldo):
    """
    Converte um saldo no formato +HH:MM ou -HH:MM para minutos.

    Exemplos:

        +01:30 -> 90
        -02:10 -> -130
        00:00  -> 0
    """

    if saldo is None:
        return 0

    texto = str(saldo).strip()

    if not texto:
        return 0

    sinal = -1 if texto.startswith("-") else 1

    texto_limpo = (
        texto
        .replace("+", "")
        .replace("-", "")
        .strip()
    )

    partes = texto_limpo.split(":")

    if len(partes) != 2:
        return 0

    try:
        horas = int(partes[0])
        minutos = int(partes[1])

    except (TypeError, ValueError):
        return 0

    if horas < 0 or minutos < 0:
        return 0

    return sinal * (
        horas * 60 + minutos
    )


def minutos_para_horas(
    total_minutos,
    exibir_sinal_positivo=True
):
    """
    Converte minutos para o formato de horas.

    Exemplos:

        90   -> +01:30
        -130 -> -02:10
        0    -> +00:00
    """

    try:
        total = int(total_minutos)

    except (TypeError, ValueError):
        total = 0

    if total < 0:
        sinal = "-"

    elif exibir_sinal_positivo:
        sinal = "+"

    else:
        sinal = ""

    horas, minutos = divmod(
        abs(total),
        60
    )

    return (
        f"{sinal}{horas:02d}:{minutos:02d}"
    )


def formatar_minutos_com_sinal(
    total_minutos,
    exibir_sinal_positivo=True
):
    """
    Formata a representação em minutos.

    Exemplos:

        90   -> +90 min
        -130 -> -130 min
    """

    try:
        total = int(total_minutos)

    except (TypeError, ValueError):
        total = 0

    if total < 0:
        sinal = "-"

    elif exibir_sinal_positivo:
        sinal = "+"

    else:
        sinal = ""

    return f"{sinal}{abs(total)} min"


def calcular_totais_saldo(registros):
    """
    Calcula os totais positivos, negativos e o resultado final.

    As horas negativas são retornadas como um número negativo.

    Retorno:

        total_positivo,
        total_negativo,
        resultado_final
    """

    total_positivo = 0
    total_negativo = 0

    for registro in registros:
        if len(registro) <= 5:
            continue

        minutos = saldo_para_minutos(
            registro[5]
        )

        if minutos > 0:
            total_positivo += minutos

        elif minutos < 0:
            total_negativo += minutos

    resultado_final = (
        total_positivo
        + total_negativo
    )

    return (
        total_positivo,
        total_negativo,
        resultado_final
    )


def obter_dia_semana(data):
    """
    Retorna a abreviação do dia da semana.
    """

    nomes_dias = [
        "Seg",
        "Ter",
        "Qua",
        "Qui",
        "Sex",
        "Sáb",
        "Dom"
    ]

    try:
        data_objeto = datetime.datetime.strptime(
            str(data),
            "%d/%m/%Y"
        )

        return nomes_dias[
            data_objeto.weekday()
        ]

    except (TypeError, ValueError):
        return ""


def limitar_texto(
    canvas,
    texto,
    largura_maxima,
    nome_fonte,
    tamanho_fonte
):
    """
    Reduz um texto com reticências quando ele não couber
    na largura disponível.
    """

    from reportlab.pdfbase.pdfmetrics import stringWidth

    texto = str(texto or "")

    if stringWidth(
        texto,
        nome_fonte,
        tamanho_fonte
    ) <= largura_maxima:
        return texto

    sufixo = "..."

    while texto:
        candidato = texto.rstrip() + sufixo

        if stringWidth(
            candidato,
            nome_fonte,
            tamanho_fonte
        ) <= largura_maxima:
            return candidato

        texto = texto[:-1]

    return sufixo


def quebrar_texto(
    texto,
    largura_maxima,
    nome_fonte,
    tamanho_fonte,
    maximo_linhas=2
):
    """
    Divide o texto em linhas de acordo com a largura disponível.

    Caso o conteúdo ultrapasse o limite de linhas, a última linha
    será reduzida e receberá reticências.
    """

    from reportlab.pdfbase.pdfmetrics import stringWidth

    texto = str(texto or "").strip()

    if not texto:
        return [""]

    palavras = texto.replace(
        "\n",
        " "
    ).split()

    linhas = []
    linha_atual = ""

    for palavra in palavras:
        candidato = (
            palavra
            if not linha_atual
            else linha_atual + " " + palavra
        )

        if stringWidth(
            candidato,
            nome_fonte,
            tamanho_fonte
        ) <= largura_maxima:
            linha_atual = candidato

        else:
            if linha_atual:
                linhas.append(
                    linha_atual
                )

            linha_atual = palavra

            if len(linhas) >= maximo_linhas:
                break

    if (
        linha_atual
        and len(linhas) < maximo_linhas
    ):
        linhas.append(
            linha_atual
        )

    texto_reconstruido = " ".join(linhas)

    texto_original_normalizado = " ".join(
        palavras
    )

    if (
        texto_reconstruido
        != texto_original_normalizado
        and linhas
    ):
        ultima = linhas[-1]

        while ultima:
            candidato = ultima.rstrip() + "..."

            if stringWidth(
                candidato,
                nome_fonte,
                tamanho_fonte
            ) <= largura_maxima:
                linhas[-1] = candidato
                break

            ultima = ultima[:-1]

        if not ultima:
            linhas[-1] = "..."

    return linhas[:maximo_linhas]


# =============================================================================
# FUNÇÕES DE DESENHO
# =============================================================================

def desenhar_texto_centralizado(
    canvas,
    texto,
    centro_x,
    y,
    nome_fonte,
    tamanho_fonte,
    cor
):
    """
    Desenha um texto centralizado horizontalmente.
    """

    canvas.setFont(
        nome_fonte,
        tamanho_fonte
    )

    canvas.setFillColor(
        cor
    )

    canvas.drawCentredString(
        centro_x,
        y,
        str(texto)
    )


def desenhar_celula(
    canvas,
    x,
    y,
    largura,
    altura,
    texto,
    tamanho_fonte,
    cor_texto,
    cor_fundo,
    cor_borda,
    alinhamento="center",
    negrito=False,
    maximo_linhas=1
):
    """
    Desenha uma célula da tabela.
    """

    from reportlab.lib import colors

    canvas.setFillColor(
        colors.HexColor(cor_fundo)
    )

    canvas.rect(
        x,
        y,
        largura,
        altura,
        stroke=0,
        fill=1
    )

    canvas.setStrokeColor(
        colors.HexColor(cor_borda)
    )

    canvas.setLineWidth(0.35)

    canvas.rect(
        x,
        y,
        largura,
        altura,
        stroke=1,
        fill=0
    )

    nome_fonte = (
        "Helvetica-Bold"
        if negrito
        else "Helvetica"
    )

    canvas.setFont(
        nome_fonte,
        tamanho_fonte
    )

    canvas.setFillColor(
        colors.HexColor(cor_texto)
    )

    margem_horizontal = 2.2

    largura_texto = max(
        1,
        largura - 2 * margem_horizontal
    )

    linhas = quebrar_texto(
        texto,
        largura_texto,
        nome_fonte,
        tamanho_fonte,
        maximo_linhas=maximo_linhas
    )

    entrelinha = tamanho_fonte + 0.8

    altura_texto = (
        len(linhas) * entrelinha
    )

    linha_y = (
        y
        + altura / 2
        + altura_texto / 2
        - entrelinha
        + 0.5
    )

    for linha in linhas:
        if alinhamento == "left":
            canvas.drawString(
                x + margem_horizontal,
                linha_y,
                linha
            )

        elif alinhamento == "right":
            canvas.drawRightString(
                x + largura - margem_horizontal,
                linha_y,
                linha
            )

        else:
            canvas.drawCentredString(
                x + largura / 2,
                linha_y,
                linha
            )

        linha_y -= entrelinha


def desenhar_caixa_total(
    canvas,
    x,
    y,
    largura,
    altura,
    titulo,
    valor_horas,
    valor_minutos,
    cor_principal,
    cor_fundo
):
    """
    Desenha uma caixa com o total em horas e minutos.
    """

    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth

    canvas.setFillColor(
        colors.HexColor(cor_fundo)
    )

    canvas.setStrokeColor(
        colors.HexColor(COR_BORDA)
    )

    canvas.setLineWidth(0.6)

    canvas.roundRect(
        x,
        y,
        largura,
        altura,
        4,
        stroke=1,
        fill=1
    )

    canvas.setFillColor(
        colors.HexColor(COR_CABECALHO)
    )

    canvas.setFont(
        "Helvetica-Bold",
        7
    )

    canvas.drawString(
        x + 5,
        y + altura - 10,
        titulo
    )

    tamanho_horas = 12
    tamanho_minutos = 7

    largura_horas = stringWidth(
        valor_horas,
        "Helvetica-Bold",
        tamanho_horas
    )

    largura_minutos = stringWidth(
        valor_minutos,
        "Helvetica",
        tamanho_minutos
    )

    espacamento = 5

    largura_conjunto = (
        largura_horas
        + espacamento
        + largura_minutos
    )

    inicio_x = (
        x
        + (largura - largura_conjunto) / 2
    )

    base_y = y + 7

    canvas.setFillColor(
        colors.HexColor(cor_principal)
    )

    canvas.setFont(
        "Helvetica-Bold",
        tamanho_horas
    )

    canvas.drawString(
        inicio_x,
        base_y,
        valor_horas
    )

    canvas.setFillColor(
        colors.HexColor(COR_CINZA)
    )

    canvas.setFont(
        "Helvetica",
        tamanho_minutos
    )

    canvas.drawString(
        inicio_x
        + largura_horas
        + espacamento,
        base_y + 1.5,
        f"({valor_minutos})"
    )


# =============================================================================
# GERAÇÃO DO PDF
# =============================================================================

def gerar_pdf(
    caminho_arquivo,
    mes_ano,
    registros,
    saldo_mes=None,
    matricula=""
):
    """
    Gera o relatório mensal do Banco de Horas.

    O relatório é sempre criado em:

    - Papel A4.
    - Orientação retrato.
    - Uma única página.
    - Ajuste automático de linhas e fontes.

    Estrutura esperada para cada registro:

        0  - data
        1  - m1
        2  - m2
        3  - m3
        4  - m4
        5  - saldo
        6  - manual
        7  - justificativa
        8  - orig_m1
        9  - orig_m2
        10 - orig_m3
        11 - orig_m4
    """

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdf_canvas

    except ImportError as erro:
        raise RuntimeError(
            "A biblioteca reportlab não está instalada."
        ) from erro

    if not registros:
        raise ValueError(
            "Não existem registros para gerar o relatório."
        )

    caminho_arquivo = str(
        caminho_arquivo
    )

    largura_pagina, altura_pagina = A4

    pdf = pdf_canvas.Canvas(
        caminho_arquivo,
        pagesize=A4,
        pageCompression=1
    )

    pdf.setTitle(
        f"Banco de Horas - {mes_ano}"
    )

    pdf.setAuthor(
        "Assistente do PontoWeb MGS"
    )

    pdf.setSubject(
        "Relatório mensal do Banco de Horas"
    )

    margem_horizontal = 8 * mm
    margem_superior = 8 * mm
    margem_inferior = 8 * mm

    largura_util = (
        largura_pagina
        - 2 * margem_horizontal
    )

    centro_pagina = (
        largura_pagina / 2
    )

    # -------------------------------------------------------------------------
    # Cabeçalho
    # -------------------------------------------------------------------------

    y = (
        altura_pagina
        - margem_superior
    )

    desenhar_texto_centralizado(
        pdf,
        "Relatório de Banco de Horas",
        centro_pagina,
        y - 10,
        "Helvetica-Bold",
        16,
        colors.HexColor(COR_CABECALHO)
    )

    y -= 24

    informacoes = [
        f"Período: {mes_ano}"
    ]

    if matricula:
        informacoes.append(
            f"Matrícula: {matricula}"
        )

    informacoes.append(
        "Emissão: "
        + datetime.datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    desenhar_texto_centralizado(
        pdf,
        "    |    ".join(informacoes),
        centro_pagina,
        y,
        "Helvetica",
        7.5,
        colors.HexColor(COR_TEXTO)
    )

    y -= 13

    # -------------------------------------------------------------------------
    # Legenda
    # -------------------------------------------------------------------------

    tamanho_quadrado = 7
    espaco_legenda = 6

    pdf.setFillColor(
        colors.HexColor(COR_FUNDO_SISTEMA)
    )

    pdf.setStrokeColor(
        colors.HexColor(COR_AZUL_SISTEMA)
    )

    pdf.rect(
        margem_horizontal,
        y - 2,
        tamanho_quadrado,
        tamanho_quadrado,
        stroke=1,
        fill=1
    )

    pdf.setFont(
        "Helvetica",
        6.5
    )

    pdf.setFillColor(
        colors.HexColor(COR_TEXTO)
    )

    pdf.drawString(
        margem_horizontal
        + tamanho_quadrado
        + 3,
        y,
        "Horário obtido do sistema"
    )

    segunda_legenda_x = (
        margem_horizontal
        + 62 * mm
    )

    pdf.setFillColor(
        colors.HexColor(COR_FUNDO_MANUAL)
    )

    pdf.setStrokeColor(
        colors.HexColor(COR_TEXTO_MANUAL)
    )

    pdf.rect(
        segunda_legenda_x,
        y - 2,
        tamanho_quadrado,
        tamanho_quadrado,
        stroke=1,
        fill=1
    )

    pdf.setFillColor(
        colors.HexColor(COR_TEXTO)
    )

    pdf.drawString(
        segunda_legenda_x
        + tamanho_quadrado
        + 3,
        y,
        "Horário inserido ou alterado manualmente"
    )

    y -= 13

    # -------------------------------------------------------------------------
    # Áreas reservadas
    # -------------------------------------------------------------------------

    altura_resumo = 25 * mm
    altura_rodape = 8 * mm

    limite_inferior_tabela = (
        margem_inferior
        + altura_rodape
        + altura_resumo
        + 3 * mm
    )

    topo_tabela = y

    altura_disponivel_tabela = (
        topo_tabela
        - limite_inferior_tabela
    )

    quantidade_registros = len(
        registros
    )

    quantidade_linhas = (
        quantidade_registros + 1
    )

    altura_linha = (
        altura_disponivel_tabela
        / quantidade_linhas
    )

    # O mês normalmente terá no máximo 31 registros.
    # A fonte é reduzida proporcionalmente quando necessário.
    tamanho_fonte_corpo = min(
        7.2,
        max(
            4.2,
            altura_linha * 0.34
        )
    )

    tamanho_fonte_cabecalho = min(
        6.7,
        max(
            4.1,
            altura_linha * 0.31
        )
    )

    # -------------------------------------------------------------------------
    # Larguras das colunas
    # -------------------------------------------------------------------------

    proporcoes_colunas = [
        0.105,
        0.052,
        0.090,
        0.112,
        0.112,
        0.090,
        0.105,
        0.334
    ]

    larguras_colunas = [
        largura_util * proporcao
        for proporcao in proporcoes_colunas
    ]

    cabecalhos = [
        "Data",
        "Dia",
        "Entrada",
        "Saída Almoço",
        "Retorno Almoço",
        "Saída",
        "Saldo Dia",
        "Justificativa"
    ]

    # -------------------------------------------------------------------------
    # Cabeçalho da tabela
    # -------------------------------------------------------------------------

    linha_y = (
        topo_tabela
        - altura_linha
    )

    coluna_x = margem_horizontal

    for indice, cabecalho in enumerate(
        cabecalhos
    ):
        desenhar_celula(
            pdf,
            coluna_x,
            linha_y,
            larguras_colunas[indice],
            altura_linha,
            cabecalho,
            tamanho_fonte_cabecalho,
            COR_BRANCO,
            COR_CABECALHO,
            COR_BORDA,
            alinhamento="center",
            negrito=True,
            maximo_linhas=2
        )

        coluna_x += larguras_colunas[
            indice
        ]

    # -------------------------------------------------------------------------
    # Linhas do relatório
    # -------------------------------------------------------------------------

    for indice_registro, registro in enumerate(
        registros
    ):
        linha_y -= altura_linha

        cor_fundo_linha = (
            COR_BRANCO
            if indice_registro % 2 == 0
            else COR_FUNDO_ALTERNADO
        )

        data = formatar_valor(
            registro[0]
            if len(registro) > 0
            else ""
        )

        m1 = formatar_valor(
            registro[1]
            if len(registro) > 1
            else ""
        )

        m2 = formatar_valor(
            registro[2]
            if len(registro) > 2
            else ""
        )

        m3 = formatar_valor(
            registro[3]
            if len(registro) > 3
            else ""
        )

        m4 = formatar_valor(
            registro[4]
            if len(registro) > 4
            else ""
        )

        saldo = formatar_valor(
            registro[5]
            if len(registro) > 5
            else "",
            ""
        )

        manual = bool(
            registro[6]
            if len(registro) > 6
            else False
        )

        justificativa = formatar_valor(
            registro[7]
            if len(registro) > 7
            else "",
            ""
        )

        orig_m1 = (
            registro[8]
            if len(registro) > 8
            else ""
        )

        orig_m2 = (
            registro[9]
            if len(registro) > 9
            else ""
        )

        orig_m3 = (
            registro[10]
            if len(registro) > 10
            else ""
        )

        orig_m4 = (
            registro[11]
            if len(registro) > 11
            else ""
        )

        dia_semana = obter_dia_semana(
            data
        )

        valores = [
            data,
            dia_semana,
            m1,
            m2,
            m3,
            m4,
            saldo,
            justificativa
        ]

        originais = {
            2: orig_m1,
            3: orig_m2,
            4: orig_m3,
            5: orig_m4
        }

        coluna_x = margem_horizontal

        for indice_coluna, valor in enumerate(
            valores
        ):
            cor_fundo = cor_fundo_linha
            cor_texto = COR_TEXTO
            negrito = False
            alinhamento = "center"
            maximo_linhas = 1

            if indice_coluna in originais:
                alterado = horario_foi_alterado(
                    valor,
                    originais[indice_coluna],
                    manual
                )

                if alterado:
                    cor_fundo = COR_FUNDO_MANUAL
                    cor_texto = COR_TEXTO_MANUAL
                    negrito = True

                else:
                    cor_texto = COR_AZUL_SISTEMA

            elif indice_coluna == 6:
                minutos_saldo = saldo_para_minutos(
                    valor
                )

                if minutos_saldo > 0:
                    cor_texto = COR_VERDE
                    negrito = True

                elif minutos_saldo < 0:
                    cor_texto = COR_VERMELHO
                    negrito = True

                else:
                    cor_texto = COR_CINZA

            elif indice_coluna == 7:
                alinhamento = "left"
                maximo_linhas = 2

            desenhar_celula(
                pdf,
                coluna_x,
                linha_y,
                larguras_colunas[indice_coluna],
                altura_linha,
                valor,
                tamanho_fonte_corpo,
                cor_texto,
                cor_fundo,
                COR_BORDA,
                alinhamento=alinhamento,
                negrito=negrito,
                maximo_linhas=maximo_linhas
            )

            coluna_x += larguras_colunas[
                indice_coluna
            ]

    # -------------------------------------------------------------------------
    # Totais do período
    # -------------------------------------------------------------------------

    (
        total_positivo,
        total_negativo,
        resultado_final
    ) = calcular_totais_saldo(
        registros
    )

    y_resumo = (
        margem_inferior
        + altura_rodape
        + 2 * mm
    )

    espacamento_caixas = 3 * mm

    largura_caixa = (
        largura_util
        - 2 * espacamento_caixas
    ) / 3

    altura_caixa = 18 * mm

    desenhar_caixa_total(
        pdf,
        margem_horizontal,
        y_resumo,
        largura_caixa,
        altura_caixa,
        "Horas positivas",
        minutos_para_horas(
            total_positivo
        ),
        formatar_minutos_com_sinal(
            total_positivo
        ),
        COR_VERDE,
        COR_VERDE_CLARO
    )

    desenhar_caixa_total(
        pdf,
        margem_horizontal
        + largura_caixa
        + espacamento_caixas,
        y_resumo,
        largura_caixa,
        altura_caixa,
        "Horas negativas",
        minutos_para_horas(
            total_negativo
        ),
        formatar_minutos_com_sinal(
            total_negativo
        ),
        COR_VERMELHO,
        COR_VERMELHO_CLARO
    )

    cor_resultado = COR_CINZA
    fundo_resultado = COR_CINZA_CLARO

    if resultado_final > 0:
        cor_resultado = COR_VERDE
        fundo_resultado = COR_VERDE_CLARO

    elif resultado_final < 0:
        cor_resultado = COR_VERMELHO
        fundo_resultado = COR_VERMELHO_CLARO

    desenhar_caixa_total(
        pdf,
        margem_horizontal
        + 2 * (
            largura_caixa
            + espacamento_caixas
        ),
        y_resumo,
        largura_caixa,
        altura_caixa,
        "Resultado final",
        minutos_para_horas(
            resultado_final
        ),
        formatar_minutos_com_sinal(
            resultado_final
        ),
        cor_resultado,
        fundo_resultado
    )

    # -------------------------------------------------------------------------
    # Rodapé
    # -------------------------------------------------------------------------

    rodape_y = margem_inferior

    pdf.setStrokeColor(
        colors.HexColor(COR_BORDA)
    )

    pdf.setLineWidth(0.4)

    pdf.line(
        margem_horizontal,
        rodape_y + 6,
        largura_pagina - margem_horizontal,
        rodape_y + 6
    )

    pdf.setFont(
        "Helvetica",
        6
    )

    pdf.setFillColor(
        colors.HexColor(COR_CINZA)
    )

    pdf.drawString(
        margem_horizontal,
        rodape_y,
        "Assistente do PontoWeb MGS"
    )

    pdf.drawRightString(
        largura_pagina - margem_horizontal,
        rodape_y,
        "Página 1 de 1"
    )

    # Uma única chamada de showPage garante uma única folha.
    pdf.showPage()
    pdf.save()

    return caminho_arquivo
