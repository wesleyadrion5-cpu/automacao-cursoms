import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
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
# CONFIGURAÇÃO DO TEMA MODERNO (CUSTOMTKINTER)
# =============================================================================
ctk.set_appearance_mode("dark")  # Modo Escuro
ctk.set_default_color_theme("blue")  # Tema de cores azul

class MigradorUltra:
    def __init__(self, root):
        self.root = root
        self.root.title("Robô V40 Ultra - Vídeos & Materiais ⚡👑")
        self.root.geometry("600x900")
        self.root.attributes('-topmost', True)
        
        self.gui_queue = queue.Queue()
        self.driver = None
        self.silenciar = tk.BooleanVar(value=False)
        self.parar_loop = False
        
        # Variáveis Aba Vídeos
        self.fila_videos = [] 
        self.v_total_capturados = self.v_stats_sucessos = self.v_stats_erros = self.v_feitos_lote = 0
        self.v_inicio_lote = 0
        self.status_var_v = ctk.StringVar(value="Aguardando ação...")
        
        # Variáveis Aba Arquivos
        self.fila_arquivos = [] 
        self.a_total_capturados = self.a_stats_sucessos = self.a_stats_erros = self.a_feitos_lote = 0
        self.a_inicio_lote = 0
        self.var_categoria = ctk.StringVar()
        self.var_tipo = ctk.StringVar()
        self.var_vinculo = ctk.StringVar()
        self.status_var_a = ctk.StringVar(value="Aguardando ação...")

        self.carregar_config()
        self.ordem_atual = self.config.get("ultima_ordem", 1)
        self.ordem_str = ctk.StringVar(value=f"{self.ordem_atual:02d}")

        self.setup_ui()
        self.ativar_atalhos()
        self.processar_fila_gui()
        
    def processar_fila_gui(self):
        try:
            while True: self.gui_queue.get_nowait()()
        except queue.Empty: pass
        self.root.after(100, self.processar_fila_gui)

    def ui_do(self, acao): self.gui_queue.put(acao)

    def carregar_config(self):
        self.arquivo_config = "config_unificada.json"
        dados_padrao = {
            "antigo_url": "https://cursoms.com.br/ead/admin/principal.asp",
            "antigo_user": "SEU_USUARIO", "antigo_pass": "SUA_SENHA",
            "novo_url": "https://novo.cursoms.com.br/login",
            "novo_user": "SEU_EMAIL", "novo_pass": "SUA_SENHA",
            "ultima_ordem": 1, "telegram_token": "", "telegram_chat_id": "",
            "ultima_categoria": "1", "ultimo_tipo": "Module", "ultimo_vinculo": ""
        }
        if not os.path.exists(self.arquivo_config):
            with open(self.arquivo_config, "w", encoding="utf-8") as f: json.dump(dados_padrao, f, indent=4)
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
            with open(self.arquivo_config, "w", encoding="utf-8") as f: json.dump(self.config, f, indent=4)
        except: pass

    # =========================================================================
    # SISTEMA DE LOGS COLORIDOS DINÂMICOS
    # =========================================================================
    def config_tags_log(self, txt_widget):
        txt_widget.tag_config("hora", foreground="#888888") # Cinza
        txt_widget.tag_config("ok", foreground="#2ECC71") # Verde
        txt_widget.tag_config("erro", foreground="#E74C3C") # Vermelho
        txt_widget.tag_config("info", foreground="#3498DB") # Azul
        txt_widget.tag_config("texto", foreground="#ECF0F1") # Branco/Gelo

    def log_v(self, tipo, msg):
        def _inserir():
            hora = datetime.now().strftime("%H:%M:%S")
            self.txt_log_v.configure(state="normal")
            self.txt_log_v.insert("end", f"[{hora}] ", "hora")
            if tipo == "OK": self.txt_log_v.insert("end", "SUCESSO ", "ok")
            elif tipo == "ERRO": self.txt_log_v.insert("end", "ERRO ", "erro")
            else: self.txt_log_v.insert("end", "INFO ", "info")
            self.txt_log_v.insert("end", f"- {msg}\n", "texto")
            self.txt_log_v.configure(state="disabled")
            self.txt_log_v.see("end")
        self.ui_do(_inserir)

    def log_a(self, tipo, msg):
        def _inserir():
            hora = datetime.now().strftime("%H:%M:%S")
            self.txt_log_a.configure(state="normal")
            self.txt_log_a.insert("end", f"[{hora}] ", "hora")
            if tipo == "OK": self.txt_log_a.insert("end", "SUCESSO ", "ok")
            elif tipo == "ERRO": self.txt_log_a.insert("end", "ERRO ", "erro")
            else: self.txt_log_a.insert("end", "INFO ", "info")
            self.txt_log_a.insert("end", f"- {msg}\n", "texto")
            self.txt_log_a.configure(state="disabled")
            self.txt_log_a.see("end")
        self.ui_do(_inserir)

    # =========================================================================
    # INTERFACE MODERNA
    # =========================================================================
    def setup_ui(self):
        # TOPO MODERNO
        top = ctk.CTkFrame(self.root, fg_color="#1A1A1A", corner_radius=0)
        top.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(top, text="ROBÔ ULTRA V40 ⚡", font=("Impact", 24), text_color="#3498DB").pack(pady=10)
        
        cmds = ctk.CTkFrame(self.root, fg_color="transparent")
        cmds.pack(fill="x", padx=10)
        ctk.CTkButton(cmds, text="1. Login Antigo", command=self.login_antigo, width=140).pack(side="left", padx=5)
        ctk.CTkButton(cmds, text="🌐 Iniciar Navegador", fg_color="#27AE60", hover_color="#1E8449", command=self.iniciar_browser).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(cmds, text="2. Login Novo", command=self.login_novo, width=140).pack(side="right", padx=5)

        # TABVIEW (ABAS)
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        tab_v = self.tabview.add("▶️ Vídeos")
        tab_a = self.tabview.add("📄 Materiais")

        self.build_aba_videos(tab_v)
        self.build_aba_arquivos(tab_a)

    def build_aba_videos(self, tab):
        # Captura
        step1 = ctk.CTkFrame(tab)
        step1.pack(fill="x", pady=5)
        ctk.CTkLabel(step1, text="PASSO 1: Captura", font=("Arial", 12, "bold"), text_color="#F39C12").pack(pady=5)
        ctk.CTkButton(step1, text="🔍 LER LISTA", fg_color="#F39C12", hover_color="#D68910", command=self.iniciar_varredura_v_thread).pack(fill="x", padx=15, pady=5)
        self.lbl_fila_v = ctk.CTkLabel(step1, text="Fila: 0 vídeos", text_color="#E74C3C", font=("Arial", 14, "bold"))
        self.lbl_fila_v.pack()
        ctk.CTkButton(step1, text="🗑️ Pular 1º da Fila", fg_color="#7F8C8D", hover_color="#616A6B", command=self.pular_primeiro_v).pack(fill="x", padx=40, pady=5)

        # Execução
        step2 = ctk.CTkFrame(tab)
        step2.pack(fill="x", pady=5)
        ctk.CTkLabel(step2, text="PASSO 2: Execução", font=("Arial", 12, "bold"), text_color="#E74C3C").pack(pady=5)
        ctk.CTkButton(step2, text="🚀 COLAR TUDO AUTOMÁTICO", fg_color="#E74C3C", hover_color="#C0392B", font=("Arial", 14, "bold"), command=self.iniciar_colagem_v_thread).pack(fill="x", padx=15, pady=5)

        # Dashboard e Controles
        dash = ctk.CTkFrame(tab, fg_color="#17202A")
        dash.pack(fill="x", pady=5)
        
        cnt = ctk.CTkFrame(dash, fg_color="transparent")
        cnt.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(cnt, text="🔄 Reset Ordem", fg_color="#2980B9", width=100, command=self.resetar_ordem_v).pack(side="left")
        ctk.CTkLabel(cnt, textvariable=self.ordem_str, font=("Segoe UI", 24, "bold"), text_color="#3498DB").pack(side="left", padx=20)
        ctk.CTkButton(cnt, text="🛑 PARAR", fg_color="#000000", hover_color="#111111", width=100, command=self.parar_tudo).pack(side="right")

        prog_frame = ctk.CTkFrame(dash, fg_color="transparent")
        prog_frame.pack(fill="x", padx=10, pady=5)
        self.progress_bar_v = ctk.CTkProgressBar(prog_frame)
        self.progress_bar_v.pack(side="top", fill="x")
        self.progress_bar_v.set(0)
        self.lbl_eta_v = ctk.CTkLabel(prog_frame, text="⏱️ Estimativa: --:--", font=("Arial", 11))
        self.lbl_eta_v.pack()

        # LOGS TEXTBOX
        self.txt_log_v = ctk.CTkTextbox(tab, font=("Consolas", 13), fg_color="#0A0A0A")
        self.txt_log_v.pack(fill="both", expand=True, pady=5)
        self.config_tags_log(self.txt_log_v)
        self.txt_log_v.configure(state="disabled")

    def build_aba_arquivos(self, tab):
        filtros = ctk.CTkFrame(tab)
        filtros.pack(fill="x", pady=5)
        
        ctk.CTkLabel(filtros, text="Categoria:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.combo_cat = ctk.CTkComboBox(filtros, variable=self.var_categoria, values=["1 - Material do curso", "2 - Gabarito", "3 - Atividades Sugeridas", "4 - Slide", "5 - Áudio"], width=250)
        self.combo_cat.grid(row=0, column=1, pady=5)
        cat_salva = self.config.get("ultima_categoria", "1")
        for val in ["1 - Material do curso", "2 - Gabarito", "3 - Atividades Sugeridas", "4 - Slide", "5 - Áudio"]:
            if val.startswith(cat_salva): self.combo_cat.set(val)

        ctk.CTkLabel(filtros, text="Vínculo:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.combo_tipo = ctk.CTkComboBox(filtros, variable=self.var_tipo, values=["Module - Módulo", "Course - Curso", "Lesson - Aula"], width=250)
        self.combo_tipo.grid(row=1, column=1, pady=5)
        tipo_salvo = self.config.get("ultimo_tipo", "Module")
        for val in ["Module - Módulo", "Course - Curso", "Lesson - Aula"]:
            if val.startswith(tipo_salvo): self.combo_tipo.set(val)

        ctk.CTkLabel(filtros, text="Nome Exato:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.ent_vinculo = ctk.CTkEntry(filtros, textvariable=self.var_vinculo, width=250)
        self.ent_vinculo.grid(row=2, column=1, pady=5)
        self.var_vinculo.set(self.config.get("ultimo_vinculo", ""))

        step1 = ctk.CTkFrame(tab)
        step1.pack(fill="x", pady=5)
        ctk.CTkButton(step1, text="🔍 LER LISTA", fg_color="#F39C12", hover_color="#D68910", command=self.iniciar_varredura_a_thread).pack(fill="x", padx=15, pady=5)
        self.lbl_fila_a = ctk.CTkLabel(step1, text="Fila: 0 Arquivos", text_color="#E74C3C", font=("Arial", 14, "bold"))
        self.lbl_fila_a.pack()

        step2 = ctk.CTkFrame(tab)
        step2.pack(fill="x", pady=5)
        ctk.CTkButton(step2, text="🚀 MIGRAR MATERIAIS AUTOMÁTICO", fg_color="#E74C3C", hover_color="#C0392B", font=("Arial", 14, "bold"), command=self.iniciar_migracao_a_thread).pack(fill="x", padx=15, pady=5)

        cnt = ctk.CTkFrame(tab, fg_color="transparent")
        cnt.pack(fill="x", pady=5)
        ctk.CTkButton(cnt, text="🛑 PARAR", fg_color="#000000", hover_color="#111111", width=120, command=self.parar_tudo).pack(side="left")
        ctk.CTkButton(cnt, text="🔄 ZERAR DASH", fg_color="#2980B9", width=120, command=self.resetar_dashboard_a).pack(side="right")

        self.progress_bar_a = ctk.CTkProgressBar(tab)
        self.progress_bar_a.pack(fill="x", pady=5)
        self.progress_bar_a.set(0)

        # LOGS TEXTBOX
        self.txt_log_a = ctk.CTkTextbox(tab, font=("Consolas", 13), fg_color="#0A0A0A")
        self.txt_log_a.pack(fill="both", expand=True, pady=5)
        self.config_tags_log(self.txt_log_a)
        self.txt_log_a.configure(state="disabled")

    def ativar_atalhos(self):
        keyboard.add_hotkey('f8', self.resetar_ordem_v)
        keyboard.add_hotkey('f9', self.colar_proximo_manual_v)
        keyboard.add_hotkey('f10', self.iniciar_migracao_a_thread)

    # NAVEGADOR E LOGINS
    def iniciar_browser(self):
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            self.driver.maximize_window()
            self.log_v("INFO", "Navegador aberto com sucesso.")
            self.log_a("INFO", "Navegador aberto com sucesso.")
        except Exception as e: messagebox.showerror("Erro", str(e))

    def parar_tudo(self):
        self.parar_loop = True
        self.log_v("ERRO", "PARADA SOLICITADA PELO USUÁRIO.")
        self.log_a("ERRO", "PARADA SOLICITADA PELO USUÁRIO.")

    def login_antigo(self): threading.Thread(target=self._login_antigo_thread).start()
    def _login_antigo_thread(self):
        try:
            self.driver.execute_script("window.open('');"); self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(self.config["antigo_url"])
            wait = WebDriverWait(self.driver, 10)
            u = wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao")))
            u.click(); u.clear(); u.send_keys(self.config["antigo_user"])
            s = self.driver.find_element(By.NAME, "senhadagestao")
            s.click(); s.clear(); s.send_keys(self.config["antigo_pass"])
            self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
            self.log_v("OK", "Login Antigo Realizado")
        except: pass

    def login_novo(self): threading.Thread(target=self._login_novo_thread).start()
    def _login_novo_thread(self):
        try:
            self.driver.execute_script(f"window.open('{self.config['novo_url']}');"); self.driver.switch_to.window(self.driver.window_handles[-1])
            wait = WebDriverWait(self.driver, 10)
            email = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email.send_keys(self.config["novo_user"])
            pwd = self.driver.find_element(By.NAME, "password")
            pwd.send_keys(self.config["novo_pass"]); pwd.send_keys(Keys.ENTER)
            self.log_v("OK", "Login Novo Realizado")
        except: pass

    def focar_site_novo(self):
        for aba in self.driver.window_handles:
            self.driver.switch_to.window(aba)
            if "novo.cursoms" in self.driver.current_url: return True
        return False
    def focar_site_antigo(self):
        for aba in self.driver.window_handles:
            self.driver.switch_to.window(aba)
            if "cursoms.com.br" in self.driver.current_url and "novo.cursoms" not in self.driver.current_url: return True
        return False

    # =========================================================================
    # LÓGICA VÍDEOS (Velocidade Extrema)
    # =========================================================================
    def atualizar_dashboard_v(self):
        if self.v_total_capturados > 0:
            restantes = len(self.fila_videos)
            feitos = self.v_total_capturados - restantes
            pct = feitos / self.v_total_capturados
            self.ui_do(lambda: self.progress_bar_v.set(pct))
            if self.v_feitos_lote > 0 and restantes > 0:
                m, s = divmod(int(((time.time() - self.v_inicio_lote) / self.v_feitos_lote) * restantes), 60)
                self.ui_do(lambda: self.lbl_eta_v.configure(text=f"⏱️ Restante: {m:02d}:{s:02d}"))
            elif restantes == 0: self.ui_do(lambda: self.lbl_eta_v.configure(text="⏱️ Concluído!"))
        else: self.ui_do(lambda: self.progress_bar_v.set(0))

    def resetar_ordem_v(self):
        self.ordem_atual = 1; self.ordem_str.set("01"); self.salvar_config(); self.log_v("INFO", "Ordem resetada para 01")
        
    def pular_primeiro_v(self):
        if self.fila_videos:
            removido = self.fila_videos.pop(0)
            self.ui_do(lambda: self.lbl_fila_v.configure(text=f"Fila: {len(self.fila_videos)} vídeos"))
            self.log_v("ERRO", f"PULADO: {removido['titulo']}")
            self.v_stats_erros += 1; self.v_feitos_lote += 1; self.ordem_atual += 1
            self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}"))
            self.salvar_config(); self.atualizar_dashboard_v()

    def iniciar_varredura_v_thread(self): threading.Thread(target=self.varrer_lista_v).start()
    def varrer_lista_v(self):
        if not self.focar_site_antigo(): return
        self.fila_videos.clear(); self.ui_do(lambda: self.lbl_fila_v.configure(text="Fila: 0 vídeos"))
        self.log_v("INFO", "Lendo HTML da página antiga...")
        
        def buscar_links():
            links = self.driver.find_elements(By.XPATH, f"//a[contains(@href, 'alterar_video.asp')]")
            if links: return [l.get_attribute("href") for l in links]
            for q in self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe"):
                try:
                    self.driver.switch_to.frame(q)
                    encontrados = buscar_links() 
                    if encontrados: return encontrados
                    self.driver.switch_to.parent_frame() 
                except: self.driver.switch_to.parent_frame()
            return []

        urls = []
        for _ in range(5):
            self.driver.switch_to.default_content() 
            urls = buscar_links()
            if urls: break 
            time.sleep(1)

        if not urls: return self.log_v("ERRO", "Nenhum vídeo encontrado!")
        
        urls.reverse()
        janela_princ = self.driver.current_window_handle
        for i, url in enumerate(urls):
            try:
                self.driver.execute_script(f"window.open('{url}');"); self.driver.switch_to.window(self.driver.window_handles[-1])
                wait = WebDriverWait(self.driver, 5)
                elem_t = wait.until(EC.presence_of_element_located((By.ID, "assunto")))
                texto = " ".join(elem_t.get_attribute("value").strip().split())
                tit = " ".join([p if p in ['de', 'da', 'do', 'e', 'a', 'o', 'em', 'na', 'no', 'com', 'por', 'para'] else p.capitalize() for p in texto.lower().split()])
                vim = self.driver.find_element(By.ID, "vimeo").get_attribute("value")
                self.fila_videos.append({"titulo": tit, "vimeo": vim})
                self.ui_do(lambda: self.lbl_fila_v.configure(text=f"Fila: {len(self.fila_videos)} vídeos"))
                self.driver.close(); self.driver.switch_to.window(janela_princ) 
            except: self.driver.close(); self.driver.switch_to.window(janela_princ)

        self.v_total_capturados = len(self.fila_videos); self.v_stats_sucessos = self.v_stats_erros = 0
        self.atualizar_dashboard_v(); self.log_v("OK", f"Capturados {self.v_total_capturados} vídeos!")

    def iniciar_colagem_v_thread(self):
        if not self.fila_videos: return
        self.parar_loop = False; threading.Thread(target=self.loop_colagem_v).start()

    def loop_colagem_v(self):
        if not self.focar_site_novo(): return self.log_v("ERRO", "Site novo não encontrado!")
        self.v_inicio_lote = time.time(); self.v_feitos_lote = 0

        while self.fila_videos and not self.parar_loop:
            dados = self.fila_videos[0] 
            vimeo_str = dados['vimeo'].strip()
            if not vimeo_str.isdigit() or len(vimeo_str) < 5:
                self.log_v("ERRO", f"ID INVÁLIDO: {dados['titulo']}")
                self.fila_videos.pop(0); self.v_stats_erros += 1; self.v_feitos_lote += 1; self.ordem_atual += 1
                self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}")); self.atualizar_dashboard_v(); continue

            sucesso = self.processar_video_completo_v(dados)
            if sucesso:
                self.log_v("OK", f"[{self.ordem_atual:02d}] {dados['titulo']}")
                self.fila_videos.pop(0) 
                self.ui_do(lambda: self.lbl_fila_v.configure(text=f"Fila: {len(self.fila_videos)} restantes"))
                self.v_stats_sucessos += 1; self.v_feitos_lote += 1; self.ordem_atual += 1
                self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}")); self.salvar_config(); self.atualizar_dashboard_v()
            else:
                self.log_v("ERRO", f"FALHA: {dados['titulo']}")
                try: self.driver.execute_script("window.history.back();")
                except: pass
                self.fila_videos.pop(0); self.v_stats_erros += 1; self.v_feitos_lote += 1; self.ordem_atual += 1
                self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}")); self.atualizar_dashboard_v()
        
        if not self.fila_videos and not self.parar_loop: self.log_v("INFO", "LOTE DE VÍDEOS CONCLUÍDO!")

    def processar_video_completo_v(self, dados):
        try:
            wait = WebDriverWait(self.driver, 10) 
            try: wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "add_new_btn"))).click()
            except: pass

            campo_vimeo = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@*[name()='wire:model']='lessons.vimeo_id']")))
            self.preencher_input_v(campo_vimeo, dados['vimeo']); campo_vimeo.send_keys(Keys.TAB) 
            
            try: wait.until(lambda d: d.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.time']").get_attribute("value") not in ["", "0"])
            except: self.preencher_input_v(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.time']"), "1")

            self.preencher_input_v(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.order']"), str(self.ordem_atual))
            self.preencher_input_v(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.name']"), dados['titulo'])
            self.preencher_input_v(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.filename']"), dados['titulo'])
            self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.publish_date']").send_keys(datetime.now().strftime("%d%m%Y")) 
            
            self.driver.find_element(By.XPATH, "//button[contains(text(), 'Salvar')]").click()
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "add_new_btn")))
            return True
        except: return False

    def preencher_input_v(self, elemento, valor):
        try: elemento.click(); elemento.send_keys(Keys.CONTROL + "a"); elemento.send_keys(Keys.DELETE); elemento.send_keys(valor)
        except: pass

    def colar_proximo_manual_v(self):
        if self.fila_videos:
            self.parar_loop = True 
            dados = self.fila_videos[0]
            if self.focar_site_novo():
                if self.processar_video_completo_v(dados):
                    self.fila_videos.pop(0)
                    self.ui_do(lambda: self.lbl_fila_v.configure(text=f"Fila: {len(self.fila_videos)}"))
                    self.log_v("OK", f"MANUAL: {dados['titulo']}")
                    self.v_stats_sucessos += 1; self.v_feitos_lote += 1; self.ordem_atual += 1
                    self.ui_do(lambda: self.ordem_str.set(f"{self.ordem_atual:02d}")); self.salvar_config(); self.atualizar_dashboard_v()

    # =========================================================================
    # LÓGICA ARQUIVOS (Estabilidade Livewire e Velocidade)
    # =========================================================================
    def atualizar_dashboard_a(self):
        if self.a_total_capturados > 0:
            restantes = len(self.fila_arquivos)
            pct = (self.a_total_capturados - restantes) / self.a_total_capturados
            self.ui_do(lambda: self.progress_bar_a.set(pct))
        else: self.ui_do(lambda: self.progress_bar_a.set(0))

    def resetar_dashboard_a(self):
        self.parar_loop = True; self.fila_arquivos.clear()
        self.a_total_capturados = self.a_stats_sucessos = self.a_stats_erros = self.a_inicio_lote = self.a_feitos_lote = 0
        self.ui_do(lambda: self.lbl_fila_a.configure(text="Fila: 0 Arquivos")); self.atualizar_dashboard_a()
        self.log_a("INFO", "DASHBOARD ZERADO!")

    def iniciar_varredura_a_thread(self): threading.Thread(target=self.varrer_lista_a).start()
    def varrer_lista_a(self):
        if not self.driver: return
        self.fila_arquivos.clear(); self.ui_do(lambda: self.lbl_fila_a.configure(text="Fila: 0 Arquivos"))
        self.log_a("INFO", "Extraindo arquivos do site antigo...")
        try:
            if len(self.driver.window_handles) > 0: self.driver.switch_to.window(self.driver.window_handles[0])
            url_atual = self.driver.current_url
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            for item in soup.find_all('div', class_='list-item box'):
                titulo = item.find('td', class_='subject').text.strip() if item.find('td', class_='subject') else "Sem Titulo"
                for a_tag in item.find_all('a', href=True):
                    if "arquivoid.asp" in a_tag['href'].lower():
                        self.fila_arquivos.append({'titulo': titulo, 'url_ver': urljoin(url_atual, a_tag['href'])})
                        break
            self.fila_arquivos.reverse()
            self.a_total_capturados = len(self.fila_arquivos)
            self.ui_do(lambda: self.lbl_fila_a.configure(text=f"Fila: {self.a_total_capturados} Arquivos"))
            self.log_a("OK", "Lista capturada com sucesso!")
        except Exception as e: self.log_a("ERRO", f"Erro captura: {e}")

    def iniciar_migracao_a_thread(self):
        if not self.fila_arquivos: return
        self.salvar_config(); self.parar_loop = False; threading.Thread(target=self.loop_migracao_a).start()

    def loop_migracao_a(self):
        self.a_inicio_lote = time.time(); self.a_feitos_lote = 0
        session = requests.Session()
        for c in self.driver.get_cookies(): session.cookies.set(c['name'], c['value'])
        
        aba_principal_antigo = self.driver.window_handles[0]
        aba_fixa_novo = None
        for aba in self.driver.window_handles:
            self.driver.switch_to.window(aba)
            if "novo.cursoms" in self.driver.current_url or "about:blank" in self.driver.current_url: aba_fixa_novo = aba; break
        if not aba_fixa_novo: self.driver.execute_script("window.open('https://novo.cursoms.com.br/attachments/create', '_blank');"); aba_fixa_novo = self.driver.window_handles[-1]
            
        PASTA_DOWNLOADS = "arquivos_migracao" 
        if not os.path.exists(PASTA_DOWNLOADS): os.makedirs(PASTA_DOWNLOADS)

        while self.fila_arquivos and not self.parar_loop:
            dados = self.fila_arquivos[0]
            status_proc = self.processar_arquivo_completo_a(dados, session, aba_principal_antigo, aba_fixa_novo, PASTA_DOWNLOADS)
            self.fila_arquivos.pop(0)
            self.ui_do(lambda: self.lbl_fila_a.configure(text=f"Fila: {len(self.fila_arquivos)} restantes"))
            
            if status_proc: self.a_stats_sucessos += 1; self.log_a("OK", f"{dados['titulo'][:40]}")
            else: self.a_stats_erros += 1; self.log_a("ERRO", f"FALHOU: {dados['titulo'][:40]}")
            self.a_feitos_lote += 1; self.atualizar_dashboard_a()
        
        try: self.driver.switch_to.window(aba_principal_antigo)
        except: pass
        self.log_a("INFO", "LOTE DE ARQUIVOS CONCLUÍDO!")

    def processar_arquivo_completo_a(self, dados, session, aba_principal_antigo, aba_fixa_novo, pasta_downloads):
        try:
            # 1. DOWNLOAD
            self.driver.switch_to.window(aba_principal_antigo)
            self.driver.execute_script(f"window.open('{dados['url_ver']}', '_blank');")
            aba_temporaria = self.driver.window_handles[-1]
            self.driver.switch_to.window(aba_temporaria)
            
            wait_fast = WebDriverWait(self.driver, 10)
            wait_fast.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            exts = ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.pps']
            link = soup.find('a', href=lambda h: h and any(ext in h.lower() for ext in exts))
            if not link: 
                link = soup.find('a', string=re.compile(r'baixar|download|arquivo|salvar', re.IGNORECASE))
                if not link: self.driver.close(); return False
            
            url_arq = urljoin("https://cursoms.com.br/ead/", link['href'].replace("../../", ""))
            extensao_real = next((ext for ext in exts if ext in url_arq.lower()), ".pdf")
            nome_arq = re.sub(r'[\\/*?:"<>|]', "", dados['titulo'])[:60] + extensao_real
            caminho_local = os.path.abspath(os.path.join(pasta_downloads, nome_arq))
            
            with open(caminho_local, 'wb') as f: f.write(session.get(url_arq).content)
            self.driver.close() 

            # 2. UPLOAD NOVO SITE
            self.driver.switch_to.window(aba_fixa_novo)
            self.driver.get('https://novo.cursoms.com.br/attachments/create')
            
            wait = WebDriverWait(self.driver, 20)
            f_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[wire\\:model="attachment.filename"]')))
            self.driver.execute_script("arguments[0].style.display='block'; arguments[0].style.visibility='visible';", f_input)
            f_input.send_keys(caminho_local)

            titulo_limpo = dados['titulo'][:65].strip()
            input_n = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[wire\\:model="attachment.name"]')))
            input_n.clear(); input_n.send_keys(titulo_limpo)
            
            cat_val = self.var_categoria.get().split(" - ")[0]
            tip_val = self.var_tipo.get().split(" - ")[0]
            self.driver.execute_script("""
                let cat = document.querySelector('select[wire\\\\:model="attachment.type"]');
                let tip = document.querySelector('select[wire\\\\:model="attachment.attachable_type"]');
                if(cat) { cat.value = arguments[0]; cat.dispatchEvent(new Event('input', { bubbles: true })); cat.dispatchEvent(new Event('change', { bubbles: true })); }
                if(tip) { tip.value = arguments[1]; tip.dispatchEvent(new Event('input', { bubbles: true })); tip.dispatchEvent(new Event('change', { bubbles: true })); }
            """, cat_val, tip_val)

            # --- CORREÇÃO 1: Pausa para o site injetar o campo de busca na tela ---
            time.sleep(2.5) 

            vinc_val = self.var_vinculo.get().strip()
            if vinc_val:
                # --- CORREÇÃO 2: Voltando ao rastreador de inputs infalível da V27 ---
                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input.form-control[type='text']")
                for i in inputs:
                    if i.get_attribute("wire:model") != "attachment.name" and not i.get_attribute("value"):
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", i)
                        time.sleep(0.5)
                        i.click()
                        time.sleep(0.5)
                        i.send_keys(vinc_val)
                        
                        # --- CORREÇÃO 3: Pausa para o servidor buscar as opções ---
                        time.sleep(3) 
                        
                        v_safe = vinc_val.lower().replace("'", "") 
                        xpath_profundo = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}') and not(*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}')])]"
                        
                        opcoes = self.driver.find_elements(By.XPATH, xpath_profundo)
                        for opcao in opcoes:
                            if opcao.is_displayed() and opcao.tag_name.lower() not in ['input', 'html', 'body']:
                                try: ActionChains(self.driver).move_to_element(opcao).click().perform()
                                except: self.driver.execute_script("arguments[0].click();", opcao)
                                break
                        break # Sai do loop de inputs

            # --- CORREÇÃO AQUI: CLIQUE TRATOR E REDIRECIONAMENTO FORÇADO ---
            
            # Aguarda 6 segundos para dar tempo do upload (barra verde) terminar
            time.sleep(6)

            try:
                # Tenta forçar o clique em qualquer botão de submit que achar na tela
                botoes = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
                clicou = False
                for btn in botoes:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", btn)
                        clicou = True
                        break
                
                # Se não achar o botão, manda a ordem direto pro sistema do site
                if not clicou:
                    self.driver.execute_script("Livewire.first().call('handleSubmit');")
            except: pass

            # Espera 5 segundos para o site processar o salvamento
            time.sleep(5)

            # Força o robô a voltar para a lista de materiais, evitando congelamentos
            self.driver.get("https://novo.cursoms.com.br/attachments")
            time.sleep(2)
            
            return True

        except Exception as e:
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
    root = ctk.CTk()
    app = MigradorUltra(root)
    root.mainloop()