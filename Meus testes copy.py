# * =============================================================================
# * ROBÔ HÍBRIDO V106 - TITANIUM CORE (THE LIVEWIRE WHISPERER)
# * =============================================================================

import csv
import difflib
import json
import logging
import os
import queue
import re
import socket
import sqlite3
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
CONFIG_PATH = os.path.join(BASE_DIR, "config_unificada.json")

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
    <title>Robô Híbrido - Monitor</title>
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
    <h1>🤖 Frota Enterprise</h1>
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
        self.fila_videos = []
        self.fila_arquivos = []
        self.ordem_atual = 1

    @property
    def driver(self) -> WebDriver:
        if self._driver is None:
            raise RuntimeError("WebDriver not initialized")
        return self._driver

    def log(self, tipo, msg):
        self.motor.log(tipo, f"[Robô {self.worker_id}] {msg}")

    def calcular_similaridade(self, nome_excel, nome_site):
        def limpar(t):
            return "".join(
                c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn"
            ).lower()

        n_exc = limpar(nome_excel)
        n_site = limpar(nome_site)
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
        return difflib.SequenceMatcher(None, str_exc, str_site).ratio()

    def preencher_input(self, elemento, valor):
        try:
            elemento.click()
            elemento.send_keys(Keys.CONTROL + "a")
            elemento.send_keys(Keys.DELETE)
            elemento.send_keys(valor)
        except:
            pass

    def preencher_input_humano(self, elemento, valor):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
            time.sleep(0.5)
            elemento.click()
            time.sleep(0.2)
            elemento.send_keys(Keys.CONTROL + "a")
            time.sleep(0.1)
            elemento.send_keys(Keys.DELETE)
            time.sleep(0.2)
            for char in str(valor):
                elemento.send_keys(char)
                time.sleep(0.02)
        except:
            pass

    def _buscar_valor_campo(self, by, locator):
        try:
            return (self.driver.find_element(by, locator).get_attribute("value") or "").strip()
        except:
            return ""

    def _normalizar_texto_modulo(self, texto):
        texto_limpo = "".join(
            c
            for c in unicodedata.normalize("NFD", str(texto or ""))
            if unicodedata.category(c) != "Mn"
        )
        texto_limpo = re.sub(r"[^a-z0-9\s]", " ", texto_limpo.lower())
        return " ".join(texto_limpo.split())

    def _modulos_equivalentes(self, nome_a, nome_b):
        a = self._normalizar_texto_modulo(nome_a)
        b = self._normalizar_texto_modulo(nome_b)
        if not a or not b:
            return False
        if a == b or a in b or b in a:
            return True

        stopwords = {"de", "da", "do", "das", "dos", "e", "a", "o", "para", "com", "em", "na", "no"}
        tokens_a = {t for t in a.split() if t not in stopwords}
        tokens_b = {t for t in b.split() if t not in stopwords}
        if tokens_a and tokens_b and (tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a)):
            return True

        similaridade = difflib.SequenceMatcher(None, a.replace(" ", ""), b.replace(" ", "")).ratio()
        return similaridade >= 0.92

    def _encontrar_modulo_no_novo(self, nome_modulo):
        for h6 in self.driver.find_elements(By.TAG_NAME, "h6"):
            if self._modulos_equivalentes(nome_modulo, h6.text):
                return h6
        return None

    def _eh_modulo_plano_estudos(self, nome_modulo):
        texto = self._normalizar_texto_modulo(nome_modulo)
        if not texto:
            return False

        if re.search(r"\bplano\s+de\s+estud\w*\b", texto):
            return True

        tokens = texto.split()
        for i, token in enumerate(tokens):
            if token != "plano":
                continue
            janela = tokens[i + 1 : i + 6]
            if any(t.startswith("estud") for t in janela):
                return True
        return False

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
        link = self._buscar_valor_campo(By.ID, "link")
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

    # ! NOVO MOTOR DE PESQUISA PARA COMPONENTES LIVEWIRE (V106)
    def _preencher_pesquisa_livewire(self, wait, nome_label, texto_pesquisa):
        self.log("INFO", f"Pesquisando {nome_label}: {texto_pesquisa}")

        # 1. Isola o grupo correto (div) baseando-se no texto da Label
        xp_container = f"//label[contains(text(), '{nome_label}')]/ancestor::div[contains(@class, 'form-group')]"
        container = wait.until(EC.presence_of_element_located((By.XPATH, xp_container)))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
        time.sleep(0.5)

        # 2. Encontra a caixa de texto (input) DENTRO desse grupo específico
        input_elem = container.find_element(By.XPATH, ".//input[@type='text']")
        self.driver.execute_script("arguments[0].click();", input_elem)
        time.sleep(0.3)
        input_elem.send_keys(Keys.CONTROL + "a")
        input_elem.send_keys(Keys.DELETE)
        time.sleep(0.5)

        # Digita e força a procura
        input_elem.send_keys(texto_pesquisa)
        time.sleep(
            1
        )  # Aguarda o debounce de 1500ms do site (Tempo que ele demora a pesquisar depois de pararmos de escrever)

        # 3. Aguarda o servidor responder e construir a lista (ul -> li)
        tentativas_espera = 0
        clicou = False
        xp_lista = ".//ul[contains(@class, 'list-group')]/li"

        while tentativas_espera < 15:  # Espera no máximo 7.5 segundos
            opcoes = container.find_elements(By.XPATH, xp_lista)
            for op in opcoes:
                # Se for um item da lista visível e não for texto vazio
                if op.is_displayed() and len(op.text.strip()) > 2:
                    self.driver.execute_script("arguments[0].click();", op)
                    clicou = True
                    self.log("INFO", f"Selecionado: {op.text.strip()}")
                    time.sleep(1)
                    return True  # Sai da função, foi um sucesso!

            time.sleep(0.5)
            tentativas_espera += 1

        # Se chegou aqui, não achou nada na lista.
        if not clicou:
            raise Exception(
                f"Não foi possível encontrar a opção '{texto_pesquisa}' na lista para o campo {nome_label}."
            )

    def run(self):
        try:
            self.log("INFO", f"Ligando motores para '{self.nome_arquivo}'...")
            self._driver = webdriver.Chrome(  # type: ignore[reportCallIssue]
                service=Service(ChromeDriverManager().install())
            )
            self.driver.maximize_window()
            wait = WebDriverWait(self.driver, 15)

            self.driver.get(
                self.motor.config.get(
                    "antigo_url", "https://cursoms.com.br/ead/admin/principal.asp"
                )
            )
            wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao"))).send_keys(
                self.motor.config.get("antigo_user", "")
            )
            self.driver.find_element(By.NAME, "senhadagestao").send_keys(
                self.motor.config.get("antigo_pass", "")
            )
            self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
            aba_antiga = self.driver.current_window_handle

            self.driver.execute_script(
                f"window.open('{self.motor.config.get('novo_url', 'https://novo.cursoms.com.br/login')}');"
            )
            aba_nova = self.driver.window_handles[-1]
            self.driver.switch_to.window(aba_nova)
            wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(
                self.motor.config.get("novo_user", "")
            )
            pwd = self.driver.find_element(By.NAME, "password")
            pwd.send_keys(self.motor.config.get("novo_pass", ""))
            pwd.send_keys(Keys.ENTER)
            time.sleep(3)

            self.driver.switch_to.window(aba_antiga)
            script_banner = f"document.title = '🤖 R{self.worker_id} - ' + document.title; let d = document.createElement('div'); d.innerHTML = '<h3 style=\"margin:0; font-family:sans-serif; font-size: 16px;\">🤖 SOU O ROBÔ {self.worker_id} | Planilha: {self.nome_arquivo}</h3>'; d.style.cssText = 'position:relative; width:100%; background:#4F46E5; color:white; text-align:center; z-index:999999; padding:8px; border-bottom:4px solid #F59E0B; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);'; document.body.prepend(d);"
            self.driver.execute_script(script_banner)

            self.log(
                "MODULO",
                f"Logins concluídos! Vá ao Chrome do Robô {self.worker_id}, abra o Curso desejado e aguarde.",
            )
            self.motor.evento_inicio_trabalho.wait()
            if self.motor.parar_loop:
                return

            self.driver.switch_to.window(aba_antiga)
            url_lista_antiga = self.driver.current_url

            limite_rigor = float(self.motor.config.get("match_threshold", 0.65))
            metodo_busca = self.motor.config.get(
                "search_method", "Ordem Exata (Linha 1 = Módulo 1)"
            )

            self.log("INFO", f"⚙️ Modo de Extração: {metodo_busca}")

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
                if not nome_modulo or nome_modulo.lower() == "nan":
                    continue
                curso = str(row.get("curso", "")).strip()
                professor = str(row.get("professor", row.get("professor(a)", ""))).strip()
                self.log("MODULO", f"INICIANDO: {nome_modulo}")

                # RADAR ANTI-DUPLICATAS
                self.driver.switch_to.window(aba_nova)
                self.driver.get("https://novo.cursoms.com.br/modules")
                time.sleep(2)
                try:
                    search = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//input[@type='text' and contains(@class, 'form-control')]")
                        )
                    )
                    self.preencher_input(search, nome_modulo)
                    time.sleep(3.5)
                    modulo_existente = self._encontrar_modulo_no_novo(nome_modulo)
                    if modulo_existente:
                        self.log(
                            "INFO",
                            f"🎯 Radar Ativado: Módulo '{nome_modulo}' já migrado. Saltando...",
                        )
                        self.motor.registrar_conclusao_modulo("Aviso")
                        self.motor.salvar_no_banco(
                            nome_modulo, curso, professor, "Pulado (Já Existe)"
                        )
                        indice_modulo_site += 1
                        continue
                except:
                    pass

                status_final = "Erro"
                for tentativa in range(2):
                    if self.motor.parar_loop:
                        break
                    self.fila_videos.clear()
                    self.fila_arquivos.clear()
                    self.ordem_atual = 1
                    status_final = "Sucesso"

                    try:
                        self.driver.switch_to.window(aba_antiga)
                        self.driver.get(url_lista_antiga)
                        time.sleep(1)
                        tds = wait.until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, "td.textointernos")
                            )
                        )
                        melhor_td = None
                        maior_nota = 0.0

                        if metodo_busca == "Ordem Exata (Linha 1 = Módulo 1)":
                            if indice_modulo_site < len(tds):
                                melhor_td = tds[indice_modulo_site]
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
                            self._extrair_dados_ativos()
                        else:
                            self.log("ERRO", f"Módulo antigo não encontrado.")
                            status_final = "Criado Vazio"

                        self.driver.switch_to.window(aba_nova)
                        self.driver.get("https://novo.cursoms.com.br/modules/create")
                        time.sleep(2)
                        xpath_n = "//input[@*[name()='wire:model']='module.name']"
                        input_n = wait.until(EC.presence_of_element_located((By.XPATH, xpath_n)))
                        self.preencher_input_humano(input_n, nome_modulo)
                        self.preencher_input(
                            wait.until(
                                EC.presence_of_element_located(
                                    (By.XPATH, "//input[@*[name()='wire:model']='module.time']")
                                )
                            ),
                            "0",
                        )

                        # ! PREENCHIMENTO DO CURSO E PROFESSOR COM A NOVA FUNÇÃO V106
                        if curso and str(curso).lower() != "nan":
                            self._preencher_pesquisa_livewire(wait, "Curso", curso)

                        if professor and str(professor).lower() != "nan":
                            self._preencher_pesquisa_livewire(wait, "Professor", professor)

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
                        time.sleep(4)

                        if self.fila_videos or self.fila_arquivos:
                            self.driver.get("https://novo.cursoms.com.br/modules")
                            time.sleep(2)
                            search = wait.until(
                                EC.element_to_be_clickable(
                                    (
                                        By.XPATH,
                                        "//input[@type='text' and contains(@class, 'form-control')]",
                                    )
                                )
                            )
                            self.preencher_input(search, nome_modulo)
                            time.sleep(4)

                            url_aulas = None
                            h6_modulo = self._encontrar_modulo_no_novo(nome_modulo)
                            if h6_modulo:
                                tr = h6_modulo.find_element(By.XPATH, "./ancestor::tr")
                                url_aulas = tr.find_element(
                                    By.XPATH, ".//a[contains(@href, '/lessons/')]"
                                ).get_attribute("href")

                            if url_aulas:
                                if self._eh_modulo_plano_estudos(nome_modulo):
                                    self._forcar_video_plano_estudos()
                                if self.fila_videos:
                                    self.driver.get(url_aulas)
                                    time.sleep(2)
                                    self._injetar_videos(wait, nome_modulo)
                                if self.fila_arquivos:
                                    self._injetar_materiais(wait, nome_modulo, aba_antiga, aba_nova)
                            else:
                                raise Exception(
                                    "Módulo criado não encontrado na busca (Provavelmente falhou a gravar o Curso/Professor)."
                                )
                        break
                    except Exception as e:
                        if tentativa == 0:
                            self.log(
                                "INFO",
                                f"🛡️ Auto-Cura ativada. Falha detetada: {str(e)[:50]}... reiniciando processo.",
                            )
                            time.sleep(2)
                        else:
                            self.log("ERRO", f"Falha definitiva no módulo.")
                            self.motor.registrar_falha_caixa_preta(
                                f"Frota {self.worker_id} - {nome_modulo}", e
                            )
                            status_final = "Erro"

                if status_final in ["Sucesso", "Criado Vazio"]:
                    self.motor.registrar_conclusao_modulo("Sucesso")
                else:
                    self.motor.registrar_conclusao_modulo("Erro")
                self.motor.salvar_no_banco(nome_modulo, curso, professor, status_final)

                indice_modulo_site += 1

        except Exception as e:
            self.motor.registrar_falha_caixa_preta(f"Frota {self.worker_id} Crítico", e)
            self.log("ERRO", f"Falha crítica no worker {self.worker_id}.")
            self.motor.tocar_som("error")
        finally:
            if self._driver:
                try:
                    self._driver.quit()
                except:
                    pass
            self.motor.registrar_fim_worker(self.worker_id)

    def _extrair_dados_ativos(self):
        d_url = self.driver.current_url
        if self.driver.find_elements(By.XPATH, "//a[contains(@href, 'videos.asp')]"):
            href_videos = (
                self.driver.find_elements(By.XPATH, "//a[contains(@href, 'videos.asp')]")[0]
                .get_attribute("href")
                or ""
            )
            if href_videos:
                self.driver.get(href_videos)
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

            def buscar():
                lk = self.driver.find_elements(
                    By.XPATH, f"//a[contains(@href, 'alterar_video.asp')]"
                )
                if lk:
                    return [l.get_attribute("href") for l in lk]
                for q in self.driver.find_elements(
                    By.TAG_NAME, "frame"
                ) + self.driver.find_elements(By.TAG_NAME, "iframe"):
                    try:
                        self.driver.switch_to.frame(q)
                        e = buscar()
                        if e:
                            return e
                        self.driver.switch_to.parent_frame()
                    except:
                        self.driver.switch_to.parent_frame()
                return []

            urls = buscar()
            if urls:
                urls.reverse()
                jp = self.driver.current_window_handle
                for url in urls:
                    ja = set(self.driver.window_handles)
                    try:
                        self.driver.execute_script(f"window.open('{url}');")
                        WebDriverWait(self.driver, 5).until(
                            lambda d: len(d.window_handles) > len(ja)
                        )
                        na = list(set(self.driver.window_handles) - ja)[0]
                        self.driver.switch_to.window(na)
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
                        self.fila_videos.append({"titulo": tit, **dados_video})
                        self.driver.close()
                        self.driver.switch_to.window(jp)
                    except:
                        for al in set(self.driver.window_handles) - ja:
                            self.driver.switch_to.window(al)
                            self.driver.close()
                        self.driver.switch_to.window(jp)
            self.driver.get(d_url)

        setores = {
            "Material Impresso": {"xp": "//a[contains(@href, 'setor=1')]", "id": "1"},
            "Slides": {"xp": "//a[contains(@href, 'setor=2')]", "id": "4"},
            "Atividades": {"xp": "//a[contains(@href, 'setor=4')]", "id": "3"},
        }
        for nm, inf in setores.items():
            els = self.driver.find_elements(By.XPATH, inf["xp"])
            if els:
                try:
                    href_setor = els[0].get_attribute("href") or ""
                    if href_setor:
                        self.driver.get(href_setor)
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
                    ls.reverse()
                    self.fila_arquivos.extend(ls)
                except:
                    pass
                self.driver.get(d_url)

    def _injetar_videos(self, wait, m_nome):
        if self._eh_modulo_plano_estudos(m_nome):
            self._forcar_video_plano_estudos()
        for d in list(self.fila_videos):
            if self.motor.parar_loop:
                break
            vs = d.get("vimeo", "").strip()
            youtube_link = d.get("youtube_link", "").strip()
            canal = (d.get("canal") or "").strip().lower()
            vimeo_valido = vs.isdigit() and len(vs) >= 5
            usar_youtube = canal == "youtube" or (not vimeo_valido and youtube_link)
            valor_video = youtube_link if usar_youtube else vs
            tipo_video = "YouTube" if usar_youtube else "Vimeo"

            if usar_youtube and not youtube_link:
                self.log("ERRO", f"Link do YouTube ausente: {d['titulo']}")
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Vídeo", "Item": d["titulo"], "Status": "ERRO"}
                )
                self.ordem_atual += 1
                continue

            if not usar_youtube and not vimeo_valido:
                self.log("ERRO", f"Vídeo Inválido: {d['titulo']}")
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Vídeo", "Item": d["titulo"], "Status": "ERRO"}
                )
                self.ordem_atual += 1
                continue
            try:
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "add_new_btn"))).click()
                time.sleep(1)
                self._selecionar_canal_video("youtube" if usar_youtube else "vimeo")
                cv = self._localizar_campo_video(wait, "youtube" if usar_youtube else "vimeo")
                self.preencher_input(cv, valor_video)
                cv.send_keys(Keys.TAB)
                time.sleep(3.5)
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
                    d["titulo"],
                )
                time.sleep(0.5)
                self.preencher_input(
                    self.driver.find_element(
                        By.XPATH, "//input[@*[name()='wire:model']='lessons.filename']"
                    ),
                    d["titulo"],
                )
                time.sleep(0.5)
                self.driver.find_element(
                    By.XPATH, "//input[@*[name()='wire:model']='lessons.publish_date']"
                ).send_keys(datetime.now().strftime("%d%m%Y"))
                time.sleep(1)
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Salvar')]").click()
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "add_new_btn")))
                time.sleep(0.5)
                self.log("OK", f"{tipo_video} Subido: {d['titulo'][:15]}...")
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Vídeo", "Item": d["titulo"], "Status": "Sucesso"}
                )
                self.ordem_atual += 1
            except Exception:
                self.log("ERRO", f"Falha no {tipo_video} {d['titulo'][:15]}")
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Vídeo", "Item": d["titulo"], "Status": "ERRO"}
                )
                try:
                    self.driver.refresh()
                    time.sleep(3)
                except:
                    pass

    def _injetar_materiais(self, wait, m_nome, aba_ant, aba_nov):
        ss = requests.Session()
        self.driver.switch_to.window(aba_ant)
        for c in self.driver.get_cookies():
            ss.cookies.set(c["name"], c["value"])
        self.driver.switch_to.window(aba_nov)
        psta = f"arquivos_migracao_{self.worker_id}"
        if not os.path.exists(psta):
            os.makedirs(psta)

        for d in list(self.fila_arquivos):
            if self.motor.parar_loop:
                break
            try:
                self.driver.switch_to.window(aba_ant)
                ja = set(self.driver.window_handles)
                self.driver.execute_script(f"window.open('{d['url_ver']}', '_blank');")
                WebDriverWait(self.driver, 5).until(lambda x: len(x.window_handles) > len(ja))
                ab_t = list(set(self.driver.window_handles) - ja)[0]
                self.driver.switch_to.window(ab_t)
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
                with open(cm, "wb") as f:
                    f.write(ss.get(u_arq).content)
                self.driver.close()
                self.driver.switch_to.window(aba_nov)

                self.driver.get("https://novo.cursoms.com.br/attachments/create")
                time.sleep(1)
                fi = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'input[wire\\:model="attachment.filename"]')
                    )
                )
                self.driver.execute_script(
                    "arguments[0].style.display='block'; arguments[0].style.visibility='visible';",
                    fi,
                )
                fi.send_keys(cm)
                i_n = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, 'input[wire\\:model="attachment.name"]')
                    )
                )
                self.preencher_input_humano(i_n, d["titulo"][:65].strip())
                cv = d.get("categoria_id", "1")
                self.driver.execute_script(
                    "let c = document.querySelector('select[wire\\\\:model=\"attachment.type\"]'); let t = document.querySelector('select[wire\\\\:model=\"attachment.attachable_type\"]'); if(c){c.value=arguments[0];c.dispatchEvent(new Event('change',{bubbles:true}));} if(t){t.value='Module';t.dispatchEvent(new Event('change',{bubbles:true}));}",
                    cv,
                )
                time.sleep(2.5)

                ips = self.driver.find_elements(
                    By.XPATH, "//input[@type='text' and contains(@class, 'form-control')]"
                )
                for i in ips:
                    if i.get_attribute("wire:model") == "attachment.name":
                        continue
                    if not i.get_attribute("value"):
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", i
                        )
                        time.sleep(0.5)
                        self.preencher_input_humano(i, m_nome)
                        time.sleep(4.5)
                        vs = m_nome.lower().replace("'", "")
                        xp = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{vs}') and not(*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{vs}')])]"
                        for op in self.driver.find_elements(By.XPATH, xp):
                            if op.is_displayed() and op.tag_name.lower() not in [
                                "input",
                                "html",
                                "body",
                            ]:
                                try:
                                    ActionChains(self.driver).move_to_element(op).click().perform()
                                except:
                                    self.driver.execute_script("arguments[0].click();", op)
                                break
                        break
                time.sleep(6)
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
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Material", "Item": d["titulo"], "Status": "Sucesso"}
                )
            except Exception:
                self.log("ERRO", f"Arquivo {d['titulo'][:15]}")
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Material", "Item": d["titulo"], "Status": "ERRO"}
                )
                try:
                    for ab in self.driver.window_handles:
                        if ab != aba_ant and ab != aba_nov:
                            self.driver.switch_to.window(ab)
                            self.driver.close()
                    self.driver.switch_to.window(aba_nov)
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
        self.title("Robô Híbrido V106 Login")
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

    def carregar_dados_login(self):
        self.arquivo_config = CONFIG_PATH
        self.dados_padrao = {
            "antigo_url": "https://cursoms.com.br/ead/admin/principal.asp",
            "antigo_user": "",
            "antigo_pass": "",
            "novo_url": "https://novo.cursoms.com.br/login",
            "novo_user": "",
            "novo_pass": "",
            "lembrar_user": "",
            "groq_key": CHAVE_GROQ,
            "match_threshold": 0.65,
            "whatsapp_number": "",
            "whatsapp_key": "",
            "theme": "dark",
            "search_method": "Ordem Exata (Linha 1 = Módulo 1)",
        }
        if os.path.exists(self.arquivo_config):
            try:
                with open(self.arquivo_config, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    for k, v in self.dados_padrao.items():
                        if k not in self.config:
                            self.config[k] = v
            except:
                self.config = self.dados_padrao
        else:
            self.config = self.dados_padrao

    def salvar_dados_login(self, usuario, lembrar):
        self.config["lembrar_user"] = usuario if lembrar else ""
        try:
            with open(self.arquivo_config, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except:
            pass

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
        self.title("Robô Híbrido V106 - The Livewire Whisperer")
        self.geometry("1150x800")
        MotorRobo(self, self.config)


class MotorRobo:
    def __init__(self, root, config_carregada):
        self.root = root
        self.config = config_carregada
        self.gui_queue = queue.Queue()
        self.parar_loop = False
        self.is_running = False

        self.lista_de_planilhas = []
        self.auditoria = []
        self.evento_inicio_trabalho = threading.Event()
        self.progresso_lock = threading.Lock()
        self.total_modulos = 0
        self.modulos_concluidos = 0
        self.workers_ativos = 0
        self.stats_contagem = {"Sucesso": 0, "Erro": 0, "Aviso": 0}
        self.tempo_inicio_trabalho = None

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
            except:
                pass
        else:
            if tipo == "start":
                winsound.Beep(800, 200)
            elif tipo == "success":
                winsound.Beep(1200, 300)
                time.sleep(0.1)
                winsound.Beep(1200, 300)
            elif tipo == "error":
                winsound.Beep(400, 500)

    def rotacionar_logs(self):
        if not os.path.exists("logs"):
            os.makedirs("logs")
        agora = time.time()
        for filename in os.listdir("logs"):
            filepath = os.path.join("logs", filename)
            if os.path.isfile(filepath):
                if os.stat(filepath).st_mtime < agora - 7 * 86400:
                    try:
                        os.remove(filepath)
                    except:
                        pass

    def registrar_falha_caixa_preta(self, local_erro, excecao):
        if not os.path.exists("logs"):
            os.makedirs("logs")
        try:
            with open(
                f"logs/erro_log_{datetime.now().strftime('%d-%m-%Y')}.txt", "a", encoding="utf-8"
            ) as f:
                f.write(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ERRO EM: {local_erro}\nMENSAGEM: {str(excecao)}\nRASTREAMENTO:\n{traceback.format_exc()}\n"
                    + "-" * 60
                    + "\n"
                )
        except:
            pass

    def inicializar_banco_dados(self):
        try:
            conn = sqlite3.connect("banco_frota.db")
            cursor = conn.cursor()
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS historico_modulos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_modulo TEXT, curso TEXT, professor TEXT, status TEXT, data_hora TEXT)"""
            )
            conn.commit()
            conn.close()
        except:
            pass

    def salvar_no_banco(self, nome_modulo, curso, professor, status):
        try:
            conn = sqlite3.connect("banco_frota.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO historico_modulos (nome_modulo, curso, professor, status, data_hora) VALUES (?, ?, ?, ?, ?)",
                (
                    nome_modulo,
                    curso,
                    professor,
                    status,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            conn.close()
        except:
            pass

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
        txt_widget.tag_config("ok", foreground=VERDE_ACAO)
        txt_widget.tag_config("erro", foreground=VERMELHO_PARAR)
        txt_widget.tag_config("info", foreground=AZUL_PASSO)
        txt_widget.tag_config("texto", foreground="#E2E8F0")
        txt_widget.tag_config("destaque", foreground="#F59E0B")

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

        colunas = ("id", "modulo", "curso", "status", "data")
        tv = ttk.Treeview(frame_tb, columns=colunas, show="headings")
        tv.heading("id", text="ID")
        tv.heading("modulo", text="Módulo")
        tv.heading("curso", text="Curso")
        tv.heading("status", text="Status")
        tv.heading("data", text="Data/Hora")
        tv.column("id", width=40)
        tv.column("modulo", width=300)
        tv.column("curso", width=200)
        tv.column("status", width=120)
        tv.column("data", width=150)
        tv.pack(fill="both", expand=True)

        try:
            conn = sqlite3.connect("banco_frota.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nome_modulo, curso, status, data_hora FROM historico_modulos ORDER BY id DESC"
            )
            for linha in cursor.fetchall():
                tv.insert("", "end", values=linha)
            conn.close()
        except:
            pass

        def exportar_erros():
            try:
                conn = sqlite3.connect("banco_frota.db")
                df = pd.read_sql_query(
                    "SELECT nome_modulo AS 'Nome do Módulo', curso AS 'Curso', professor AS 'Professor' FROM historico_modulos WHERE status != 'Sucesso' AND status != 'Pulado (Já Existe)'",
                    conn,
                )
                conn.close()
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
            if not os.path.exists("logs"):
                return messagebox.showinfo("IA", "Nenhum ficheiro de log encontrado!")
            arquivos = [os.path.join("logs", f) for f in os.listdir("logs") if f.endswith(".txt")]
            if not arquivos:
                return messagebox.showinfo("IA", "Nenhum erro registado ainda.")
            with open(max(arquivos, key=os.path.getctime), "r", encoding="utf-8") as f:
                logs = f.readlines()
            ultimo_erro = "".join(logs[-15:])
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
        try:
            self.ent_pergunta.delete(0, "end")
        except:
            pass
        self.txt_chat.configure(state="normal")
        self.txt_chat.insert("end", f"⚡ Llama 3.1: Processando...\n")
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")

        def _thread_ia():
            try:
                client = Groq(api_key=self.config.get("groq_key", CHAVE_GROQ))
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
            font=("Inter", 14, "bold"),
            text_color="#0EA5E9",
        ).pack(pady=5)
        cbox_search = ctk.CTkComboBox(
            f_busca,
            values=["Ordem Exata (Linha 1 = Módulo 1)", "Fuzzy Match (Buscar por Nomes)"],
            width=300,
        )
        cbox_search.set(self.config.get("search_method", "Ordem Exata (Linha 1 = Módulo 1)"))
        cbox_search.pack(pady=(5, 10))

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
            self.config["antigo_url"] = e_ant_url.get()
            self.config["antigo_user"] = e_ant_usr.get()
            self.config["antigo_pass"] = e_ant_pwd.get()
            self.config["novo_url"] = e_nov_url.get()
            self.config["novo_user"] = e_nov_usr.get()
            self.config["novo_pass"] = e_nov_pwd.get()
            self.config["groq_key"] = e_groq.get()
            self.config["whatsapp_number"] = e_wpp_num.get()
            self.config["whatsapp_key"] = e_wpp_key.get()
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            ctk.set_appearance_mode(self.config["theme"])
            messagebox.showinfo("Sucesso", "Configurações guardadas!")
            tela_cfg.destroy()

        ctk.CTkButton(
            tela_cfg,
            text="💾 SALVAR",
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            height=50,
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
            except:
                pass

    def setup_ui(self):
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
            header_side, text="🤖 ROBÔ HÍBRIDO", font=("Inter Black", 18), text_color=AZUL_PASSO
        ).pack(anchor="w")
        ctk.CTkLabel(
            header_side, text="TITANIUM V106", font=("Inter", 10, "bold"), text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(0, 10))

        frota_frame = ctk.CTkFrame(
            sidebar,
            fg_color="#1E1B4B" if self.config.get("theme") == "dark" else "#E0E7FF",
            border_width=1,
            border_color="#4338CA",
            corner_radius=8,
        )
        frota_frame.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(
            frota_frame,
            text="🏭 STATUS DA FROTA",
            font=("Inter", 12, "bold"),
            text_color="#A5B4FC" if self.config.get("theme") == "dark" else "#3730A3",
        ).pack(pady=(10, 5))
        self.lbl_workers = ctk.CTkLabel(
            frota_frame,
            text="0 Robôs Carregados",
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
            content, fg_color=_ib, border_color=BORDER_COLOR, border_width=1, corner_radius=8
        )
        area_excel.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        ctk.CTkLabel(
            area_excel,
            text="Segure CTRL para selecionar múltiplos arquivos.",
            font=("Inter", 13),
            text_color="#F59E0B",
        ).pack(pady=(30, 15))
        ctk.CTkButton(
            area_excel,
            text="📂 CARREGAR PLANILHA(S)",
            font=("Inter", 14, "bold"),
            fg_color="#F59E0B",
            hover_color="#D97706",
            height=45,
            command=self.carregar_excel,
        ).pack(pady=10)
        self.lbl_status_excel = ctk.CTkLabel(
            area_excel,
            text="Aguardando arquivos...",
            font=("Inter", 12, "bold"),
            text_color=VERMELHO_PARAR,
        )
        self.lbl_status_excel.pack(pady=10)

        actions_frame = ctk.CTkFrame(content, fg_color="transparent")
        actions_frame.pack(fill="x", padx=20, pady=10)
        self.btn_preparar = ctk.CTkButton(
            actions_frame,
            text="1️⃣ PREPARAR FROTA",
            font=("Inter", 14, "bold"),
            fg_color="#0EA5E9",
            hover_color="#0284C7",
            height=50,
            command=self.preparar_frota,
        )
        self.btn_preparar.pack(fill="x", pady=(0, 10))
        self.btn_iniciar = ctk.CTkButton(
            actions_frame,
            text="2️⃣ INICIAR INJEÇÃO",
            font=("Inter", 14, "bold"),
            fg_color="#4F46E5",
            hover_color="#4338CA",
            height=50,
            state="disabled",
            command=self.iniciar_trabalho,
        )
        self.btn_iniciar.pack(fill="x")

        bottom_area = ctk.CTkFrame(
            main_container,
            height=200,
            fg_color="#0B1119" if self.config.get("theme") == "dark" else "#E2E8F0",
            corner_radius=10,
        )
        bottom_area.pack(fill="x", side="bottom", pady=(15, 0))
        bottom_area.pack_propagate(False)
        status_bar = ctk.CTkFrame(bottom_area, fg_color="transparent")
        status_bar.pack(fill="x", padx=15, pady=(15, 5))
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
            height=10,
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
            width=80,
            height=30,
            command=self.parar_tudo,
        ).pack(side="right")

        self.txt_log = ctk.CTkTextbox(
            bottom_area,
            font=("Consolas", 12),
            fg_color="transparent",
            text_color="#E2E8F0" if self.config.get("theme") == "dark" else "#1E293B",
        )
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(5, 10))
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
            try:
                self.lista_de_planilhas = []
                self.total_modulos = 0
                for arq in arquivos:
                    df = pd.read_excel(arq)
                    df.columns = df.columns.astype(str).str.strip().str.lower()
                    self.lista_de_planilhas.append(
                        {"nome": os.path.basename(arq), "dados": df.to_dict("records")}
                    )
                    self.total_modulos += len(df.to_dict("records"))
                self.lbl_status_excel.configure(
                    text=f"✅ {len(arquivos)} Arquivo(s) Carregado(s)!", text_color=VERDE_ACAO
                )
                self.lbl_workers.configure(text=f"{len(arquivos)} Robô(s) Carregado(s)")
                self.stats_contagem = {"Sucesso": 0, "Erro": 0, "Aviso": 0}
            except Exception as e:
                messagebox.showerror("Erro", f"Planilha inválida: {e}")

    def preparar_frota(self):
        if not self.lista_de_planilhas:
            return messagebox.showwarning("Aviso", "Carregue a(s) planilha(s) primeiro!")
        self.parar_loop = False
        self.is_running = True
        self.modulos_concluidos = 0
        self.workers_ativos = len(self.lista_de_planilhas)
        self.auditoria = []
        self.stats_contagem = {"Sucesso": 0, "Erro": 0, "Aviso": 0}
        self.evento_inicio_trabalho.clear()
        for i, plan in enumerate(self.lista_de_planilhas):
            worker = FrotaWorker(self, i + 1, plan["dados"], plan["nome"])
            worker.start()
            if i < len(self.lista_de_planilhas) - 1:
                time.sleep(1.5)
        self.btn_preparar.configure(state="disabled")
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
                    text=f"🏭 FROTA: Processados {self.modulos_concluidos}/{self.total_modulos} Módulos"
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
                        f"🤖 *Relatório da Frota*\nFinalizado!\n✅ Sucessos: {self.stats_contagem['Sucesso']}\n❌ Erros: {self.stats_contagem['Erro']}\n⏭️ Pulados: {self.stats_contagem['Aviso']}"
                    )
                self.gerar_relatorio_csv()
                self.is_running = False
                self.ui_do(lambda: self.btn_preparar.configure(state="normal"))

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
                writer.writerow(["Modulo", "Tipo (Vídeo/Material)", "Item", "Status"])
                for l in self.auditoria:
                    writer.writerow(
                        [
                            l.get("Modulo", ""),
                            l.get("Tipo", ""),
                            l.get("Item", ""),
                            l.get("Status", ""),
                        ]
                    )
        except Exception as e:
            self.registrar_falha_caixa_preta("gerar_relatorio_csv", e)


if __name__ == "__main__":
    app = AppPrincipal()
    app.mainloop()
