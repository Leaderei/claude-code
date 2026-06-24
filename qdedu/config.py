"""Configuração central, lida de variáveis de ambiente (.env opcional)."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:  # carregamento opcional de .env
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv é opcional
    pass


# Termos usados para localizar a secretaria de educação no texto dos diários.
# Sintaxe de query_string do Elasticsearch (aspas = frase exata).
DEFAULT_EDU_QUERY = (
    '"secretaria municipal de educação" '
    'OR "secretaria de educação" '
    'OR "secretaria municipal de educacao" '
    'OR "secretária de educação" '
    'OR "secretário de educação"'
)


@dataclass(frozen=True)
class Settings:
    qd_api_base: str = os.getenv("QD_API_BASE", "https://api.queridodiario.ok.org.br")
    ibge_api_base: str = os.getenv(
        "IBGE_API_BASE", "https://servicodados.ibge.gov.br/api/v1"
    )
    db_path: str = os.getenv("QD_DB_PATH", "data/qdedu.sqlite")
    rate_rps: float = float(os.getenv("QD_RATE_RPS", "2.0"))
    user_agent: str = os.getenv("QD_USER_AGENT", "qdedu/0.1 (+prospeccao)")
    timeout: float = float(os.getenv("QD_HTTP_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("QD_HTTP_RETRIES", "4"))


settings = Settings()
