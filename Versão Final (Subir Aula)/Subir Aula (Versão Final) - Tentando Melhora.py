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
import queue 

# =============================================================================
# CONFIGURAÇÃO DO TEMA MODERNO
# =============================================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AppPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Acesso Restrito - Login")
        self.geometry("400x550")
        
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = (largura_tela // 2) - (400 // 2)
        pos_y = (altura_tela // 2) - (550 // 2)
        self.geometry(f"400x550+{pos_x}+{pos_y}")
        self.attributes('-topmost', True)
        self.autenticado = False
        self.construir_tela_login()

    def construir_tela_login(self):
        self.frame_login = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_login.pack(fill="both", expand=True)

        ctk.CTkLabel(self.frame_login, text="🔐", font=("Arial", 60)).pack(pady=(30, 10))
        ctk.CTkLabel(self.frame_login, text="CENTRAL DE COMANDO", font=("Impact", 24), text_color="#3498DB").pack(pady=(0, 20))

        self.ent_user = ctk.CTkEntry(self.frame_login, placeholder_text="Seu Usuário", width=260, height=45, font=("Arial", 14), justify="center")
        self.ent_user.pack(pady=10)

        self.ent_pass = ctk.CTkEntry(self.frame_login, placeholder_text="Sua Senha", show="*", width=260, height=45, font=("Arial", 14), justify="center")
        self.ent_pass.pack(pady=10)

        ctk.CTkButton(self.frame_login, text="ENTRAR NO SISTEMA", font=("Arial", 15, "bold"), width=260, height=45, fg_color="#27AE60", hover_color="#1E8449", command=self.fazer_login).pack(pady=(20, 10))
        
        self.lbl_status = ctk.CTkLabel(self.frame_login, text="", text_color="#E74C3C", font=("Arial", 13, "bold"))
        self.lbl_status.pack(pady=5)

    def fazer_login(self):
        user = self.ent_user.get().strip()
        senha = self.ent_pass.get().strip()
        if not user or not senha:
            self.lbl_status.configure(text="⚠️ Preencha usuário e senha!", text_color="#F39C12")
            return
        self.lbl_status.configure(text="Conectando ao servidor...", text_color="#3498DB")
        self.update()
        try:
            url_api = "https://WesleyAdrion.pythonanywhere.com/api/login/" 
            resposta = requests.post(url_api, json={"username": user, "password": senha}, timeout=10)
            if resposta.status_code != 200:
                self.lbl_status.configure(text=f"❌ Erro no Servidor", text_color="#E74C3C")
                return
            dados = resposta.json()
            if dados.get("status") == "sucesso":
                self.iniciar_robo_principal()
            else:
                self.lbl_status.configure(text="❌ Usuário ou senha incorretos!", text_color="#E74C3C")
        except Exception:
            self.lbl_status.configure(text="⚠️ Servidor offline!", text_color="#E74C3C")

    def iniciar_robo_principal(self):
        self.frame_login.destroy()
      Subir Aula (Versão Final) - Tentando Melhora  self.title("Robô Híbrido V80 - Transporte Master 🚛")
        self.geometry("750x950")
        MotorRobo(self)


class MotorRobo:
    def __init__(self, root):
        self.root = root
        self.gui_queue = queue.Queue()
        self.driver = None
        self.parar_loop = False
        self.is_running = False 
        
        self.fila_videos = [] 
        self.fila_arquivos = [] 
        self.memoria_lote = [] 
        self.ordem_atual = 1
        
        self.stats = {"v_sucesso": 0, "v_erro": 0, "a_sucesso": 0, "a_erro": 0}

        self.carregar_config()
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
        dados_padrao = {"antigo_url": "https://cursoms.com.br/ead/admin/principal.asp", "antigo_user": "", "antigo_pass": "", "novo_url": "https://novo.cursoms.com.br/login", "novo_user": "", "novo_pass": ""}
        if not os.path.exists(self.arquivo_config):
            with open(self.arquivo_config, "w", encoding="utf-8") as f: json.dump(dados_padrao, f, indent=4)
            self.config = dados_padrao
        else:
            try:
                with open(self.arquivo_config, "r", encoding="utf-8") as f: self.config = json.load(f)
            except: self.config = dados_padrao

    def config_tags_log(self, txt_widget):
        txt_widget.tag_config("hora", foreground="#888888") 
        txt_widget.tag_config("ok", foreground="#2ECC71") 
        txt_widget.tag_config("erro", foreground="#E74C3C") 
        txt_widget.tag_config("info", foreground="#3498DB") 
        txt_widget.tag_config("texto", foreground="#ECF0F1") 
        txt_widget.tag_config("destaque", foreground="#F1C40F") 

    def log(self, tipo, msg):
        def _inserir():
            hora = datetime.now().strftime("%H:%M:%S")
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"[{hora}] ", "hora")
            if tipo == "OK": self.txt_log.insert("end", "SUCESSO ", "ok")
            elif tipo == "ERRO": self.txt_log.insert("end", "ERRO ", "erro")
            elif tipo == "MODULO": self.txt_log.insert("end", "▶ FASE ", "destaque")
            else: self.txt_log.insert("end", "INFO ", "info")
            self.txt_log.insert("end", f"- {msg}\n", "texto" if tipo != "MODULO" else "destaque")
            self.txt_log.configure(state="disabled")
            self.txt_log.see("end")
        self.ui_do(_inserir)

    def setup_ui(self):
        top = ctk.CTkFrame(self.root, fg_color="#1A1A1A", corner_radius=0)
        top.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(top, text="ROBÔ HÍBRIDO V80 🚛", font=("Impact", 28), text_color="#3498DB").pack(pady=10)
        
        cmds = ctk.CTkFrame(self.root, fg_color="transparent")
        cmds.pack(fill="x", padx=10)
        ctk.CTkButton(cmds, text="1. Login Antigo", command=self.login_antigo, width=140).pack(side="left", padx=5)
        ctk.CTkButton(cmds, text="🌐 Iniciar Navegador", fg_color="#27AE60", hover_color="#1E8449", command=self.iniciar_browser).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(cmds, text="2. Login Novo", command=self.login_novo, width=140).pack(side="right", padx=5)

        tab_esteira = ctk.CTkFrame(self.root)
        tab_esteira.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(tab_esteira, text="📝 Cole a lista (APENAS O NOME DO MÓDULO, UM POR LINHA):", font=("Arial", 14, "bold"), text_color="#BDC3C7").pack(pady=5)
        self.txt_lote = ctk.CTkTextbox(tab_esteira, font=("Consolas", 14), height=200)
        self.txt_lote.pack(fill="both", expand=True, padx=10, pady=5)
        self.txt_lote.insert("0.0", "(SESAU) Revisão Em Questões\n(SESAU) Biossegurança")

        botoes_fase = ctk.CTkFrame(tab_esteira, fg_color="transparent")
        botoes_fase.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(botoes_fase, text="📦 1. EXTRAIR DO ANTIGO", font=("Arial", 14, "bold"), height=50, fg_color="#D68910", hover_color="#B9770E", command=self.iniciar_extracao_massa).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(botoes_fase, text="🚀 2. INJETAR NO NOVO", font=("Arial", 14, "bold"), height=50, fg_color="#E74C3C", hover_color="#C0392B", command=self.iniciar_injecao_massa).pack(side="right", expand=True, padx=5)

        self.lbl_memoria = ctk.CTkLabel(tab_esteira, text="🧠 Módulos na Memória: 0", font=("Arial", 14, "bold"), text_color="#2ECC71")
        self.lbl_memoria.pack(pady=5)

        dash = ctk.CTkFrame(self.root, fg_color="#17202A")
        dash.pack(fill="x", padx=15, pady=5)
        
        cnt = ctk.CTkFrame(dash, fg_color="transparent")
        cnt.pack(fill="x", padx=10, pady=5)
        self.lbl_status_mod = ctk.CTkLabel(cnt, text="Status: Aguardando...", font=("Segoe UI", 16, "bold"), text_color="#2ECC71")
        self.lbl_status_mod.pack(side="left", padx=10)
        ctk.CTkButton(cnt, text="🛑 PARAR", fg_color="#000000", hover_color="#111111", width=120, command=self.parar_tudo).pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(dash)
        self.progress_bar.pack(fill="x", padx=10, pady=10)
        self.progress_bar.set(0)

        self.txt_log = ctk.CTkTextbox(self.root, font=("Consolas", 13), fg_color="#0A0A0A", height=180)
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=5)
        self.config_tags_log(self.txt_log)
        self.txt_log.configure(state="disabled")

    def ativar_atalhos(self):
        keyboard.add_hotkey('f12', self.parar_tudo)

    def iniciar_browser(self):
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            self.driver.maximize_window()
            self.log("INFO", "Navegador aberto.")
        except Exception as e: messagebox.showerror("Erro", str(e))

    def parar_tudo(self):
        self.parar_loop = True
        self.log("ERRO", "PARADA DE EMERGÊNCIA SOLICITADA.")

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
            self.log("OK", "Login Antigo Realizado")
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
            self.log("OK", "Login Novo Realizado")
        except: pass

    # =========================================================================
    # FUNÇÕES DE DIGITAÇÃO
    # =========================================================================
    def preencher_input(self, elemento, valor):
        # A MÁGICA DA V53 (Rápido, sem pausa)
        try: 
            elemento.click()
            elemento.send_keys(Keys.CONTROL + "a")
            elemento.send_keys(Keys.DELETE)
            elemento.send_keys(valor)
        except: pass

    def preencher_input_humano(self, elemento, valor):
        # Digitação lenta para formulários do Livewire de upload
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
        except: pass

    def expandir_paginacao_jplist(self):
        try:
            self.driver.switch_to.default_content()
            painel = self.driver.find_element(By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel")
            self.driver.execute_script("arguments[0].click();", painel)
            time.sleep(0.5)
            ver_todos = self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']")
            self.driver.execute_script("arguments[0].click();", ver_todos)
            time.sleep(2.5) 
        except: pass

    def atualizar_progresso(self):
        total = len(self.fila_videos) + len(self.fila_arquivos) + self.stats['v_sucesso'] + self.stats['v_erro'] + self.stats['a_sucesso'] + self.stats['a_erro']
        if total > 0:
            feitos = total - (len(self.fila_videos) + len(self.fila_arquivos))
            self.ui_do(lambda: self.progress_bar.set(feitos / total))

    def _varrer_tudo_sincrono(self, aba_antiga):
        dashboard_url = self.driver.current_url
        self.fila_videos.clear()
        self.fila_arquivos.clear()
        
        # VÍDEOS
        icone_video = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'videos.asp')]")
        if icone_video:
            self.driver.get(icone_video[0].get_attribute("href"))
            time.sleep(2)
            self.expandir_paginacao_jplist()
            
            def buscar_links_v():
                links = self.driver.find_elements(By.XPATH, f"//a[contains(@href, 'alterar_video.asp')]")
                if links: return [l.get_attribute("href") for l in links]
                for q in self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe"):
                    try:
                        self.driver.switch_to.frame(q)
                        en = buscar_links_v() 
                        if en: return en
                        self.driver.switch_to.parent_frame() 
                    except: self.driver.switch_to.parent_frame()
                return []

            urls = buscar_links_v()
            if urls:
                urls.reverse()
                janela_princ = self.driver.current_window_handle
                for url in urls:
                    janelas_antes = set(self.driver.window_handles) 
                    try:
                        self.driver.execute_script(f"window.open('{url}');")
                        WebDriverWait(self.driver, 5).until(lambda d: len(d.window_handles) > len(janelas_antes))
                        nova_aba = list(set(self.driver.window_handles) - janelas_antes)[0]
                        self.driver.switch_to.window(nova_aba)
                        
                        wait = WebDriverWait(self.driver, 5)
                        elem_t = wait.until(EC.presence_of_element_located((By.ID, "assunto")))
                        tit = " ".join([p if p in ['de', 'da', 'do', 'e', 'a', 'o', 'em', 'na', 'no', 'com', 'por', 'para'] else p.capitalize() for p in " ".join(elem_t.get_attribute("value").strip().split()).lower().split()])
                        vim = self.driver.find_element(By.ID, "vimeo").get_attribute("value")
                        self.fila_videos.append({"titulo": tit, "vimeo": vim})
                        self.driver.close() 
                        self.driver.switch_to.window(janela_princ) 
                    except: 
                        janelas_atuais = set(self.driver.window_handles)
                        abas_lixo = janelas_atuais - janelas_antes
                        for aba_lixo in abas_lixo:
                            self.driver.switch_to.window(aba_lixo); self.driver.close()
                        self.driver.switch_to.window(janela_princ)
            self.driver.get(dashboard_url)

        # MATERIAIS
        links_setores = {
            "Material Impresso": {"xpath": "//a[contains(@href, 'setor=1')]", "cat_id": "1"},
            "Slides": {"xpath": "//a[contains(@href, 'setor=2')]", "cat_id": "4"},
            "Atividades": {"xpath": "//a[contains(@href, 'setor=4')]", "cat_id": "3"}
        }
        
        for nome, info in links_setores.items():
            elems = self.driver.find_elements(By.XPATH, info["xpath"])
            if elems:
                self.driver.get(elems[0].get_attribute("href"))
                time.sleep(2)
                self.expandir_paginacao_jplist()
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                lote_setor = []
                for item in soup.find_all('div', class_='list-item box'):
                    titulo = item.find('td', class_='subject').text.strip() if item.find('td', class_='subject') else "Sem Titulo"
                    for a_tag in item.find_all('a', href=True):
                        if "arquivoid.asp" in a_tag['href'].lower():
                            lote_setor.append({'titulo': titulo, 'url_ver': urljoin(self.driver.current_url, a_tag['href']), 'categoria_id': info["cat_id"], 'nome_categoria': nome})
                            break
                lote_setor.reverse()
                self.fila_arquivos.extend(lote_setor)
                self.driver.get(dashboard_url)

    # =========================================================================
    # CORREÇÃO DA V53 (O TAB MÁGICO)
    # =========================================================================
    def _despejar_videos(self):
        wait = WebDriverWait(self.driver, 10)
        for dados in list(self.fila_videos):
            if self.parar_loop: break
            vimeo_str = dados['vimeo'].strip()
            
            if not vimeo_str.isdigit() or len(vimeo_str) < 5:
                self.log("ERRO", f"VÍDEO INVÁLIDO: {dados['titulo']}")
                self.ordem_atual += 1
                self.fila_videos.pop(0)
                self.stats['v_erro'] += 1
                self.atualizar_progresso()
                continue
                
            try:
                # Clica em Adicionar Nova Aula
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "add_new_btn"))).click()
                time.sleep(1) 
                
                # Preenche o ID do Vimeo e dá TAB (O GATILHO MÁGICO DA V53)
                campo_vimeo = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@*[name()='wire:model']='lessons.vimeo_id']")))
                self.preencher_input(campo_vimeo, dados['vimeo'])
                campo_vimeo.send_keys(Keys.TAB) 
                
                # 🛑 FREIO 1: Pausa de 3.5 segundos para o Livewire buscar os dados no Vimeo
                time.sleep(3.5) 
                
                # Aguarda e preenche a duração (Tempo)
                try: 
                    wait.until(lambda d: d.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.time']").get_attribute("value") not in ["", "0"])
                except: 
                    self.preencher_input(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.time']"), "1")
                
                # 🛑 FREIOS 2: Preenche os nomes com pausas curtas (0.5s) da V53
                self.preencher_input(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.order']"), str(self.ordem_atual))
                time.sleep(0.5)
                
                self.preencher_input(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.name']"), dados['titulo'])
                time.sleep(0.5)
                
                self.preencher_input(self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.filename']"), dados['titulo'])
                time.sleep(0.5)
                
                self.driver.find_element(By.XPATH, "//input[@*[name()='wire:model']='lessons.publish_date']").send_keys(datetime.now().strftime("%d%m%Y")) 
                time.sleep(1)
                
                # Clica em Salvar
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Salvar')]").click()
                
                # Aguarda o botão Adicionar reaparecer para confirmar que salvou
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "add_new_btn")))
                time.sleep(0.5)
                
                self.log("OK", f"Vídeo Subido: {dados['titulo'][:20]}...")
                self.ordem_atual += 1
                self.fila_videos.pop(0)
                self.stats['v_sucesso'] += 1
                self.atualizar_progresso()
                
            except Exception as e:
                self.log("ERRO", f"Falha no vídeo {dados['titulo']}")
                self.ordem_atual += 1
                self.fila_videos.pop(0)
                self.stats['v_erro'] += 1
                self.atualizar_progresso()
                try: 
                    self.driver.refresh()
                    time.sleep(3) 
                except: pass

    def _despejar_materiais(self, modulo_nome, aba_antiga, aba_nova):
        session = requests.Session()
        self.driver.switch_to.window(aba_antiga)
        for c in self.driver.get_cookies(): session.cookies.set(c['name'], c['value'])
        self.driver.switch_to.window(aba_nova)
        wait = WebDriverWait(self.driver, 15)
        
        PASTA = "arquivos_migracao" 
        if not os.path.exists(PASTA): os.makedirs(PASTA)

        for dados in list(self.fila_arquivos):
            if self.parar_loop: break
            try:
                self.driver.switch_to.window(aba_antiga)
                janelas_antes = set(self.driver.window_handles)
                self.driver.execute_script(f"window.open('{dados['url_ver']}', '_blank');")
                WebDriverWait(self.driver, 5).until(lambda d: len(d.window_handles) > len(janelas_antes))
                aba_temp = list(set(self.driver.window_handles) - janelas_antes)[0]
                self.driver.switch_to.window(aba_temp)
                
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                exts = ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.pps']
                link = soup.find('a', href=lambda h: h and any(ext in h.lower() for ext in exts))
                if not link: link = soup.find('a', string=re.compile(r'baixar|download|arquivo|salvar', re.IGNORECASE))
                if not link: raise Exception("Sem link")
                
                url_arq = urljoin("https://cursoms.com.br/ead/", link['href'].replace("../../", ""))
                nome_arq = re.sub(r'[\\/*?:"<>|]', "", dados['titulo'])[:60] + next((ext for ext in exts if ext in url_arq.lower()), ".pdf")
                cam = os.path.abspath(os.path.join(PASTA, nome_arq))
                
                with open(cam, 'wb') as f: f.write(session.get(url_arq).content)
                self.driver.close()

                self.driver.switch_to.window(aba_nova)
                self.driver.get('https://novo.cursoms.com.br/attachments/create')
                time.sleep(1)
                
                f_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[wire\\:model="attachment.filename"]')))
                self.driver.execute_script("arguments[0].style.display='block'; arguments[0].style.visibility='visible';", f_input)
                f_input.send_keys(cam)

                input_n = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[wire\\:model="attachment.name"]')))
                self.preencher_input_humano(input_n, dados['titulo'][:65].strip())
                
                cat_val = dados.get('categoria_id', "1")
                self.driver.execute_script("""
                    let cat = document.querySelector('select[wire\\\\:model="attachment.type"]');
                    let tip = document.querySelector('select[wire\\\\:model="attachment.attachable_type"]');
                    if(cat) { cat.value = arguments[0]; cat.dispatchEvent(new Event('change', { bubbles: true })); }
                    if(tip) { tip.value = 'Module'; tip.dispatchEvent(new Event('change', { bubbles: true })); }
                """, cat_val)
                time.sleep(2.5) 

                inputs = self.driver.find_elements(By.XPATH, "//input[@type='text' and contains(@class, 'form-control')]")
                for i in inputs:
                    if i.get_attribute("wire:model") == "attachment.name": continue
                    if not i.get_attribute("value"):
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", i)
                        time.sleep(0.5)
                        self.preencher_input_humano(i, modulo_nome)
                        time.sleep(4.5) 
                        v_safe = modulo_nome.lower().replace("'", "") 
                        xp = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}') and not(*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}')])]"
                        for opcao in self.driver.find_elements(By.XPATH, xp):
                            if opcao.is_displayed() and opcao.tag_name.lower() not in ['input', 'html', 'body']:
                                try: ActionChains(self.driver).move_to_element(opcao).click().perform()
                                except: self.driver.execute_script("arguments[0].click();", opcao)
                                break
                        break 

                time.sleep(6)
                try:
                    botoes = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
                    clicou = False
                    for btn in botoes:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(0.5); self.driver.execute_script("arguments[0].click();", btn)
                            clicou = True; break
                    if not clicou: self.driver.execute_script("Livewire.first().call('handleSubmit');")
                except: pass

                time.sleep(5)
                self.driver.get("https://novo.cursoms.com.br/attachments")
                time.sleep(2)
                try: os.remove(cam)
                except: pass
                
                self.log("OK", f"Arquivo Subido: {dados['titulo'][:20]}...")
                self.fila_arquivos.pop(0)
                self.stats['a_sucesso'] += 1
                self.atualizar_progresso()
            except Exception as e:
                self.log("ERRO", f"Arquivo {dados['titulo'][:20]}")
                self.fila_arquivos.pop(0)
                self.stats['a_erro'] += 1
                self.atualizar_progresso()
                try:
                    janelas_atuais = self.driver.window_handles
                    for aba in janelas_atuais:
                        if aba != aba_antiga and aba != aba_nova:
                            self.driver.switch_to.window(aba); self.driver.close()
                    self.driver.switch_to.window(aba_nova)
                except: pass

    # =========================================================================
    # FASE 1: LER TUDO DO ANTIGO
    # =========================================================================
    def iniciar_extracao_massa(self):
        if getattr(self, 'is_running', False): return messagebox.showwarning("Aviso", "O robô já está rodando!")
        if not self.driver: return messagebox.showwarning("Aviso", "Inicie o navegador e faça os logins!")
        
        texto_bruto = self.txt_lote.get("1.0", "end-1c").strip()
        lote = [linha.strip() for linha in texto_bruto.split("\n") if linha.strip()]
        
        if not lote: return messagebox.showwarning("Aviso", "A lista está vazia.")

        self.parar_loop = False; self.is_running = True
        threading.Thread(target=self._extracao_massa_thread, args=(lote,)).start()

    def _extracao_massa_thread(self, lote):
        try:
            aba_antiga = None
            for aba in self.driver.window_handles:
                self.driver.switch_to.window(aba)
                if "cursoms.com.br" in self.driver.current_url and "novo." not in self.driver.current_url: aba_antiga = aba; break
            
            if not aba_antiga: return self.log("ERRO", "Site antigo não encontrado.")

            self.driver.switch_to.window(aba_antiga)
            url_lista = self.driver.current_url
            self.memoria_lote = [] 

            self.ui_do(lambda: self.lbl_status_mod.configure(text=f"FASE 1: Extraindo 0/{len(lote)}", text_color="#F39C12"))

            for i, nome_modulo in enumerate(lote):
                if self.parar_loop: break
                
                self.log("MODULO", f"EXTRAINDO: {nome_modulo}")
                self.driver.switch_to.window(aba_antiga)
                self.driver.get(url_lista)
                time.sleep(1)

                try:
                    wait = WebDriverWait(self.driver, 10)
                    tds = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "td.textointernos")))
                    btn_acessar_modulo = None
                    nome_procurado = re.sub(r'[^\w]', '', str(nome_modulo).lower())
                    
                    for td in tds:
                        texto_td = re.sub(r'[^\w]', '', str(td.text).lower())
                        if nome_procurado in texto_td or texto_td in nome_procurado:
                            btn_acessar_modulo = td.find_element(By.XPATH, "./preceding-sibling::td//a")
                            break
                    
                    if btn_acessar_modulo:
                        self.driver.execute_script("arguments[0].click();", btn_acessar_modulo)
                        btn_aula = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'aula.asp')]")))
                        self.driver.execute_script("arguments[0].click();", btn_aula)
                        
                        self._varrer_tudo_sincrono(aba_antiga)
                        
                        self.memoria_lote.append({
                            "nome_modulo": nome_modulo,
                            "videos": list(self.fila_videos),
                            "arquivos": list(self.fila_arquivos)
                        })
                        self.log("INFO", f"Guardado: {len(self.fila_videos)} vídeos e {len(self.fila_arquivos)} materiais.")
                    else:
                        self.log("ERRO", f"Módulo não encontrado no antigo.")
                except Exception as e:
                    self.log("ERRO", f"Falha ao ler {nome_modulo}: {e}")

                pct = (i + 1) / len(lote)
                self.ui_do(lambda: self.progress_bar.set(pct))
                self.ui_do(lambda: self.lbl_memoria.configure(text=f"🧠 Módulos na Memória: {len(self.memoria_lote)}"))
                self.ui_do(lambda: self.lbl_status_mod.configure(text=f"FASE 1: Extraindo {i+1}/{len(lote)}"))

            if not self.parar_loop:
                self.log("MODULO", "✅ EXTRAÇÃO CONCLUÍDA! Clique no PASSO 2.")
                winsound.Beep(1000, 300)
                
        finally:
            self.is_running = False

    # =========================================================================
    # FASE 2: INJETAR NO SITE NOVO (COM A BUSCA INFALÍVEL DA V53)
    # =========================================================================
    def iniciar_injecao_massa(self):
        if getattr(self, 'is_running', False): return messagebox.showwarning("Aviso", "O robô já está rodando!")
        if not self.memoria_lote: return messagebox.showwarning("Aviso", "A memória está vazia. Extraia do site antigo primeiro!")
        
        self.parar_loop = False; self.is_running = True
        threading.Thread(target=self._injecao_massa_thread).start()

    def _injecao_massa_thread(self):
        try:
            aba_nova = None; aba_antiga = self.driver.window_handles[0]
            for aba in self.driver.window_handles:
                self.driver.switch_to.window(aba)
                if "novo.cursoms" in self.driver.current_url: aba_nova = aba; break
            
            if not aba_nova: return self.log("ERRO", "Site novo não encontrado. Faça o login.")

            self.ui_do(lambda: self.lbl_status_mod.configure(text=f"FASE 2: Injetando 0/{len(self.memoria_lote)}", text_color="#E74C3C"))

            for i, dados_memoria in enumerate(self.memoria_lote):
                if self.parar_loop: break
                
                nome_modulo = dados_memoria["nome_modulo"]
                self.fila_videos = list(dados_memoria["videos"])
                self.fila_arquivos = list(dados_memoria["arquivos"])
                self.ordem_atual = 1

                self.log("MODULO", f"BUSCANDO NO SITE NOVO: {nome_modulo}")
                
                if self.fila_videos and not self.parar_loop:
                    try:
                        self.driver.switch_to.window(aba_nova)
                        self.driver.get("https://novo.cursoms.com.br/modules")
                        wait = WebDriverWait(self.driver, 15)
                        time.sleep(2)
                        
                        # ========================================================
                        # AQUI ENTRA A MÁGICA DA V53 (BUSCA INFALÍVEL RÁPIDA)
                        # ========================================================
                        search_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='text' and contains(@class, 'form-control')]")))
                        self.preencher_input(search_input, nome_modulo)
                        
                        # Aguarda o Livewire recarregar a tabela (como na V53)
                        time.sleep(4) 
                        
                        modulos_h6 = self.driver.find_elements(By.TAG_NAME, "h6")
                        url_aulas = None
                        
                        nome_limpo = " ".join(nome_modulo.lower().split())
                        
                        for h6 in modulos_h6:
                            texto_h6 = " ".join(h6.text.lower().split())
                            
                            if nome_limpo in texto_h6 or texto_h6 in nome_limpo:
                                tr = h6.find_element(By.XPATH, "./ancestor::tr")
                                btn_aulas = tr.find_element(By.XPATH, ".//a[contains(@href, '/lessons/')]")
                                url_aulas = btn_aulas.get_attribute("href")
                                break

                        if url_aulas:
                            self.driver.get(url_aulas)
                            time.sleep(2)
                            self._despejar_videos()
                        else:
                            self.log("ERRO", "Módulo não encontrado no painel novo.")
                    except Exception as e:
                        self.log("ERRO", f"Erro etapa de vídeos: {e}")

                if self.fila_arquivos and not self.parar_loop:
                    self._despejar_materiais(nome_modulo, aba_antiga, aba_nova)

                pct = (i + 1) / len(self.memoria_lote)
                self.ui_do(lambda: self.progress_bar.set(pct))
                self.ui_do(lambda: self.lbl_status_mod.configure(text=f"FASE 2: Injetando {i+1}/{len(self.memoria_lote)}"))

            if not self.parar_loop:
                self.log("MODULO", "🎉 INJEÇÃO FINALIZADA COM SUCESSO! TUDO MIGRADO.")
                winsound.Beep(1200, 300); time.sleep(0.1); winsound.Beep(1200, 300)
                
        finally:
            self.is_running = False 

if __name__ == "__main__":
    app_login = AppPrincipal()
    app_login.mainloop()