import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin 
import re 
import requests
import time
import keyboard 
import winsound
import threading 
import json
import os
import csv
import queue 
import urllib.request
import urllib.parse

# =============================================================================
# CORES E ESTILO
# =============================================================================
CORES = {
    "bg": "#FFFFFF", "topo": "#F8F9FA", "texto": "#2C3E50", 
    "destaque": "#0052CC", "destaque_a": "#8E44AD", 
    "matrix_bg": "#111111", "matrix_fg": "#00FF00",
    "btn_bg": "#ECF0F1", "sucesso": "#27AE60", "erro": "#C0392B", "dash": "#E8F8F5"
}

class MigradorUnificado:
    def __init__(self, root):
        self.root = root
        self.root.title("Robô Unificado V30 - Vídeos & Materiais 👑📲")
        self.root.geometry("540x980")
        self.root.configure(bg=CORES["bg"])
        self.root.attributes('-topmost', True)
        
        self.gui_queue = queue.Queue()
        self.driver = None
        self.silenciar = tk.BooleanVar(value=False)
        self.parar_loop = False
        
        # --- Variáveis: Aba VÍDEOS ---
        self.fila_videos = [] 
        self.v_total_capturados = 0
        self.v_stats_sucessos = 0
        self.v_stats_erros = 0
        self.v_inicio_lote = 0
        self.v_feitos_lote = 0
        self.status_var_v = tk.StringVar(value="Aguardando ação...")
        
        # --- Variáveis: Aba ARQUIVOS ---
        self.fila_arquivos = [] 
        self.a_total_capturados = 0
        self.a_stats_sucessos = 0
        self.a_stats_erros = 0
        self.a_inicio_lote = 0
        self.a_feitos_lote = 0
        self.var_categoria = tk.StringVar()
        self.var_tipo = tk.StringVar()
        self.var_vinculo = tk.StringVar()
        self.status_var_a = tk.StringVar(value="Aguardando ação...")

        self.carregar_config()
        self.ordem_atual = self.config.get("ultima_ordem", 1)
        self.ordem_str = tk.StringVar(value=f"{self.ordem_atual:02d}")

        self.setup_ui()
        self.ativar_atalhos()
        self.processar_fila_gui()
        
    # =========================================================================
    #  SISTEMA (Threads, Audio, Config, Telegram)
    # =========================================================================
    def processar_fila_gui(self):
        try:
            while True:
                tarefa = self.gui_queue.get_nowait()
                tarefa()
        except queue.Empty:
            pass
        self.root.after(100, self.processar_fila_gui)

    def ui_do(self, acao):
        self.gui_queue.put(acao)

    def carregar_config(self):
        self.arquivo_config = "config_unificada.json"
        dados_padrao = {
            "antigo_url": "https://cursoms.com.br/ead/admin/principal.asp",
            "antigo_user": "SEU_USUARIO", "antigo_pass": "SUA_SENHA",
            "novo_url": "https://novo.cursoms.com.br/login",
            "novo_user": "SEU_EMAIL", "novo_pass": "SUA_SENHA",
            "ultima_ordem": 1,
            "telegram_token": "", "telegram_chat_id": "",
            "ultima_categoria": "1", "ultimo_tipo": "Module", "ultimo_vinculo": ""
        }
        
        # Migração Inteligente de Configurações Antigas
        if not os.path.exists(self.arquivo_config):
            if os.path.exists("config.json"):
                try:
                    with open("config.json", "r", encoding="utf-8") as f: dados_padrao.update(json.load(f))
                except: pass
            if os.path.exists("config_pdf.json"):
                try:
                    with open("config_pdf.json", "r", encoding="utf-8") as f: 
                        pdf_cfg = json.load(f)
                        dados_padrao["ultima_categoria"] = pdf_cfg.get("ultima_categoria", "1")
                        dados_padrao["ultimo_tipo"] = pdf_cfg.get("ultimo_tipo", "Module")
                        dados_padrao["ultimo_vinculo"] = pdf_cfg.get("ultimo_vinculo", "")
                except: pass
            
            with open(self.arquivo_config, "w", encoding="utf-8") as f:
                json.dump(dados_padrao, f, indent=4)
            self.config = dados_padrao
        else:
            try:
                with open(self.arquivo_config, "r", encoding="utf-8") as f: self.config = json.load(f)
            except: self.config = dados_padrao

    def salvar_config(self):
        try:
            self.config["ultima_ordem"] = self.ordem_atual
            self.config["ultima_categoria"] = self.var_categoria.get().split(" - ")[0]
            self.config["ultimo_tipo"] = self.var_tipo.get().split(" - ")[0]
            self.config["ultimo_vinculo"] = self.var_vinculo.get()
            with open(self.arquivo_config, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except: pass

    def bip_sucesso(self):
        if not self.silenciar.get():
            try: winsound.Beep(1200, 100)
            except: pass

    def bip_erro(self):
        if not self.silenciar.get():
            try: winsound.Beep(500, 300)
            except: pass

    def enviar_telegram(self, mensagem):
        token = self.config.get("telegram_token", "")
        chat_id = self.config.get("telegram_chat_id", "")
        if not token or not chat_id: return 
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            dados = urllib.parse.urlencode({"chat_id": chat_id, "text": mensagem}).encode("utf-8")
            urllib.request.urlopen(url, data=dados, timeout=5)
        except Exception as e: print("Erro Telegram:", e)

    # =========================================================================
    #  INTERFACE GRÁFICA GERAL
    # =========================================================================
    def setup_ui(self):
        # TOPO (Compartilhado)
        top = tk.Frame(self.root, bg=CORES["topo"], pady=10, bd=1, relief="solid")
        top.pack(fill="x")
        tk.Label(top, text="ROBÔ UNIFICADO V30 👑📲", bg=CORES["topo"], font=("Impact", 15), fg=CORES["destaque"]).pack()
        tk.Checkbutton(top, text="🔇 Silenciar Bips", variable=self.silenciar, bg=CORES["topo"], font=("Arial", 8)).pack()
        tk.Button(top, text="🌐 Iniciar Navegador", bg=CORES["texto"], fg="white", font=("Arial", 9, "bold"), command=self.iniciar_browser).pack(pady=5)

        cmds = tk.Frame(self.root, bg=CORES["bg"], pady=5)
        cmds.pack(fill="x")
        tk.Button(cmds, text="1. Login Antigo", command=self.login_antigo, width=15).pack(side="left", padx=10)
        tk.Button(cmds, text="2. Login Novo", bg="#D5F5E3", fg="#1E8449", command=self.login_novo, width=15).pack(side="right", padx=10)

        # NOTEBOOK (Abas)
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Arial", 10, "bold"), padding=[10, 5])
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_videos = tk.Frame(self.notebook, bg=CORES["bg"])
        self.tab_arquivos = tk.Frame(self.notebook, bg=CORES["bg"])

        self.notebook.add(self.tab_videos, text="▶️ Migrar Vídeos")
        self.notebook.add(self.tab_arquivos, text="📄 Migrar Materiais")

        self.build_aba_videos()
        self.build_aba_arquivos()

    def build_aba_videos(self):
        # PASSO 1
        step1 = tk.LabelFrame(self.tab_videos, text="PASSO 1: Captura de Vídeos", bg=CORES["bg"], font=("Arial", 9, "bold"), fg="#2980B9")
        step1.pack(fill="x", padx=10, pady=5)
        tk.Button(step1, text="🔍 LER LISTA", bg="#F39C12", fg="white", font=("Arial", 10, "bold"), command=self.iniciar_varredura_v_thread).pack(fill="x", padx=5, pady=5)
        self.lbl_fila_v = tk.Label(step1, text="Fila: 0 vídeos", bg=CORES["bg"], fg="red", font=("Arial", 10))
        self.lbl_fila_v.pack()
        tk.Button(step1, text="🗑️ Pular 1º da Fila", bg="#BDC3C7", command=self.pular_primeiro_v).pack(fill="x", padx=20, pady=2)

        # PASSO 2
        step2 = tk.LabelFrame(self.tab_videos, text="PASSO 2: Execução", bg=CORES["bg"], font=("Arial", 9, "bold"), fg="red")
        step2.pack(fill="x", padx=10, pady=5)
        tk.Button(step2, text="🚀 COLAR TUDO AUTOMÁTICO", bg="red", fg="white", font=("Arial", 11, "bold"), command=self.iniciar_colagem_v_thread).pack(fill="x", padx=5, pady=5)

        # DASHBOARD
        dash = tk.Frame(self.tab_videos, bg=CORES["dash"], bd=1, relief="solid")
        dash.pack(fill="x", padx=10, pady=5)
        stat_grid = tk.Frame(dash, bg=CORES["dash"])
        stat_grid.pack(fill="x", padx=10, pady=2)
        self.lbl_stat_sucesso_v = tk.Label(stat_grid, text="✅ Sucessos: 0", bg=CORES["dash"], font=("Arial", 9), fg="#1E8449")
        self.lbl_stat_sucesso_v.pack(side="left")
        self.lbl_stat_erro_v = tk.Label(stat_grid, text="❌ Erros: 0", bg=CORES["dash"], font=("Arial", 9), fg="#C0392B")
        self.lbl_stat_erro_v.pack(side="right")

        prog_frame = tk.Frame(dash, bg=CORES["dash"])
        prog_frame.pack(fill="x", padx=10, pady=5)
        self.progress_bar_v = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.progress_bar_v.pack(side="top", fill="x")
        self.lbl_eta_v = tk.Label(prog_frame, text="⏱️ Estimativa: --:--", bg=CORES["dash"], font=("Arial", 9, "bold"), fg="#2980B9")
        self.lbl_eta_v.pack(side="bottom")

        # CONTADORES
        cnt = tk.Frame(self.tab_videos, bg=CORES["bg"], pady=5)
        cnt.pack()
        tk.Button(cnt, text="🔄 Reset (F8)", bg="#3498DB", fg="white", font=("Arial", 8, "bold"), command=self.resetar_ordem_v).pack(side="left", padx=10)
        frame_num = tk.Frame(cnt, bg=CORES["bg"])
        frame_num.pack(side="left", padx=5)
        tk.Label(frame_num, text="Ordem:", bg=CORES["bg"]).pack(side="left")
        tk.Label(frame_num, textvariable=self.ordem_str, font=("Segoe UI", 24, "bold"), bg=CORES["bg"], fg="blue").pack(side="left")
        tk.Button(cnt, text="🛑 PARAR", bg="black", fg="white", command=self.parar_tudo).pack(side="right", padx=10)

        # MATRIX VISUAL
        matrix = tk.Frame(self.tab_videos, bg=CORES["matrix_bg"], bd=2, relief="sunken")
        matrix.pack(fill="both", expand=True, padx=10, pady=5)
        self.lbl_status_acao_v = tk.Label(matrix, text="Aguardando Vídeos...", bg="black", fg="#0F0", font=("Consolas", 10))
        self.lbl_status_acao_v.pack(fill="x")
        
        tk.Label(matrix, text="✅ Histórico de Sucessos:", bg=CORES["matrix_bg"], fg="#00FF00", font=("Arial", 8, "bold")).pack(anchor="w", padx=5)
        self.lista_hist_v = tk.Listbox(matrix, bg=CORES["matrix_bg"], fg="#00FF00", height=3, bd=0, font=("Consolas", 9))
        self.lista_hist_v.pack(fill="both", expand=True, padx=5)

        tk.Label(matrix, text="⚠️ Histórico de Erros / Pulados:", bg=CORES["matrix_bg"], fg="#FF4444", font=("Arial", 8, "bold")).pack(anchor="w", padx=5)
        self.lista_erros_v = tk.Listbox(matrix, bg=CORES["matrix_bg"], fg="#FF4444", height=3, bd=0, font=("Consolas", 9))
        self.lista_erros_v.pack(fill="both", expand=True, padx=5)

        tk.Label(self.tab_videos, textvariable=self.status_var_v, bg="#ECF0F1", anchor="w", padx=5).pack(side="bottom", fill="x")

    def build_aba_arquivos(self):
        # FILTROS
        filtros = tk.LabelFrame(self.tab_arquivos, text="Configuração do Lote", bg=CORES["bg"], font=("Arial", 9, "bold"), fg=CORES["destaque_a"])
        filtros.pack(fill="x", padx=10, pady=5)
        
        tk.Label(filtros, text="Categoria:", bg=CORES["bg"]).grid(row=0, column=0, sticky="w", padx=5)
        self.combo_cat = ttk.Combobox(filtros, textvariable=self.var_categoria, values=["1 - Material do curso", "2 - Gabarito", "3 - Atividades Sugeridas", "4 - Slide", "5 - Áudio"], state="readonly", width=25)
        self.combo_cat.grid(row=0, column=1, padx=5, pady=2)
        cat_salva = self.config.get("ultima_categoria", "1")
        for val in self.combo_cat['values']:
            if val.startswith(cat_salva): self.combo_cat.set(val); break

        tk.Label(filtros, text="Vincular ao:", bg=CORES["bg"]).grid(row=1, column=0, sticky="w", padx=5)
        self.combo_tipo = ttk.Combobox(filtros, textvariable=self.var_tipo, values=["Module - Módulo", "Course - Curso", "Lesson - Aula"], state="readonly", width=25)
        self.combo_tipo.grid(row=1, column=1, padx=5, pady=2)
        tipo_salvo = self.config.get("ultimo_tipo", "Module")
        for val in self.combo_tipo['values']:
            if val.startswith(tipo_salvo): self.combo_tipo.set(val); break

        tk.Label(filtros, text="Nome Exato:", bg=CORES["bg"], font=("Arial", 8, "bold")).grid(row=2, column=0, sticky="w", padx=5)
        self.ent_vinculo = ttk.Entry(filtros, textvariable=self.var_vinculo, width=28)
        self.ent_vinculo.grid(row=2, column=1, padx=5, pady=2)
        self.var_vinculo.set(self.config.get("ultimo_vinculo", ""))

        # PASSO 1 e 2
        step1 = tk.LabelFrame(self.tab_arquivos, text="PASSO 1: Captura de Materiais", bg=CORES["bg"], font=("Arial", 9, "bold"), fg="#2980B9")
        step1.pack(fill="x", padx=10, pady=5)
        tk.Button(step1, text="🔍 LER LISTA", bg="#F39C12", fg="white", font=("Arial", 10, "bold"), command=self.iniciar_varredura_a_thread).pack(fill="x", padx=15, pady=5)
        self.lbl_fila_a = tk.Label(step1, text="Fila: 0 Arquivos", bg=CORES["bg"], fg="red")
        self.lbl_fila_a.pack()

        step2 = tk.LabelFrame(self.tab_arquivos, text="PASSO 2: Execução", bg=CORES["bg"], font=("Arial", 9, "bold"), fg="red")
        step2.pack(fill="x", padx=10, pady=5)
        tk.Button(step2, text="🚀 MIGRAR TUDO AUTOMÁTICO", bg="red", fg="white", font=("Arial", 11, "bold"), command=self.iniciar_migracao_a_thread).pack(fill="x", padx=15, pady=5)

        # DASHBOARD
        dash = tk.Frame(self.tab_arquivos, bg=CORES["dash"], bd=1, relief="solid")
        dash.pack(fill="x", padx=10, pady=5)
        stat_grid = tk.Frame(dash, bg=CORES["dash"])
        stat_grid.pack(fill="x", padx=10)
        self.lbl_stat_sucesso_a = tk.Label(stat_grid, text="✅ Sucessos: 0", bg=CORES["dash"], font=("Arial", 9), fg="#1E8449")
        self.lbl_stat_sucesso_a.pack(side="left")
        self.lbl_stat_erro_a = tk.Label(stat_grid, text="❌ Erros: 0", bg=CORES["dash"], font=("Arial", 9), fg="#C0392B")
        self.lbl_stat_erro_a.pack(side="right")

        prog_frame = tk.Frame(dash, bg=CORES["dash"])
        prog_frame.pack(fill="x", padx=10, pady=5)
        self.progress_bar_a = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.progress_bar_a.pack(side="top", fill="x")
        self.lbl_eta_a = tk.Label(prog_frame, text="⏱️ Estimativa: --:--", bg=CORES["dash"], font=("Arial", 9, "bold"), fg="#2980B9")
        self.lbl_eta_a.pack(side="bottom")

        # BOTOES E MATRIX
        cnt = tk.Frame(self.tab_arquivos, bg=CORES["bg"], pady=5)
        cnt.pack(fill="x", padx=20)
        tk.Button(cnt, text="🛑 PARAR", bg="black", fg="white", font=("Arial", 9, "bold"), width=12, command=self.parar_tudo).pack(side="left")
        tk.Button(cnt, text="🔄 ZERAR DASH", bg="#3498DB", fg="white", font=("Arial", 9, "bold"), command=self.resetar_dashboard_a).pack(side="right")

        matrix = tk.Frame(self.tab_arquivos, bg="black", bd=2, relief="sunken")
        matrix.pack(fill="both", expand=True, padx=10, pady=5)
        self.lbl_status_acao_a = tk.Label(matrix, text="Aguardando Materiais...", bg="black", fg="#0F0", font=("Consolas", 10))
        self.lbl_status_acao_a.pack(fill="x")
        self.lista_hist_a = tk.Listbox(matrix, bg="black", fg="#008000", height=6, bd=0, font=("Consolas", 9))
        self.lista_hist_a.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        tk.Label(self.tab_arquivos, textvariable=self.status_var_a, bg="#ECF0F1", anchor="w", padx=5).pack(side="bottom", fill="x")

    def ativar_atalhos(self):
        keyboard.add_hotkey('f8', self.resetar_ordem_v)
        keyboard.add_hotkey('f9', self.colar_proximo_manual_v)
        keyboard.add_hotkey('f10', self.iniciar_migracao_a_thread)

    # =========================================================================
    #  NAVEGADOR E LOGINS COMPARTILHADOS
    # =========================================================================
    def iniciar_browser(self):
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            self.driver.maximize_window()
            msg = "Navegador aberto. Faça os logins."
            self.status_var_v.set(msg); self.status_var_a.set(msg)
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def parar_tudo(self):
        self.parar_loop = True
        msg = "🛑 Parada solicitada..."
        self.status_var_v.set(msg); self.status_var_a.set(msg)
        self.enviar_telegram("🛑 Operação pausada pelo utilizador.")

    def login_antigo(self): threading.Thread(target=self._login_antigo_thread).start()
    def _login_antigo_thread(self):
        try:
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(self.config["antigo_url"])
            wait = WebDriverWait(self.driver, 10)
            u = wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao")))
            u.click(); u.clear(); u.send_keys(self.config["antigo_user"])
            s = self.driver.find_element(By.NAME, "senhadagestao")
            s.click(); s.clear(); s.send_keys(self.config["antigo_pass"])
            self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
            self.ui_do(lambda: self.status_var_v.set("Login antigo OK"))
        except: pass

    def login_novo(self): threading.Thread(target=self._login_novo_thread).start()
    def _login_novo_thread(self):
        try:
            self.driver.execute_script(f"window.open('{self.config['novo_url']}');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            wait = WebDriverWait(self.driver, 10)
            email = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email.send_keys(self.config["novo_user"])
            pwd = self.driver.find_element(By.NAME, "password")
            pwd.send_keys(self.config["novo_pass"])
            pwd.send_keys(Keys.ENTER)
            self.ui_do(lambda: self.status_var_v.set("Login novo OK"))
        except: pass

    def focar_site_novo(self):
        for aba in self.driver.window_handles:
            self.driver.switch_to.window(aba)
            if "novo.cursoms" in self.driver.current_url: return True
        return False

    def focar_site_antigo(self):
        for aba in self.driver.window_handles:
            self.driver.switch_to.window(aba)
            url = self.driver.current_url
            if "cursoms.com.br" in url and "novo.cursoms" not in url: return True
        return False

    # =========================================================================
    #  LÓGICA - ABA DE VÍDEOS (V17)
    # =========================================================================
    def atualizar_dashboard_v(self):
        self.ui_do(lambda: self.lbl_stat_sucesso_v.config(text=f"✅ Sucessos: {self.v_stats_sucessos}"))
        self.ui_do(lambda: self.lbl_stat_erro_v.config(text=f"❌ Erros: {self.v_stats_erros}"))
        
        if self.v_total_capturados > 0:
            restantes = len(self.fila_videos)
            feitos = self.v_total_capturados - restantes
            pct = (feitos / self.v_total_capturados) * 100
            self.ui_do(lambda: self.progress_bar_v.config(value=pct))
            
            if self.v_feitos_lote > 0 and restantes > 0:
                tempo_medio = (time.time() - self.v_inicio_lote) / self.v_feitos_lote
                m, s = divmod(int(tempo_medio * restantes), 60)
                self.ui_do(lambda: self.lbl_eta_v.config(text=f"⏱️ Estimativa: {m:02d}:{s:02d}"))
            elif restantes == 0:
                self.ui_do(lambda: self.lbl_eta_v.config(text="⏱️ Estimativa: Concluído!"))
        else:
            self.ui_do(lambda: self.lbl_eta_v.config(text="⏱️ Estimativa: --:--"))
            self.ui_do(lambda: self.progress_bar_v.config(value=0))

    def salvar_relatorio_v(self, titulo, vimeo, status):
        try:
            existe = os.path.exists("relatorio_videos.csv")
            with open("relatorio_videos.csv", mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';') 
                if not existe: writer.writerow(['Data/Hora', 'Ordem', 'Titulo da Aula', 'ID Vimeo', 'Status'])
                writer.writerow([datetime.now().strftime("%d/%m/%Y %H:%M:%S"), self.ordem_atual, titulo, vimeo, status])
        except: pass

    def resetar_ordem_v(self):
        self.ordem_atual = 1
        self.ordem_str.set("01")
        self.salvar_config()
        self.status_var_v.set("🔄 Ordem resetada para 01!")
        self.bip_erro() 

    def pular_primeiro_v(self):
        if self.fila_videos:
            removido = self.fila_videos.pop(0)
            self.lbl_fila_v.config(text=f"Fila: {len(self.fila_videos)} vídeos")
            self.status_var_v.set(f"Pulado: {removido['titulo']}")
            self.salvar_relatorio_v(removido['titulo'], removido['vimeo'], "Pulado Manualmente")
            self.lista_erros_v.insert(0, f"[{self.ordem_atual:02d}] PULADO: {removido['titulo']}")
            self.v_stats_erros += 1
            self.v_feitos_lote += 1
            self.ordem_atual += 1
            self.ordem_str.set(f"{self.ordem_atual:02d}")
            self.salvar_config()
            self.atualizar_dashboard_v()

    def iniciar_varredura_v_thread(self): threading.Thread(target=self.varrer_lista_v).start()
    def varrer_lista_v(self):
        if not self.driver: return
        if not self.focar_site_antigo():
            self.ui_do(lambda: messagebox.showerror("Erro", "Aba do site antigo não encontrada."))
            return

        self.fila_videos.clear()
        self.ui_do(lambda: self.lbl_fila_v.config(text="Fila: 0 vídeos"))
        self.ui_do(lambda: self.status_var_v.set("🔍 Caçando vídeos (Aguarde)..."))
        
        def buscar_links_em_frames():
            links = self.driver.find_elements(By.XPATH, f"//a[contains(@href, 'alterar_video.asp')]")
            if links: return [l.get_attribute("href") for l in links]
            quadros = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
            for quadro in quadros:
                try:
                    self.driver.switch_to.frame(quadro)
                    encontrados = buscar_links_em_frames() 
                    if encontrados: return encontrados
                    self.driver.switch_to.parent_frame() 
                except: self.driver.switch_to.parent_frame()
            return []

        try:
            urls = []
            for _ in range(5):
                self.driver.switch_to.default_content() 
                urls = buscar_links_em_frames()
                if urls: break 
                time.sleep(1) 

            if not urls:
                self.ui_do(lambda: self.status_var_v.set("❌ NADA ENCONTRADO!"))
                return

            urls.reverse() 
            self.ui_do(lambda: self.status_var_v.set(f"Capturando {len(urls)} vídeos..."))
            janela_princ = self.driver.current_window_handle
            
            for i, url in enumerate(urls):
                try:
                    self.ui_do(lambda: self.status_var_v.set(f"Extraindo dados... ({i+1}/{len(urls)})"))
                    self.driver.execute_script(f"window.open('{url}');") 
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    wait = WebDriverWait(self.driver, 5)
                    elem_t = wait.until(EC.presence_of_element_located((By.ID, "assunto")))
                    tit = self.embelezar_texto_v(elem_t.get_attribute("value"))
                    vim = self.driver.find_element(By.ID, "vimeo").get_attribute("value")
                    
                    self.fila_videos.append({"titulo": tit, "vimeo": vim})
                    self.ui_do(lambda: self.lbl_fila_v.config(text=f"Fila: {len(self.fila_videos)} vídeos"))
                    self.driver.close() 
                    self.driver.switch_to.window(janela_princ) 
                except:
                    self.driver.close()
                    self.driver.switch_to.window(janela_princ)

            self.v_total_capturados = len(self.fila_videos)
            self.v_stats_sucessos = 0
            self.v_stats_erros = 0
            self.atualizar_dashboard_v()
            self.ui_do(lambda: self.lista_hist_v.delete(0, tk.END))
            self.ui_do(lambda: self.lista_erros_v.delete(0, tk.END))
            self.ui_do(lambda: self.status_var_v.set("✅ Captura de Vídeos finalizada!"))
            self.bip_sucesso()
        except Exception as e:
            self.ui_do(lambda: self.status_var_v.set(f"Erro fatal captura: {e}"))

    def embelezar_texto_v(self, texto):
        if not texto: return ""
        texto = " ".join(texto.strip().split())
        excecoes = ['de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'as', 'os', 'em', 'na', 'no', 'com', 'por', 'para']
        palavras = texto.lower().split()
        if not palavras: return ""
        resultado = [palavras[0].capitalize()] 
        for p in palavras[1:]:
            if p in excecoes: resultado.append(p)
            else: resultado.append(p.capitalize())
        return " ".join(resultado)

    def iniciar_colagem_v_thread(self):
        if not self.fila_videos: return
        self.parar_loop = False
        threading.Thread(target=self.loop_colagem_v).start()

    def loop_colagem_v(self):
        if not self.focar_site_novo():
            self.ui_do(lambda: self.status_var_v.set("❌ Site novo não encontrado!"))
            return

        self.v_inicio_lote = time.time()
        self.v_feitos_lote = 0

        while self.fila_videos and not self.parar_loop:
            dados = self.fila_videos[0] 
            vimeo_str = dados['vimeo'].strip()
            
            if not vimeo_str.isdigit() or len(vimeo_str) < 5:
                self.ui_do(lambda: self.status_var_v.set(f"🗑️ ID Lixo ignorado: {dados['titulo']}"))
                self.salvar_relatorio_v(dados['titulo'], vimeo_str, "Erro: ID Inválido")
                self.ui_do(lambda: self.lista_erros_v.insert(0, f"[{self.ordem_atual:02d}] INVÁLIDO: {dados['titulo']}"))
                self.fila_videos.pop(0)
                self.v_stats_erros += 1
                self.v_feitos_lote += 1
                self.ordem_atual += 1
                self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}"))
                self.atualizar_dashboard_v()
                self.bip_erro()
                continue

            sucesso = self.processar_video_completo_v(dados)
            
            if sucesso:
                self.fila_videos.pop(0) 
                self.ui_do(lambda: self.lbl_fila_v.config(text=f"Fila: {len(self.fila_videos)} restantes"))
                self.salvar_relatorio_v(dados['titulo'], dados['vimeo'], "Sucesso")
                self.v_stats_sucessos += 1
                self.v_feitos_lote += 1
                self.ordem_atual += 1
                self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}"))
                self.salvar_config()
                self.atualizar_dashboard_v()
                time.sleep(1.0) 
            else:
                self.ui_do(lambda: self.status_var_v.set("⚠️ Falha crítica. Pulando..."))
                self.bip_erro()
                self.salvar_relatorio_v(dados['titulo'], dados['vimeo'], "Falha Crítica na Cópia")
                self.ui_do(lambda: self.lista_erros_v.insert(0, f"[{self.ordem_atual:02d}] FALHOU: {dados['titulo']}"))
                try: self.driver.execute_script("window.history.back();"); time.sleep(2)
                except: pass
                self.fila_videos.pop(0) 
                self.v_stats_erros += 1
                self.v_feitos_lote += 1
                self.ordem_atual += 1
                self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}"))
                self.atualizar_dashboard_v()
        
        if not self.fila_videos and not self.parar_loop:
            self.ui_do(lambda: self.status_var_v.set("🎉 PROCESSO CONCLUÍDO!"))
            self.bip_sucesso()
            self.enviar_telegram(f"🎉 Migração de Módulo (Vídeos) Concluída!\n✅ Sucessos: {self.v_stats_sucessos}\n❌ Erros: {self.v_stats_erros}")

    def processar_video_completo_v(self, dados):
        try:
            wait = WebDriverWait(self.driver, 15) 
            try:
                btn_add = self.driver.find_element(By.CLASS_NAME, "add_new_btn")
                self.ui_do(lambda: self.lbl_status_acao_v.config(text=f"Adicionando: {dados['titulo']}..."))
                self.driver.execute_script("arguments[0].click();", btn_add)
            except: pass

            self.ui_do(lambda: self.lbl_status_acao_v.config(text="Preenchendo ID..."))
            campo_vimeo = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@*[name()='wire:model']='lessons.vimeo_id']")))
            campo_ordem = self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.order']")
            campo_nome  = self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.name']")
            campo_arq   = self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.filename']")
            campo_data  = self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.publish_date']")
            
            self.preencher_input_v(campo_vimeo, dados['vimeo'])
            campo_vimeo.send_keys(Keys.TAB) 
            
            self.ui_do(lambda: self.lbl_status_acao_v.config(text="⏳ Aguardando dados do Vimeo..."))
            def duracao_apareceu(driver):
                try:
                    val = driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.time']").get_attribute("value")
                    return val and val.isdigit() and int(val) > 0
                except: return False

            try:
                WebDriverWait(self.driver, 3).until(duracao_apareceu)
                time.sleep(0.5) 
            except:
                self.ui_do(lambda: self.lbl_status_acao_v.config(text="⚠️ Timeout. Forçando '1'..."))
                try: self.preencher_input_v(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.time']"), "1")
                except: pass

            self.ui_do(lambda: self.lbl_status_acao_v.config(text="Sobrescrevendo nomes..."))
            self.preencher_input_v(campo_ordem, str(self.ordem_atual))
            self.preencher_input_v(campo_nome, dados['titulo'])
            self.preencher_input_v(campo_arq, dados['titulo'])
            campo_data.send_keys(datetime.now().strftime("%d%m%Y")) 
            
            self.ui_do(lambda: self.lbl_status_acao_v.config(text="Salvando..."))
            btn_salvar = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Salvar')]")
            self.driver.execute_script("arguments[0].click();", btn_salvar)
            
            self.ui_do(lambda: self.lbl_status_acao_v.config(text="Verificando..."))
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "add_new_btn")))
                self.ui_do(lambda: self.lista_hist_v.insert(0, f"✅ [{self.ordem_atual:02d}] {dados['titulo']}"))
                return True
            except:
                self.ui_do(lambda: self.lbl_status_acao_v.config(text="❌ Erro ao salvar!"))
                return False
        except: return False

    def preencher_input_v(self, elemento, valor):
        try:
            elemento.click()
            elemento.send_keys(Keys.CONTROL + "a")
            elemento.send_keys(Keys.DELETE)
            elemento.send_keys(valor)
        except: pass

    def colar_proximo_manual_v(self):
        if self.fila_videos:
            self.parar_loop = True 
            if self.v_feitos_lote == 0: self.v_inicio_lote = time.time()
            dados = self.fila_videos[0]
            if self.focar_site_novo():
                if self.processar_video_completo_v(dados):
                    self.fila_videos.pop(0)
                    self.ui_do(lambda: self.lbl_fila_v.config(text=f"Fila: {len(self.fila_videos)}"))
                    self.salvar_relatorio_v(dados['titulo'], dados['vimeo'], "Sucesso (Manual)")
                    self.v_stats_sucessos += 1
                    self.v_feitos_lote += 1
                    self.ordem_atual += 1
                    self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}"))
                    self.salvar_config()
                    self.atualizar_dashboard_v()
                    self.bip_sucesso()

    # =========================================================================
    #  LÓGICA - ABA DE ARQUIVOS (V27)
    # =========================================================================
    def atualizar_dashboard_a(self):
        self.ui_do(lambda: self.lbl_stat_sucesso_a.config(text=f"✅ Sucessos: {self.a_stats_sucessos}"))
        self.ui_do(lambda: self.lbl_stat_erro_a.config(text=f"❌ Erros: {self.a_stats_erros}"))
        
        if self.a_total_capturados > 0:
            restantes = len(self.fila_arquivos)
            feitos = self.a_total_capturados - restantes
            pct = (feitos / self.a_total_capturados) * 100
            self.ui_do(lambda: self.progress_bar_a.config(value=pct))
            
            if self.a_feitos_lote > 0 and restantes > 0:
                tempo_medio = (time.time() - self.a_inicio_lote) / self.a_feitos_lote
                m, s = divmod(int(tempo_medio * restantes), 60)
                self.ui_do(lambda: self.lbl_eta_a.config(text=f"⏱️ Estimativa: {m:02d}:{s:02d}"))
            elif restantes == 0:
                self.ui_do(lambda: self.lbl_eta_a.config(text="⏱️ Estimativa: Concluído!"))
        else:
            self.ui_do(lambda: self.lbl_eta_a.config(text="⏱️ Estimativa: --:--"))
            self.ui_do(lambda: self.progress_bar_a.config(value=0))

    def salvar_relatorio_a(self, titulo, status):
        try:
            existe = os.path.exists("relatorio_pdfs.csv")
            with open("relatorio_pdfs.csv", mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';') 
                if not existe: writer.writerow(['Data/Hora', 'Titulo do Arquivo', 'Status'])
                writer.writerow([datetime.now().strftime("%d/%m/%Y %H:%M:%S"), titulo, status])
        except: pass

    def resetar_dashboard_a(self):
        self.parar_loop = True 
        self.fila_arquivos.clear()
        self.a_total_capturados = self.a_stats_sucessos = self.a_stats_erros = self.a_inicio_lote = self.a_feitos_lote = 0
        self.ui_do(lambda: self.lbl_fila_a.config(text="Fila: 0 Arquivos"))
        self.ui_do(lambda: self.lista_hist_a.delete(0, tk.END))
        self.atualizar_dashboard_a()
        self.ui_do(lambda: self.status_var_a.set("🔄 Zerado! Mude a página no Chrome e clique em LER LISTA."))
        self.ui_do(lambda: self.lbl_status_acao_a.config(text="Aguardando próximo lote..."))

    def iniciar_varredura_a_thread(self): threading.Thread(target=self.varrer_lista_a).start()
    def varrer_lista_a(self):
        if not self.driver: return
        self.fila_arquivos.clear()
        self.ui_do(lambda: self.lbl_fila_a.config(text="Fila: 0 Arquivos"))
        self.ui_do(lambda: self.status_var_a.set("🔍 Lendo HTML da página..."))
        
        try:
            if len(self.driver.window_handles) > 0:
                self.driver.switch_to.window(self.driver.window_handles[0])
                
            url_atual = self.driver.current_url
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            itens = soup.find_all('div', class_='list-item box')
            
            for item in itens:
                titulo = item.find('td', class_='subject').text.strip() if item.find('td', class_='subject') else "Sem Titulo"
                link_correto = None
                for a_tag in item.find_all('a', href=True):
                    if "arquivoid.asp" in a_tag['href'].lower():
                        link_correto = a_tag
                        break
                if link_correto: 
                    self.fila_arquivos.append({'titulo': titulo, 'url_ver': urljoin(url_atual, link_correto['href'])})
                    
            self.fila_arquivos.reverse()
            self.a_total_capturados = len(self.fila_arquivos)
            self.ui_do(lambda: self.lbl_fila_a.config(text=f"Fila: {self.a_total_capturados} Arquivos"))
            self.ui_do(lambda: self.status_var_a.set("✅ Capturado de baixo para cima!"))
            self.bip_sucesso()
        except Exception as e: 
            self.ui_do(lambda: self.status_var_a.set(f"Erro captura: {e}"))

    def iniciar_migracao_a_thread(self):
        if not self.fila_arquivos: return
        self.salvar_config()
        self.parar_loop = False
        threading.Thread(target=self.loop_migracao_a).start()

    def loop_migracao_a(self):
        self.a_inicio_lote = time.time()
        self.a_feitos_lote = 0
        session = requests.Session()
        for c in self.driver.get_cookies(): session.cookies.set(c['name'], c['value'])
        
        aba_principal_antigo = self.driver.window_handles[0]
        aba_fixa_novo = None
        for aba in self.driver.window_handles:
            self.driver.switch_to.window(aba)
            if "novo.cursoms" in self.driver.current_url or "about:blank" in self.driver.current_url:
                aba_fixa_novo = aba
                break
                
        if not aba_fixa_novo:
            self.driver.execute_script("window.open('https://novo.cursoms.com.br/attachments/create', '_blank');")
            aba_fixa_novo = self.driver.window_handles[-1]
            
        PASTA_DOWNLOADS = "arquivos_migracao" 
        if not os.path.exists(PASTA_DOWNLOADS): os.makedirs(PASTA_DOWNLOADS)

        while self.fila_arquivos and not self.parar_loop:
            try:
                if aba_principal_antigo not in self.driver.window_handles:
                    self.ui_do(lambda: self.status_var_a.set("❌ Erro: Navegador fechado!"))
                    break
            except: break

            dados = self.fila_arquivos[0]
            status_proc = self.processar_arquivo_completo_a(dados, session, aba_principal_antigo, aba_fixa_novo, PASTA_DOWNLOADS)
            
            self.fila_arquivos.pop(0)
            self.ui_do(lambda: self.lbl_fila_a.config(text=f"Fila: {len(self.fila_arquivos)} restantes"))
            
            if status_proc: self.a_stats_sucessos += 1
            else: self.a_stats_erros += 1
            
            self.a_feitos_lote += 1
            self.atualizar_dashboard_a()
        
        try: self.driver.switch_to.window(aba_principal_antigo)
        except: pass
        self.ui_do(lambda: self.status_var_a.set("🎉 LOTE CONCLUÍDO! Clique em ZERAR DASHBOARD."))
        self.enviar_telegram(f"🎉 Migração de Materiais Concluída!\n✅ Sucessos: {self.a_stats_sucessos}\n❌ Erros: {self.a_stats_erros}")

    def processar_arquivo_completo_a(self, dados, session, aba_principal_antigo, aba_fixa_novo, pasta_downloads):
        try:
            self.driver.switch_to.window(aba_principal_antigo)
            self.ui_do(lambda: self.lbl_status_acao_a.config(text=f"Lendo: {dados['titulo'][:20]}..."))
            
            self.driver.execute_script(f"window.open('{dados['url_ver']}', '_blank');")
            time.sleep(2)
            aba_temporaria = self.driver.window_handles[-1]
            self.driver.switch_to.window(aba_temporaria)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            extensoes_permitidas = ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.pps']
            link = soup.find('a', href=lambda h: h and any(ext in h.lower() for ext in extensoes_permitidas))
            
            if not link: 
                link = soup.find('a', string=re.compile(r'baixar|download|arquivo|salvar', re.IGNORECASE))
                if not link:
                    self.driver.close()
                    return False
            
            url_arq = link['href']
            if "../../" in url_arq: url_arq = url_arq.replace("../../", "https://cursoms.com.br/ead/")
            elif not url_arq.startswith("http"): url_arq = urljoin("https://cursoms.com.br/ead/", url_arq)
            
            extensao_real = ".pdf"
            for ext in extensoes_permitidas:
                if ext in url_arq.lower(): extensao_real = ext; break
            
            nome_arq = re.sub(r'[\\/*?:"<>|]', "", dados['titulo'])[:60] + extensao_real
            caminho_local = os.path.abspath(os.path.join(pasta_downloads, nome_arq))
            
            self.ui_do(lambda: self.lbl_status_acao_a.config(text=f"Baixando Arquivo ({extensao_real})..."))
            with open(caminho_local, 'wb') as f: f.write(session.get(url_arq).content)
            self.driver.close() 

            self.driver.switch_to.window(aba_fixa_novo)
            self.driver.get('https://novo.cursoms.com.br/attachments/create')
            
            if "login" in self.driver.current_url.lower():
                self.ui_do(lambda: self.lbl_status_acao_a.config(text="Sessão caiu! Refazendo login automático..."))
                try:
                    self.driver.find_element(By.NAME, "email").send_keys(self.config["novo_user"])
                    p = self.driver.find_element(By.NAME, "password")
                    p.send_keys(self.config["novo_pass"])
                    p.send_keys(Keys.ENTER)
                    time.sleep(3)
                    self.driver.get('https://novo.cursoms.com.br/attachments/create')
                except: pass

            wait = WebDriverWait(self.driver, 20)
            self.ui_do(lambda: self.lbl_status_acao_a.config(text="Iniciando Upload do Arquivo..."))
            f_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[wire\\:model="attachment.filename"]')))
            self.driver.execute_script("arguments[0].style.display='block'; arguments[0].style.visibility='visible';", f_input)
            f_input.send_keys(caminho_local)

            self.ui_do(lambda: self.lbl_status_acao_a.config(text="Preenchendo nome do material..."))
            titulo_limpo = dados['titulo'][:65].strip()
            input_n = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[wire\\:model="attachment.name"]')))
            input_n.clear()
            input_n.send_keys(titulo_limpo)
            
            self.ui_do(lambda: self.lbl_status_acao_a.config(text="Setando Categoria e Tipo..."))
            cat_val = self.var_categoria.get().split(" - ")[0]
            tip_val = self.var_tipo.get().split(" - ")[0]
            self.driver.execute_script("""
                let cat = document.querySelector('select[wire\\\\:model="attachment.type"]');
                let tip = document.querySelector('select[wire\\\\:model="attachment.attachable_type"]');
                if(cat) { cat.value = arguments[0]; cat.dispatchEvent(new Event('input', { bubbles: true })); cat.dispatchEvent(new Event('change', { bubbles: true })); }
                if(tip) { tip.value = arguments[1]; tip.dispatchEvent(new Event('input', { bubbles: true })); tip.dispatchEvent(new Event('change', { bubbles: true })); }
            """, cat_val, tip_val)
            
            time.sleep(4) 

            vinc_val = self.var_vinculo.get().strip()
            if vinc_val:
                self.ui_do(lambda: self.lbl_status_acao_a.config(text="Pesquisando Módulo..."))
                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input.form-control[type='text']")
                for i in inputs:
                    if i.get_attribute("wire:model") != "attachment.name" and not i.get_attribute("value"):
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", i)
                        time.sleep(0.5)
                        i.click()
                        time.sleep(0.5)
                        i.send_keys(vinc_val)
                        
                        self.ui_do(lambda: self.lbl_status_acao_a.config(text="Aguardando lista do servidor (3s)..."))
                        time.sleep(3) 
                        
                        try:
                            v_safe = vinc_val.lower().replace("'", "") 
                            xpath_profundo = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}') and not(*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}')])]"
                            opcoes = self.driver.find_elements(By.XPATH, xpath_profundo)
                            clicou = False
                            
                            for opcao in opcoes:
                                if opcao.is_displayed() and opcao.tag_name.lower() not in ['input', 'html', 'body']:
                                    try: ActionChains(self.driver).move_to_element(opcao).click().perform()
                                    except: self.driver.execute_script("arguments[0].click();", opcao)
                                    clicou = True
                                    self.ui_do(lambda: self.lbl_status_acao_a.config(text="✅ Módulo Clicado!"))
                                    time.sleep(1)
                                    break
                            
                            if not clicou:
                                i.send_keys(Keys.ARROW_DOWN)
                                time.sleep(0.5)
                                i.send_keys(Keys.TAB)
                        except: pass
                        break

            self.ui_do(lambda: self.lbl_status_acao_a.config(text="Aguardando confirmação de Upload (6s)..."))
            time.sleep(6) 

            self.ui_do(lambda: self.lbl_status_acao_a.config(text="Salvando na plataforma..."))
            try: self.driver.execute_script("Livewire.first().call('handleSubmit');")
            except:
                btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                self.driver.execute_script("arguments[0].click();", btn)
            
            self.ui_do(lambda: self.lbl_status_acao_a.config(text="Aguardando Redirecionamento..."))
            time.sleep(6)

            self.driver.get("https://novo.cursoms.com.br/attachments")
            time.sleep(2)

            self.salvar_relatorio_a(titulo_limpo, "Sucesso")
            self.ui_do(lambda: self.lista_hist_a.insert(0, f"✅ OK: {titulo_limpo}"))
            return True

        except Exception as e:
            self.salvar_relatorio_a(dados['titulo'][:65].strip(), "Falha Crítica")
            try:
                if self.driver.session_id:
                    for aba in self.driver.window_handles:
                        if aba != aba_principal_antigo and aba != aba_fixa_novo:
                            self.driver.switch_to.window(aba)
                            self.driver.close()
                    self.driver.switch_to.window(aba_fixa_novo)
            except: pass
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = MigradorUnificado(root)
    root.mainloop()