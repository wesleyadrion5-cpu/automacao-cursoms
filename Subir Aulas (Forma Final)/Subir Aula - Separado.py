# * =============================================================================
# * ISAURA - TITANIUM CORE (THE LIVEWIRE WHISPERER)
# * =============================================================================

import csv
import difflib
import json
import logging
import os
import queue
import re
import socket
import sys
import threading
import time
import tkinter as tk
import traceback
import unicodedata
import winsound
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Optional
from urllib.parse import quote, urljoin

import customtkinter as ctk
import keyboard
import matplotlib.pyplot as plt
import pandas as pd
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string
from groq import Groq
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)  # pasta pai: Subir Aula CursoMS
CONFIG_PATH = os.path.join(PARENT_DIR, "config_unificada.json")
LOGS_DIR = os.path.join(PARENT_DIR, "logs")
DIAGNOSTICS_DIR = os.path.join(PARENT_DIR, "logs", "diagnosticos")
DB_PATH = os.path.join(PARENT_DIR, "banco_frota.db")
REFATORACAO_SRC_DIR = os.path.join(BASE_DIR, "refatoracao_cursoms", "src")
if os.path.isdir(REFATORACAO_SRC_DIR) and REFATORACAO_SRC_DIR not in sys.path:
    sys.path.insert(0, REFATORACAO_SRC_DIR)

try:
    from cursoms_refatoracao.configuracao import (
        DEFAULT_CONFIG,
        load_config,
        resolve_groq_key,
        save_config,
    )
    from cursoms_refatoracao.diagnosticos import ErrorLogger
    from cursoms_refatoracao.matching import (
        is_plano_estudos_module,
        module_match_score,
        module_names_equivalent,
        normalize_text,
    )
    from cursoms_refatoracao.persistencia import HistoryRepository
    from cursoms_refatoracao.planilhas import load_excel_records
    from cursoms_refatoracao.regras_especiais import resolve_video_payload
    from cursoms_refatoracao.seletores import SELECTORS
    from cursoms_refatoracao.selenium_utils import (
        build_chrome_options_accepting_old_certificates,
        bypass_chrome_certificate_warning,
        clear_and_type,
        close_extra_windows,
        navigate_with_certificate_bypass,
        open_new_tab,
        safe_switch_to_window,
        session_is_active,
    )
except Exception:
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

    class _FallbackVideoPayload:
        def __init__(self, titulo, canal, valor, origem):
            self.titulo = titulo
            self.canal = canal
            self.valor = valor
            self.origem = origem

    def normalize_text(text):
        texto = "".join(
            c
            for c in unicodedata.normalize("NFD", str(text or ""))
            if unicodedata.category(c) != "Mn"
        )
        texto = re.sub(r"[^a-z0-9\s]", " ", texto.lower())
        return " ".join(texto.split())

    def is_plano_estudos_module(name):
        texto = normalize_text(name)
        return bool(texto and "plano" in texto and "estud" in texto)

    def module_names_equivalent(name_a, name_b, minimum_ratio=0.92):
        a = normalize_text(name_a)
        b = normalize_text(name_b)
        if not a or not b:
            return False
        if a == b or a in b or b in a:
            return True
        return difflib.SequenceMatcher(None, a, b).ratio() >= minimum_ratio

    def module_match_score(target_name, candidate_name, candidate_teacher=""):
        target = normalize_text(target_name)
        candidate = normalize_text(candidate_name)
        if not target or not candidate:
            return 0.0
        score = difflib.SequenceMatcher(None, target, candidate).ratio()
        if candidate_teacher and "professor" in normalize_text(candidate_teacher):
            score += 0.01
        return min(score, 1.0)

    def resolve_video_payload(module_name, title="", vimeo="", youtube_link="", canal=""):
        clean_vimeo = re.sub(r"\s+", "", str(vimeo or ""))
        clean_youtube = (youtube_link or "").strip()
        if is_plano_estudos_module(module_name):
            return _FallbackVideoPayload(
                "Acesse seu Material", "vimeo", "1173006649", "regra_especial_plano_estudos"
            )
        if clean_vimeo.isdigit():
            return _FallbackVideoPayload(title, "vimeo", clean_vimeo, "vimeo")
        if clean_youtube:
            return _FallbackVideoPayload(title, "youtube", clean_youtube, "youtube")
        return None

    class _FallbackSelectors:
        modules_search_css = 'input[wire\\:model\\.debounce\\.500ms="search"]'
        module_name_css = 'input[wire\\:model="module.name"]'
        module_time_css = 'input[wire\\:model="module.time"]'
        searchable_term_css = 'input[wire\\:model\\.debounce\\.1500ms="searchTerm"]'
        attachment_file_css = 'input[wire\\:model="attachment.filename"]'
        attachment_name_css = 'input[wire\\:model="attachment.name"]'
        attachment_type_css = 'select[wire\\:model="attachment.type"]'
        attachment_attachable_css = 'select[wire\\:model="attachment.attachable_type"]'
        old_video_title_name = "assunto"
        old_video_link_name = "link"
        old_video_channel_name = "ativavimeo"
        old_video_vimeo_name = "vimeo"

    SELECTORS = _FallbackSelectors()

    def resolve_groq_key(config=None):
        config = config or {}
        return str(config.get("groq_key", "") or "").strip()

    def load_config(config_path, defaults=None):
        config = dict(defaults or DEFAULT_CONFIG)
        erro = None
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as arquivo:
                    carregado = json.load(arquivo)
                if isinstance(carregado, dict):
                    config.update(carregado)
            except Exception as exc:
                erro = exc
        return config, erro

    def save_config(config_path, config):
        with open(config_path, "w", encoding="utf-8") as arquivo:
            json.dump(config, arquivo, indent=4, ensure_ascii=False)

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
            caminho = os.path.join(
                self.logs_dir, f"erro_log_{datetime.now().strftime('%d-%m-%Y')}.txt"
            )
            rastreamento = "".join(
                traceback.format_exception(type(excecao), excecao, excecao.__traceback__)
            )
            with self._lock:
                with open(caminho, "a", encoding="utf-8", newline="\n") as arquivo:
                    arquivo.write(
                        f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ERRO EM: {local_erro}\n"
                        f"MENSAGEM: {excecao}\n"
                        f"RASTREAMENTO:\n{rastreamento}\n"
                        f"{'-' * 60}\n"
                    )
            return caminho

        def latest_log_excerpt(self, line_count=15):
            if not os.path.isdir(self.logs_dir):
                return None, ""
            candidatos = [
                os.path.join(self.logs_dir, nome)
                for nome in os.listdir(self.logs_dir)
                if nome.startswith("erro_log_") and nome.endswith(".txt")
            ]
            for caminho in sorted(candidatos, key=os.path.getmtime, reverse=True):
                try:
                    with open(caminho, "r", encoding="utf-8", errors="replace") as arquivo:
                        conteudo = arquivo.read().replace("\x00", "").strip()
                    if conteudo:
                        linhas = conteudo.splitlines()
                        return caminho, "\n".join(linhas[-line_count:])
                except OSError:
                    continue
            return None, ""

    class HistoryRepository:
        def __init__(self, db_path):
            self.db_path = db_path
            self._lock = threading.Lock()

        def initialize(self):
            import sqlite3

            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "CREATE TABLE IF NOT EXISTS historico_modulos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_modulo TEXT, curso TEXT, professor TEXT, status TEXT, data_hora TEXT, arquivo_origem TEXT)"
                    )
                    cursor.execute("PRAGMA table_info(historico_modulos)")
                    colunas = {linha[1] for linha in cursor.fetchall()}
                    if "arquivo_origem" not in colunas:
                        cursor.execute(
                            "ALTER TABLE historico_modulos ADD COLUMN arquivo_origem TEXT"
                        )
                    conn.commit()

        def insert_history(self, nome_modulo, curso, professor, status, arquivo_origem=""):
            import sqlite3

            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO historico_modulos (nome_modulo, curso, professor, status, data_hora, arquivo_origem) VALUES (?, ?, ?, ?, ?, ?)",
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
            import sqlite3

            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, nome_modulo, curso, status, data_hora, COALESCE(arquivo_origem, '') FROM historico_modulos ORDER BY id DESC"
                    )
                    return cursor.fetchall()

        def fetch_retry_rows(self):
            import sqlite3

            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT nome_modulo AS 'Nome do Módulo', curso AS 'Curso', professor AS 'Professor' FROM historico_modulos WHERE status != 'Sucesso' AND status != 'Pulado (Já Existe)'"
                    )
                    return [dict(linha) for linha in cursor.fetchall()]

    def load_excel_records(path):
        df = pd.read_excel(path)
        df.columns = df.columns.astype(str).map(normalize_text)
        if df.empty:
            raise ValueError(f"A planilha '{os.path.basename(path)}' está vazia.")
        if not set(df.columns).intersection({"nome do modulo", "nome do módulo", "modulo", "módulo"}):
            raise ValueError(
                f"A planilha '{os.path.basename(path)}' não possui coluna de módulo."
            )
        registros = df.to_dict("records")
        return {"nome": os.path.basename(path), "dados": registros, "total": len(registros)}

    def session_is_active(driver):
        try:
            return bool(driver and driver.session_id and driver.window_handles)
        except Exception:
            return False

    def safe_switch_to_window(driver, handle, context):
        if not session_is_active(driver):
            raise RuntimeError(f"Sessão do navegador indisponível ao tentar acessar {context}.")
        handles = list(driver.window_handles)
        if handle not in handles:
            raise RuntimeError(
                f"Janela indisponível ao tentar acessar {context}. Handles atuais: {len(handles)}"
            )
        driver.switch_to.window(handle)
        return handle

    def build_chrome_options_accepting_old_certificates():
        options = webdriver.ChromeOptions()
        options.set_capability("acceptInsecureCerts", True)
        try:
            options.accept_insecure_certs = True
        except Exception:
            pass
        for argumento in [
            "--ignore-certificate-errors",
            "--ignore-ssl-errors=yes",
            "--allow-insecure-localhost",
        ]:
            options.add_argument(argumento)
        return options

    def _chrome_certificate_warning_visible(driver):
        try:
            if not session_is_active(driver):
                return False
            url_atual = (driver.current_url or "").lower()
            titulo = (driver.title or "").lower()
        except Exception:
            return False

        if url_atual.startswith("chrome-error://"):
            return True
        if "erro de privacidade" in titulo or "privacy error" in titulo:
            return True

        try:
            return bool(
                driver.execute_script(
                    """
                    const texto = (document.body && document.body.innerText || '').toLowerCase();
                    return Boolean(
                        document.querySelector('#details-button, #proceed-link') ||
                        texto.includes('err_cert') ||
                        texto.includes('sua conexão não é particular') ||
                        texto.includes('sua conexao nao e particular') ||
                        texto.includes('your connection is not private')
                    );
                    """
                )
            )
        except Exception:
            return False

    def bypass_chrome_certificate_warning(driver, context="", timeout=4):
        fim = time.time() + timeout
        tentou_bypass = False

        while time.time() < fim:
            if not _chrome_certificate_warning_visible(driver):
                return tentou_bypass

            acao = ""
            try:
                acao = str(
                    driver.execute_script(
                        """
                        const visivel = (el) => Boolean(
                            el && !el.disabled &&
                            window.getComputedStyle(el).display !== 'none' &&
                            window.getComputedStyle(el).visibility !== 'hidden'
                        );
                        const proceed = document.querySelector('#proceed-link');
                        if (visivel(proceed)) {
                            proceed.click();
                            return 'proceed';
                        }
                        const details = document.querySelector('#details-button');
                        if (visivel(details)) {
                            details.click();
                            return 'advanced';
                        }
                        return '';
                        """
                    )
                    or ""
                )
            except Exception:
                acao = ""

            if acao == "advanced":
                tentou_bypass = True
                time.sleep(0.4)
                continue
            if acao == "proceed":
                tentou_bypass = True
                time.sleep(1.0)
                continue

            try:
                driver.find_element(By.TAG_NAME, "body").send_keys("thisisunsafe")
                tentou_bypass = True
                time.sleep(1.0)
            except Exception:
                time.sleep(0.25)

        return tentou_bypass and not _chrome_certificate_warning_visible(driver)

    def navigate_with_certificate_bypass(driver, url, context="", timeout=4):
        driver.get(url)
        return bypass_chrome_certificate_warning(driver, context, timeout=timeout)

    def open_new_tab(driver, url, context, timeout=10):
        anteriores = set(driver.window_handles)
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        WebDriverWait(driver, timeout).until(lambda d: len(d.window_handles) > len(anteriores))
        novos = list(set(driver.window_handles) - anteriores)
        if not novos:
            raise RuntimeError(f"Não foi possível abrir nova aba para {context}.")
        novo_handle = novos[0]
        safe_switch_to_window(driver, novo_handle, context)
        return novo_handle

    def close_extra_windows(driver, keep_handles, context):
        for handle in list(driver.window_handles):
            if handle in keep_handles:
                continue
            safe_switch_to_window(driver, handle, context)
            driver.close()
        if keep_handles:
            safe_switch_to_window(driver, next(iter(keep_handles)), context)

    def clear_and_type(elemento, valor, delay_between_chars=0.0):
        elemento.click()
        elemento.send_keys(Keys.CONTROL + "a")
        elemento.send_keys(Keys.DELETE)
        if delay_between_chars <= 0:
            elemento.send_keys("" if valor is None else str(valor))
            return
        for char in str(valor or ""):
            elemento.send_keys(char)

DEFAULT_CONFIG = {
    **DEFAULT_CONFIG,
    "upload_mode": "completo",
    "module_scope": "todos",
    "single_module_target": "",
}


def extract_module_name_from_row(row):
    return str(
        row.get(
            "nome do mÃ³dulo",
            row.get("nome do modulo", row.get("modulo", row.get("mÃ³dulo", ""))),
        )
        or ""
    ).strip()


def build_module_name_variants(text):
    bruto = str(text or "").strip()
    if not bruto:
        return set()

    candidatos = {bruto}
    sem_indice = re.sub(r"^\s*\d+\s*[\.\-\)]\s*", "", bruto).strip()
    if sem_indice:
        candidatos.add(sem_indice)

    sem_prefixo_parenteses = re.sub(r"^\s*\([^)]*\)\s*", "", sem_indice or bruto).strip()
    if sem_prefixo_parenteses:
        candidatos.add(sem_prefixo_parenteses)

    sem_parenteses = re.sub(r"\([^)]*\)", " ", bruto)
    sem_parenteses = re.sub(r"\s+", " ", sem_parenteses).strip()
    if sem_parenteses:
        candidatos.add(sem_parenteses)

    sem_indice_e_parenteses = re.sub(r"\([^)]*\)", " ", sem_indice or bruto)
    sem_indice_e_parenteses = re.sub(r"\s+", " ", sem_indice_e_parenteses).strip()
    if sem_indice_e_parenteses:
        candidatos.add(sem_indice_e_parenteses)

    return {normalize_text(valor) for valor in candidatos if normalize_text(valor)}


NOVO_MODULES_URL = "https://novo.cursoms.com.br/modules"
NOVO_MODULE_CREATE_URL = "https://novo.cursoms.com.br/modules/create"
NOVO_MODULE_SEARCH_XPATH = "//input[@type='text' and contains(@class, 'form-control')]"
NOVO_MODULE_NAME_XPATH = "//input[@*[name()='wire:model']='module.name']"
NOVO_MODULE_TIME_XPATH = "//input[@*[name()='wire:model']='module.time']"
NOVO_LESSONS_LINK_XPATH = ".//a[contains(@href, '/lessons/')]"

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

# * =======================================================
# * CHAVES E CONFIGURAÇÕES VISUAIS GLOBAIS
# * =======================================================
CHAVE_GROQ = ""

BG_WINDOW = "#0F1216"
BG_CARD = "#1E293B"
BG_INPUT = "#111827"
BORDER_COLOR = "#334155"
VERDE_ACAO = "#00A36C"
VERDE_HOVER = "#059669"
TEXT_LIGHT = "#FFFFFF"
TEXT_MUTED = "#94A3B8"
AZUL_PASSO = "#2D68FF"
VERMELHO_PARAR = "#D33F49"
ROXO_IA = "#8B5CF6"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# * =========================================================================
# * MINI SERVIDOR WEB PARA O TELEMÓVEL (FLASK)
# * =========================================================================
app_flask = Flask(__name__)
motor_global = None

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Isaura - Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background-color: #0F1216; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 20px; }
        .card { background-color: #1E293B; border-radius: 15px; padding: 20px; margin: 15px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h1 { color: #2D68FF; margin-bottom: 5px; }
        h2 { font-size: 40px; margin: 10px 0; }
        .success { color: #00A36C; } .error { color: #D33F49; } .warning { color: #F59E0B; }
        .progresso-bg { background-color: #111827; border-radius: 10px; height: 25px; width: 100%; overflow: hidden; margin-top: 20px;}
        .progresso-bar { background-color: #2D68FF; height: 100%; width: 0%; transition: width 0.5s; }
        .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-top: 10px;}
        .running { background-color: #00A36C; color: white; } .stopped { background-color: #475569; color: white; }
    </style>
</head>
<body>
    <h1>🪢 Isaura Enterprise</h1>
    <p>Monitorização em Tempo Real</p>
    
    <div class="card">
        <div id="status_badge" class="status-badge stopped">PARADO</div>
        <h3 style="margin-top:20px; color:#94A3B8;">Progresso Global</h3>
        <h2><span id="concluidos">0</span> / <span id="total">0</span></h2>
        <div class="progresso-bg"><div id="barra" class="progresso-bar"></div></div>
    </div>

    <div style="display: flex; justify-content: space-between; gap: 10px;">
        <div class="card" style="flex: 1;">
            <h4 style="margin:0; color:#94A3B8;">Sucesso</h4>
            <h2 class="success" id="sucesso">0</h2>
        </div>
        <div class="card" style="flex: 1;">
            <h4 style="margin:0; color:#94A3B8;">Erros</h4>
            <h2 class="error" id="erro">0</h2>
        </div>
        <div class="card" style="flex: 1;">
            <h4 style="margin:0; color:#94A3B8;">Avisos</h4>
            <h2 class="warning" id="aviso">0</h2>
        </div>
    </div>

    <script>
        setInterval(() => {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('sucesso').innerText = data.sucesso;
                    document.getElementById('erro').innerText = data.erro;
                    document.getElementById('aviso').innerText = data.aviso;
                    document.getElementById('concluidos').innerText = data.concluidos;
                    document.getElementById('total').innerText = data.total;
                    
                    let pct = data.total > 0 ? (data.concluidos / data.total) * 100 : 0;
                    document.getElementById('barra').style.width = pct + '%';
                    
                    let badge = document.getElementById('status_badge');
                    if(data.is_running) { badge.className = 'status-badge running'; badge.innerText = 'EM OPERAÇÃO'; }
                    else { badge.className = 'status-badge stopped'; badge.innerText = 'AGUARDANDO'; }
                });
        }, 2000);
    </script>
</body>
</html>
"""


@app_flask.route("/")
def index():
    return render_template_string(HTML_DASHBOARD)


@app_flask.route("/api/stats")
def stats():
    global motor_global
    if motor_global:
        return jsonify(
            {
                "sucesso": motor_global.stats_contagem["Sucesso"],
                "erro": motor_global.stats_contagem["Erro"],
                "aviso": motor_global.stats_contagem["Aviso"],
                "concluidos": motor_global.modulos_concluidos,
                "total": motor_global.total_modulos,
                "is_running": motor_global.is_running,
            }
        )
    return jsonify(
        {"sucesso": 0, "erro": 0, "aviso": 0, "concluidos": 0, "total": 0, "is_running": False}
    )


def start_flask_server():
    try:
        app_flask.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except:
        pass


# * =========================================================================
# * CLASSE DOS OPERÁRIOS DA FROTA
# * =========================================================================
class FrotaWorker(threading.Thread):
    def __init__(self, motor, worker_id, chunk_excel, nome_arquivo):
        super().__init__()
        self.motor = motor
        self.worker_id = worker_id
        self.chunk_excel = chunk_excel
        self.nome_arquivo = nome_arquivo
        self._driver: Optional[WebDriver] = None
        self.aba_antiga: Optional[str] = None
        self.aba_nova: Optional[str] = None
        self.fila_videos = []
        self.fila_arquivos = []
        self.ordem_atual = 1
        self.cache_modulos_visiveis = []

    @property
    def driver(self) -> WebDriver:
        if self._driver is None:
            raise RuntimeError("WebDriver not initialized")
        return self._driver

    def _iniciar_driver_e_logins(self):
        self._driver = webdriver.Chrome(  # type: ignore[reportCallIssue]
            service=Service(ChromeDriverManager().install()),
            options=build_chrome_options_accepting_old_certificates(),
        )
        self.driver.maximize_window()
        wait = WebDriverWait(self.driver, 15)

        self._abrir_url_com_certificado(
            self.motor.config.get(
                "antigo_url", "https://cursoms.com.br/ead/admin/principal.asp"
            ),
            "login do site antigo",
        )
        wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao"))).send_keys(
            self.motor.config.get("antigo_user", "")
        )
        self.driver.find_element(By.NAME, "senhadagestao").send_keys(
            self.motor.config.get("antigo_pass", "")
        )
        self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
        self.aba_antiga = self.driver.current_window_handle

        self.aba_nova = open_new_tab(
            self.driver,
            self.motor.config.get("novo_url", "https://novo.cursoms.com.br/login"),
            "login do site novo",
        )
        self._trocar_para_janela_segura(self.aba_nova, "login do site novo")
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(
            self.motor.config.get("novo_user", "")
        )
        pwd = self.driver.find_element(By.NAME, "password")
        pwd.send_keys(self.motor.config.get("novo_pass", ""))
        pwd.send_keys(Keys.ENTER)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1.5)

    def _reiniciar_sessao_chrome(self):
        try:
            if self._driver:
                self._driver.quit()
        except Exception:
            pass
        self._driver = None
        self._iniciar_driver_e_logins()

    def log(self, tipo, msg):
        self.motor.log(tipo, f"[Robô {self.worker_id}] {msg}")

    def calcular_similaridade(self, nome_excel, nome_site):
        n_exc = normalize_text(nome_excel)
        n_site = normalize_text(nome_site)
        n_exc = re.sub(r"\(pacatuba/ce\)", "", n_exc)
        n_exc = re.sub(r"\([^)]+\)$", "", n_exc).strip()
        n_site = re.sub(r"^-\s*", "", n_site)
        n_site = re.sub(r"^\d+[\.\-]\s*", "", n_site).strip()
        str_exc = re.sub(r"[^a-z0-9]", "", n_exc)
        str_site = re.sub(r"[^a-z0-9]", "", n_site)
        if not str_exc or not str_site:
            return 0.0
        if str_site in str_exc or str_exc in str_site:
            return 1.0
        if len(str_site) > 15 and len(str_exc) > 15 and str_site[:15] == str_exc[:15]:
            return 0.95
        set_exc = set(re.sub(r"[^a-z0-9\s]", " ", n_exc).split())
        set_site = set(re.sub(r"[^a-z0-9\s]", " ", n_site).split())
        stopwords = {"de", "da", "do", "e", "a", "o", "em", "nas", "nos", "para", "com", "no"}
        if (set_site - stopwords) and (set_site - stopwords).issubset(set_exc):
            return 0.90
        return max(
            difflib.SequenceMatcher(None, str_exc, str_site).ratio(),
            module_match_score(nome_excel, nome_site),
        )

    def preencher_input(self, elemento, valor):
        try:
            clear_and_type(elemento, valor)
            return True
        except Exception as exc:
            self.log("INFO", f"Falha ao preencher campo rapidamente: {str(exc)[:80]}")
            return False

    def preencher_input_humano(self, elemento, valor):
        try:
            self._tentar_recuperar_overlay_500("antes de preencher campo")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
            WebDriverWait(self.driver, 5).until(lambda d: elemento.is_displayed() and elemento.is_enabled())
            clear_and_type(elemento, valor, delay_between_chars=0.02)
            return True
        except Exception as exc:
            self.log("INFO", f"Falha ao preencher campo lentamente: {str(exc)[:80]}")
            return False

    def _overlay_500_visivel(self):
        if not self._sessao_ativa():
            return False
        xpaths = [
            "//*[contains(translate(normalize-space(.), 'server error', 'SERVER ERROR'), 'SERVER ERROR') and contains(normalize-space(.), '500')]",
            "//*[contains(translate(normalize-space(.), 'server error', 'SERVER ERROR'), 'SERVER ERROR')]",
        ]
        for xpath in xpaths:
            try:
                for elemento in self.driver.find_elements(By.XPATH, xpath):
                    if elemento.is_displayed():
                        return True
            except Exception:
                continue
        return False

    def _clicar_em_ponto_da_tela(self, x, y):
        try:
            return bool(
                self.driver.execute_script(
                    """
                    const x = arguments[0];
                    const y = arguments[1];
                    const alvo = document.elementFromPoint(x, y);
                    if (!alvo) return false;
                    ['pointerdown', 'mousedown', 'mouseup', 'click'].forEach(tipo => {
                        alvo.dispatchEvent(new MouseEvent(tipo, {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: x,
                            clientY: y
                        }));
                    });
                    return true;
                    """,
                    int(x),
                    int(y),
                )
            )
        except Exception:
            return False

    def _tentar_recuperar_overlay_500(self, contexto="", tentativas=3):
        if not self._overlay_500_visivel():
            return False

        detalhe = f" ({contexto})" if contexto else ""
        self.log("INFO", f"Overlay 500 detectado{detalhe}. Tentando clicar fora para liberar a tela.")

        for _ in range(tentativas):
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass

            try:
                largura = int(
                    self.driver.execute_script(
                        "return Math.max(window.innerWidth || 0, document.documentElement.clientWidth || 0);"
                    )
                    or 0
                )
                altura = int(
                    self.driver.execute_script(
                        "return Math.max(window.innerHeight || 0, document.documentElement.clientHeight || 0);"
                    )
                    or 0
                )
            except Exception:
                largura = 0
                altura = 0

            pontos = [
                (20, 20),
                (max(20, largura - 20), 20),
                (20, max(20, altura - 20)),
                (max(20, largura - 20), max(20, altura - 20)),
                (max(25, largura // 2), 20),
            ]
            for x, y in pontos:
                self._clicar_em_ponto_da_tela(x, y)
                time.sleep(0.35)
                if not self._overlay_500_visivel():
                    self.log("INFO", "Overlay 500 fechado com clique fora.")
                    return True

            time.sleep(0.5)

        self.log("INFO", "Overlay 500 continuou visível após as tentativas de clique fora.")
        return False

    def _buscar_valor_campo(self, by, locator):
        try:
            return (self.driver.find_element(by, locator).get_attribute("value") or "").strip()
        except:
            return ""

    def _registrar_auditoria_item(self, modulo, tipo, item, status, detalhes=""):
        self.motor.auditoria.append(
            {
                "Modulo": modulo,
                "Tipo": tipo,
                "Item": item,
                "Status": status,
                "Detalhes": detalhes,
                "Momento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    def _slug_contexto(self, texto):
        normalizado = self._normalizar_texto_modulo(texto)
        return re.sub(r"\s+", "_", normalizado) or "contexto"

    def _sessao_ativa(self):
        return session_is_active(self._driver)

    def _erro_sessao_invalida(self, excecao):
        texto = f"{type(excecao).__name__}: {excecao}".lower()
        return any(
            trecho in texto
            for trecho in [
                "invalid session id",
                "nosuchwindowexception",
                "no such window",
                "target window already closed",
            ]
        )

    def _trocar_para_janela_segura(self, handle, contexto):
        return safe_switch_to_window(self.driver, handle, contexto)

    def _abrir_url_com_certificado(self, url, contexto):
        ignorou_certificado = navigate_with_certificate_bypass(self.driver, url, contexto)
        if ignorou_certificado:
            self.log("INFO", f"Aviso de certificado ignorado no site antigo ({contexto}).")
        return ignorou_certificado

    def _ignorar_aviso_certificado_se_aparecer(self, contexto):
        ignorou_certificado = bypass_chrome_certificate_warning(self.driver, contexto)
        if ignorou_certificado:
            self.log("INFO", f"Aviso de certificado ignorado no site antigo ({contexto}).")
        return ignorou_certificado

    def _capturar_diagnostico_worker(self, etapa, nome_modulo=""):
        os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"r{self.worker_id}_{self._slug_contexto(nome_modulo or etapa)}_{timestamp}"
        screenshot_path = os.path.join(DIAGNOSTICS_DIR, f"{base}.png")
        html_path = os.path.join(DIAGNOSTICS_DIR, f"{base}.html")
        url_atual = ""

        if not self._sessao_ativa():
            return {"url": "", "screenshot": None, "html": None}

        try:
            url_atual = self.driver.current_url or ""
        except Exception:
            pass

        try:
            self.driver.save_screenshot(screenshot_path)
        except Exception:
            screenshot_path = None

        try:
            with open(html_path, "w", encoding="utf-8") as arquivo_html:
                arquivo_html.write(self.driver.page_source)
        except Exception:
            html_path = None

        return {"url": url_atual, "screenshot": screenshot_path, "html": html_path}

    def _registrar_falha_worker(self, local_erro, excecao, etapa="", nome_modulo=""):
        diagnostico = self._capturar_diagnostico_worker(etapa or local_erro, nome_modulo)
        detalhes = [str(excecao)]
        if diagnostico["url"]:
            detalhes.append(f"URL atual: {diagnostico['url']}")
        if diagnostico["screenshot"]:
            detalhes.append(f"Screenshot: {diagnostico['screenshot']}")
        if diagnostico["html"]:
            detalhes.append(f"HTML: {diagnostico['html']}")
        self.motor.registrar_falha_caixa_preta(local_erro, Exception("\n".join(detalhes)))

    def _normalizar_texto_modulo(self, texto):
        return normalize_text(texto)

    def _modulos_equivalentes(self, nome_a, nome_b):
        return module_names_equivalent(nome_a, nome_b)

    def _coletar_modulos_visiveis_novo(self):
        modulos = []
        try:
            pagina = self.driver.page_source or ""
            url_base = self.driver.current_url or NOVO_MODULES_URL
        except Exception:
            pagina = ""
            url_base = NOVO_MODULES_URL

        soup = BeautifulSoup(pagina, "html.parser")
        for tr in soup.find_all("tr"):
            h6 = tr.find("h6")
            nome = " ".join((h6.get_text(" ", strip=True) if h6 else "").split())
            if not nome:
                continue

            professor = ""
            for p in tr.find_all("p"):
                texto_p = " ".join((p.get_text(" ", strip=True) or "").split())
                if "professor" in self._normalizar_texto_modulo(texto_p):
                    professor = texto_p
                    break

            url_aulas = ""
            for link in tr.find_all("a", href=True):
                href = str(link.get("href", "") or "").strip()
                if "/lessons/" in href:
                    url_aulas = urljoin(url_base, href)
                    break

            modulos.append(
                {
                    "nome": nome,
                    "professor": professor,
                    "url_aulas": url_aulas,
                }
            )
        self.cache_modulos_visiveis = modulos
        return modulos

    def _encontrar_modulo_no_novo(self, nome_modulo, professor=""):
        equivalentes = []
        melhor = None
        melhor_score = 0.0
        professor_norm = self._normalizar_texto_modulo(professor)
        for modulo in self._coletar_modulos_visiveis_novo():
            if self._modulos_equivalentes(nome_modulo, modulo["nome"]):
                equivalentes.append(modulo)
            score = module_match_score(nome_modulo, modulo["nome"], modulo.get("professor", ""))
            if professor_norm:
                professor_site = self._normalizar_texto_modulo(modulo.get("professor", ""))
                if professor_site and professor_norm in professor_site:
                    score += 0.03
            if score > melhor_score:
                melhor = modulo
                melhor_score = score

        if equivalentes:
            if professor_norm:
                for modulo in equivalentes:
                    professor_site = self._normalizar_texto_modulo(modulo.get("professor", ""))
                    if professor_site and professor_norm in professor_site:
                        return modulo
            return equivalentes[0]

        if melhor_score >= 0.92:
            return melhor
        return None

    def _abrir_lista_modulos_novo(self, wait):
        self.driver.get(NOVO_MODULES_URL)
        try:
            return wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTORS.modules_search_css))
            )
        except Exception:
            return wait.until(EC.element_to_be_clickable((By.XPATH, NOVO_MODULE_SEARCH_XPATH)))

    def _aguardar_resultado_pesquisa_modulo(self, nome_modulo, professor="", timeout=6):
        fim = time.time() + timeout
        ultimo_resultado = None
        while time.time() < fim:
            try:
                ultimo_resultado = self._encontrar_modulo_no_novo(nome_modulo, professor)
                if ultimo_resultado:
                    return ultimo_resultado
            except Exception as exc:
                if "stale element reference" not in str(exc).lower():
                    raise
            time.sleep(0.4)
        return ultimo_resultado

    def _pesquisar_modulo_novo(
        self, wait, nome_modulo, professor="", curso="", tentativas=3, intervalo_base=1.2
    ):
        ultimo_erro = None
        termos = [nome_modulo]

        for tentativa in range(tentativas):
            try:
                search = self._abrir_lista_modulos_novo(wait)
                self.preencher_input(search, nome_modulo)
                modulo = self._aguardar_resultado_pesquisa_modulo(
                    nome_modulo,
                    professor=professor,
                    timeout=max(4, int(intervalo_base + tentativa + 2)),
                )
                if modulo:
                    self.log(
                        "INFO",
                        f"Radar encontrou módulo candidato: {modulo.get('nome', '')} | {modulo.get('professor', '')}",
                    )
                    return modulo
            except Exception as exc:
                ultimo_erro = exc
                time.sleep(intervalo_base + tentativa * 0.5)

        if ultimo_erro:
            self.log(
                "INFO",
                f"Pesquisa do módulo '{nome_modulo}' não confirmou resultado: {str(ultimo_erro)[:90]}",
            )
        return None

    def _buscar_url_aulas_modulo_novo(self, wait, nome_modulo, professor="", curso="", tentativas=5):
        for tentativa in range(tentativas):
            modulo = self._pesquisar_modulo_novo(
                wait,
                nome_modulo,
                professor=professor,
                curso=curso,
                tentativas=1,
                intervalo_base=1.5 + tentativa,
            )
            if modulo:
                if isinstance(modulo, dict) and modulo.get("url_aulas"):
                    return modulo.get("url_aulas")
            self.driver.get(NOVO_MODULES_URL)
            time.sleep(1 + tentativa * 0.3)
        return None

    def _abrir_modulo_existente_no_novo(
        self,
        wait,
        nome_modulo,
        professor="",
        curso="",
        url_aulas="",
        tentativas=4,
        exigir_painel_aulas=False,
    ):
        ultimo_erro = None
        for tentativa in range(tentativas):
            try:
                nome_busca = " ".join((nome_modulo or "").strip().split())
                nome_norm = self._normalizar_texto_modulo(nome_busca)
                professor_norm = self._normalizar_texto_modulo(professor)
                destino = (url_aulas or "").strip() if tentativa == 0 else ""
                self.log("INFO", f"Buscando modulo existente no painel novo: {nome_busca}")
                self.driver.get(NOVO_MODULES_URL)
                search_input = self._abrir_lista_modulos_novo(wait)
                self.preencher_input(search_input, nome_busca)
                time.sleep(4 + tentativa * 0.5)

                melhor_url = ""
                melhor_score = 0.0
                for h6 in self.driver.find_elements(By.TAG_NAME, "h6"):
                    janelas_antes = set(self.driver.window_handles)
                    try:
                        texto_h6 = " ".join((h6.text or "").split())
                        if not texto_h6:
                            continue
                        texto_norm = self._normalizar_texto_modulo(texto_h6)
                        score = module_match_score(nome_modulo, texto_h6, "")
                        equivalente = bool(nome_norm) and bool(texto_norm) and (
                            nome_norm in texto_norm
                            or texto_norm in nome_norm
                            or self._modulos_equivalentes(nome_modulo, texto_h6)
                        )
                        if not equivalente and score < 0.92:
                            continue
                        tr = h6.find_element(By.XPATH, "./ancestor::tr")
                        href = tr.find_element(By.XPATH, NOVO_LESSONS_LINK_XPATH).get_attribute("href") or ""
                        if not href:
                            continue
                        professor_tr = self._normalizar_texto_modulo(tr.text)
                        if professor_norm and professor_tr and professor_norm in professor_tr:
                            melhor_url = href
                            break
                        if score > melhor_score or (equivalente and not melhor_url):
                            melhor_score = score
                            melhor_url = href
                    except Exception:
                        continue

                destino = melhor_url or destino or self._buscar_url_aulas_modulo_novo(
                    wait,
                    nome_modulo,
                    professor=professor,
                    curso=curso,
                    tentativas=2,
                )
                if not destino:
                    raise Exception("Lista de aulas do módulo não localizada.")

                self.log("INFO", f"Modulo existente localizado. Abrindo aulas em: {destino}")
                self.driver.get(destino)
                time.sleep(2 + tentativa * 0.4)

                if exigir_painel_aulas:
                    wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, "add_new_btn"))
                    )
                return destino
            except Exception as exc:
                ultimo_erro = exc
                self.driver.get(NOVO_MODULES_URL)
                time.sleep(1 + tentativa * 0.5)

        if ultimo_erro:
            raise ultimo_erro
        raise Exception("Não foi possível abrir o módulo existente no site novo.")

    def _eh_modulo_plano_estudos(self, nome_modulo):
        return is_plano_estudos_module(nome_modulo)

    def _forcar_video_plano_estudos(self):
        self.fila_videos = [
            {
                "titulo": "Acesse seu Material",
                "vimeo": "1173006649",
                "youtube_link": "",
                "canal": "vimeo",
            }
        ]

    def _extrair_dados_video_antigo(self):
        vimeo = self._buscar_valor_campo(By.ID, "vimeo")
        if vimeo:
            vimeo = re.sub(r"\s+", "", vimeo)
        link = self._buscar_valor_campo(By.ID, "link")
        if link:
            link = link.strip()
        canal = "vimeo"

        try:
            if self.driver.find_element(
                By.XPATH, "//input[@name='ativavimeo' and @value='0']"
            ).is_selected():
                canal = "youtube"
            elif self.driver.find_element(
                By.XPATH, "//input[@name='ativavimeo' and @value='1']"
            ).is_selected():
                canal = "vimeo"
        except:
            pass

        if (not vimeo or not vimeo.isdigit()) and link:
            canal = "youtube"

        return {"vimeo": vimeo, "youtube_link": link, "canal": canal}

    def _clicar_se_visivel(self, elemento):
        try:
            if not elemento.is_displayed():
                return False
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
            time.sleep(0.2)
            self.driver.execute_script("arguments[0].click();", elemento)
            time.sleep(0.4)
            return True
        except:
            return False

    def _selecionar_canal_video(self, canal):
        rotulos = ["YouTube", "Youtube", "youtube"] if canal == "youtube" else ["Vimeo", "vimeo"]
        xpaths = [
            f"//input[@type='radio' and (contains(@id, '{canal}') or contains(@name, '{canal}'))]"
        ]
        for rotulo in rotulos:
            xpaths.extend(
                [
                    f"//input[@type='radio' and @value='{rotulo}']",
                    f"//label[contains(normalize-space(.), '{rotulo}')]",
                    f"//button[contains(normalize-space(.), '{rotulo}')]",
                    f"//*[contains(@class, 'tab') and contains(normalize-space(.), '{rotulo}')]",
                ]
            )

        for xp in xpaths:
            for elemento in self.driver.find_elements(By.XPATH, xp):
                if self._clicar_se_visivel(elemento):
                    return True
        return False

    def _localizar_campo_video(self, wait, canal):
        espera_curta = WebDriverWait(self.driver, 2)
        candidatos = []
        if canal == "youtube":
            candidatos.extend(
                [
                    "//input[@*[name()='wire:model']='lessons.youtube_link']",
                    "//input[@*[name()='wire:model']='lessons.youtube_url']",
                    "//input[@*[name()='wire:model']='lessons.video_url']",
                    "//input[@*[name()='wire:model']='lessons.link']",
                    "//input[contains(@name, 'youtube') or contains(@id, 'youtube')]",
                    "//input[contains(@name, 'YouTube') or contains(@id, 'YouTube')]",
                    "//input[contains(@placeholder, 'YouTube') or contains(@placeholder, 'Youtube')]",
                    "//label[contains(normalize-space(.), 'YouTube')]/following::input[1]",
                    "//label[contains(normalize-space(.), 'Youtube')]/following::input[1]",
                    "//label[contains(normalize-space(.), 'Link')]/following::input[1]",
                    "//label[contains(normalize-space(.), 'link')]/following::input[1]",
                    "//input[@*[name()='wire:model']='lessons.vimeo_id']",
                ]
            )
        else:
            candidatos.extend(
                [
                    "//input[@*[name()='wire:model']='lessons.vimeo_id']",
                    "//input[contains(@name, 'vimeo') or contains(@id, 'vimeo')]",
                    "//label[contains(normalize-space(.), 'Vimeo')]/following::input[1]",
                ]
            )

        ultimo_erro = None
        for xp in candidatos:
            try:
                return espera_curta.until(EC.element_to_be_clickable((By.XPATH, xp)))
            except Exception as exc:
                ultimo_erro = exc

        if ultimo_erro:
            raise ultimo_erro
        raise Exception(f"Campo de {canal} nÃ£o encontrado")

    def _localizar_container_livewire(self, wait, nome_label):
        xpaths = [
            f"//label[contains(normalize-space(.), '{nome_label}')]/ancestor::div[contains(@class, 'form-group')][1]",
            f"//label[contains(normalize-space(.), '{nome_label}')]/ancestor::div[.//input[contains(@wire:model, 'searchTerm')]][1]",
            f"//*[self::label or self::span][contains(normalize-space(.), '{nome_label}')]/ancestor::div[.//input[contains(@wire:model, 'searchTerm')]][1]",
        ]
        ultimo_erro = None
        for xpath in xpaths:
            try:
                return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            except Exception as exc:
                ultimo_erro = exc
        if ultimo_erro:
            raise ultimo_erro
        raise Exception(f"Container Livewire não encontrado para {nome_label}.")

    def _localizar_input_livewire(self, container, nome_label):
        candidatos = []
        for elemento in container.find_elements(By.XPATH, ".//input[@type='text']"):
            try:
                wire_model = (elemento.get_attribute("wire:model") or "").strip()
                if wire_model in {"module.name", "module.time", "attachment.name"}:
                    continue
                if "searchTerm" in wire_model:
                    candidatos.insert(0, elemento)
                else:
                    candidatos.append(elemento)
            except Exception:
                continue

        for elemento in candidatos:
            try:
                if elemento.is_displayed() and elemento.is_enabled():
                    return elemento
            except Exception:
                continue

        raise Exception(f"Input Livewire não encontrado para {nome_label}.")

    def _listar_opcoes_livewire_visiveis(self, container):
        xp_lista = (
            ".//ul[contains(@class, 'list-group')]/li | "
            ".//*[contains(@class, 'list-group-item')] | "
            ".//*[@role='option']"
        )
        opcoes = []
        for op in container.find_elements(By.XPATH, xp_lista):
            try:
                texto_opcao = " ".join((op.text or "").split())
                if op.is_displayed() and len(texto_opcao) > 1:
                    opcoes.append((op, texto_opcao))
            except Exception:
                continue
        return opcoes

    def _texto_preenchido_input_livewire(self, input_elem):
        try:
            valor = (input_elem.get_attribute("value") or "").strip()
            if valor:
                return valor
            return (input_elem.get_attribute("placeholder") or "").strip()
        except Exception:
            return ""

    def _selecao_livewire_confirmada(self, container, input_elem, texto_pesquisa):
        texto_norm = normalize_text(texto_pesquisa)
        try:
            for botao in container.find_elements(By.XPATH, ".//*[@wire:click='clearSelectedValue']"):
                estilo = (botao.get_attribute("style") or "").lower()
                if botao.is_displayed() and "display: none" not in estilo:
                    return True
        except Exception as exc:
            if "stale" in str(exc).lower():
                return True

        try:
            if self._listar_opcoes_livewire_visiveis(container):
                return False
        except Exception as exc:
            if "stale" in str(exc).lower():
                return True

        try:
            valor_atual = normalize_text(self._texto_preenchido_input_livewire(input_elem))
        except Exception as exc:
            return "stale" in str(exc).lower()

        return bool(
            valor_atual
            and (valor_atual == texto_norm or texto_norm in valor_atual or valor_atual in texto_norm)
        )

    def _aguardar_campo_livewire_pronto(self, nome_label, timeout=8):
        fim = time.time() + timeout
        ultimo_erro = None
        while time.time() < fim:
            self._tentar_recuperar_overlay_500(f"aguardando campo {nome_label}")
            try:
                espera_curta = WebDriverWait(self.driver, 2)
                container = self._localizar_container_livewire(espera_curta, nome_label)
                input_elem = self._localizar_input_livewire(container, nome_label)
                disabled = (input_elem.get_attribute("disabled") or "").strip().lower()
                readonly = (input_elem.get_attribute("readonly") or "").strip().lower()
                if input_elem.is_displayed() and input_elem.is_enabled() and not disabled and not readonly:
                    return container, input_elem
            except Exception as exc:
                ultimo_erro = exc
            time.sleep(0.35)

        if ultimo_erro:
            raise ultimo_erro
        raise Exception(f"Campo Livewire '{nome_label}' não ficou pronto a tempo.")

    def _aguardar_confirmacao_livewire(self, container, input_elem, texto_pesquisa, timeout=2.4):
        fim = time.time() + timeout
        while time.time() < fim:
            self._tentar_recuperar_overlay_500("confirmação Livewire")
            if self._selecao_livewire_confirmada(container, input_elem, texto_pesquisa):
                return True
            time.sleep(0.25)
        return self._selecao_livewire_confirmada(container, input_elem, texto_pesquisa)

    def _selecionar_opcao_livewire(self, container, input_elem, texto_pesquisa):
        texto_norm = normalize_text(texto_pesquisa)
        ultimo_visivel = []

        for _ in range(16):
            opcoes = self._listar_opcoes_livewire_visiveis(container)
            if opcoes:
                ultimo_visivel = opcoes
                melhor = None
                melhor_score = -1.0
                for op, texto_opcao in opcoes:
                    score = module_match_score(texto_pesquisa, texto_opcao)
                    opcao_norm = normalize_text(texto_opcao)
                    if opcao_norm == texto_norm:
                        score = 2.0
                    elif texto_norm and texto_norm in opcao_norm:
                        score += 0.2
                    if score > melhor_score:
                        melhor = (op, texto_opcao)
                        melhor_score = score

                if melhor:
                    alvo, texto_escolhido = melhor
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", alvo
                        )
                    except Exception:
                        pass
                    confirmou = False
                    try:
                        self.driver.execute_script("arguments[0].click();", alvo)
                        confirmou = self._aguardar_confirmacao_livewire(
                            container, input_elem, texto_pesquisa
                        )
                    except Exception:
                        try:
                            ActionChains(self.driver).move_to_element(alvo).click().perform()
                            confirmou = self._aguardar_confirmacao_livewire(
                                container, input_elem, texto_pesquisa
                            )
                        except Exception:
                            input_elem.send_keys(Keys.ARROW_DOWN)
                            input_elem.send_keys(Keys.ENTER)
                            confirmou = self._aguardar_confirmacao_livewire(
                                container, input_elem, texto_pesquisa
                            )
                            if confirmou:
                                self.log("INFO", f"Selecionado por teclado: {texto_pesquisa}")
                                time.sleep(0.8)
                                return True
                    if confirmou:
                        self.log("INFO", f"Selecionado: {texto_escolhido}")
                        time.sleep(0.8)
                        return True
                    self.log(
                        "INFO",
                        f"Clique em '{texto_escolhido}' nÃ£o confirmou a seleÃ§Ã£o. Tentando de novo...",
                    )

            time.sleep(0.4)

        if ultimo_visivel:
            opcoes_txt = ", ".join(texto for _, texto in ultimo_visivel[:5])
            raise Exception(
                f"Nenhuma opção clicável encontrada para '{texto_pesquisa}'. Opções visíveis: {opcoes_txt}"
            )
        raise Exception(f"Nenhuma opção apareceu para '{texto_pesquisa}'.")

    # ! NOVO MOTOR DE PESQUISA PARA COMPONENTES LIVEWIRE (V106)
    def _preencher_pesquisa_livewire(self, wait, nome_label, texto_pesquisa):
        self.log("INFO", f"Pesquisando {nome_label}: {texto_pesquisa}")
        self._tentar_recuperar_overlay_500(f"antes de pesquisar {nome_label}")
        container, input_elem = self._aguardar_campo_livewire_pronto(nome_label, timeout=8)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
        time.sleep(0.3)

        self.driver.execute_script("arguments[0].click();", input_elem)
        if not self.preencher_input_humano(input_elem, texto_pesquisa):
            clear_and_type(input_elem, texto_pesquisa, delay_between_chars=0.02)

        return self._selecionar_opcao_livewire(container, input_elem, texto_pesquisa)

    def _preencher_pesquisa_livewire_com_retry(
        self, wait, nome_label, texto_pesquisa, tentativas=3, pausa=1.0
    ):
        ultimo_erro = None
        for tentativa in range(tentativas):
            try:
                if tentativa > 0:
                    self.log(
                        "INFO",
                        f"Nova tentativa no campo {nome_label}: {texto_pesquisa} ({tentativa + 1}/{tentativas})",
                    )
                return self._preencher_pesquisa_livewire(wait, nome_label, texto_pesquisa)
            except Exception as exc:
                ultimo_erro = exc
                try:
                    self.driver.find_element(By.TAG_NAME, "body").click()
                except Exception:
                    pass
                self._tentar_recuperar_overlay_500(f"retry campo {nome_label}")
                time.sleep(pausa + tentativa * 0.4)

        if ultimo_erro:
            raise ultimo_erro
        raise Exception(f"Não foi possível preencher {nome_label}: {texto_pesquisa}")

    def _preencher_pesquisa_livewire_multiplos_rotulos(self, wait, rotulos, texto_pesquisa):
        ultimo_erro = None
        for rotulo in rotulos:
            try:
                return self._preencher_pesquisa_livewire(wait, rotulo, texto_pesquisa)
            except Exception as exc:
                ultimo_erro = exc
        rotulos_normalizados = [normalize_text(rotulo) for rotulo in rotulos]
        if any("modulo" in rotulo for rotulo in rotulos_normalizados):
            inputs = self.driver.find_elements(
                By.XPATH, "//input[@type='text' and contains(@class, 'form-control')]"
            )
            valor_busca = (texto_pesquisa or "").lower().replace("'", "")
            xp_opcao = (
                "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                f"'{valor_busca}') and not(*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                f"'abcdefghijklmnopqrstuvwxyz'), '{valor_busca}')])]"
            )
            for campo in inputs:
                try:
                    wire_model = (campo.get_attribute("wire:model") or "").strip()
                    if wire_model == "attachment.name":
                        continue
                    if campo.get_attribute("value"):
                        continue
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", campo
                    )
                    time.sleep(0.4)
                    self.preencher_input_humano(campo, texto_pesquisa)
                    time.sleep(4.5)
                    for opcao in self.driver.find_elements(By.XPATH, xp_opcao):
                        try:
                            if not opcao.is_displayed():
                                continue
                            if opcao.tag_name.lower() in {"input", "html", "body"}:
                                continue
                            try:
                                ActionChains(self.driver).move_to_element(opcao).click().perform()
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", opcao)
                            time.sleep(1.2)
                            return
                        except Exception:
                            continue
                except Exception as exc:
                    ultimo_erro = exc
        if ultimo_erro:
            raise ultimo_erro
        raise Exception(f"Campo Livewire nÃ£o encontrado para {texto_pesquisa}.")

    def _definir_select_livewire(self, wait, css_selector, valor, descricao, timeout=8):
        self._tentar_recuperar_overlay_500(f"antes de definir {descricao}")
        select_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_elem)
        selecionado = self.driver.execute_script(
            """
            const campo = arguments[0];
            const valor = arguments[1];
            if (!campo) return false;
            campo.value = valor;
            campo.dispatchEvent(new Event('input', { bubbles: true }));
            campo.dispatchEvent(new Event('change', { bubbles: true }));
            return campo.value === valor;
            """,
            select_elem,
            valor,
        )
        if not selecionado:
            raise Exception(f"NÃ£o foi possÃ­vel definir {descricao} como '{valor}'.")
        WebDriverWait(self.driver, timeout).until(
            lambda d: (
                d.find_element(By.CSS_SELECTOR, css_selector).get_attribute("value") or ""
            ).strip()
            == valor
        )
        time.sleep(0.8)
        return True

    def run(self):
        try:
            self.log("INFO", f"Ligando motores para '{self.nome_arquivo}'...")
            self._iniciar_driver_e_logins()
            wait = WebDriverWait(self.driver, 15)

            self._trocar_para_janela_segura(self.aba_antiga, "retorno ao site antigo após login")
            script_banner = f"document.title = '🤖 R{self.worker_id} - ' + document.title; let d = document.createElement('div'); d.innerHTML = '<h3 style=\"margin:0; font-family:sans-serif; font-size: 16px;\">🤖 SOU O ROBÔ {self.worker_id} | Planilha: {self.nome_arquivo}</h3>'; d.style.cssText = 'position:relative; width:100%; background:#4F46E5; color:white; text-align:center; z-index:999999; padding:8px; border-bottom:4px solid #F59E0B; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);'; document.body.prepend(d);"
            self.driver.execute_script(script_banner)

            self.log(
                "MODULO",
                f"Logins concluídos! Vá ao Chrome do Robô {self.worker_id}, abra o Curso desejado e aguarde.",
            )
            self.motor.evento_inicio_trabalho.wait()
            if self.motor.parar_loop:
                return

            self._trocar_para_janela_segura(self.aba_antiga, "captura da URL do curso antigo")
            url_lista_antiga = self.driver.current_url

            limite_rigor = float(self.motor.config.get("match_threshold", 0.65))
            metodo_busca = self.motor.config.get(
                "search_method", "Ordem Exata (Linha 1 = Módulo 1)"
            )

            self.log("INFO", f"⚙️ Modo de Extração: {metodo_busca}")

            self.log("INFO", f"Modo de Upload: {self.motor.descricao_modo_upload()}")

            indice_modulo_site = 0

            for row in self.chunk_excel:
                if self.motor.parar_loop:
                    break
                nome_modulo = str(
                    row.get(
                        "nome do módulo",
                        row.get("nome do modulo", row.get("modulo", row.get("módulo", ""))),
                    )
                ).strip()
                nome_modulo = extract_module_name_from_row(row)
                if not nome_modulo or nome_modulo.lower() == "nan":
                    continue
                curso = str(row.get("curso", "")).strip()
                professor = str(row.get("professor", row.get("professor(a)", ""))).strip()
                subir_videos = self.motor.deve_subir_videos()
                subir_materiais = self.motor.deve_subir_materiais()
                modo_somente_conteudo = self.motor.modo_somente_conteudo()
                modo_exige_modulo_existente = self.motor.module_scope == "unico"
                self.log("MODULO", f"INICIANDO: {nome_modulo}")

                modulo_existente = None
                url_aulas_existente = ""

                # RADAR ANTI-DUPLICATAS
                try:
                    self._trocar_para_janela_segura(self.aba_nova, "radar anti-duplicatas")
                    modulo_existente = self._pesquisar_modulo_novo(
                        wait,
                        nome_modulo,
                        professor=professor,
                        curso=curso,
                        tentativas=2,
                    )
                    url_aulas_existente = str(modulo_existente.get("url_aulas", "") or "").strip() if modulo_existente else ""
                    if modulo_existente and modo_exige_modulo_existente:
                        self.log(
                            "INFO",
                            f"MÃ³dulo '{nome_modulo}' jÃ¡ existe. Vou complementar apenas {self.motor.descricao_resumida_conteudo()}.",
                        )
                    elif modulo_existente:
                        self.log(
                            "INFO",
                            f"🎯 Radar Ativado: Módulo '{nome_modulo}' já migrado. Saltando...",
                        )
                        self.motor.registrar_conclusao_modulo("Aviso")
                        self.motor.salvar_no_banco(
                            nome_modulo, curso, professor, "Pulado (Já Existe)", self.nome_arquivo
                        )
                        indice_modulo_site += 1
                        continue
                except Exception as radar_erro:
                    if self._erro_sessao_invalida(radar_erro):
                        raise
                    self.log(
                        "INFO",
                        f"Radar do módulo '{nome_modulo}' não confirmou duplicidade: {str(radar_erro)[:70]}",
                    )

                status_final = "Erro"
                for tentativa in range(2):
                    if self.motor.parar_loop:
                        break
                    self.fila_videos.clear()
                    self.fila_arquivos.clear()
                    self.ordem_atual = 1
                    status_final = "Sucesso"

                    try:
                        self._trocar_para_janela_segura(self.aba_antiga, "módulo antigo")
                        self._abrir_url_com_certificado(url_lista_antiga, "lista de módulos antigos")
                        time.sleep(1)
                        tds = wait.until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, "td.textointernos")
                            )
                        )
                        melhor_td = None
                        maior_nota = 0.0
                        indice_origem = int(row.get("_source_index", indice_modulo_site) or 0)
                        busca_manual_sem_planilha = bool(row.get("_manual_single_module"))
                        if busca_manual_sem_planilha:
                            metodo_busca = "Fuzzy Match (Buscar por Nomes)"

                        if metodo_busca == "Ordem Exata (Linha 1 = Módulo 1)":
                            if indice_origem < len(tds):
                                melhor_td = tds[indice_origem]
                                maior_nota = 1.0
                                self.log(
                                    "INFO",
                                    f"🎯 Mapeamento por Ordem: Entrando no Módulo #{indice_modulo_site + 1}",
                                )
                            else:
                                self.log(
                                    "ERRO", f"O site antigo tem menos módulos do que o seu Excel."
                                )
                        else:
                            for td in tds:
                                texto_site = str(td.text).strip()
                                if not texto_site:
                                    continue
                                nota = self.calcular_similaridade(nome_modulo, texto_site)
                                if nota > maior_nota:
                                    maior_nota = nota
                                    melhor_td = td
                                if nota == 1.0:
                                    break

                        if melhor_td and maior_nota >= limite_rigor:
                            btn_acessar = melhor_td.find_element(
                                By.XPATH, "./preceding-sibling::td//a"
                            )
                            self.driver.execute_script("arguments[0].click();", btn_acessar)
                            try:
                                btn_aula = WebDriverWait(self.driver, 2).until(
                                    EC.element_to_be_clickable(
                                        (By.XPATH, "//a[contains(@href, 'aula.asp')]")
                                    )
                                )
                                self.driver.execute_script("arguments[0].click();", btn_aula)
                            except:
                                pass
                            if modo_exige_modulo_existente:
                                self._extrair_dados_modulo_antigo_unico(
                                    capturar_videos=subir_videos,
                                    capturar_materiais=subir_materiais,
                                )
                            else:
                                self._extrair_dados_ativos(
                                    capturar_videos=subir_videos,
                                    capturar_materiais=subir_materiais,
                                )
                        else:
                            self.log("ERRO", f"Módulo antigo não encontrado.")
                            status_final = "Criado Vazio"
                        if modo_somente_conteudo and not self.fila_videos and not self.fila_arquivos:
                            self.log(
                                "INFO",
                                f"Nenhum {self.motor.descricao_resumida_conteudo()} encontrado no mÃ³dulo antigo. Nada para enviar.",
                            )
                            status_final = "Pulado (Sem ConteÃºdo do Modo)"
                            break

                        self.log(
                            "INFO",
                            f"Conteudo capturado do modulo antigo: videos={len(self.fila_videos)} | materiais={len(self.fila_arquivos)}",
                        )

                        if self.motor.modo_auditoria_ativo():
                            detalhes = (
                                f"videos={len(self.fila_videos)}; materiais={len(self.fila_arquivos)}; "
                                f"curso={curso}; professor={professor}; modo={self.motor.upload_mode}"
                            )
                            self.log(
                                "INFO",
                                f"Modo auditoria ativo. Módulo '{nome_modulo}' não será criado nem enviado.",
                            )
                            self._registrar_auditoria_item(
                                nome_modulo, "Modulo", nome_modulo, "AUDITORIA", detalhes
                            )
                            status_final = "Auditoria (Sem Upload)"
                            break

                        self._trocar_para_janela_segura(self.aba_nova, "criação do módulo no site novo")
                        if modo_exige_modulo_existente and modulo_existente:
                            url_aulas = self._abrir_modulo_existente_no_novo(
                                wait,
                                nome_modulo,
                                professor=professor,
                                curso=curso,
                                url_aulas=url_aulas_existente,
                                tentativas=4,
                                exigir_painel_aulas=bool(self.fila_videos),
                            )
                            if not url_aulas:
                                raise Exception(
                                    "MÃ³dulo existente encontrado, mas a lista de aulas nÃ£o foi localizada no site novo."
                                )
                            self._trocar_para_janela_segura(self.aba_nova, "mÃ³dulo existente no site novo")
                            if self._eh_modulo_plano_estudos(nome_modulo):
                                self._forcar_video_plano_estudos()
                            if self.fila_videos:
                                self._injetar_videos(wait, nome_modulo)
                            if self.fila_arquivos:
                                self._injetar_materiais(wait, nome_modulo, self.aba_antiga, self.aba_nova)
                            break

                        if modo_exige_modulo_existente and not modulo_existente:
                            raise Exception(
                                "Este modo usa apenas mÃ³dulos que jÃ¡ existem no site novo. Use o primeiro botÃ£o com planilha se quiser criar mÃ³dulos."
                            )

                        self.driver.get(NOVO_MODULE_CREATE_URL)
                        try:
                            input_n = wait.until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, SELECTORS.module_name_css)
                                )
                            )
                        except Exception:
                            input_n = wait.until(
                                EC.presence_of_element_located((By.XPATH, NOVO_MODULE_NAME_XPATH))
                            )
                        self.preencher_input_humano(input_n, nome_modulo)
                        self.preencher_input(
                            wait.until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, SELECTORS.module_time_css)
                                )
                            ),
                            "0",
                        )

                        # ! PREENCHIMENTO DO CURSO E PROFESSOR COM A NOVA FUNÇÃO V106
                        if curso and str(curso).lower() != "nan":
                            self._preencher_pesquisa_livewire_com_retry(wait, "Curso", curso)

                        if professor and str(professor).lower() != "nan":
                            self._aguardar_campo_livewire_pronto("Professor", timeout=10)
                            time.sleep(0.8)
                            self._preencher_pesquisa_livewire_com_retry(
                                wait, "Professor", professor, tentativas=4, pausa=1.2
                            )

                        botoes = self.driver.find_elements(
                            By.XPATH,
                            "//button[@type='submit' and contains(translate(text(), 'SALVAR', 'salvar'), 'salvar')]",
                        )
                        btn_salvar = next((b for b in botoes if b.is_displayed()), None)
                        if btn_salvar:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();",
                                btn_salvar,
                            )
                        else:
                            self.driver.execute_script("document.querySelector('form').submit();")
                        WebDriverWait(self.driver, 8).until(
                            lambda d: "/modules/create" not in d.current_url
                            or len(d.find_elements(By.CSS_SELECTOR, SELECTORS.modules_search_css)) > 0
                            or len(d.find_elements(By.XPATH, NOVO_MODULE_SEARCH_XPATH)) > 0
                        )

                        if self.fila_videos or self.fila_arquivos:
                            url_aulas = self._buscar_url_aulas_modulo_novo(
                                wait,
                                nome_modulo,
                                professor=professor,
                                curso=curso,
                                tentativas=5,
                            )

                            if url_aulas:
                                if self._eh_modulo_plano_estudos(nome_modulo):
                                    self._forcar_video_plano_estudos()
                                if self.fila_videos:
                                    self.driver.get(url_aulas)
                                    time.sleep(2)
                                    self._injetar_videos(wait, nome_modulo)
                                if self.fila_arquivos:
                                    self._injetar_materiais(wait, nome_modulo, self.aba_antiga, self.aba_nova)
                            else:
                                raise Exception(
                                    "Módulo criado não encontrado após múltiplas buscas no site novo. Verifique Curso/Professor e os diagnósticos salvos em logs/diagnosticos."
                                )
                        break
                    except Exception as e:
                        if self._erro_sessao_invalida(e):
                            if tentativa == 0:
                                self.log(
                                    "INFO",
                                    "⚠️ Sessão do Chrome perdida! Tentando recuperar e reiniciar sessão...",
                                )
                                try:
                                    self._reiniciar_sessao_chrome()
                                    wait = WebDriverWait(self.driver, 15)
                                    self.log("INFO", "🛡️ Sessão recuperada com sucesso! Retomando migração...")
                                    continue
                                except Exception as recovery_error:
                                    self.log("ERRO", f"Falha definitiva ao recuperar sessão do Chrome: {recovery_error}")
                                    self._registrar_falha_worker(
                                        f"Frota {self.worker_id} - {nome_modulo}",
                                        e,
                                        "sessao_invalida",
                                        nome_modulo,
                                    )
                                    raise
                            else:
                                self.log(
                                    "ERRO",
                                    "Sessão do Chrome perdida na segunda tentativa. Abortando worker.",
                                )
                                self._registrar_falha_worker(
                                    f"Frota {self.worker_id} - {nome_modulo}",
                                    e,
                                    "sessao_invalida_definitiva",
                                    nome_modulo,
                                )
                                raise
                        if tentativa == 0:
                            self.log(
                                "INFO",
                                f"🛡️ Auto-Cura ativada. Falha detetada: {str(e)[:50]}... reiniciando processo.",
                            )
                            time.sleep(2)
                        else:
                            self.log("ERRO", f"Falha definitiva no módulo.")
                            self._registrar_falha_worker(
                                f"Frota {self.worker_id} - {nome_modulo}",
                                e,
                                "falha_definitiva_modulo",
                                nome_modulo,
                            )
                            status_final = "Erro"

                if status_final in [
                    "Sucesso",
                    "Criado Vazio",
                    "Auditoria (Sem Upload)",
                    "Pulado (Sem ConteÃºdo do Modo)",
                ]:
                    self.motor.registrar_conclusao_modulo("Sucesso")
                else:
                    self.motor.registrar_conclusao_modulo("Erro")
                self.motor.salvar_no_banco(
                    nome_modulo, curso, professor, status_final, self.nome_arquivo
                )

                indice_modulo_site += 1

        except Exception as e:
            self._registrar_falha_worker(
                f"Frota {self.worker_id} Crítico",
                e,
                "worker_critico",
                self.nome_arquivo,
            )
            self.log("ERRO", f"Falha crítica no worker {self.worker_id}.")
            self.motor.tocar_som("error")
        finally:
            if self._driver:
                try:
                    self._driver.quit()
                except:
                    pass
            self.motor.registrar_fim_worker(self.worker_id)

    def _localizar_elemento_recursivo_frames(self, xpath):
        """
        Busca um elemento por XPath varrendo recursivamente a página principal e todos os frames/iframes.
        Retorna o elemento encontrado ou None.
        Ao final da execução (seja sucesso ou falha), restaura o driver para o default_content().
        """
        def _buscar():
            alvo = self.driver.find_elements(By.XPATH, xpath)
            if alvo:
                return alvo[0]
            
            # Buscar frames no contexto atual
            frames = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
            for f in frames:
                try:
                    self.driver.switch_to.frame(f)
                    res = _buscar()
                    if res:
                        return res
                    self.driver.switch_to.parent_frame()
                except:
                    try:
                        self.driver.switch_to.parent_frame()
                    except:
                        pass
            return None

        self.driver.switch_to.default_content()
        el = _buscar()
        if not el:
            self.driver.switch_to.default_content()
        return el

    def _clicar_elemento_em_frames(self, xpath):
        el = self._localizar_elemento_recursivo_frames(xpath)
        if el:
            try:
                self.driver.execute_script("arguments[0].click();", el)
                return True
            except Exception as e:
                self.log("ERRO", f"Erro ao clicar no elemento {xpath} no frame: {str(e)}")
        return False

    def _extrair_dados_ativos(self, capturar_videos=True, capturar_materiais=True):
        d_url = self.driver.current_url
        self.fila_videos.clear()
        self.fila_arquivos.clear()

        if capturar_videos:
            self.log("INFO", "Iniciando captura de vídeos do módulo no site antigo...")
            botao_video = self._localizar_elemento_recursivo_frames("//a[contains(@href, 'videos.asp')]")
            if botao_video:
                self.log("INFO", "Botão de vídeos (videos.asp) encontrado! Acessando...")
                href_videos = botao_video.get_attribute("href") or ""
                if href_videos and not href_videos.startswith("#") and "javascript" not in href_videos:
                    self._abrir_url_com_certificado(href_videos, "lista de vídeos do site antigo")
                else:
                    self.driver.execute_script("arguments[0].click();", botao_video)
                time.sleep(2.5)
                
                try:
                    self.driver.switch_to.default_content()
                    p = self.driver.find_element(
                        By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
                    )
                    self.driver.execute_script("arguments[0].click();", p)
                    time.sleep(0.5)
                    self.driver.execute_script(
                        "arguments[0].click();",
                        self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']"),
                    )
                    time.sleep(2.5)
                except:
                    pass

                def buscar_todos_links(lista_acumulada):
                    lk = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'alterar_video.asp')]")
                    for l in lk:
                        href = l.get_attribute("href")
                        if href and href not in lista_acumulada:
                            lista_acumulada.append(href)
                    
                    frames = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
                    for f in frames:
                        try:
                            self.driver.switch_to.frame(f)
                            buscar_todos_links(lista_acumulada)
                            self.driver.switch_to.parent_frame()
                        except:
                            try:
                                self.driver.switch_to.parent_frame()
                            except:
                                pass

                self.log("INFO", "Procurando links de vídeos (alterar_video.asp)...")
                self.driver.switch_to.default_content()
                urls = []
                buscar_todos_links(urls)
                
                if urls:
                    self.log("INFO", f"Encontrados {len(urls)} vídeos para extrair.")
                    urls.reverse()
                    jp = self.driver.current_window_handle
                    for idx, url in enumerate(urls, 1):
                        janelas_antes = set(self.driver.window_handles)
                        try:
                            self.log("INFO", f"Extraindo vídeo {idx}/{len(urls)}...")
                            na = open_new_tab(self.driver, url, "extração de vídeo em nova aba", timeout=5)
                            self._trocar_para_janela_segura(na, "extração de vídeo em nova aba")
                            self._ignorar_aviso_certificado_se_aparecer("extração de vídeo em nova aba")
                            wt = WebDriverWait(self.driver, 5)
                            et = wt.until(EC.presence_of_element_located((By.ID, "assunto")))
                            raw_title = et.get_attribute("value") or ""
                            tit = " ".join(
                                [
                                    (
                                        p
                                        if p
                                        in [
                                            "de",
                                            "da",
                                            "do",
                                            "e",
                                            "a",
                                            "o",
                                            "em",
                                            "na",
                                            "no",
                                            "com",
                                            "por",
                                            "para",
                                        ]
                                        else p.capitalize()
                                    )
                                    for p in " ".join(raw_title.strip().split())
                                    .lower()
                                    .split()
                                ]
                            )
                            dados_video = self._extrair_dados_video_antigo()
                            self.log("OK", f"Vídeo {idx} extraído: '{tit}' -> Vimeo: {dados_video.get('vimeo')}, Youtube: {dados_video.get('youtube_link')}")
                            self.fila_videos.append({"titulo": tit, **dados_video})
                            self.driver.close()
                            self._trocar_para_janela_segura(jp, "retorno da extração de vídeo")
                        except Exception as ex:
                            self.log("ERRO", f"Falha ao extrair vídeo na URL {url}: {str(ex)}")
                            close_extra_windows(
                                self.driver,
                                {jp},
                                "fechamento de aba temporária de vídeo",
                            )
                            self._trocar_para_janela_segura(jp, "retorno após falha na extração de vídeo")
                else:
                    self.log("AVISO", "Nenhum link de vídeo (alterar_video.asp) encontrado na página de listagem!")
            else:
                self.log("AVISO", "Botão de vídeos (videos.asp) NÃO encontrado na página do módulo!")
            self._abrir_url_com_certificado(d_url, "retorno ao módulo antigo após vídeos")

        if capturar_materiais:
            self.log("INFO", "Iniciando captura de materiais do módulo no site antigo...")
            setores = {
                "Material Impresso": {"xp": "//a[contains(@href, 'setor=1')]", "id": "1"},
                "Slides": {"xp": "//a[contains(@href, 'setor=2')]", "id": "4"},
                "Atividades": {"xp": "//a[contains(@href, 'setor=4')]", "id": "3"},
            }
            for nm, inf in setores.items():
                self.driver.switch_to.default_content()
                botao_setor = self._localizar_elemento_recursivo_frames(inf["xp"])
                if botao_setor:
                    try:
                        self.log("INFO", f"Acessando setor de materiais: {nm}...")
                        href_setor = botao_setor.get_attribute("href") or ""
                        if href_setor and not href_setor.startswith("#") and "javascript" not in href_setor:
                            self._abrir_url_com_certificado(href_setor, f"setor antigo: {nm}")
                        else:
                            self.driver.execute_script("arguments[0].click();", botao_setor)
                        time.sleep(2)
                        
                        try:
                            self.driver.switch_to.default_content()
                            p = self.driver.find_element(
                                By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
                            )
                            self.driver.execute_script("arguments[0].click();", p)
                            time.sleep(0.5)
                            self.driver.execute_script(
                                "arguments[0].click();",
                                self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']"),
                            )
                            time.sleep(2.5)
                        except:
                            pass
                        
                        sp = BeautifulSoup(self.driver.page_source, "html.parser")
                        ls = []
                        for it in sp.find_all("div", class_="list-item box"):
                            subject = it.find("td", class_="subject")
                            t = subject.text.strip() if subject and subject.text else "Sem Titulo"
                            for a in it.find_all("a", href=True):
                                href = str(a.get("href", ""))
                                if "arquivoid.asp" in href.lower():
                                    ls.append(
                                        {
                                            "titulo": t,
                                            "url_ver": urljoin(self.driver.current_url, href),
                                            "categoria_id": inf["id"],
                                            "nome_categoria": nm,
                                        }
                                    )
                                    break
                        if ls:
                            self.log("INFO", f"Encontrados {len(ls)} materiais no setor {nm}.")
                            ls.reverse()
                            self.fila_arquivos.extend(ls)
                        else:
                            self.log("INFO", f"Nenhum material encontrado no setor {nm}.")
                    except Exception as e_mat:
                        self.log("ERRO", f"Erro no setor {nm}: {str(e_mat)}")
                    self._abrir_url_com_certificado(d_url, "retorno ao módulo antigo após materiais")
                else:
                    self.log("INFO", f"Setor {nm} não disponível neste módulo.")

    def _extrair_dados_modulo_antigo_unico(self, capturar_videos=True, capturar_materiais=True):
        dashboard_url = self.driver.current_url
        self.fila_videos.clear()
        self.fila_arquivos.clear()

        if capturar_videos:
            self.log("INFO", "Iniciando captura de vídeos do módulo único no site antigo...")
            botao_video = self._localizar_elemento_recursivo_frames("//a[contains(@href, 'videos.asp')]")
            if botao_video:
                self.log("INFO", "Botão de vídeos (videos.asp) encontrado! Acessando...")
                href_videos = botao_video.get_attribute("href") or ""
                if href_videos and not href_videos.startswith("#") and "javascript" not in href_videos:
                    self._abrir_url_com_certificado(href_videos, "lista de vídeos do módulo único no site antigo")
                else:
                    self.driver.execute_script("arguments[0].click();", botao_video)
                time.sleep(2)
                
                try:
                    self.driver.switch_to.default_content()
                    p = self.driver.find_element(
                        By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
                    )
                    self.driver.execute_script("arguments[0].click();", p)
                    time.sleep(0.5)
                    self.driver.execute_script(
                        "arguments[0].click();",
                        self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']"),
                    )
                    time.sleep(2.5)
                except Exception:
                    pass

                def buscar_todos_links(lista_acumulada):
                    lk = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'alterar_video.asp')]")
                    for l in lk:
                        href = l.get_attribute("href")
                        if href and href not in lista_acumulada:
                            lista_acumulada.append(href)
                    
                    frames = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
                    for f in frames:
                        try:
                            self.driver.switch_to.frame(f)
                            buscar_todos_links(lista_acumulada)
                            self.driver.switch_to.parent_frame()
                        except:
                            try:
                                self.driver.switch_to.parent_frame()
                            except:
                                pass

                self.log("INFO", "Procurando links de vídeos (alterar_video.asp) para módulo único...")
                self.driver.switch_to.default_content()
                urls = []
                buscar_todos_links(urls)
                
                if urls:
                    self.log("INFO", f"Encontrados {len(urls)} vídeos para extrair.")
                    urls.reverse()
                    janela_princ = self.driver.current_window_handle
                    for idx, url in enumerate(urls, 1):
                        janelas_antes = set(self.driver.window_handles)
                        try:
                            self.log("INFO", f"Extraindo vídeo {idx}/{len(urls)}...")
                            self.driver.execute_script("window.open(arguments[0], '_blank');", url)
                            WebDriverWait(self.driver, 5).until(
                                lambda d: len(d.window_handles) > len(janelas_antes)
                            )
                            nova_aba = list(set(self.driver.window_handles) - janelas_antes)[0]
                            self.driver.switch_to.window(nova_aba)
                            self._ignorar_aviso_certificado_se_aparecer("extração de vídeo do módulo único")

                            wait_local = WebDriverWait(self.driver, 5)
                            elem_t = wait_local.until(EC.presence_of_element_located((By.ID, "assunto")))
                            raw_title = elem_t.get_attribute("value") or ""
                            tit = " ".join(
                                [
                                    (
                                        p
                                        if p in ["de", "da", "do", "e", "a", "o", "em", "na", "no", "com", "por", "para"]
                                        else p.capitalize()
                                    )
                                    for p in " ".join(raw_title.strip().split()).lower().split()
                                ]
                            )
                            dados_video = self._extrair_dados_video_antigo()
                            self.log("OK", f"Vídeo {idx} extraído: '{tit}' -> Vimeo: {dados_video.get('vimeo')}, Youtube: {dados_video.get('youtube_link')}")
                            self.fila_videos.append({"titulo": tit, **dados_video})
                        except Exception as e:
                            self.log("ERRO", f"Falha ao extrair vídeo na URL {url}: {str(e)}")
                            self._registrar_falha_worker(
                                f"Frota {self.worker_id} - extracao de video do modulo unico",
                                e,
                                "extracao_video_unico",
                                url,
                            )
                        finally:
                            for aba in list(set(self.driver.window_handles) - janelas_antes):
                                try:
                                    self.driver.switch_to.window(aba)
                                    self.driver.close()
                                except Exception:
                                    pass
                            self.driver.switch_to.window(janela_princ)
                else:
                    self.log("AVISO", "Nenhum link de vídeo (alterar_video.asp) encontrado!")
            else:
                self.log("AVISO", "Botão de vídeos (videos.asp) NÃO encontrado na página do módulo único!")
            self._abrir_url_com_certificado(dashboard_url, "retorno ao módulo único após vídeos")

        if capturar_materiais:
            self.log("INFO", "Iniciando captura de materiais do módulo único no site antigo...")
            links_setores = {
                "Material Impresso": {"xpath": "//a[contains(@href, 'setor=1')]", "cat_id": "1"},
                "Slides": {"xpath": "//a[contains(@href, 'setor=2')]", "cat_id": "4"},
                "Atividades": {"xpath": "//a[contains(@href, 'setor=4')]", "cat_id": "3"},
            }

            for nome, info in links_setores.items():
                self.driver.switch_to.default_content()
                botao_setor = self._localizar_elemento_recursivo_frames(info["xpath"])
                if botao_setor:
                    try:
                        self.log("INFO", f"Acessando setor de materiais do módulo único: {nome}...")
                        href_setor = botao_setor.get_attribute("href") or ""
                        if href_setor and not href_setor.startswith("#") and "javascript" not in href_setor:
                            self._abrir_url_com_certificado(href_setor, f"setor do módulo único: {nome}")
                        else:
                            self.driver.execute_script("arguments[0].click();", botao_setor)
                        time.sleep(2)
                        
                        try:
                            self.driver.switch_to.default_content()
                            p = self.driver.find_element(
                                By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
                            )
                            self.driver.execute_script("arguments[0].click();", p)
                            time.sleep(0.5)
                            self.driver.execute_script(
                                "arguments[0].click();",
                                self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']"),
                            )
                            time.sleep(2.5)
                        except Exception:
                            pass

                        soup = BeautifulSoup(self.driver.page_source, "html.parser")
                        lote_setor = []
                        for item in soup.find_all("div", class_="list-item box"):
                            subject = item.find("td", class_="subject")
                            titulo = subject.text.strip() if subject and subject.text else "Sem Titulo"
                            for a_tag in item.find_all("a", href=True):
                                href = str(a_tag.get("href", ""))
                                if "arquivoid.asp" in href.lower():
                                    lote_setor.append(
                                        {
                                            "titulo": titulo,
                                            "url_ver": urljoin(self.driver.current_url, href),
                                            "categoria_id": info["cat_id"],
                                            "nome_categoria": nome,
                                        }
                                    )
                                    break
                        if lote_setor:
                            self.log("INFO", f"Encontrados {len(lote_setor)} materiais no setor {nome}.")
                            lote_setor.reverse()
                            self.fila_arquivos.extend(lote_setor)
                        else:
                            self.log("INFO", f"Nenhum material encontrado no setor {nome}.")
                    except Exception as e:
                        self.log("ERRO", f"Erro no setor de material {nome}: {str(e)}")
                        self._registrar_falha_worker(
                            f"Frota {self.worker_id} - extracao de materiais do modulo unico",
                            e,
                            "extracao_materiais_unico",
                            nome,
                        )
                    self._abrir_url_com_certificado(dashboard_url, "retorno ao módulo único após materiais")
                else:
                    self.log("INFO", f"Setor {nome} não disponível neste módulo único.")

    def _vincular_material_ao_modulo(self, wait, modulo_nome):
        ultimo_erro = None

        try:
            self._preencher_pesquisa_livewire_multiplos_rotulos(
                wait, ["MÃ³dulo", "Modulo"], modulo_nome
            )
            time.sleep(1.5)
            return
        except Exception as exc:
            ultimo_erro = exc

        inputs = self.driver.find_elements(
            By.XPATH, "//input[@type='text' and contains(@class, 'form-control')]"
        )
        valor_busca = modulo_nome.lower().replace("'", "")
        xp_opcao = (
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
            f"'{valor_busca}') and not(*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            f"'abcdefghijklmnopqrstuvwxyz'), '{valor_busca}')])]"
        )

        for campo in inputs:
            try:
                wire_model = (campo.get_attribute("wire:model") or "").strip()
                if wire_model == "attachment.name":
                    continue
                if campo.get_attribute("value"):
                    continue

                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", campo
                )
                time.sleep(0.4)
                self.preencher_input_humano(campo, modulo_nome)
                time.sleep(4.5)

                for opcao in self.driver.find_elements(By.XPATH, xp_opcao):
                    try:
                        if not opcao.is_displayed():
                            continue
                        if opcao.tag_name.lower() in {"input", "html", "body"}:
                            continue
                        try:
                            ActionChains(self.driver).move_to_element(opcao).click().perform()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", opcao)
                        time.sleep(1.2)
                        return
                    except Exception:
                        continue
            except Exception as exc:
                ultimo_erro = exc

        if ultimo_erro:
            raise ultimo_erro
        raise Exception("NÃ£o foi possÃ­vel vincular o material ao mÃ³dulo no site novo.")

    def _injetar_videos(self, wait, m_nome):
        if self._eh_modulo_plano_estudos(m_nome):
            self._forcar_video_plano_estudos()
        for d in list(self.fila_videos):
            if self.motor.parar_loop:
                break
            payload = resolve_video_payload(
                m_nome,
                title=d.get("titulo", ""),
                vimeo=d.get("vimeo", ""),
                youtube_link=d.get("youtube_link", ""),
                canal=d.get("canal", ""),
            )
            if not payload:
                self.log("ERRO", f"Vídeo inválido: {d['titulo']}")
                self._registrar_auditoria_item(
                    m_nome, "Vídeo", d["titulo"], "ERRO", "payload_invalido"
                )
                self.ordem_atual += 1
                continue
            tipo_video = "YouTube" if payload.canal == "youtube" else "Vimeo"
            try:
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "add_new_btn"))).click()
                time.sleep(0.6)
                self._selecionar_canal_video(payload.canal)
                cv = self._localizar_campo_video(wait, payload.canal)
                self.preencher_input(cv, payload.valor)
                cv.send_keys(Keys.TAB)
                time.sleep(2.2)
                try:
                    wait.until(
                        lambda x: x.find_element(
                            By.XPATH, "//input[@*[name()='wire:model']='lessons.time']"
                        ).get_attribute("value")
                        not in ["", "0"]
                    )
                except:
                    self.preencher_input(
                        self.driver.find_element(
                            By.XPATH, "//input[@*[name()='wire:model']='lessons.time']"
                        ),
                        "1",
                    )
                self.preencher_input(
                    self.driver.find_element(
                        By.XPATH, "//input[@*[name()='wire:model']='lessons.order']"
                    ),
                    str(self.ordem_atual),
                )
                time.sleep(0.5)
                self.preencher_input(
                    self.driver.find_element(
                        By.XPATH, "//input[@*[name()='wire:model']='lessons.name']"
                    ),
                    payload.titulo,
                )
                time.sleep(0.5)
                self.preencher_input(
                    self.driver.find_element(
                        By.XPATH, "//input[@*[name()='wire:model']='lessons.filename']"
                    ),
                    payload.titulo,
                )
                time.sleep(0.5)
                self.driver.find_element(
                    By.XPATH, "//input[@*[name()='wire:model']='lessons.publish_date']"
                ).send_keys(datetime.now().strftime("%d%m%Y"))
                time.sleep(1)
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Salvar')]").click()
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "add_new_btn")))
                time.sleep(0.5)
                self.log("OK", f"{tipo_video} Subido: {payload.titulo[:15]}...")
                self._registrar_auditoria_item(
                    m_nome, "Vídeo", payload.titulo, "Sucesso", payload.origem
                )
                self.ordem_atual += 1
            except Exception:
                self.log("ERRO", f"Falha no {tipo_video} {payload.titulo[:15]}")
                self._registrar_auditoria_item(
                    m_nome, "Vídeo", payload.titulo, "ERRO", payload.origem
                )
                try:
                    self.driver.refresh()
                    time.sleep(3)
                except:
                    pass

    def _injetar_materiais(self, wait, m_nome, aba_ant, aba_nov):
        ss = requests.Session()
        ss.verify = False
        try:
            requests.packages.urllib3.disable_warnings()
        except Exception:
            pass
        self._trocar_para_janela_segura(aba_ant, "coleta de cookies do site antigo")
        for c in self.driver.get_cookies():
            ss.cookies.set(c["name"], c["value"])
        self._trocar_para_janela_segura(aba_nov, "retorno ao site novo para materiais")
        psta = f"arquivos_migracao_{self.worker_id}"
        if not os.path.exists(psta):
            os.makedirs(psta)

        for d in list(self.fila_arquivos):
            if self.motor.parar_loop:
                break
            try:
                self._trocar_para_janela_segura(aba_ant, "download de material no site antigo")
                ab_t = open_new_tab(
                    self.driver, d["url_ver"], "aba temporária do material", timeout=5
                )
                self._trocar_para_janela_segura(ab_t, "aba temporária do material")
                self._ignorar_aviso_certificado_se_aparecer("aba temporária do material")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                bs = BeautifulSoup(self.driver.page_source, "html.parser")
                exts = [
                    ".pdf",
                    ".ppt",
                    ".pptx",
                    ".doc",
                    ".docx",
                    ".xls",
                    ".xlsx",
                    ".zip",
                    ".rar",
                    ".pps",
                ]
                lk = bs.find(
                    "a", href=lambda h: any(ext in str(h).lower() for ext in exts)
                )
                if not lk:
                    def _is_download_link(tag):
                        if getattr(tag, "name", None) != "a":
                            return False
                        txt = tag.get_text(strip=True) or ""
                        return bool(
                            re.search(r"baixar|download|arquivo|salvar", txt, re.IGNORECASE)
                        )

                    lk = bs.find(_is_download_link)
                if not lk:
                    raise Exception("Sem link")
                href = str(lk.get("href", ""))
                u_arq = urljoin("https://cursoms.com.br/ead/", href.replace("../../", ""))
                n_arq = re.sub(r'[\\/*?:"<>|]', "", d["titulo"])[:60] + next(
                    (e for e in exts if e in u_arq.lower()), ".pdf"
                )
                cm = os.path.abspath(os.path.join(psta, n_arq))
                resposta_arquivo = ss.get(u_arq, timeout=30)
                resposta_arquivo.raise_for_status()
                with open(cm, "wb") as f:
                    f.write(resposta_arquivo.content)
                self.driver.close()
                self._trocar_para_janela_segura(aba_nov, "upload do material no site novo")

                self.driver.get("https://novo.cursoms.com.br/attachments/create")
                fi = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, SELECTORS.attachment_file_css)
                    )
                )
                self.driver.execute_script(
                    "arguments[0].style.display='block'; arguments[0].style.visibility='visible';",
                    fi,
                )
                fi.send_keys(cm)
                i_n = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, SELECTORS.attachment_name_css)
                    )
                )
                self.preencher_input_humano(i_n, d["titulo"][:65].strip())
                cv = d.get("categoria_id", "1")
                self._definir_select_livewire(
                    wait, SELECTORS.attachment_type_css, str(cv), "categoria do material"
                )
                self._definir_select_livewire(
                    wait, SELECTORS.attachment_attachable_css, "Module", "tipo de vinculo"
                )
                self._preencher_pesquisa_livewire_multiplos_rotulos(
                    wait, ["Módulo", "Modulo"], m_nome
                )
                time.sleep(1.5)
                try:
                    bts = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
                    cl = False
                    for b in bts:
                        if b.is_displayed():
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();",
                                b,
                            )
                            cl = True
                            break
                    if not cl:
                        self.driver.execute_script("Livewire.first().call('handleSubmit');")
                except:
                    pass
                time.sleep(5)
                self.driver.get("https://novo.cursoms.com.br/attachments")
                time.sleep(2)
                try:
                    os.remove(cm)
                except:
                    pass
                self.log("OK", f"Arquivo Subido: {d['titulo'][:15]}...")
                self._registrar_auditoria_item(m_nome, "Material", d["titulo"], "Sucesso")
            except Exception as e:
                self.log("ERRO", f"Arquivo {d['titulo'][:15]}: {str(e)[:90]}")
                self._registrar_falha_worker(
                    f"Frota {self.worker_id} - material {d['titulo'][:40]}",
                    e,
                    "upload_material_novo",
                    d["titulo"],
                )
                self._registrar_auditoria_item(m_nome, "Material", d["titulo"], "ERRO")
                try:
                    close_extra_windows(
                        self.driver,
                        {aba_ant, aba_nov},
                        "fechamento de abas temporárias de material",
                    )
                    self._trocar_para_janela_segura(aba_nov, "retorno final ao site novo")
                except:
                    pass


# * =========================================================================
# * APP LOGIN E MOTOR PRINCIPAL
# * =========================================================================
class AppPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.carregar_dados_login()
        ctk.set_appearance_mode(self.config.get("theme", "dark"))
        self.title("ISAURA V106 — Login | Conteúdo Seletivo")
        self.geometry("450x650")
        _bg_app = BG_WINDOW if self.config.get("theme", "dark") == "dark" else "#F1F5F9"
        self.configure(fg_color=_bg_app)
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = (largura_tela // 2) - (450 // 2)
        pos_y = (altura_tela // 2) - (650 // 2)
        self.geometry(f"450x650+{pos_x}+{pos_y}")
        self.attributes("-topmost", True)
        self.construir_tela_login()
        if getattr(self, "config_load_error", None):
            self.after(
                200,
                lambda: messagebox.showwarning(
                    "Configurações",
                    f"Não foi possível ler totalmente o config_unificada.json.\n{self.config_load_error}",
                ),
            )

    def carregar_dados_login(self):
        self.arquivo_config = CONFIG_PATH
        self.dados_padrao = dict(DEFAULT_CONFIG)
        self.config, self.config_load_error = load_config(self.arquivo_config, self.dados_padrao)

    def salvar_dados_login(self, usuario, lembrar):
        self.config["lembrar_user"] = usuario if lembrar else ""
        try:
            save_config(self.arquivo_config, self.config)
        except Exception:
            return

    def construir_tela_login(self):
        _bg_card = BG_CARD if self.config.get("theme", "dark") == "dark" else "#FFFFFF"
        _text_color = TEXT_LIGHT if self.config.get("theme", "dark") == "dark" else "#1E293B"
        _input_bg = BG_INPUT if self.config.get("theme", "dark") == "dark" else "#F8FAFC"

        self.card = ctk.CTkFrame(
            self, fg_color=_bg_card, border_width=1, border_color=BORDER_COLOR, corner_radius=16
        )
        self.card.pack(expand=True, fill="both", padx=40, pady=60)
        ctk.CTkLabel(self.card, text="🧠", font=("Arial", 45), text_color=VERDE_ACAO).pack(
            pady=(30, 5)
        )
        ctk.CTkLabel(
            self.card, text="Welcome Back", font=("Inter", 24, "bold"), text_color=_text_color
        ).pack()
        ctk.CTkLabel(
            self.card,
            text="Secure automation login portal",
            font=("Inter", 12),
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 25))
        fu = ctk.CTkFrame(self.card, fg_color="transparent")
        fu.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(fu, text="Usuário", font=("Inter", 12, "bold"), text_color=TEXT_MUTED).pack(
            anchor="w", padx=5
        )
        self.ent_user = ctk.CTkEntry(
            fu,
            placeholder_text="Digite seu usuário",
            height=45,
            fg_color=_input_bg,
            border_color=BORDER_COLOR,
            text_color=_text_color,
            corner_radius=8,
        )
        self.ent_user.pack(fill="x", pady=(2, 0))
        if self.config.get("lembrar_user"):
            self.ent_user.insert(0, self.config.get("lembrar_user"))
        fp = ctk.CTkFrame(self.card, fg_color="transparent")
        fp.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(fp, text="Senha", font=("Inter", 12, "bold"), text_color=TEXT_MUTED).pack(
            anchor="w", padx=5
        )
        self.ent_pass = ctk.CTkEntry(
            fp,
            placeholder_text="Digite sua senha",
            show="•",
            height=45,
            fg_color=_input_bg,
            border_color=BORDER_COLOR,
            text_color=_text_color,
            corner_radius=8,
        )
        self.ent_pass.pack(fill="x", pady=(2, 0))
        fo = ctk.CTkFrame(self.card, fg_color="transparent")
        fo.pack(fill="x", padx=30, pady=5)
        self.var_lembrar = ctk.BooleanVar(value=bool(self.config.get("lembrar_user")))
        chk = ctk.CTkCheckBox(
            fo,
            text="Lembrar",
            variable=self.var_lembrar,
            font=("Inter", 12),
            text_color=TEXT_MUTED,
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            border_color=BORDER_COLOR,
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
        )
        chk.pack(side="left")
        ctk.CTkButton(
            fo,
            text="Esqueceu a senha?",
            font=("Inter", 12, "bold"),
            text_color=VERDE_ACAO,
            fg_color="transparent",
            hover_color=_input_bg,
            width=10,
            command=self.recuperar_senha,
        ).pack(side="right")
        ctk.CTkButton(
            self.card,
            text="ENTRAR",
            font=("Inter", 14, "bold"),
            height=48,
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            corner_radius=8,
            command=self.fazer_login,
        ).pack(fill="x", padx=30, pady=(20, 10))
        self.lbl_status = ctk.CTkLabel(
            self.card, text="", text_color=VERMELHO_PARAR, font=("Inter", 12, "bold")
        )
        self.lbl_status.pack()

    def recuperar_senha(self):
        messagebox.showinfo("Recuperação", "Contacte o administrador para redefinir a senha.")

    def fazer_login(self):
        user = self.ent_user.get().strip()
        senha = self.ent_pass.get().strip()
        lembrar = self.var_lembrar.get()
        if not user or not senha:
            return self.lbl_status.configure(
                text="⚠️ Preencha usuário e senha!", text_color="#F59E0B"
            )
        self.salvar_dados_login(user, lembrar)
        self.lbl_status.configure(text="Conectando...", text_color=VERDE_ACAO)
        self.update()
        try:
            url_api = "https://wesleyadrion.pythonanywhere.com/api/login/"
            resposta = requests.post(
                url_api, json={"username": user, "password": senha}, timeout=10
            )
            try:
                dados = resposta.json()
            except ValueError:
                return self.lbl_status.configure(
                    text=f"❌ O Servidor retornou HTML.", text_color=VERMELHO_PARAR
                )
            if resposta.status_code != 200:
                return self.lbl_status.configure(
                    text=f"❌ Erro {resposta.status_code}.", text_color=VERMELHO_PARAR
                )
            if dados.get("status") == "sucesso":
                self.iniciar_robo_principal()
            else:
                self.lbl_status.configure(
                    text=f"❌ {dados.get('mensagem', 'Usuário/senha incorretos')}",
                    text_color=VERMELHO_PARAR,
                )
        except Exception as e:
            self.lbl_status.configure(text=f"⚠️ Erro de rede", text_color=VERMELHO_PARAR)

    def iniciar_robo_principal(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.title("ISAURA V106 — CONTEÚDO SELETIVO (PLANILHA)")
        self.geometry("1380x960")
        MotorRobo(self, self.config)


class MotorRobo:
    def __init__(self, root, config_carregada):
        self.root = root
        self.config = config_carregada
        self.gui_queue = queue.Queue()
        self.parar_loop = False
        self.is_running = False
        self.error_logger = ErrorLogger(LOGS_DIR)
        self.history_repo = HistoryRepository(DB_PATH)

        self.lista_de_planilhas = []
        self.auditoria = []
        self.evento_inicio_trabalho = threading.Event()
        self.progresso_lock = threading.Lock()
        self.total_modulos = 0
        self.modulos_concluidos = 0
        self.workers_ativos = 0
        self.stats_contagem = {"Sucesso": 0, "Erro": 0, "Aviso": 0}
        self.tempo_inicio_trabalho = None
        self.upload_mode = str(self.config.get("upload_mode", "completo") or "completo")
        self.module_scope = "todos"
        self.single_module_target = str(self.config.get("single_module_target", "") or "").strip()
        self.manual_platform_driver: Optional[WebDriver] = None
        self.manual_platform_lock = threading.Lock()

        global motor_global
        motor_global = self
        threading.Thread(target=start_flask_server, daemon=True).start()

        self.rotacionar_logs()
        self.inicializar_banco_dados()
        self.setup_ui()
        self.ativar_atalhos()
        self.processar_fila_gui()

    def tocar_som(self, tipo):
        som_path = f"sounds/{tipo}.wav"
        if os.path.exists(som_path):
            try:
                winsound.PlaySound(som_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except RuntimeError as exc:
                self.registrar_falha_caixa_preta(f"tocar_som:{tipo}", exc)
        else:
            if tipo == "start":
                winsound.Beep(800, 200)
            elif tipo == "success":
                caminho_musica = os.path.join(BASE_DIR, "Escrava-isaura-_fundo_.wav")
                if os.path.exists(caminho_musica):
                    winsound.PlaySound(caminho_musica, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    winsound.Beep(1200, 300)
                    time.sleep(0.1)
                    winsound.Beep(1200, 300)
            elif tipo == "error":
                winsound.Beep(400, 500)

    def rotacionar_logs(self):
        self.error_logger.rotate(retention_days=7)

    def registrar_falha_caixa_preta(self, local_erro, excecao):
        try:
            self.error_logger.write_failure(local_erro, excecao)
        except Exception:
            return

    def inicializar_banco_dados(self):
        try:
            self.history_repo.initialize()
        except Exception as exc:
            self.registrar_falha_caixa_preta("inicializar_banco_dados", exc)

    def salvar_no_banco(self, nome_modulo, curso, professor, status, arquivo_origem=""):
        try:
            self.history_repo.insert_history(
                nome_modulo, curso, professor, status, arquivo_origem
            )
        except Exception as exc:
            self.registrar_falha_caixa_preta("salvar_no_banco", exc)

    def modo_auditoria_ativo(self):
        return bool(self.config.get("audit_mode", False))

    def deve_subir_videos(self):
        return self.upload_mode in {"completo", "videos"}

    def deve_subir_materiais(self):
        return self.upload_mode in {"completo", "materiais"}

    def modo_somente_conteudo(self):
        return self.upload_mode in {"videos", "materiais"}

    def descricao_modo_upload(self):
        descricoes = {
            "completo": "Módulo completo",
            "videos": "Só vídeos",
            "materiais": "Só materiais",
        }
        return descricoes.get(self.upload_mode, "Módulo completo")

    def descricao_resumida_conteudo(self):
        descricoes = {
            "completo": "vídeos e materiais",
            "videos": "vídeos",
            "materiais": "materiais",
        }
        return descricoes.get(self.upload_mode, "vídeos e materiais")

    def descricao_escopo(self):
        if self.module_scope == "unico":
            alvo = self.single_module_target or "1 módulo"
            return f"Só um módulo ({alvo})"
        return "Todos os módulos"

    def _registro_corresponde_filtro(self, row, filtro_texto):
        nome_modulo = extract_module_name_from_row(row)
        if not nome_modulo:
            return False
        filtro = (filtro_texto or "").strip()
        if not filtro:
            return False
        nome_variantes = build_module_name_variants(nome_modulo)
        filtro_variantes = build_module_name_variants(filtro)
        if not nome_variantes or not filtro_variantes:
            return False
        if nome_variantes.intersection(filtro_variantes):
            return True

        for nome_normalizado in nome_variantes:
            for filtro_normalizado in filtro_variantes:
                menor = min(len(nome_normalizado), len(filtro_normalizado))
                if menor >= 18 and (
                    nome_normalizado in filtro_normalizado or filtro_normalizado in nome_normalizado
                ):
                    return True
        return False

    def _filtrar_planilhas_para_execucao(self):
        planilhas_filtradas = []
        total_modulos = 0
        filtro = self.single_module_target.strip()
        indice_desejado = None
        somente_indice = filtro.isdigit()

        if self.module_scope == "unico":
            if not filtro:
                raise ValueError(
                    "Informe o n\u00famero da linha ou o nome do m\u00f3dulo para o modo 'S\u00f3 um m\u00f3dulo'."
                )
            if somente_indice and self.lista_de_planilhas and len(self.lista_de_planilhas) > 1:
                raise ValueError(
                    "Com mais de uma planilha carregada, use o nome do m\u00f3dulo no modo 'S\u00f3 um m\u00f3dulo'."
                )
            if somente_indice and not self.lista_de_planilhas:
                raise ValueError(
                    "Sem planilha carregada, use o nome do m\u00f3dulo em vez do n\u00famero da linha."
                )

        if self.module_scope == "unico":
            if not filtro:
                raise ValueError("Informe o número da linha ou o nome do módulo para o modo 'Só um módulo'.")
            if filtro.isdigit() and self.lista_de_planilhas:
                indice_desejado = max(int(filtro) - 1, 0)
            elif filtro.isdigit() and not self.lista_de_planilhas:
                raise ValueError(
                    "Sem planilha carregada, use o nome do mÃ³dulo em vez do nÃºmero da linha."
                )

        if self.module_scope == "unico" and not self.lista_de_planilhas:
            row = {
                "nome do modulo": filtro,
                "modulo": filtro,
                "_manual_single_module": True,
            }
            return [{"nome": "modo_unico_manual", "dados": [row], "total": 1}], 1

        for planilha in self.lista_de_planilhas:
            dados_originais = [
                {**dict(row), "_source_index": indice}
                for indice, row in enumerate(planilha.get("dados", []))
            ]
            dados_filtrados = dados_originais

            if self.module_scope == "unico":
                if indice_desejado is not None:
                    dados_filtrados = (
                        [dados_originais[indice_desejado]]
                        if indice_desejado < len(dados_originais)
                        else []
                    )
                else:
                    dados_filtrados = [
                        row for row in dados_originais if self._registro_corresponde_filtro(row, filtro)
                    ]

            if not dados_filtrados:
                continue

            planilhas_filtradas.append(
                {
                    "nome": planilha.get("nome", ""),
                    "dados": dados_filtrados,
                    "total": len(dados_filtrados),
                }
            )
            total_modulos += len(dados_filtrados)

        return planilhas_filtradas, total_modulos

    def atualizar_resumo_modo(self):
        if self.module_scope == "todos":
            resumo = "Planilha acima = subir vários módulos"
        else:
            alvo = self.single_module_target or "informe a linha ou o nome do módulo"
            resumo = f"Modo atual: {self.descricao_modo_upload()} de um módulo | Alvo: {alvo}"
        if hasattr(self, "lbl_modo_resumo"):
            self.lbl_modo_resumo.configure(text=resumo)

    def descricao_modo_upload(self):
        descricoes = {
            "completo": "M\u00f3dulo completo",
            "videos": "S\u00f3 v\u00eddeos",
            "materiais": "S\u00f3 materiais",
        }
        return descricoes.get(self.upload_mode, "M\u00f3dulo completo")

    def descricao_resumida_conteudo(self):
        descricoes = {
            "completo": "v\u00eddeos e materiais",
            "videos": "v\u00eddeos",
            "materiais": "materiais",
        }
        return descricoes.get(self.upload_mode, "v\u00eddeos e materiais")

    def descricao_escopo(self):
        if self.module_scope == "unico":
            alvo = self.single_module_target or "1 m\u00f3dulo"
            return f"S\u00f3 um m\u00f3dulo ({alvo})"
        return "Todos os m\u00f3dulos"

    def atualizar_resumo_modo(self):
        if self.module_scope == "todos":
            resumo = "Planilha acima = subir v\u00e1rios m\u00f3dulos"
        else:
            alvo = self.single_module_target or "informe a linha ou o nome do m\u00f3dulo"
            resumo = f"Modo atual: {self.descricao_modo_upload()} de um m\u00f3dulo | Alvo: {alvo}"
        if hasattr(self, "lbl_modo_resumo"):
            self.lbl_modo_resumo.configure(text=resumo)

    def atualizar_botoes_modo(self):
        if hasattr(self, "botoes_preset"):
            for (modo, escopo), botao in self.botoes_preset.items():
                selecionado = modo == self.upload_mode and escopo == self.module_scope
                cor = "#F59E0B" if escopo == "todos" else (AZUL_PASSO if modo == "videos" else "#14B8A6" if modo == "materiais" else VERDE_ACAO)
                hover = "#D97706" if escopo == "todos" else ("#1D4ED8" if modo == "videos" else "#0F766E" if modo == "materiais" else VERDE_HOVER)
                cor_base = "#4C3410" if escopo == "todos" else ("#112C66" if modo == "videos" else "#0D4040" if modo == "materiais" else "#113D31")
                botao.configure(
                    fg_color=cor if selecionado else cor_base,
                    hover_color=hover,
                    border_color=cor,
                    text_color="#FFFFFF",
                )

        if hasattr(self, "frame_modulo_unico"):
            self.frame_modulo_unico.pack_forget()

        self.atualizar_resumo_modo()

    def selecionar_preset_execucao(self, modo, escopo):
        self.upload_mode = modo
        self.module_scope = escopo
        self.config["upload_mode"] = modo
        self.config["module_scope"] = escopo
        if hasattr(self, "ent_modulo_alvo"):
            self.single_module_target = self.ent_modulo_alvo.get().strip()
        self.config["single_module_target"] = self.single_module_target
        try:
            save_config(CONFIG_PATH, self.config)
        except Exception:
            pass
        self.atualizar_botoes_modo()

    def selecionar_modo_upload(self, modo):
        self.upload_mode = modo
        self.config["upload_mode"] = modo
        try:
            save_config(CONFIG_PATH, self.config)
        except Exception:
            pass
        self.atualizar_botoes_modo()

    def selecionar_escopo(self, escopo):
        self.module_scope = escopo
        self.config["module_scope"] = escopo
        self.single_module_target = self.ent_modulo_alvo.get().strip() if hasattr(self, "ent_modulo_alvo") else self.single_module_target
        self.config["single_module_target"] = self.single_module_target
        try:
            save_config(CONFIG_PATH, self.config)
        except Exception:
            pass
        self.atualizar_botoes_modo()

    def atualizar_alvo_modulo(self, _event=None):
        if not hasattr(self, "ent_modulo_alvo"):
            return
        self.single_module_target = self.ent_modulo_alvo.get().strip()
        self.config["single_module_target"] = self.single_module_target
        try:
            save_config(CONFIG_PATH, self.config)
        except Exception:
            pass
        self.atualizar_resumo_modo()

    def abrir_plataformas(self):
        threading.Thread(target=self._abrir_plataformas_worker, daemon=True).start()

    def _abrir_plataformas_worker(self):
        try:
            with self.manual_platform_lock:
                if session_is_active(self.manual_platform_driver):
                    try:
                        self.manual_platform_driver.maximize_window()
                    except Exception:
                        pass
                    self.log("INFO", "Chrome das plataformas ja esta aberto.")
                    return

                self.log("INFO", "Abrindo Chrome e conectando nas plataformas...")
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=build_chrome_options_accepting_old_certificates(),
                )
                driver.maximize_window()
                wait = WebDriverWait(driver, 15)

                ignorou_certificado = navigate_with_certificate_bypass(
                    driver,
                    self.config.get("antigo_url", "https://cursoms.com.br/ead/admin/principal.asp"),
                    "login manual do site antigo",
                )
                if ignorou_certificado:
                    self.log("INFO", "Aviso de certificado ignorado no login manual do site antigo.")
                wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao"))).send_keys(
                    self.config.get("antigo_user", "")
                )
                driver.find_element(By.NAME, "senhadagestao").send_keys(
                    self.config.get("antigo_pass", "")
                )
                driver.find_element(By.XPATH, "//input[@value='Entrar']").click()

                aba_nova = open_new_tab(
                    driver,
                    self.config.get("novo_url", "https://novo.cursoms.com.br/login"),
                    "abertura da plataforma nova",
                )
                safe_switch_to_window(driver, aba_nova, "login da plataforma nova")
                wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(
                    self.config.get("novo_user", "")
                )
                senha = driver.find_element(By.NAME, "password")
                senha.send_keys(self.config.get("novo_pass", ""))
                senha.send_keys(Keys.ENTER)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                self.manual_platform_driver = driver
                self.log(
                    "OK",
                    "Chrome aberto com site antigo e novo prontos. Esse botao nao depende de planilha.",
                )
        except Exception as exc:
            self.manual_platform_driver = None
            self.registrar_falha_caixa_preta("abrir_plataformas", exc)
            self.log("ERRO", f"Falha ao abrir plataformas: {str(exc)[:90]}")

    def processar_fila_gui(self):
        try:
            while True:
                self.gui_queue.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(100, self.processar_fila_gui)

    def ui_do(self, acao):
        self.gui_queue.put(acao)

    def config_tags_log(self, txt_widget):
        txt_widget.tag_config("hora", foreground=TEXT_MUTED)
        txt_widget.tag_config("ok", foreground="#34D399")
        txt_widget.tag_config("erro", foreground="#FCA5A5")
        txt_widget.tag_config("info", foreground="#93C5FD")
        txt_widget.tag_config("texto", foreground="#E2E8F0")
        txt_widget.tag_config("destaque", foreground="#FCD34D")

    def log(self, tipo, msg):
        def _inserir():
            hora = datetime.now().strftime("%H:%M:%S")
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"[{hora}] ", "hora")
            if tipo == "OK":
                self.txt_log.insert("end", "SUCESSO ", "ok")
            elif tipo == "ERRO":
                self.txt_log.insert("end", "ERRO ", "erro")
            elif tipo == "MODULO":
                self.txt_log.insert("end", "▶ FASE ", "destaque")
            else:
                self.txt_log.insert("end", "INFO ", "info")
            self.txt_log.insert("end", f"- {msg}\n", "texto" if tipo != "MODULO" else "destaque")
            self.txt_log.configure(state="disabled")
            self.txt_log.see("end")

        self.ui_do(_inserir)

    def abrir_leitor_bd(self):
        janela = ctk.CTkToplevel(self.root)
        janela.title("🗄️ Histórico de Banco de Dados")
        janela.geometry("900x600")
        janela.configure(fg_color=BG_WINDOW if self.config.get("theme") == "dark" else "#F1F5F9")
        janela.attributes("-topmost", True)

        ctk.CTkLabel(janela, text="Auditoria Interna (SQLite)", font=("Inter", 18, "bold")).pack(
            pady=15
        )

        style = ttk.Style()
        style.theme_use("default")
        _bg = BG_INPUT if self.config.get("theme") == "dark" else "#FFFFFF"
        _fg = "white" if self.config.get("theme") == "dark" else "black"
        style.configure(
            "Treeview",
            background=_bg,
            foreground=_fg,
            rowheight=25,
            fieldbackground=_bg,
            borderwidth=0,
        )
        style.map("Treeview", background=[("selected", AZUL_PASSO)])
        style.configure(
            "Treeview.Heading",
            background=BG_CARD,
            foreground="white",
            relief="flat",
            font=("Inter", 10, "bold"),
        )

        frame_tb = ctk.CTkFrame(janela, fg_color="transparent")
        frame_tb.pack(fill="both", expand=True, padx=20, pady=10)

        colunas = ("id", "modulo", "curso", "status", "data", "arquivo")
        tv = ttk.Treeview(frame_tb, columns=colunas, show="headings")
        tv.heading("id", text="ID")
        tv.heading("modulo", text="Módulo")
        tv.heading("curso", text="Curso")
        tv.heading("status", text="Status")
        tv.heading("data", text="Data/Hora")
        tv.heading("arquivo", text="Arquivo")
        tv.column("id", width=40)
        tv.column("modulo", width=300)
        tv.column("curso", width=200)
        tv.column("status", width=120)
        tv.column("data", width=150)
        tv.column("arquivo", width=180)
        tv.pack(fill="both", expand=True)

        try:
            for linha in self.history_repo.fetch_recent_rows():
                tv.insert("", "end", values=linha)
        except Exception as exc:
            self.registrar_falha_caixa_preta("abrir_leitor_bd", exc)

        def exportar_erros():
            try:
                df = pd.DataFrame(self.history_repo.fetch_retry_rows())
                if df.empty:
                    messagebox.showinfo(
                        "Exportar", "Excelente! Nenhum erro encontrado no histórico."
                    )
                else:
                    nome = f"Modulos_Para_Refazer_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.xlsx"
                    df.to_excel(nome, index=False)
                    messagebox.showinfo(
                        "Sucesso",
                        f"Planilha de resgate criada na pasta raiz:\n{nome}\nCarregue esta planilha no robô para refazer os falhados.",
                    )
            except Exception as e:
                messagebox.showerror("Erro", str(e))

        ctk.CTkButton(
            janela,
            text="📥 Exportar Erros para Refazer (.xlsx)",
            font=("Inter", 12, "bold"),
            fg_color=VERMELHO_PARAR,
            hover_color="#9F1239",
            height=40,
            command=exportar_erros,
        ).pack(pady=15)

    def abrir_assistente_ia(self):
        self.tela_ia = ctk.CTkToplevel(self.root)
        self.tela_ia.title("🧠 Oráculo IA - Llama 3.1")
        self.tela_ia.geometry("600x700")
        self.tela_ia.configure(
            fg_color=BG_WINDOW if self.config.get("theme") == "dark" else "#F1F5F9"
        )
        self.tela_ia.attributes("-topmost", True)
        self.txt_chat = ctk.CTkTextbox(
            self.tela_ia,
            font=("Consolas", 13),
            fg_color=BG_INPUT if self.config.get("theme") == "dark" else "#FFFFFF",
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=8,
            text_color=TEXT_LIGHT if self.config.get("theme") == "dark" else "#1E293B",
            wrap="word",
        )
        self.txt_chat.pack(fill="both", expand=True, padx=20, pady=10)
        self.txt_chat.insert("end", "⚡ Llama 3.1: Olá, Wesley! Operando na velocidade da luz.\n\n")
        self.txt_chat.configure(state="disabled")
        frame_baixo = ctk.CTkFrame(self.tela_ia, fg_color="transparent")
        frame_baixo.pack(fill="x", padx=20, pady=15)
        self.ent_pergunta = ctk.CTkEntry(
            frame_baixo,
            placeholder_text="Pergunte à IA...",
            height=40,
            fg_color=BG_CARD if self.config.get("theme") == "dark" else "#FFFFFF",
        )
        self.ent_pergunta.pack(side="left", fill="x", expand=True, padx=(0, 10))
        btn_enviar = ctk.CTkButton(
            frame_baixo,
            text="Enviar",
            width=80,
            height=40,
            fg_color=ROXO_IA,
            command=lambda: self.chamar_api_groq(self.ent_pergunta.get()),
        )
        btn_enviar.pack(side="right")
        ctk.CTkButton(
            self.tela_ia,
            text="🔍 Analisar Último Erro do Robô",
            fg_color=VERDE_ACAO,
            height=40,
            command=self.pedir_ia_analisar_erro,
        ).pack(fill="x", padx=20, pady=(0, 20))

    def pedir_ia_analisar_erro(self):
        try:
            caminho_log, ultimo_erro = self.error_logger.latest_log_excerpt(line_count=15)
            if not caminho_log or not ultimo_erro.strip():
                return messagebox.showinfo("IA", "Nenhum erro registado ainda.")
            if not ultimo_erro.strip():
                return
            self.txt_chat.configure(state="normal")
            self.txt_chat.insert("end", f"\n👤 Você: Por favor, analisa o último erro da frota.\n")
            self.txt_chat.see("end")
            self.txt_chat.configure(state="disabled")
            self.chamar_api_groq(
                f"Lê o erro do meu script de automação Python e explica-me de forma simples:\n\n{ultimo_erro}"
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler log: {e}")

    def chamar_api_groq(self, prompt):
        if not prompt:
            return
        groq_key = resolve_groq_key(self.config)
        if not groq_key:
            messagebox.showwarning(
                "API",
                "Defina a chave da Groq em GROQ_API_KEY/CURSOMS_GROQ_KEY ou nas configurações.",
            )
            return
        try:
            self.ent_pergunta.delete(0, "end")
        except Exception:
            pass
        self.txt_chat.configure(state="normal")
        self.txt_chat.insert("end", f"⚡ Llama 3.1: Processando...\n")
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")

        def _thread_ia():
            try:
                client = Groq(api_key=groq_key)
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1,
                    max_tokens=1024,
                    stream=False,
                )
                texto_real = completion.choices[0].message.content or ""

                def _update():
                    self.txt_chat.configure(state="normal")
                    txt = self.txt_chat.get("1.0", "end")
                    if "Processando..." in txt:
                        nt = txt.rsplit("Processando...", 1)
                        self.txt_chat.delete("1.0", "end")
                        self.txt_chat.insert("1.0", nt[0] + texto_real + nt[1])
                    else:
                        self.txt_chat.insert("end", f"{texto_real}\n")
                    self.txt_chat.see("end")
                    self.txt_chat.configure(state="disabled")

                self.ui_do(_update)
            except Exception as e:
                self.registrar_falha_caixa_preta("chamar_api_groq", e)
                self.ui_do(lambda: messagebox.showerror("API", str(e)))

        threading.Thread(target=_thread_ia).start()

    def abrir_dashboard(self):
        self.janela_dash = ctk.CTkToplevel(self.root)
        self.janela_dash.title("📊 Analytics Dashboard")
        self.janela_dash.geometry("550x600")
        self.janela_dash.configure(
            fg_color=BG_WINDOW if self.config.get("theme") == "dark" else "#F1F5F9"
        )
        self.janela_dash.attributes("-topmost", True)
        ctk.CTkLabel(
            self.janela_dash, text="Dashboard de Produtividade", font=("Inter", 18, "bold")
        ).pack(pady=15)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
            s.close()
        except:
            my_ip = "127.0.0.1"
        ctk.CTkLabel(
            self.janela_dash,
            text=f"📱 Monitorização no Telemóvel: Abra http://{my_ip}:5000 no Wifi",
            font=("Inter", 11),
            text_color=AZUL_PASSO,
        ).pack()
        self.fig, self.ax = plt.subplots(
            figsize=(5, 4), facecolor=BG_CARD if self.config.get("theme") == "dark" else "#FFFFFF"
        )
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.janela_dash)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=5)
        frame_eta = ctk.CTkFrame(
            self.janela_dash,
            fg_color=BG_INPUT if self.config.get("theme") == "dark" else "#E2E8F0",
            corner_radius=8,
        )
        frame_eta.pack(fill="x", padx=20, pady=20)
        self.lbl_eta = ctk.CTkLabel(
            frame_eta,
            text="ETA: Aguardando início...",
            font=("Inter", 15, "bold"),
            text_color="#F59E0B",
        )
        self.lbl_eta.pack(pady=10)
        self.atualizar_grafico_loop()

    def atualizar_grafico_loop(self):
        if not hasattr(self, "janela_dash") or not self.janela_dash.winfo_exists():
            return
        self.ax.clear()
        sizes = [
            self.stats_contagem["Sucesso"],
            self.stats_contagem["Erro"],
            self.stats_contagem["Aviso"],
        ]
        if sum(sizes) == 0:
            self.ax.pie(
                [1],
                labels=["Aguardando"],
                colors=["#334155" if self.config.get("theme") == "dark" else "#94A3B8"],
            )
        else:
            result = self.ax.pie(
                sizes,
                labels=["Sucesso", "Erros", "Pulados"],
                colors=["#00A36C", "#D33F49", "#F59E0B"],
                autopct="%1.1f%%",
                startangle=90,
            )
            texts = result[1]
            autotexts = result[2] if len(result) > 2 else []
            for text in list(texts) + list(autotexts):
                text.set_color("white")
                text.set_fontsize(10)
        self.canvas.draw()
        if self.modulos_concluidos > 0 and self.tempo_inicio_trabalho and self.is_running:
            rem = int(
                (self.total_modulos - self.modulos_concluidos)
                * ((time.time() - self.tempo_inicio_trabalho) / self.modulos_concluidos)
            )
            self.lbl_eta.configure(
                text=f"ETA (Tempo Estimado): {rem//60} min e {rem%60} seg", text_color=VERDE_ACAO
            )
        elif (
            not self.is_running
            and self.modulos_concluidos == self.total_modulos
            and self.total_modulos > 0
        ):
            self.lbl_eta.configure(text="✅ TRABALHO CONCLUÍDO!", text_color=VERDE_ACAO)
        self.root.after(2000, self.atualizar_grafico_loop)

    def abrir_configuracoes(self):
        tela_cfg = ctk.CTkToplevel(self.root)
        tela_cfg.title("⚙️ Configurações")
        tela_cfg.geometry("500x750")
        tela_cfg.attributes("-topmost", True)
        tela_cfg.configure(fg_color=BG_WINDOW if self.config.get("theme") == "dark" else "#F1F5F9")
        scroll = ctk.CTkScrollableFrame(tela_cfg, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        _bg = BG_CARD if self.config.get("theme") == "dark" else "#FFFFFF"

        f_tema = ctk.CTkFrame(scroll, fg_color=_bg)
        f_tema.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(
            f_tema, text="🎨 Apresentação UI/UX", font=("Inter", 14, "bold"), text_color=AZUL_PASSO
        ).pack(pady=5)
        cbox_theme = ctk.CTkComboBox(f_tema, values=["dark", "light"], width=200)
        cbox_theme.set(self.config.get("theme", "dark"))
        cbox_theme.pack(pady=(5, 10))

        f_busca = ctk.CTkFrame(scroll, fg_color=_bg)
        f_busca.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(
            f_busca,
            text="🎯 Método de Associação",
            font=("Inter", 15, "bold"),
            text_color="#0EA5E9",
        ).pack(pady=5)
        cbox_search = ctk.CTkComboBox(
            f_busca,
            values=["Ordem Exata (Linha 1 = Módulo 1)", "Fuzzy Match (Buscar por Nomes)"],
            width=300,
        )
        cbox_search.set(self.config.get("search_method", "Ordem Exata (Linha 1 = Módulo 1)"))
        cbox_search.pack(pady=(5, 10))

        f_auditoria = ctk.CTkFrame(scroll, fg_color=_bg)
        f_auditoria.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(
            f_auditoria,
            text="🧪 Segurança de Execução",
            font=("Inter", 15, "bold"),
            text_color="#F59E0B",
        ).pack(pady=(8, 4))
        var_auditoria = ctk.BooleanVar(value=bool(self.config.get("audit_mode", False)))
        ctk.CTkCheckBox(
            f_auditoria,
            text="Modo auditoria (não cria módulo e não envia conteúdo)",
            variable=var_auditoria,
            font=("Inter", 12),
        ).pack(anchor="w", padx=16, pady=(0, 10))

        f1 = ctk.CTkFrame(scroll, fg_color=_bg)
        f1.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(f1, text="🌐 Site Antigo", font=("Inter", 14, "bold")).pack(pady=5)
        e_ant_url = ctk.CTkEntry(f1, width=400)
        e_ant_url.insert(0, self.config.get("antigo_url", ""))
        e_ant_url.pack(pady=2)
        e_ant_usr = ctk.CTkEntry(f1, width=400)
        e_ant_usr.insert(0, self.config.get("antigo_user", ""))
        e_ant_usr.pack(pady=2)
        e_ant_pwd = ctk.CTkEntry(f1, width=400, show="*")
        e_ant_pwd.insert(0, self.config.get("antigo_pass", ""))
        e_ant_pwd.pack(pady=(2, 10))

        f2 = ctk.CTkFrame(scroll, fg_color=_bg)
        f2.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(f2, text="🚀 Site Novo", font=("Inter", 14, "bold")).pack(pady=5)
        e_nov_url = ctk.CTkEntry(f2, width=400)
        e_nov_url.insert(0, self.config.get("novo_url", ""))
        e_nov_url.pack(pady=2)
        e_nov_usr = ctk.CTkEntry(f2, width=400)
        e_nov_usr.insert(0, self.config.get("novo_user", ""))
        e_nov_usr.pack(pady=2)
        e_nov_pwd = ctk.CTkEntry(f2, width=400, show="*")
        e_nov_pwd.insert(0, self.config.get("novo_pass", ""))
        e_nov_pwd.pack(pady=(2, 10))

        f3 = ctk.CTkFrame(scroll, fg_color=_bg)
        f3.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(f3, text="🧠 IA (Groq)", font=("Inter", 14, "bold"), text_color=ROXO_IA).pack(
            pady=5
        )
        e_groq = ctk.CTkEntry(f3, width=400, show="*")
        e_groq.insert(0, self.config.get("groq_key", ""))
        e_groq.pack(pady=5)

        f4 = ctk.CTkFrame(scroll, fg_color=_bg)
        f4.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(
            f4, text="📱 WhatsApp CallMeBot", font=("Inter", 14, "bold"), text_color="#25D366"
        ).pack(pady=5)
        e_wpp_num = ctk.CTkEntry(f4, width=400, placeholder_text="+55...")
        e_wpp_num.insert(0, self.config.get("whatsapp_number", ""))
        e_wpp_num.pack(pady=2)
        e_wpp_key = ctk.CTkEntry(f4, width=400, show="*", placeholder_text="API Key")
        e_wpp_key.insert(0, self.config.get("whatsapp_key", ""))
        e_wpp_key.pack(pady=(2, 10))

        def salvar():
            self.config["theme"] = cbox_theme.get()
            self.config["search_method"] = cbox_search.get()
            self.config["audit_mode"] = bool(var_auditoria.get())
            self.config["antigo_url"] = e_ant_url.get()
            self.config["antigo_user"] = e_ant_usr.get()
            self.config["antigo_pass"] = e_ant_pwd.get()
            self.config["novo_url"] = e_nov_url.get()
            self.config["novo_user"] = e_nov_usr.get()
            self.config["novo_pass"] = e_nov_pwd.get()
            self.config["groq_key"] = e_groq.get()
            self.config["whatsapp_number"] = e_wpp_num.get()
            self.config["whatsapp_key"] = e_wpp_key.get()
            save_config(CONFIG_PATH, self.config)
            ctk.set_appearance_mode(self.config["theme"])
            messagebox.showinfo("Sucesso", "Configurações guardadas!")
            tela_cfg.destroy()

        ctk.CTkButton(
            tela_cfg,
            text="💾 SALVAR",
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            height=48,
            corner_radius=12,
            command=salvar,
        ).pack(fill="x", padx=20, pady=20)

    def enviar_whatsapp(self, mensagem):
        num = self.config.get("whatsapp_number", "").replace("+", "").strip()
        apikey = self.config.get("whatsapp_key", "").strip()
        if num and apikey:
            try:
                requests.get(
                    f"https://api.callmebot.com/whatsapp.php?phone={num}&text={quote(mensagem)}&apikey={apikey}",
                    timeout=5,
                )
            except Exception as exc:
                self.registrar_falha_caixa_preta("enviar_whatsapp", exc)

    def setup_ui(self):
        return self._setup_ui_stitch()
        _bg = BG_WINDOW if self.config.get("theme") == "dark" else "#F1F5F9"
        _bc = BG_CARD if self.config.get("theme") == "dark" else "#FFFFFF"
        _tc = TEXT_LIGHT if self.config.get("theme") == "dark" else "#1E293B"
        _ib = BG_INPUT if self.config.get("theme") == "dark" else "#F8FAFC"

        self.root.configure(fg_color=_bg)
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        top_layout = ctk.CTkFrame(main_container, fg_color="transparent")
        top_layout.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(
            top_layout,
            width=280,
            fg_color=_bc,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        sidebar.pack(side="left", fill="y", padx=(0, 20))
        sidebar.pack_propagate(False)

        header_side = ctk.CTkFrame(sidebar, fg_color="transparent")
        header_side.pack(fill="x", pady=20, padx=15)
        ctk.CTkLabel(
            header_side, text="🪢 ISAURA", font=("Inter Black", 18), text_color=AZUL_PASSO
        ).pack(anchor="w")
        ctk.CTkLabel(
            header_side, text="TITANIUM V106", font=("Inter", 10, "bold"), text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(0, 10))

        frota_frame = ctk.CTkFrame(
            sidebar,
            fg_color="#1E1B4B" if self.config.get("theme") == "dark" else "#E0E7FF",
            border_width=1,
            border_color="#059669",
            corner_radius=8,
        )
        frota_frame.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(
            frota_frame,
            text="🏭 STATUS DA ISAURA",
            font=("Inter", 12, "bold"),
            text_color="#A5B4FC" if self.config.get("theme") == "dark" else "#3730A3",
        ).pack(pady=(10, 5))
        self.lbl_workers = ctk.CTkLabel(
            frota_frame,
            text="0 Módulos Carregados",
            font=("Inter", 13, "bold"),
            text_color="#FFFFFF" if self.config.get("theme") == "dark" else "#1E293B",
        )
        self.lbl_workers.pack(pady=(0, 15))

        self.btn_db = ctk.CTkButton(
            sidebar,
            text="🗄️ Histórico BD",
            font=("Inter", 13, "bold"),
            fg_color="#F59E0B",
            hover_color="#D97706",
            height=45,
            command=self.abrir_leitor_bd,
        )
        self.btn_db.pack(fill="x", padx=15, pady=(0, 8))
        self.btn_dash = ctk.CTkButton(
            sidebar,
            text="📊 Monitor Remoto",
            font=("Inter", 13, "bold"),
            fg_color="#0891B2",
            hover_color="#0369A1",
            height=45,
            command=self.abrir_dashboard,
        )
        self.btn_dash.pack(fill="x", padx=15, pady=(0, 8))
        self.btn_ia = ctk.CTkButton(
            sidebar,
            text="⚡ Oráculo IA",
            font=("Inter", 13, "bold"),
            fg_color=ROXO_IA,
            height=45,
            command=self.abrir_assistente_ia,
        )
        self.btn_ia.pack(fill="x", padx=15, pady=(0, 8))
        self.btn_ia.pack_forget()
        self.btn_cfg = ctk.CTkButton(
            sidebar,
            text="⚙️ Configurações",
            font=("Inter", 13, "bold"),
            fg_color="#475569",
            hover_color="#334155",
            height=45,
            command=self.abrir_configuracoes,
        )
        self.btn_cfg.pack(fill="x", padx=15)

        content = ctk.CTkFrame(
            top_layout, fg_color=_bc, corner_radius=10, border_width=1, border_color=BORDER_COLOR
        )
        content.pack(side="right", fill="both", expand=True)

        top_content = ctk.CTkFrame(content, fg_color="transparent")
        top_content.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(
            top_content, text="📊 Base de Dados", font=("Inter", 16, "bold"), text_color=_tc
        ).pack(side="left")

        area_excel = ctk.CTkFrame(
            content,
            fg_color=_ib,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=8,
            height=132,
        )
        area_excel.pack(fill="x", padx=20, pady=(0, 10))
        area_excel.pack_propagate(False)
        ctk.CTkLabel(
            area_excel,
            text="Segure CTRL para selecionar múltiplos arquivos.",
            font=("Inter", 13),
            text_color="#F59E0B",
        ).pack(pady=(30, 15))
        self.btn_planilhas = ctk.CTkButton(
            area_excel,
            text="📂 CARREGAR PLANILHA(S)",
            font=("Inter", 14, "bold"),
            fg_color="#F59E0B",
            hover_color="#D97706",
            height=45,
            command=self.carregar_excel,
        )
        self.btn_planilhas.pack(pady=10)
        self.btn_planilhas.configure(text="PLANILHA - VARIOS MODULOS")
        self.lbl_status_excel = ctk.CTkLabel(
            area_excel,
            text="Aguardando arquivos...",
            font=("Inter", 12, "bold"),
            text_color=VERMELHO_PARAR,
        )
        self.lbl_status_excel.pack(pady=10)
        ctk.CTkLabel(
            area_excel,
            text="Use esta area quando quiser subir varios modulos pela planilha.",
            font=("Inter", 12),
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 12))

        modos_frame = ctk.CTkFrame(
            content, fg_color=_ib, border_color=BORDER_COLOR, border_width=1, corner_radius=8
        )
        modos_frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(
            modos_frame,
            text="Modos de ExecuÃ§Ã£o",
            font=("Inter", 15, "bold"),
            text_color=_tc,
        ).pack(anchor="w", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            modos_frame,
            text="Escolha o que subir no robÃ´ principal.",
            font=("Inter", 12),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 10))

        upload_frame = ctk.CTkFrame(modos_frame, fg_color="transparent")
        upload_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(
            upload_frame,
            text="Tipo de envio",
            font=("Inter", 12, "bold"),
            text_color=AZUL_PASSO,
        ).pack(anchor="w", pady=(0, 8))
        self.botoes_upload = {}
        for modo, texto in [
            ("completo", "Modo inteiro (.exe)"),
            ("videos", "SÃ³ vÃ­deos"),
            ("materiais", "SÃ³ materiais"),
        ]:
            botao = ctk.CTkButton(
                upload_frame,
                text=texto,
                height=40,
                border_width=1,
                command=lambda m=modo: self.selecionar_modo_upload(m),
            )
            botao.pack(fill="x", pady=4)
            self.botoes_upload[modo] = botao

        escopo_frame = ctk.CTkFrame(modos_frame, fg_color="transparent")
        escopo_frame.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(
            escopo_frame,
            text="Escopo",
            font=("Inter", 12, "bold"),
            text_color=VERDE_ACAO,
        ).pack(anchor="w", pady=(0, 8))
        self.botoes_escopo = {}
        for escopo, texto in [("todos", "VÃ¡rios mÃ³dulos"), ("unico", "SÃ³ um mÃ³dulo")]:
            botao = ctk.CTkButton(
                escopo_frame,
                text=texto,
                height=40,
                border_width=1,
                command=lambda e=escopo: self.selecionar_escopo(e),
            )
            botao.pack(fill="x", pady=4)
            self.botoes_escopo[escopo] = botao

        upload_frame.pack_forget()
        escopo_frame.pack_forget()

        presets_frame = ctk.CTkFrame(modos_frame, fg_color="transparent")
        presets_frame.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(
            presets_frame,
            text="Botoes diretos",
            font=("Inter", 12, "bold"),
            text_color=AZUL_PASSO,
        ).pack(anchor="w", pady=(0, 8))
        self.botoes_preset = {}
        for modo, escopo, texto in [
            ("videos", "todos", "SUBIR APENAS VÍDEOS — PLANILHA"),
            ("materiais", "todos", "SUBIR APENAS MATERIAIS IMPRESSOS — PLANILHA"),
        ]:
            botao = ctk.CTkButton(
                presets_frame,
                text=texto,
                height=48,
                corner_radius=12,
                border_width=1,
                font=("Inter", 14, "bold"),
                command=lambda m=modo, e=escopo: self.selecionar_preset_execucao(m, e),
            )
            botao.pack(fill="x", pady=4)
            self.botoes_preset[(modo, escopo)] = botao
        ctk.CTkLabel(
            modos_frame,
            text="So o primeiro botao usa planilha e cria modulos. Os outros usam o modulo ja criado no site novo.",
            font=("Inter", 12),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(2, 8))

        self.lbl_modo_resumo = ctk.CTkLabel(
            modos_frame,
            text="",
            font=("Inter", 12, "bold"),
            text_color="#F59E0B",
        )
        self.lbl_modo_resumo.pack(anchor="w", padx=16, pady=(0, 14))

        self.frame_modulo_unico = ctk.CTkFrame(
            content, fg_color=_ib, border_color=BORDER_COLOR, border_width=1, corner_radius=8
        )
        ctk.CTkLabel(
            self.frame_modulo_unico,
            text="Alvo do modo 'SÃ³ um mÃ³dulo'",
            font=("Inter", 13, "bold"),
            text_color=_tc,
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            self.frame_modulo_unico,
            text="Pode ser o nÃºmero da linha da planilha ou o nome exato do mÃ³dulo.",
            font=("Inter", 12),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))
        self.ent_modulo_alvo = ctk.CTkEntry(
            self.frame_modulo_unico,
            placeholder_text="Ex.: 1 ou Fundamentos do Curso",
            height=40,
        )
        if self.single_module_target:
            self.ent_modulo_alvo.insert(0, self.single_module_target)
        self.ent_modulo_alvo.pack(fill="x", padx=16, pady=(0, 14))
        self.ent_modulo_alvo.bind("<KeyRelease>", self.atualizar_alvo_modulo)

        self.browser_actions_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.browser_actions_frame.pack(fill="x", padx=20, pady=(0, 8))
        self.btn_abrir_plataformas = ctk.CTkButton(
            self.browser_actions_frame,
            text="ABRIR CHROME ANTIGO E NOVO",
            font=("Inter", 14, "bold"),
            fg_color="#0891B2",
            hover_color="#0369A1",
            height=46,
            corner_radius=12,
            command=self.abrir_plataformas,
        )
        self.btn_abrir_plataformas.pack(fill="x")

        self.actions_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.actions_frame.pack(fill="x", padx=20, pady=(6, 12))
        self.btn_preparar = ctk.CTkButton(
            self.actions_frame,
            text="1 - PREPARAR ROBO",
            font=("Inter", 15, "bold"),
            fg_color="#0EA5E9",
            hover_color="#0284C7",
            height=48,
            corner_radius=12,
            command=self.preparar_frota,
        )
        self.btn_preparar.pack(fill="x", pady=(0, 8))
        self.btn_iniciar = ctk.CTkButton(
            self.actions_frame,
            text="2 - Começar a Escravidão",
            font=("Inter", 14, "bold"),
            fg_color="#4F46E5",
            hover_color="#4338CA",
            height=48,
            corner_radius=12,
            state="disabled",
            command=self.iniciar_trabalho,
        )
        self.btn_iniciar.pack(fill="x")
        self.atualizar_botoes_modo()

        bottom_area = ctk.CTkFrame(
            main_container,
            height=270,
            fg_color="#0B1119" if self.config.get("theme") == "dark" else "#E2E8F0",
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        bottom_area.pack(fill="x", side="bottom", pady=(15, 0))
        bottom_area.pack_propagate(False)
        ctk.CTkLabel(
            bottom_area,
            text="Log da Isaura",
            font=("Inter", 15, "bold"),
            text_color=_tc,
        ).pack(anchor="w", padx=15, pady=(12, 0))
        status_bar = ctk.CTkFrame(bottom_area, fg_color="transparent")
        status_bar.pack(fill="x", padx=15, pady=(8, 6))
        self.lbl_status_mod = ctk.CTkLabel(
            status_bar,
            text="Status: Aguardando...",
            font=("Inter", 13, "bold"),
            text_color=VERDE_ACAO,
        )
        self.lbl_status_mod.pack(side="left")
        self.progress_bar = ctk.CTkProgressBar(
            status_bar,
            progress_color=AZUL_PASSO,
            fg_color="#1F252D" if self.config.get("theme") == "dark" else "#CBD5E1",
            height=12,
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=20)
        self.progress_bar.set(0)
        ctk.CTkButton(
            status_bar,
            text="🛑 PARAR",
            font=("Inter", 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=VERMELHO_PARAR,
            text_color=VERMELHO_PARAR,
            width=110,
            height=36,
            command=self.parar_tudo,
        ).pack(side="right")

        self.txt_log = ctk.CTkTextbox(
            bottom_area,
            font=("Consolas", 12),
            fg_color=BG_INPUT if self.config.get("theme") == "dark" else "#FFFFFF",
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=10,
            text_color="#E2E8F0" if self.config.get("theme") == "dark" else "#1E293B",
        )
        self.txt_log.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.config_tags_log(self.txt_log)
        self.txt_log.configure(state="disabled")
        self.log("INFO", "Sistema V106 (The Livewire Whisperer) Iniciado.")

    def _setup_ui_stitch(self):
        dark_theme = self.config.get("theme") == "dark"
        _bg = "#0B1326" if dark_theme else "#EFF4FF"
        _surface = "#11182D" if dark_theme else "#FFFFFF"
        _surface_alt = "#171F33" if dark_theme else "#E8EEF9"
        _surface_soft = "#202843" if dark_theme else "#DCE7F8"
        _surface_log = "#000000" if dark_theme else "#F8FAFC"
        _tc = "#DAE2FD" if dark_theme else "#12223D"
        _muted = "#8F9AB8" if dark_theme else "#5B6B8A"
        _outline = "#434C63" if dark_theme else "#BFCCE4"

        def card_title(parent, icon_text, title_text, accent="#B4C5FF"):
            header = ctk.CTkFrame(parent, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(18, 10))
            ctk.CTkLabel(
                header,
                text=f"{icon_text} {title_text}",
                font=("Space Grotesk", 17, "bold"),
                text_color=accent,
            ).pack(anchor="w")
            ctk.CTkFrame(header, fg_color=_outline, height=1).pack(fill="x", pady=(10, 0))

        def nav_button(parent, text, command):
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                anchor="w",
                height=50,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#18284E" if dark_theme else "#D9E6FF",
                text_color="#7AB2FF" if dark_theme else "#214D99",
                border_width=0,
                font=("Space Grotesk", 16, "bold"),
            )

        def action_button(parent, text, fg_color, hover_color, border_color, command, state="normal"):
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                state=state,
                height=116,
                corner_radius=8,
                fg_color=fg_color,
                hover_color=hover_color,
                border_width=1,
                border_color=border_color,
                text_color="#EAF0FF",
                font=("Space Grotesk", 20, "bold"),
            )

        self.root.configure(fg_color=_bg)

        shell = ctk.CTkFrame(self.root, fg_color="transparent")
        shell.pack(fill="both", expand=True)

        topbar = ctk.CTkFrame(
            shell,
            height=68,
            fg_color="#070D1E" if dark_theme else "#DCE7F8",
            corner_radius=0,
            border_width=0,
        )
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        brand = ctk.CTkFrame(topbar, fg_color="transparent")
        brand.pack(side="left", fill="y", padx=28)
        ctk.CTkLabel(
            brand,
            text="ISAURA — SELETIVO",
            font=("Space Grotesk", 22, "bold"),
            text_color="#10B981" if dark_theme else "#059669",
        ).pack(side="left", pady=18)

        topbar_actions = ctk.CTkFrame(topbar, fg_color="transparent")
        topbar_actions.pack(side="right", pady=12, padx=22)
        ctk.CTkButton(
            topbar_actions,
            text="BASE",
            width=88,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            hover_color=_surface_soft,
            border_width=1,
            border_color=_outline,
            text_color=_tc,
            font=("Inter", 11, "bold"),
            command=self.abrir_leitor_bd,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            topbar_actions,
            text="SETUP",
            width=88,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            hover_color=_surface_soft,
            border_width=1,
            border_color=_outline,
            text_color=_tc,
            font=("Inter", 11, "bold"),
            command=self.abrir_configuracoes,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            topbar_actions,
            text="DEPLOY",
            width=102,
            height=40,
            corner_radius=8,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="#F8FBFF",
            font=("Inter", 12, "bold"),
            command=self.preparar_frota,
        ).pack(side="left")

        body = ctk.CTkFrame(shell, fg_color="transparent")
        body.pack(fill="both", expand=True)

        footer = ctk.CTkFrame(
            shell,
            height=260,
            fg_color="#05080F" if dark_theme else "#FFFFFF",
            corner_radius=0,
            border_width=0,
        )
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        sidebar = ctk.CTkFrame(
            body,
            width=300,
            fg_color="#11172A" if dark_theme else "#E8EEF9",
            corner_radius=0,
            border_width=1,
            border_color=_outline,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        main_surface = ctk.CTkFrame(
            body,
            fg_color="#141D31" if dark_theme else "#F5F8FF",
            corner_radius=0,
            border_width=0,
        )
        main_surface.pack(side="left", fill="both", expand=True)

        sidebar_top = ctk.CTkFrame(sidebar, fg_color="transparent")
        sidebar_top.pack(fill="x", padx=18, pady=(30, 24))
        icon_shell = ctk.CTkFrame(
            sidebar_top,
            width=96,
            height=96,
            fg_color="#24304D" if dark_theme else "#D6E0F5",
            corner_radius=16,
            border_width=1,
            border_color="#4B5874" if dark_theme else "#AFBEDC",
        )
        icon_shell.pack(pady=(0, 18))
        icon_shell.pack_propagate(False)
        ctk.CTkLabel(
            icon_shell,
            text="[CPU]",
            font=("Space Grotesk", 20, "bold"),
            text_color="#10B981" if dark_theme else "#059669",
        ).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(
            sidebar_top,
            text="SELETIVO",
            font=("Space Grotesk", 28, "bold"),
            text_color=_tc,
        ).pack()
        ctk.CTkLabel(
            sidebar_top,
            text="MIGRAÇÃO FILTRADA",
            font=("Inter", 11, "bold"),
            text_color=_muted,
        ).pack(pady=(4, 0))

        status_card = ctk.CTkFrame(
            sidebar,
            fg_color="#1C2540" if dark_theme else "#FFFFFF",
            border_width=1,
            border_color="#596583" if dark_theme else "#BFCBE2",
            corner_radius=8,
        )
        status_card.pack(fill="x", padx=18, pady=(0, 22))
        ctk.CTkLabel(
            status_card,
            text="FILTRO ATIVO",
            font=("Inter", 12, "bold"),
            text_color=_muted,
        ).pack(pady=(18, 8))
        self.lbl_workers = ctk.CTkLabel(
            status_card,
            text="0 MÓDULOS FILTRADOS",
            font=("Space Grotesk", 24, "bold"),
            text_color="#B9CBFF" if dark_theme else "#254B99",
            justify="center",
        )
        self.lbl_workers.pack(padx=12, pady=(0, 18))

        nav_group = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_group.pack(fill="x", padx=14)
        dashboard_card = ctk.CTkFrame(
            nav_group,
            fg_color="#162654" if dark_theme else "#DCE7FF",
            corner_radius=0,
        )
        dashboard_card.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            dashboard_card,
            text="DASHBOARD",
            font=("Space Grotesk", 16, "bold"),
            text_color="#65A8FF" if dark_theme else "#1D4ED8",
        ).pack(anchor="w", padx=18, pady=16)
        self.btn_db = nav_button(nav_group, "HISTORICO BD", self.abrir_leitor_bd)
        self.btn_db.pack(fill="x", pady=4)
        self.btn_dash = nav_button(nav_group, "MONITOR REMOTO", self.abrir_dashboard)
        self.btn_dash.pack(fill="x", pady=4)
        self.btn_ia = nav_button(nav_group, "ORACULO IA", self.abrir_assistente_ia)
        self.btn_ia.pack(fill="x", pady=4)
        self.btn_ia.pack_forget()
        self.btn_cfg = nav_button(nav_group, "CONFIGURACOES", self.abrir_configuracoes)
        self.btn_cfg.pack(fill="x", pady=4)

        sidebar_bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        sidebar_bottom.pack(side="bottom", fill="x", padx=18, pady=18)
        self.btn_sidebar_prepare = ctk.CTkButton(
            sidebar_bottom,
            text="INITIALIZE BOT",
            height=50,
            corner_radius=8,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="#F8FBFF",
            font=("Space Grotesk", 16, "bold"),
            command=self.preparar_frota,
        )
        self.btn_sidebar_prepare.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(
            sidebar_bottom,
            text="SUPPORT",
            anchor="w",
            text_color=_muted,
            font=("Inter", 11, "bold"),
        ).pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            sidebar_bottom,
            text="API DOCS",
            anchor="w",
            text_color=_muted,
            font=("Inter", 11, "bold"),
        ).pack(fill="x")

        content_wrap = ctk.CTkFrame(main_surface, fg_color="transparent")
        content_wrap.pack(fill="both", expand=True, padx=28, pady=28)

        top_grid = ctk.CTkFrame(content_wrap, fg_color="transparent")
        top_grid.pack(fill="x")
        top_grid.grid_columnconfigure(0, weight=1)
        top_grid.grid_columnconfigure(1, weight=1)

        db_card = ctk.CTkFrame(
            top_grid,
            fg_color=_surface,
            corner_radius=8,
            border_width=1,
            border_color=_outline,
        )
        db_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        card_title(db_card, "[DB]", "BASE DE DADOS")

        area_excel = ctk.CTkFrame(
            db_card,
            fg_color="#0C1428" if dark_theme else "#F1F6FF",
            border_color="#3A4257" if dark_theme else "#C9D5EA",
            border_width=1,
            corner_radius=8,
            height=276,
        )
        area_excel.pack(fill="x", padx=20, pady=(0, 20))
        area_excel.pack_propagate(False)
        ctk.CTkLabel(
            area_excel,
            text="Segure CTRL para selecionar m\u00faltiplos arquivos",
            font=("Inter", 16),
            text_color=_tc,
            wraplength=420,
            justify="center",
        ).pack(pady=(54, 18))
        self.btn_planilhas = ctk.CTkButton(
            area_excel,
            text="PLANILHA - V\u00c1RIOS M\u00d3DULOS",
            font=("Space Grotesk", 17, "bold"),
            fg_color="#39425D" if dark_theme else "#D8E0F1",
            hover_color="#4A5575" if dark_theme else "#C9D5EA",
            border_width=1,
            border_color="#94A3B8" if dark_theme else "#AAB9D6",
            text_color="#DCE7FF" if dark_theme else "#243B6B",
            height=64,
            corner_radius=4,
            command=self.carregar_excel,
        )
        self.btn_planilhas.pack(fill="x", padx=56, pady=(0, 16))
        self.lbl_status_excel = ctk.CTkLabel(
            area_excel,
            text="Aguardando arquivos...",
            font=("Inter", 12, "bold"),
            text_color="#FCA5A5" if dark_theme else "#B91C1C",
        )
        self.lbl_status_excel.pack()
        ctk.CTkLabel(
            area_excel,
            text="Use esta \u00e1rea para carregar planilhas com v\u00e1rios m\u00f3dulos.",
            font=("Inter", 12),
            text_color=_muted,
            wraplength=420,
            justify="center",
        ).pack(pady=(12, 0))

        modos_frame = ctk.CTkFrame(
            top_grid,
            fg_color=_surface,
            corner_radius=8,
            border_width=1,
            border_color=_outline,
        )
        modos_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        card_title(modos_frame, "[>]", "SELECIONE O TIPO DE CONTEÚDO", accent="#10B981")
        ctk.CTkLabel(
            modos_frame,
            text="Escolha o TIPO de conteúdo que deseja subir. O robô irá processar todos os módulos da planilha, migrando apenas o tipo selecionado.",
            font=("Inter", 12),
            text_color=_muted,
            justify="left",
            wraplength=520,
        ).pack(anchor="w", padx=20, pady=(0, 12))

        upload_frame = ctk.CTkFrame(modos_frame, fg_color="transparent")
        upload_frame.pack(fill="x", padx=20, pady=(0, 12))
        self.botoes_upload = {}
        for modo, texto in [
            ("completo", "MODO INTEIRO"),
            ("videos", "S\u00d3 V\u00cdDEOS"),
            ("materiais", "S\u00d3 MATERIAIS"),
        ]:
            botao = ctk.CTkButton(
                upload_frame,
                text=texto,
                height=40,
                border_width=1,
                corner_radius=6,
                fg_color=_surface_alt,
                hover_color=_surface_soft,
                border_color=_outline,
                text_color=_tc,
                font=("Inter", 12, "bold"),
                command=lambda m=modo: self.selecionar_modo_upload(m),
            )
            botao.pack(fill="x", pady=4)
            self.botoes_upload[modo] = botao

        escopo_frame = ctk.CTkFrame(modos_frame, fg_color="transparent")
        escopo_frame.pack(fill="x", padx=20, pady=(0, 12))
        self.botoes_escopo = {}
        for escopo, texto in [("todos", "V\u00c1RIOS M\u00d3DULOS"), ("unico", "S\u00d3 UM M\u00d3DULO")]:
            botao = ctk.CTkButton(
                escopo_frame,
                text=texto,
                height=40,
                border_width=1,
                corner_radius=6,
                fg_color=_surface_alt,
                hover_color=_surface_soft,
                border_color=_outline,
                text_color=_tc,
                font=("Inter", 12, "bold"),
                command=lambda e=escopo: self.selecionar_escopo(e),
            )
            botao.pack(fill="x", pady=4)
            self.botoes_escopo[escopo] = botao

        upload_frame.pack_forget()
        escopo_frame.pack_forget()

        presets_frame = ctk.CTkFrame(modos_frame, fg_color="transparent")
        presets_frame.pack(fill="x", padx=20, pady=(0, 8))
        self.botoes_preset = {}
        for modo, escopo, texto in [
            ("videos", "todos", "SUBIR APENAS VÍDEOS — PLANILHA"),
            ("materiais", "todos", "SUBIR APENAS MATERIAIS IMPRESSOS — PLANILHA"),
        ]:
            botao = ctk.CTkButton(
                presets_frame,
                text=texto,
                height=58,
                corner_radius=4,
                border_width=1,
                font=("Space Grotesk", 15, "bold"),
                anchor="w",
                command=lambda m=modo, e=escopo: self.selecionar_preset_execucao(m, e),
            )
            botao.pack(fill="x", pady=7)
            self.botoes_preset[(modo, escopo)] = botao

        self.lbl_modo_resumo = ctk.CTkLabel(
            modos_frame,
            text="",
            font=("Inter", 12, "bold"),
            text_color="#FCD34D" if dark_theme else "#B45309",
            justify="left",
        )
        self.lbl_modo_resumo.pack(anchor="w", padx=20, pady=(4, 18))

        self.frame_modulo_unico = ctk.CTkFrame(
            content_wrap,
            fg_color=_surface,
            border_color=_outline,
            border_width=1,
            corner_radius=8,
        )
        ctk.CTkLabel(
            self.frame_modulo_unico,
            text="ALVO DO MODO S\u00d3 UM M\u00d3DULO",
            font=("Space Grotesk", 15, "bold"),
            text_color="#10B981" if dark_theme else "#059669",
        ).pack(anchor="w", padx=18, pady=(18, 6))
        ctk.CTkLabel(
            self.frame_modulo_unico,
            text="Pode ser o n\u00famero da linha da planilha ou o nome exato do m\u00f3dulo.",
            font=("Inter", 12),
            text_color=_muted,
            wraplength=760,
        ).pack(anchor="w", padx=18, pady=(0, 10))
        self.ent_modulo_alvo = ctk.CTkEntry(
            self.frame_modulo_unico,
            placeholder_text="Ex.: 1 ou Fundamentos do Curso",
            height=44,
            fg_color=_surface_alt,
            border_color=_outline,
            text_color=_tc,
            corner_radius=6,
        )
        if self.single_module_target:
            self.ent_modulo_alvo.insert(0, self.single_module_target)
        self.ent_modulo_alvo.pack(fill="x", padx=18, pady=(0, 18))
        self.ent_modulo_alvo.bind("<KeyRelease>", self.atualizar_alvo_modulo)

        self.actions_frame = ctk.CTkFrame(
            content_wrap,
            fg_color=_surface_alt,
            corner_radius=8,
            border_width=1,
            border_color=_outline,
        )
        self.actions_frame.pack(fill="x", pady=(18, 0))
        actions_grid = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        actions_grid.pack(fill="x", padx=20, pady=20)
        actions_grid.grid_columnconfigure(0, weight=1)
        actions_grid.grid_columnconfigure(1, weight=1)
        actions_grid.grid_columnconfigure(2, weight=1)

        self.browser_actions_frame = ctk.CTkFrame(actions_grid, fg_color="transparent")
        self.browser_actions_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.btn_abrir_plataformas = action_button(
            self.browser_actions_frame,
            "ABRIR CHROME ANTIGO E NOVO",
            "#39425D" if dark_theme else "#D8E0F1",
            "#4A5575" if dark_theme else "#C9D5EA",
            "#6B7280" if dark_theme else "#AAB9D6",
            self.abrir_plataformas,
        )
        self.btn_abrir_plataformas.pack(fill="both", expand=True)

        prepare_wrap = ctk.CTkFrame(actions_grid, fg_color="transparent")
        prepare_wrap.grid(row=0, column=1, sticky="nsew", padx=10)
        self.btn_preparar = action_button(
            prepare_wrap,
            "1 - PREPARAR ROBO",
            "#5B4932" if dark_theme else "#FDE7BE",
            "#725B3C" if dark_theme else "#FAD89B",
            "#C58A2B" if dark_theme else "#D59632",
            self.preparar_frota,
        )
        self.btn_preparar.pack(fill="both", expand=True)

        start_wrap = ctk.CTkFrame(actions_grid, fg_color="transparent")
        start_wrap.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        self.btn_iniciar = action_button(
            start_wrap,
            "2 - COME\u00c7AR A ESCRAVID\u00c3O",
            "#35172D" if dark_theme else "#F9D4DC",
            "#4B213E" if dark_theme else "#F5C0CB",
            "#7F1D3C" if dark_theme else "#BE375F",
            self.iniciar_trabalho,
            state="disabled",
        )
        self.btn_iniciar.pack(fill="both", expand=True)
        self.atualizar_botoes_modo()

        footer_header = ctk.CTkFrame(
            footer,
            fg_color="#1A2031" if dark_theme else "#E8EEF9",
            height=50,
            corner_radius=0,
        )
        footer_header.pack(fill="x")
        footer_header.pack_propagate(False)

        health_group = ctk.CTkFrame(footer_header, fg_color="transparent")
        health_group.pack(side="left", fill="y", padx=18)
        ctk.CTkLabel(
            health_group,
            text="LOG DA ISAURA - SYSTEM STABLE",
            font=("Inter", 12, "bold"),
            text_color="#10B981" if dark_theme else "#047857",
        ).pack(side="left", pady=15)
        ctk.CTkLabel(
            health_group,
            text="|",
            font=("Inter", 12, "bold"),
            text_color=_muted,
        ).pack(side="left", padx=18, pady=15)
        self.lbl_status_mod = ctk.CTkLabel(
            health_group,
            text="STATUS: AGUARDANDO...",
            font=("Space Grotesk", 16, "bold"),
            text_color="#D4D4D8" if dark_theme else "#1F2937",
        )
        self.lbl_status_mod.pack(side="left", pady=14)
        ctk.CTkButton(
            footer_header,
            text="PARAR",
            font=("Inter", 12, "bold"),
            fg_color="#FCA5A5" if dark_theme else "#F87171",
            hover_color="#F87171" if dark_theme else "#EF4444",
            text_color="#3F0C0C" if dark_theme else "#FFFFFF",
            width=96,
            height=32,
            corner_radius=4,
            command=self.parar_tudo,
        ).pack(side="right", padx=18, pady=9)

        progress_wrap = ctk.CTkFrame(footer, fg_color="transparent", height=10)
        progress_wrap.pack(fill="x")
        self.progress_bar = ctk.CTkProgressBar(
            progress_wrap,
            progress_color="#10B981",
            fg_color="#223049" if dark_theme else "#D8E0F1",
            corner_radius=0,
            height=8,
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        self.txt_log = ctk.CTkTextbox(
            footer,
            font=("Consolas", 14),
            fg_color=_surface_log,
            border_width=0,
            corner_radius=0,
            text_color="#E5E7EB" if dark_theme else "#1F2937",
        )
        self.txt_log.pack(fill="both", expand=True, padx=0, pady=0)
        self.config_tags_log(self.txt_log)
        self.txt_log.configure(state="disabled")
        self.log("INFO", "Sistema V106 (The Livewire Whisperer) Iniciado.")

    def ativar_atalhos(self):
        keyboard.add_hotkey("f12", self.parar_tudo)

    def parar_tudo(self):
        self.parar_loop = True
        self.evento_inicio_trabalho.set()
        self.tocar_som("error")
        self.log("ERRO", "PARADA DE EMERGÊNCIA SOLICITADA.")

    def carregar_excel(self):
        arquivos = filedialog.askopenfilenames(
            filetypes=[("Excel files", "*.xlsx")], title="Selecione planilhas"
        )
        if arquivos:
            carregadas = []
            erros = []
            self.total_modulos = 0
            for arq in arquivos:
                try:
                    planilha = load_excel_records(arq)
                    carregadas.append(planilha)
                    self.total_modulos += planilha["total"]
                except Exception as exc:
                    erros.append(f"{os.path.basename(arq)}: {exc}")

            self.lista_de_planilhas = carregadas
            if carregadas:
                self.lbl_status_excel.configure(
                    text=f"✅ {len(carregadas)} Arquivo(s) Carregado(s)!", text_color=VERDE_ACAO
                )
                self.lbl_workers.configure(text=f"{len(carregadas)} Módulo(s) Carregado(s)")
                self.stats_contagem = {"Sucesso": 0, "Erro": 0, "Aviso": 0}
                self.lbl_workers.configure(text=f"{self.total_modulos} MÃ³dulo(s) na fila")
                self.atualizar_resumo_modo()
                self.lbl_status_excel.configure(
                    text=f"{len(carregadas)} planilha(s) carregada(s) para varios modulos.",
                    text_color=VERDE_ACAO,
                )
            if carregadas:
                self.lbl_status_excel.configure(
                    text=f"{len(carregadas)} planilha(s) carregada(s) para v\u00e1rios m\u00f3dulos.",
                    text_color=VERDE_ACAO,
                )
                self.lbl_workers.configure(text=f"{self.total_modulos} m\u00f3dulo(s) na fila")
            if erros:
                messagebox.showwarning("Planilhas", "\n".join(erros))

    def preparar_frota(self):
        if not self.lista_de_planilhas and self.module_scope != "unico":
            return messagebox.showwarning("Aviso", "Carregue a(s) planilha(s) primeiro!")
        self.atualizar_alvo_modulo()
        try:
            planilhas_para_execucao, total_modulos = self._filtrar_planilhas_para_execucao()
        except ValueError as exc:
            return messagebox.showwarning("Modo de execuÃ§Ã£o", str(exc))
        if not planilhas_para_execucao or total_modulos <= 0:
            return messagebox.showwarning(
                "Modo de execuÃ§Ã£o",
                "Nenhum mÃ³dulo encontrado para o filtro selecionado.",
            )
        self.parar_loop = False
        self.is_running = True
        self.total_modulos = total_modulos
        self.modulos_concluidos = 0
        self.workers_ativos = len(planilhas_para_execucao)
        self.auditoria = []
        self.stats_contagem = {"Sucesso": 0, "Erro": 0, "Aviso": 0}
        self.evento_inicio_trabalho.clear()
        self.lbl_workers.configure(text=f"{self.total_modulos} MÃ³dulo(s) preparados")
        self.lbl_status_mod.configure(
            text=f"Modo: {self.descricao_modo_upload()} | Escopo: {self.descricao_escopo()}"
        )
        self.progress_bar.set(0)
        for i, plan in enumerate(planilhas_para_execucao):
            worker = FrotaWorker(self, i + 1, plan["dados"], plan["nome"])
            worker.start()
            if i < len(planilhas_para_execucao) - 1:
                time.sleep(1.5)
        self.btn_preparar.configure(state="disabled")
        if hasattr(self, "btn_sidebar_prepare"):
            self.btn_sidebar_prepare.configure(state="disabled")
        self.btn_iniciar.configure(state="normal")

    def carregar_excel(self):
        arquivos = filedialog.askopenfilenames(
            filetypes=[("Excel files", "*.xlsx")], title="Selecione planilhas"
        )
        if not arquivos:
            return

        carregadas = []
        erros = []
        self.total_modulos = 0
        for arq in arquivos:
            try:
                planilha = load_excel_records(arq)
                carregadas.append(planilha)
                self.total_modulos += planilha["total"]
            except Exception as exc:
                erros.append(f"{os.path.basename(arq)}: {exc}")

        self.lista_de_planilhas = carregadas
        if carregadas:
            self.stats_contagem = {"Sucesso": 0, "Erro": 0, "Aviso": 0}
            self.lbl_status_excel.configure(
                text=f"{len(carregadas)} planilha(s) carregada(s) para v\u00e1rios m\u00f3dulos.",
                text_color=VERDE_ACAO,
            )
            self.lbl_workers.configure(text=f"{self.total_modulos} m\u00f3dulo(s) na fila")
            self.atualizar_resumo_modo()
        if erros:
            messagebox.showwarning("Planilhas", "\n".join(erros))

    def preparar_frota(self):
        if not self.lista_de_planilhas and self.module_scope != "unico":
            return messagebox.showwarning("Aviso", "Carregue a(s) planilha(s) primeiro!")
        self.atualizar_alvo_modulo()
        try:
            planilhas_para_execucao, total_modulos = self._filtrar_planilhas_para_execucao()
        except ValueError as exc:
            return messagebox.showwarning("Modo de execu\u00e7\u00e3o", str(exc))
        if not planilhas_para_execucao or total_modulos <= 0:
            return messagebox.showwarning(
                "Modo de execu\u00e7\u00e3o",
                "Nenhum m\u00f3dulo encontrado para o filtro selecionado.",
            )

        self.parar_loop = False
        self.is_running = True
        self.total_modulos = total_modulos
        self.modulos_concluidos = 0
        self.workers_ativos = len(planilhas_para_execucao)
        self.auditoria = []
        self.stats_contagem = {"Sucesso": 0, "Erro": 0, "Aviso": 0}
        self.evento_inicio_trabalho.clear()
        self.lbl_workers.configure(text=f"{self.total_modulos} m\u00f3dulo(s) preparados")
        self.lbl_status_mod.configure(
            text=f"Modo: {self.descricao_modo_upload()} | Escopo: {self.descricao_escopo()}"
        )
        self.progress_bar.set(0)
        for i, plan in enumerate(planilhas_para_execucao):
            worker = FrotaWorker(self, i + 1, plan["dados"], plan["nome"])
            worker.start()
            if i < len(planilhas_para_execucao) - 1:
                time.sleep(1.5)
        self.btn_preparar.configure(state="disabled")
        if hasattr(self, "btn_sidebar_prepare"):
            self.btn_sidebar_prepare.configure(state="disabled")
        self.btn_iniciar.configure(state="normal")

    def iniciar_trabalho(self):
        self.btn_iniciar.configure(state="disabled")
        self.tempo_inicio_trabalho = time.time()
        self.evento_inicio_trabalho.set()
        self.tocar_som("start")

    def registrar_conclusao_modulo(self, status="Sucesso"):
        with self.progresso_lock:
            self.modulos_concluidos += 1
            if status in self.stats_contagem:
                self.stats_contagem[status] += 1
            pct = self.modulos_concluidos / self.total_modulos if self.total_modulos > 0 else 0
            self.ui_do(lambda: self.progress_bar.set(pct))
            self.ui_do(
                lambda: self.lbl_status_mod.configure(
                    text=f"🪢 ISAURA: Processados {self.modulos_concluidos}/{self.total_modulos} Módulos"
                )
            )

    def registrar_fim_worker(self, worker_id):
        with self.progresso_lock:
            self.workers_ativos -= 1
            if self.workers_ativos <= 0:
                if not self.parar_loop:
                    self.log("MODULO", "🎉 MISSÃO CUMPRIDA! Planilhas Injetadas.")
                    self.tocar_som("success")
                    self.enviar_whatsapp(
                        f"🪢 *Relatório da Isaura*\nFinalizado!\n✅ Sucessos: {self.stats_contagem['Sucesso']}\n❌ Erros: {self.stats_contagem['Erro']}\n⏭️ Pulados: {self.stats_contagem['Aviso']}"
                    )
                self.gerar_relatorio_csv()
                self.is_running = False
                self.ui_do(lambda: self.btn_preparar.configure(state="normal"))
                if hasattr(self, "btn_sidebar_prepare"):
                    self.ui_do(lambda: self.btn_sidebar_prepare.configure(state="normal"))

    def gerar_relatorio_csv(self):
        if not self.auditoria:
            return
        try:
            with open(
                f"Relatorio_Frota_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.csv",
                mode="w",
                newline="",
                encoding="utf-8-sig",
            ) as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(
                    ["Modulo", "Tipo (Vídeo/Material)", "Item", "Status", "Detalhes", "Momento"]
                )
                for l in self.auditoria:
                    writer.writerow(
                        [
                            l.get("Modulo", ""),
                            l.get("Tipo", ""),
                            l.get("Item", ""),
                            l.get("Status", ""),
                            l.get("Detalhes", ""),
                            l.get("Momento", ""),
                        ]
                    )
        except Exception as e:
            self.registrar_falha_caixa_preta("gerar_relatorio_csv", e)


if __name__ == "__main__":
    app = AppPrincipal()
    app.mainloop()
