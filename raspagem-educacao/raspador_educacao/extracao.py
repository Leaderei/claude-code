"""Extração e ranqueamento de e-mails e telefones a partir do texto dos diários.

Estratégia:
  1. Localizar no texto as janelas de contexto ao redor de menções à
     Secretaria de Educação (e sinônimos).
  2. Dentro (e ao redor) dessas janelas, capturar e-mails e telefones.
  3. Pontuar cada contato por: proximidade da palavra "educação", domínio
     governamental, e frequência. Deduplicar normalizando o valor.

Nenhuma dessas heurísticas garante que o contato seja o "oficial atual" da
secretaria — diários trazem contatos de editais, licitações, chamamentos etc.
Por isso cada contato carrega evidências (trecho + fonte) para conferência.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Optional

# --------------------------------------------------------------------------- #
# Palavras-chave que indicam a Secretaria de Educação
# --------------------------------------------------------------------------- #
TERMOS_EDUCACAO = [
    "secretaria municipal de educacao",
    "secretaria de educacao",
    "secretaria municipal da educacao",
    "sec. mun. de educacao",
    "semed",
    "smed",
    "sme ",
    "secretaria de educacao e",  # "...e Cultura", "...e Esporte" etc.
    "fundo municipal de educacao",
    "educacao",  # termo amplo — pontua menos (ver PESO_TERMOS)
]

# Peso de relevância por termo (o índice reflete a especificidade).
PESO_TERMOS = {
    "secretaria municipal de educacao": 5.0,
    "secretaria municipal da educacao": 5.0,
    "secretaria de educacao": 4.0,
    "sec. mun. de educacao": 4.0,
    "fundo municipal de educacao": 3.0,
    "semed": 3.0,
    "smed": 3.0,
    "sme ": 2.5,
    "secretaria de educacao e": 3.5,
    "educacao": 1.0,
}

# Janela (em caracteres) ao redor da menção onde procuramos contatos.
JANELA = 600

# Cabeçalho de qualquer secretaria — usado para delimitar a janela e evitar
# "vazamento" de contatos de outra pasta (ex.: Secretaria de Obras).
RE_SECRETARIA = re.compile(r"secretaria\s+(?:municipal\s+)?d[ae]\s+\w+", re.IGNORECASE)

# --------------------------------------------------------------------------- #
# Expressões regulares
# --------------------------------------------------------------------------- #
RE_EMAIL = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.IGNORECASE
)

# Telefones BR: opcional +55, DDD entre parênteses ou não, fixo (8) ou móvel (9).
RE_TELEFONE = re.compile(
    r"""
    (?<![\d./-])                       # não faz parte de um número maior
    (?:\+?55[\s.-]?)?                   # código do país opcional
    (?:\(?\d{2}\)?[\s.-]?)              # DDD
    (?:9[\s.-]?)?                       # nono dígito (celular) opcional
    \d{4}                              # primeira metade
    [\s.-]?                            # separador
    \d{4}                              # segunda metade
    (?![\d/-])
    """,
    re.VERBOSE,
)

# Rótulos que costumam anteceder telefones — usados para reduzir falso-positivo.
RE_ROTULO_TEL = re.compile(
    r"(tel|fone|telefone|contato|whats|celular)", re.IGNORECASE
)

DOMINIOS_GOV = (".gov.br", "prefeitura", "pmb", "camara", "educacao", "edu.br")

# E-mails claramente irrelevantes (fornecedores de sistema, etc.). Ajustável.
DOMINIOS_IGNORAR = (
    "example.com",
    "email.com",
    "dominio.com",
    "seudominio",
    "gmail.com.br",  # inexistente, típico de OCR ruim
)


def _sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _normalizar_telefone(bruto: str) -> Optional[str]:
    """Retorna apenas dígitos, com DDD; None se não for um telefone plausível."""
    digitos = re.sub(r"\D", "", bruto)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if len(digitos) == 10:  # fixo com DDD
        return digitos
    if len(digitos) == 11 and digitos[2] == "9":  # celular com DDD
        return digitos
    return None


def _formatar_telefone(digitos: str) -> str:
    ddd = digitos[:2]
    resto = digitos[2:]
    if len(resto) == 9:
        return f"({ddd}) {resto[:5]}-{resto[5:]}"
    return f"({ddd}) {resto[:4]}-{resto[4:]}"


@dataclass
class Evidencia:
    fonte_url: str
    data: str
    trecho: str


@dataclass
class Contato:
    """Um e-mail ou telefone extraído, com pontuação e evidências."""

    tipo: str  # "email" ou "telefone"
    valor: str  # valor normalizado/formatado
    valor_bruto: str
    score: float = 0.0
    ocorrencias: int = 0
    evidencias: list[Evidencia] = field(default_factory=list)

    @property
    def governamental(self) -> bool:
        v = self.valor.lower()
        return self.tipo == "email" and any(d in v for d in DOMINIOS_GOV)

    def mesclar(self, outro: "Contato") -> None:
        self.ocorrencias += outro.ocorrencias
        self.score += outro.score
        # Mantém no máx. 5 evidências (as de maior contexto primeiro).
        self.evidencias.extend(outro.evidencias)
        self.evidencias = self.evidencias[:5]

    def para_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "valor": self.valor,
            "score": round(self.score, 2),
            "ocorrencias": self.ocorrencias,
            "governamental": self.governamental,
            "evidencias": [
                {"fonte": e.fonte_url, "data": e.data, "trecho": e.trecho}
                for e in self.evidencias
            ],
        }


def _fronteiras_secretarias(texto_norm: str) -> list[tuple[int, int]]:
    """Posições (início, fim) de cabeçalhos de secretaria NÃO ligados à educação.

    Servem como paredes: a janela de contexto da educação não as ultrapassa,
    evitando capturar contatos de outra pasta.
    """
    fronteiras = []
    for m in RE_SECRETARIA.finditer(texto_norm):
        if "educacao" not in m.group(0):
            fronteiras.append((m.start(), m.end()))
    return fronteiras


def _janelas_educacao(texto_norm: str, texto_orig: str) -> list[tuple[int, int, float]]:
    """Retorna janelas (início, fim, peso) ao redor de menções à educação,
    limitadas pelos cabeçalhos de outras secretarias."""
    fronteiras = _fronteiras_secretarias(texto_norm)
    janelas: list[tuple[int, int, float]] = []
    for termo, peso in PESO_TERMOS.items():
        inicio = 0
        while True:
            pos = texto_norm.find(termo, inicio)
            if pos == -1:
                break
            fim_termo = pos + len(termo)
            ini = max(0, pos - JANELA)
            fim = min(len(texto_orig), fim_termo + JANELA)
            # Recua o início até a fronteira de secretaria anterior (se houver).
            for f_ini, f_fim in fronteiras:
                if f_fim <= pos:
                    ini = max(ini, f_fim)
                # Avança a fronteira seguinte para limitar o fim.
                elif f_ini >= fim_termo:
                    fim = min(fim, f_ini)
                    break
            janelas.append((ini, fim, peso))
            inicio = fim_termo
    return janelas


def _email_valido(email: str) -> bool:
    e = email.lower()
    if any(d in e for d in DOMINIOS_IGNORAR):
        return False
    # descarta capturas coladas em URLs de imagem etc.
    if e.endswith((".png", ".jpg", ".jpeg", ".gif")):
        return False
    return True


def extrair_contatos(
    texto: str,
    fonte_url: str,
    data: str,
    apenas_contexto_educacao: bool = True,
) -> list[Contato]:
    """Extrai contatos de um texto de diário.

    Se `apenas_contexto_educacao` for True, só considera contatos que apareçam
    nas janelas ao redor de menções à Secretaria de Educação (mais preciso).
    """
    if not texto:
        return []

    texto_norm = _sem_acento(texto)
    janelas = _janelas_educacao(texto_norm, texto)

    if apenas_contexto_educacao and not janelas:
        return []

    # Define os intervalos onde vamos procurar e o peso de cada posição.
    if apenas_contexto_educacao:
        intervalos = [(ini, fim, peso) for ini, fim, peso in janelas]
    else:
        intervalos = [(0, len(texto), 1.0)]

    achados: dict[tuple[str, str], Contato] = {}

    def _registrar(tipo: str, valor: str, valor_bruto: str, pos: int, peso: float):
        # trecho de evidência ao redor da posição
        ini_t = max(0, pos - 120)
        fim_t = min(len(texto), pos + 120)
        trecho = " ".join(texto[ini_t:fim_t].split())
        chave = (tipo, valor.lower())
        score = peso
        if tipo == "email" and any(d in valor.lower() for d in DOMINIOS_GOV):
            score += 3.0
        c = achados.get(chave)
        if c is None:
            achados[chave] = Contato(
                tipo=tipo,
                valor=valor,
                valor_bruto=valor_bruto,
                score=score,
                ocorrencias=1,
                evidencias=[Evidencia(fonte_url, data, trecho)],
            )
        else:
            c.ocorrencias += 1
            c.score += score
            if len(c.evidencias) < 5:
                c.evidencias.append(Evidencia(fonte_url, data, trecho))

    for ini, fim, peso in intervalos:
        bloco = texto[ini:fim]

        for m in RE_EMAIL.finditer(bloco):
            email = m.group(0).strip(".,;:)")
            if not _email_valido(email):
                continue
            _registrar("email", email.lower(), email, ini + m.start(), peso)

        for m in RE_TELEFONE.finditer(bloco):
            bruto = m.group(0)
            normalizado = _normalizar_telefone(bruto)
            if not normalizado:
                continue
            # exige rótulo próximo (Tel/Fone/...) para reduzir falso-positivo
            ini_ctx = max(0, m.start() - 25)
            if not RE_ROTULO_TEL.search(bloco[ini_ctx : m.start()]):
                # sem rótulo: só aceita se estiver muito perto da educação (peso alto)
                if peso < 3.0:
                    continue
            _registrar(
                "telefone",
                _formatar_telefone(normalizado),
                bruto,
                ini + m.start(),
                peso,
            )

    return list(achados.values())


def agregar_contatos(listas: Iterable[list[Contato]]) -> list[Contato]:
    """Deduplica e soma pontuações de contatos vindos de vários diários."""
    agregados: dict[tuple[str, str], Contato] = {}
    for lista in listas:
        for c in lista:
            chave = (c.tipo, c.valor.lower())
            existente = agregados.get(chave)
            if existente is None:
                agregados[chave] = c
            else:
                existente.mesclar(c)
    # Ordena: governamental primeiro, depois score, depois ocorrências.
    return sorted(
        agregados.values(),
        key=lambda c: (c.governamental, c.score, c.ocorrencias),
        reverse=True,
    )
