import json
import os
from copy import deepcopy


GROQ_ENV_VARS = ("GROQ_API_KEY", "CURSOMS_GROQ_KEY")


DEFAULT_CONFIG = {
    "antigo_url": "https://cursoms.com.br/ead/admin/principal.asp",
    "antigo_user": "",
    "antigo_pass": "",
    "novo_url": "https://novo.cursoms.com.br/login",
    "novo_user": "",
    "novo_pass": "",
    "lembrar_user": "",
    "groq_key": "",
    "match_threshold": 0.65,
    "whatsapp_number": "",
    "whatsapp_key": "",
    "theme": "dark",
    "search_method": "Ordem Exata (Linha 1 = Módulo 1)",
    "audit_mode": False,
}


def resolve_groq_key(config=None):
    config = config or {}
    for env_var in GROQ_ENV_VARS:
        value = os.getenv(env_var, "").strip()
        if value:
            return value
    return str(config.get("groq_key", "") or "").strip()


def load_config(config_path, defaults=None):
    merged = deepcopy(defaults or DEFAULT_CONFIG)
    erro = None

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as arquivo:
                loaded = json.load(arquivo)
            if not isinstance(loaded, dict):
                raise ValueError("O arquivo de configuração precisa conter um objeto JSON.")
            merged.update(loaded)
        except Exception as exc:
            erro = exc

    return merged, erro


def save_config(config_path, config):
    payload = deepcopy(config)
    with open(config_path, "w", encoding="utf-8") as arquivo:
        json.dump(payload, arquivo, indent=4, ensure_ascii=False)
