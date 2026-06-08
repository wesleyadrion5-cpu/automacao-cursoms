import os
import threading
import time
import traceback
from datetime import datetime


class ErrorLogger:
    def __init__(self, logs_dir):
        self.logs_dir = logs_dir
        self._lock = threading.Lock()

    def rotate(self, retention_days=7):
        os.makedirs(self.logs_dir, exist_ok=True)
        limite = time.time() - retention_days * 86400
        for nome in os.listdir(self.logs_dir):
            caminho = os.path.join(self.logs_dir, nome)
            if not os.path.isfile(caminho):
                continue
            try:
                if os.stat(caminho).st_mtime < limite:
                    os.remove(caminho)
            except OSError:
                continue

    def write_failure(self, local_erro, excecao):
        os.makedirs(self.logs_dir, exist_ok=True)
        nome_arquivo = f"erro_log_{datetime.now().strftime('%d-%m-%Y')}.txt"
        caminho = os.path.join(self.logs_dir, nome_arquivo)
        rastreamento = "".join(
            traceback.format_exception(type(excecao), excecao, excecao.__traceback__)
        ).strip()
        if not rastreamento:
            rastreamento = traceback.format_exc().strip()
        if not rastreamento:
            rastreamento = "Rastreamento indisponível."

        bloco = (
            f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ERRO EM: {local_erro}\n"
            f"MENSAGEM: {excecao}\n"
            f"RASTREAMENTO:\n{rastreamento}\n"
            f"{'-' * 60}\n"
        )

        with self._lock:
            with open(caminho, "a", encoding="utf-8", newline="\n") as arquivo:
                arquivo.write(bloco)
                arquivo.flush()
                try:
                    os.fsync(arquivo.fileno())
                except OSError:
                    pass
        return caminho

    def latest_log_excerpt(self, line_count=15):
        if not os.path.isdir(self.logs_dir):
            return None, ""

        candidatos = []
        for nome in os.listdir(self.logs_dir):
            if not nome.startswith("erro_log_") or not nome.endswith(".txt"):
                continue
            caminho = os.path.join(self.logs_dir, nome)
            if os.path.isfile(caminho):
                candidatos.append(caminho)

        for caminho in sorted(candidatos, key=os.path.getmtime, reverse=True):
            try:
                with open(caminho, "r", encoding="utf-8", errors="replace") as arquivo:
                    conteudo = arquivo.read().replace("\x00", "").strip()
                if not conteudo:
                    continue
                linhas = conteudo.splitlines()
                return caminho, "\n".join(linhas[-line_count:])
            except OSError:
                continue

        return None, ""
