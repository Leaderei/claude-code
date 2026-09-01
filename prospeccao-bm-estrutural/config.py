# -*- coding: utf-8 -*-
"""
Configuracao da base de prospeccao — BM Estrutural (Louveira/SP).

Ajuste APENAS este arquivo para mudar recorte geografico, CNAEs ou filtros.
Nomes de municipio devem estar em CAIXA ALTA e SEM ACENTO (padrao da Receita).
"""

# ---------------------------------------------------------------------------
# 1. RECORTE GEOGRAFICO — aneis de frete a partir da fabrica em Louveira
# ---------------------------------------------------------------------------
# Laje trelicada e frete-sensivel: o anel define a prioridade comercial,
# nao apenas a distancia. Anel 1 = vendedor externo; Anel 2 = SDR + automacao.

ANEIS = {
    1: [  # 0-30 km — atuacao direta, vendedor externo ja presente
        "LOUVEIRA",
        "VINHEDO",
        "ITUPEVA",
        "JUNDIAI",
        "VALINHOS",
        "ITATIBA",
        "CABREUVA",
    ],
    2: [  # 30-60 km — SDR interno + automacao (Campinas entra aqui)
        "CAMPINAS",
        "INDAIATUBA",
        "HORTOLANDIA",
        "SUMARE",
        "MONTE MOR",
        "SALTO",
        "VARZEA PAULISTA",
        "CAMPO LIMPO PAULISTA",
        "JARINU",
        "ATIBAIA",
        "MORUNGABA",
        "BRAGANCA PAULISTA",
        "LOUVEIRA",  # duplicatas sao ignoradas
    ],
    3: [  # 60-110 km — so com validacao de frete caso a caso
        "SOROCABA",
        "PIRACICABA",
        "LIMEIRA",
        "AMERICANA",
        "SANTA BARBARA D'OESTE",
        "NOVA ODESSA",
        "RIO CLARO",
        "FRANCO DA ROCHA",
        "CAIEIRAS",
        "BARUERI",
        "SANTANA DE PARNAIBA",
        "COTIA",
    ],
}

# Ate qual anel gerar a base. Comece com 1 para o piloto, depois suba para 2.
ANEL_MAXIMO = 2

UF = "SP"

# ---------------------------------------------------------------------------
# 2. CNAEs — codigo de 7 digitos, sem pontuacao (padrao da Receita)
# ---------------------------------------------------------------------------
# Buscados tanto no CNAE principal quanto nos secundarios.
# 'peso' alimenta o lead score; 'segmento' organiza a fila do SDR.

CNAES = {
    "7112000": {"segmento": "Engenharia",   "peso": 15, "nucleo": True},
    "4399101": {"segmento": "Gestao de obras", "peso": 15, "nucleo": True},
    "4120400": {"segmento": "Construtora",  "peso": 12, "nucleo": True},
    "7111100": {"segmento": "Arquitetura",  "peso": 8,  "nucleo": True},
    # --- periferia: validar em amostra antes de liberar para o SDR ---
    "4110700": {"segmento": "Incorporadora", "peso": 4, "nucleo": False},
    "7119703": {"segmento": "Desenho tecnico", "peso": 4, "nucleo": False},
    "7119799": {"segmento": "Tecnica NE",   "peso": 2,  "nucleo": False},
    "4399103": {"segmento": "Alvenaria",    "peso": 4,  "nucleo": False},
}

# True = so CNAEs marcados como nucleo (recomendado para o piloto)
SOMENTE_NUCLEO = True

# ---------------------------------------------------------------------------
# 3. FILTROS DE QUALIFICACAO
# ---------------------------------------------------------------------------
SITUACAO_ATIVA = "02"          # 02=Ativa (01 nula, 03 suspensa, 04 inapta, 08 baixada)
IDADE_MINIMA_MESES = 24        # empresa precisa ter historico
EXCLUIR_MEI = True             # MEI de engenharia = autonomo sem obra

# O filtro que separa engenharia de casas de incorporadora de predio.
# Acima do teto: incorporadora de larga escala — negociacao por preco,
# exatamente o perfil que Ricardo descreveu como exaustivo.
CAPITAL_SOCIAL_MIN = 20_000.0
CAPITAL_SOCIAL_MAX = 5_000_000.0
# Capital 0 e comum em sociedade simples de engenharia — manter e sinalizar.
MANTER_CAPITAL_ZERO = True

# Naturezas juridicas excluidas por prefixo (1=administracao publica,
# 3=entidades sem fins lucrativos, 4=pessoa fisica/autonomo, 5=estrangeira)
PREFIXOS_NATUREZA_EXCLUIDOS = ("1", "3", "5")

# ---------------------------------------------------------------------------
# 4. ENRIQUECIMENTO DE E-MAIL -> DOMINIO
# ---------------------------------------------------------------------------
# Dominios genericos NAO indicam site proprio da empresa.
DOMINIOS_GENERICOS = {
    "gmail.com", "hotmail.com", "outlook.com", "outlook.com.br", "yahoo.com",
    "yahoo.com.br", "uol.com.br", "bol.com.br", "terra.com.br", "ig.com.br",
    "live.com", "msn.com", "globo.com", "icloud.com", "me.com", "aol.com",
    "zipmail.com.br", "oi.com.br", "r7.com", "protonmail.com", "gmail.com.br",
    "hotmail.com.br", "superig.com.br", "click21.com.br", "itelefonica.com.br",
}

# ---------------------------------------------------------------------------
# 5. FONTE
# ---------------------------------------------------------------------------
BASE_URL = "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj"
