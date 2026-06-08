import requests
import datetime
from typing import Dict, Any, Optional

SUPABASE_URL = "https://hmyohefvgezexwixfhyb.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhteW9oZWZ2Z2V6ZXh3aXhmaHliIi"
    "wicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5MTk4OTIsImV4cCI6MjA5NjQ5NTg5Mn0.Wx4pQZUZmDS7wPIaCt9oQz6jpE-kvTMPyokM3Ifhwe8"
)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def carregar_configs() -> Dict[str, str]:
    """Busca todas as configurações da tabela automator_config no Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/automator_config?select=key,value"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {item["key"]: item["value"] for item in data if "key" in item}
    except Exception as e:
        print(f"[Supabase] Erro ao carregar configurações: {e}")
    return {}

def salvar_configs(configs: Dict[str, str]) -> bool:
    """Salva todas as configurações locais no Supabase fazendo upsert."""
    url = f"{SUPABASE_URL}/rest/v1/automator_config"
    headers_upsert = HEADERS.copy()
    headers_upsert["Prefer"] = "resolution=merge-duplicates"
    
    payload = []
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for k, v in configs.items():
        payload.append({
            "key": k,
            "value": str(v),
            "updated_at": now_str
        })
        
    try:
        response = requests.post(url, headers=headers_upsert, json=payload, timeout=10)
        return response.status_code in (200, 201)
    except Exception as e:
        print(f"[Supabase] Erro ao salvar configurações: {e}")
        return False

def registrar_log(worker_id: int, modulo: str, curso: str, professor: str, status: str, detalhes: str) -> bool:
    """Insere uma linha de log na tabela automator_logs no Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/automator_logs"
    payload = {
        "worker_id": worker_id,
        "modulo": modulo,
        "curso": curso,
        "professor": professor,
        "status": status,
        "detalhes": detalhes,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        return response.status_code in (200, 201)
    except Exception as e:
        print(f"[Supabase] Erro ao registrar log: {e}")
        return False

def criar_job(nome_planilha: str, total_modulos: int) -> Optional[int]:
    """Cria uma tarefa de lote na tabela automator_jobs e retorna o id gerado."""
    url = f"{SUPABASE_URL}/rest/v1/automator_jobs"
    headers_insert = HEADERS.copy()
    headers_insert["Prefer"] = "return=representation"
    
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "nome_planilha": nome_planilha,
        "total_modulos": total_modulos,
        "modulos_concluidos": 0,
        "status": "Executando",
        "created_at": now_str,
        "updated_at": now_str
    }
    try:
        response = requests.post(url, headers=headers_insert, json=payload, timeout=10)
        if response.status_code in (200, 201):
            data = response.json()
            if data and isinstance(data, list) and "id" in data[0]:
                return int(data[0]["id"])
    except Exception as e:
        print(f"[Supabase] Erro ao criar job: {e}")
    return None

def atualizar_progresso_job(job_id: int, concluidos: int, status: str) -> bool:
    """Atualiza a quantidade de módulos concluídos e status de uma tarefa no Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/automator_jobs?id=eq.{job_id}"
    payload = {
        "modulos_concluidos": concluidos,
        "status": status,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    try:
        response = requests.patch(url, headers=HEADERS, json=payload, timeout=10)
        return response.status_code in (200, 204)
    except Exception as e:
        print(f"[Supabase] Erro ao atualizar job: {e}")
        return False
