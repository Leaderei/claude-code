"""Identificação do(a) Secretário(a) Municipal de Educação a partir dos diários.

Ideia central: os Diários Oficiais publicam os **atos de pessoal** — nomeação,
designação e exoneração — para os cargos em comissão, inclusive o de
Secretário(a) Municipal de Educação. Reunindo esses atos numa linha do tempo,
o titular ATUAL é a pessoa da nomeação/designação mais recente que não teve
uma exoneração posterior.

Cada resultado carrega a evidência (trecho + URL + data do diário), então é
sempre auditável — importante porque a extração de nomes por regex é heurística.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .extracao import _sem_acento
from .extracao import Contato

# --------------------------------------------------------------------------- #
# Padrões
# --------------------------------------------------------------------------- #
# O cargo do(a) secretário(a) de educação (aceita "secretario/a", "de/da educação").
RE_CARGO = re.compile(
    r"secret[aá]ri[oa]\s+(?:municipal\s+)?(?:adjunt[oa]\s+)?(?:d[ae]\s+)?educa[cç][aã]o",
    re.IGNORECASE,
)

# Verbos de ato de pessoal.
RE_ACAO = re.compile(
    r"\b(nome(?:ar|ia|iar|ado|ada|a[cç][aã]o)"
    r"|design(?:ar|a|ado|ada|a[cç][aã]o)"
    r"|exoner(?:ar|a|ado|ada|a[cç][aã]o))\b",
    re.IGNORECASE,
)

# Nome próprio: sequência de palavras Title-case ou CAIXA-ALTA, com conectores.
RE_NOME = re.compile(
    r"(?:[A-ZÀ-Ý][a-zà-ÿ']+|[A-ZÀ-Ý]{2,})"
    r"(?:\s+(?:d[aeo]s?|e|[A-ZÀ-Ý][a-zà-ÿ']+|[A-ZÀ-Ý]{2,})){1,5}"
)

CONECTORES = {"de", "da", "do", "das", "dos", "e"}

# Tokens que denunciam que a captura NÃO é um nome de pessoa.
STOP_NOME = {
    "secretaria", "secretario", "secretaria", "municipal", "educacao",
    "prefeitura", "prefeito", "prefeita", "gabinete", "decreto", "portaria",
    "estado", "comissao", "cargo", "art", "lei", "nomear", "exonerar",
    "designar", "fica", "senhor", "senhora", "para", "exercer", "publico",
    "poder", "executivo", "camara", "governo", "diario", "oficial", "resolve",
    "considerando", "servidor", "servidora", "seguinte", "adjunto", "adjunta",
    "funcao", "efeito", "resolucao", "anexo", "tabela",
    "sr", "sra", "srs", "nomeada", "nomeado", "nomeia", "exonerada",
    "exonerado", "designar", "designado", "designada", "designa",
}

# Janela ao redor da menção ao cargo onde buscamos o verbo e o nome.
JANELA_ATO = 280

TIPOS_ORDEM = {"nomeacao": 3, "designacao": 2, "exoneracao": 1}


def _classificar(verbo: str) -> str:
    v = _sem_acento(verbo)
    if v.startswith("nome"):
        return "nomeacao"
    if v.startswith("design"):
        return "designacao"
    return "exoneracao"


def _nome_valido(nome: str) -> bool:
    tokens = [t for t in nome.split() if t]
    significativos = [t for t in tokens if _sem_acento(t) not in CONECTORES]
    if len(significativos) < 2:  # exige nome + sobrenome
        return False
    for t in tokens:
        if _sem_acento(t.strip(".,;:")) in STOP_NOME:
            return False
    # comprimento alfabético mínimo
    if sum(len(t) for t in significativos) < 6:
        return False
    return True


def _apara(token: str) -> str:
    return _sem_acento(token.strip(".,;:()"))


def _limpar_nome(bruto: str) -> str:
    """Apara conectores e tokens de parada (verbos, títulos) das pontas.

    Ex.: "NOMEAR MARIA DA SILVA e" -> "MARIA DA SILVA".
    Tokens de parada no MEIO não são removidos (mantêm o nome inválido, para
    que seja descartado por _nome_valido).
    """
    tokens = bruto.split()
    descartaveis = CONECTORES | STOP_NOME
    while tokens and _apara(tokens[-1]) in descartaveis:
        tokens.pop()
    while tokens and _apara(tokens[0]) in descartaveis:
        tokens.pop(0)
    return " ".join(tokens).strip(" ,.;:")


@dataclass
class AtoSecretario:
    nome: str
    tipo: str  # nomeacao | designacao | exoneracao
    data: str  # AAAA-MM-DD (data do diário)
    fonte_url: str
    trecho: str


@dataclass
class Secretario:
    nome: str
    cargo: str
    situacao: str  # tipo do ato que o(a) colocou no cargo
    desde: str  # data do ato
    fonte_url: str
    trecho: str
    confianca: str  # alta | media | baixa
    email: Optional[str] = None
    telefone: Optional[str] = None
    origem_contato: Optional[str] = None  # como o contato foi associado
    historico: list[AtoSecretario] = field(default_factory=list)

    def para_dict(self) -> dict:
        return {
            "nome": self.nome,
            "cargo": self.cargo,
            "situacao": self.situacao,
            "desde": self.desde,
            "confianca": self.confianca,
            "email": self.email,
            "telefone": self.telefone,
            "origem_contato": self.origem_contato,
            "fonte": self.fonte_url,
            "trecho": self.trecho,
            "historico": [
                {"nome": a.nome, "tipo": a.tipo, "data": a.data, "fonte": a.fonte_url}
                for a in self.historico
            ],
        }


def extrair_atos(texto: str, fonte_url: str, data: str) -> list[AtoSecretario]:
    """Extrai atos de pessoal ligados ao cargo de Secretário(a) de Educação."""
    if not texto:
        return []
    atos: list[AtoSecretario] = []
    for m_cargo in RE_CARGO.finditer(texto):
        ini = max(0, m_cargo.start() - JANELA_ATO)
        fim = min(len(texto), m_cargo.end() + JANELA_ATO)
        janela = texto[ini:fim]

        m_acao = RE_ACAO.search(janela)
        if not m_acao:
            continue
        tipo = _classificar(m_acao.group(0))
        verbo_pos = m_acao.start()

        # candidatos a nome na janela; escolhe o mais próximo do verbo.
        melhor = None
        melhor_dist = 10 ** 9
        for m_nome in RE_NOME.finditer(janela):
            nome = _limpar_nome(m_nome.group(0))
            if not _nome_valido(nome):
                continue
            # distância do início do nome ao fim do verbo (nome costuma vir após)
            dist = abs(m_nome.start() - m_acao.end())
            if dist < melhor_dist:
                melhor_dist = dist
                melhor = nome
        if not melhor:
            continue

        trecho = " ".join(janela.split())
        atos.append(
            AtoSecretario(
                nome=melhor,
                tipo=tipo,
                data=data,
                fonte_url=fonte_url,
                trecho=trecho[:400],
            )
        )
    return atos


def _mesma_pessoa(a: str, b: str) -> bool:
    ta = {t for t in _sem_acento(a).split() if t not in CONECTORES}
    tb = {t for t in _sem_acento(b).split() if t not in CONECTORES}
    if not ta or not tb:
        return False
    comuns = ta & tb
    # considera a mesma pessoa se compartilham >=2 tokens ou 60% do menor nome
    return len(comuns) >= 2 or len(comuns) >= 0.6 * min(len(ta), len(tb))


def consolidar_secretario(atos: Iterable[AtoSecretario]) -> Optional[Secretario]:
    """A partir dos atos, determina o(a) titular atual do cargo."""
    lista = [a for a in atos if a.nome]
    if not lista:
        return None

    # ordena por (data, especificidade do ato) — datas vazias vão para o fim.
    def chave(a: AtoSecretario):
        return (a.data or "0000-00-00", TIPOS_ORDEM.get(a.tipo, 0))

    lista.sort(key=chave)

    atual: Optional[AtoSecretario] = None
    for a in lista:
        if a.tipo in ("nomeacao", "designacao"):
            atual = a
        elif a.tipo == "exoneracao":
            if atual and _mesma_pessoa(atual.nome, a.nome):
                atual = None
    if atual is None:
        # ninguém "ativo": devolve a nomeação/designação mais recente como pista
        candidatos = [a for a in lista if a.tipo in ("nomeacao", "designacao")]
        if not candidatos:
            return None
        atual = candidatos[-1]
        confianca = "baixa"
    else:
        # confiança maior para nomeação recente com data conhecida
        confianca = "alta" if atual.tipo == "nomeacao" and atual.data else "media"

    historico = [a for a in lista if _mesma_pessoa(a.nome, atual.nome)]
    return Secretario(
        nome=atual.nome,
        cargo="Secretário(a) Municipal de Educação",
        situacao=atual.tipo,
        desde=atual.data,
        fonte_url=atual.fonte_url,
        trecho=atual.trecho,
        confianca=confianca,
        historico=historico,
    )


def associar_contato(secretario: Secretario, contatos: list[Contato]) -> None:
    """Associa e-mail/telefone ao secretário.

    Preferência para e-mail cujo usuário (parte antes do @) contenha um token do
    nome (provável e-mail pessoal); caso contrário, usa o melhor contato
    institucional já extraído. Preenche `email`, `telefone` e `origem_contato`.
    """
    emails = [c for c in contatos if c.tipo == "email"]
    tels = [c for c in contatos if c.tipo == "telefone"]
    tokens = [t for t in _sem_acento(secretario.nome).split() if t not in CONECTORES and len(t) >= 3]

    email_pessoal = None
    for c in emails:
        local = _sem_acento(c.valor.split("@", 1)[0])
        if any(t in local for t in tokens):
            email_pessoal = c
            break

    if email_pessoal:
        secretario.email = email_pessoal.valor
        secretario.origem_contato = "email provável pessoal (nome no usuário)"
    elif emails:
        secretario.email = emails[0].valor
        secretario.origem_contato = "e-mail institucional da secretaria"

    if tels:
        secretario.telefone = tels[0].valor
        if secretario.origem_contato is None:
            secretario.origem_contato = "telefone institucional da secretaria"
