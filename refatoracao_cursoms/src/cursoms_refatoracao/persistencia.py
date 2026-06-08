import sqlite3
import threading
from datetime import datetime


class HistoryRepository:
    def __init__(self, db_path):
        self.db_path = db_path
        self._lock = threading.Lock()

    def initialize(self):
        with self._lock:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS historico_modulos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome_modulo TEXT,
                        curso TEXT,
                        professor TEXT,
                        status TEXT,
                        data_hora TEXT,
                        arquivo_origem TEXT
                    )
                    """
                )
                cursor.execute("PRAGMA table_info(historico_modulos)")
                colunas = {linha[1] for linha in cursor.fetchall()}
                if "arquivo_origem" not in colunas:
                    cursor.execute("ALTER TABLE historico_modulos ADD COLUMN arquivo_origem TEXT")
                conn.commit()

    def insert_history(self, nome_modulo, curso, professor, status, arquivo_origem=""):
        with self._lock:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO historico_modulos
                    (nome_modulo, curso, professor, status, data_hora, arquivo_origem)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nome_modulo,
                        curso,
                        professor,
                        status,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        arquivo_origem,
                    ),
                )
                conn.commit()

    def fetch_recent_rows(self):
        with self._lock:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, nome_modulo, curso, status, data_hora, COALESCE(arquivo_origem, '')
                    FROM historico_modulos
                    ORDER BY id DESC
                    """
                )
                return cursor.fetchall()

    def fetch_retry_rows(self):
        with self._lock:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        nome_modulo AS "Nome do Módulo",
                        curso AS "Curso",
                        professor AS "Professor"
                    FROM historico_modulos
                    WHERE status != 'Sucesso' AND status != 'Pulado (Já Existe)'
                    """
                )
                return [dict(linha) for linha in cursor.fetchall()]
