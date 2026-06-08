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

# =============================================================================
# CORES E ESTILO
# =============================================================================
CORES = {
    "bg": "#FFFFFF", "topo": "#F8F9FA", "texto": "#2C3E50", 
    "destaque": "#8E44AD", "matrix_bg": "#000000", "matrix_fg": "#00FF00",
    "btn_bg": "#ECF0F1", "sucesso": "#27AE60", "erro": "#C0392B", "dash": "#E8F8F5"
}

class MigradorPDFMaster:
    def __init__(self, root):
        self.root = root
        self.root.title("Robô V26 - Lupa Sniper 👑")
        self.root.geometry("520x960")
        self.root.configure(bg=CORES["bg"])
        self.root.attributes('-topmost', True)
        
        self.gui_queue = queue.Queue()
        
        self.driver = None
        self.status_var = tk.StringVar(value="Carregando configurações...")
        self.fila_arquivos = [] 
        self.parar_loop = False
        
        self.silenciar = tk.BooleanVar(value=False)
        self.total_capturados = 0
        self.stats_sucessos = 0
        self.stats_erros = 0
        self.inicio_lote = 0
        self.feitos_lote = 0
        
        self.var_categoria = tk.StringVar()
        self.var_tipo = tk.StringVar()
        self.var_vinculo = tk.StringVar()

        self.carregar_config()
        self.setup_ui()
        self.ativar_atalhos()
        
        self.processar_fila_gui()
        self.ui_set_status("Pronto. Faça os logins e inicie a captura.")

    def processar_fila_gui(self):
        try:
            while True:
                tarefa = self.gui_queue.get_nowait()
                tarefa()
        except queue.Empty:
            pass
        self.root.after(100, self.processar_fila_gui)

    def ui_set_status(self, texto):
        self.gui_queue.put(lambda: self.status_var.set(texto))
        
    def ui_status_acao(self, texto):
        self.gui_queue.put(lambda: self.lbl_status_acao.config(text=texto))
        
    def ui_update_fila(self, texto):
        self.gui_queue.put(lambda: self.lbl_fila.config(text=texto))
        
    def ui_add_hist(self, texto):
        self.gui_queue.put(lambda: self.lista_hist.insert(0, texto))

    def atualizar_dashboard(self):
        self.gui_queue.put(self._do_atualizar_dashboard_ui)

    def _do_atualizar_dashboard_ui(self):
        self.lbl_stat_sucesso.config(text=f"✅ Sucessos: {self.stats_sucessos}")
        self.lbl_stat_erro.config(text=f"❌ Erros: {self.stats_erros}")
        if self.total_capturados > 0:
            restantes = len(self.fila_arquivos)
            feitos = self.total_capturados - restantes
            pct = (feitos / self.total_capturados) * 100
            self.progress_bar['value'] = pct
            if self.feitos_lote > 0 and restantes > 0:
                tempo_decorrido = time.time() - self.inicio_lote
                tempo_medio = tempo_decorrido / self.feitos_lote
                segundos_restantes = int(tempo_medio * restantes)
                m, s = divmod(segundos_restantes, 60)
                self.lbl_eta.config(text=f"⏱️ Estimativa: {m:02d}:{s:02d}")
            elif restantes == 0:
                self.lbl_eta.config(text="⏱️ Estimativa: Concluído!")
        else:
            self.lbl_eta.config(text="⏱️ Estimativa: --:--")
            self.progress_bar['value'] = 0

    def carregar_config(self):
        self.arquivo_config = "config_pdf.json"
        try:
            if not os.path.exists(self.arquivo_config):
                dados_padrao = {
                    "antigo_url": "https://cursoms.com.br/ead/admin/principal.asp",
                    "antigo_user": "SEU_USUARIO", "antigo_pass": "SUA_SENHA",
                    "novo_url": "https://novo.cursoms.com.br/login",
                    "novo_user": "SEU_EMAIL", "novo_pass": "SUA_SENHA",
                    "ultima_categoria": "1", "ultimo_tipo": "Module", "ultimo_vinculo": ""
                }
                with open(self.arquivo_config, "w", encoding="utf-8") as f:
                    json.dump(dados_padrao, f, indent=4)
                self.config = dados_padrao
            else:
                with open(self.arquivo_config, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
        except: self.config = {}

    def salvar_config(self):
        try:
            self.config["ultima_categoria"] = self.var_categoria.get().split(" - ")[0]
            self.config["ultimo_tipo"] = self.var_tipo.get().split(" - ")[0]
            self.config["ultimo_vinculo"] = self.var_vinculo.get()
            with open(self.arquivo_config, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except: pass

    def salvar_relatorio(self, titulo, status):
        arquivo = "relatorio_pdfs.csv"
        existe = os.path.exists(arquivo)
        try:
            with open(arquivo, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';') 
                if not existe:
                    writer.writerow(['Data/Hora', 'Titulo do Arquivo', 'Status'])
                data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                writer.writerow([data_hora, titulo, status])
        except: pass

    def setup_ui(self):
        top = tk.Frame(self.root, bg=CORES["topo"], pady=10, bd=1, relief="solid")
        top.pack(fill="x")
        tk.Label(top, text="MIGRADOR DE ARQUIVOS V26 👑", bg=CORES["topo"], font=("Impact", 14), fg=CORES["destaque"]).pack()
        tk.Checkbutton(top, text="🔇 Silenciar Bips", variable=self.silenciar, bg=CORES["topo"], font=("Arial", 8)).pack()
        tk.Button(top, text="🌐 Abrir Navegador", bg=CORES["texto"], fg="white", font=("Arial", 9, "bold"), 
                  command=self.iniciar_browser).pack(pady=5)

        cmds = tk.Frame(self.root, bg=CORES["bg"], pady=5)
        cmds.pack(fill="x")
        tk.Button(cmds, text="1. Login Antigo", command=self.login_antigo, width=15).pack(side="left", padx=10)
        tk.Button(cmds, text="2. Login Novo", bg="#D5F5E3", fg="#1E8449", command=self.login_novo, width=15).pack(side="right", padx=10)

        filtros = tk.LabelFrame(self.root, text="Configuração do Lote", bg=CORES["bg"], font=("Arial", 9, "bold"), fg="#8E44AD")
        filtros.pack(fill="x", padx=10, pady=5)
        
        tk.Label(filtros, text="Categoria do Material:", bg=CORES["bg"]).grid(row=0, column=0, sticky="w", padx=5)
        self.combo_cat = ttk.Combobox(filtros, textvariable=self.var_categoria, values=["1 - Material do curso", "2 - Gabarito", "3 - Atividades Sugeridas", "4 - Slide", "5 - Áudio"], state="readonly", width=25)
        self.combo_cat.grid(row=0, column=1, padx=5, pady=2)
        
        cat_salva = self.config.get("ultima_categoria", "1")
        for val in self.combo_cat['values']:
            if val.startswith(cat_salva):
                self.combo_cat.set(val)
                break

        tk.Label(filtros, text="Vincular ao:", bg=CORES["bg"]).grid(row=1, column=0, sticky="w", padx=5)
        self.combo_tipo = ttk.Combobox(filtros, textvariable=self.var_tipo, values=["Module - Módulo", "Course - Curso", "Lesson - Aula"], state="readonly", width=25)
        self.combo_tipo.grid(row=1, column=1, padx=5, pady=2)

        tipo_salvo = self.config.get("ultimo_tipo", "Module")
        for val in self.combo_tipo['values']:
            if val.startswith(tipo_salvo):
                self.combo_tipo.set(val)
                break

        tk.Label(filtros, text="Nome Exato do Vínculo:", bg=CORES["bg"], font=("Arial", 8, "bold")).grid(row=2, column=0, sticky="w", padx=5)
        self.ent_vinculo = ttk.Entry(filtros, textvariable=self.var_vinculo, width=28)
        self.ent_vinculo.grid(row=2, column=1, padx=5, pady=2)
        self.var_vinculo.set(self.config.get("ultimo_vinculo", ""))

        step1 = tk.LabelFrame(self.root, text="PASSO 1: Captura", bg=CORES["bg"], font=("Arial", 9, "bold"), fg="#2980B9")
        step1.pack(fill="x", padx=10, pady=5)
        tk.Button(step1, text="🔍 LER LISTA (Site Antigo)", bg="#F39C12", fg="white", font=("Arial", 10, "bold"), command=self.iniciar_varredura_thread).pack(fill="x", padx=15, pady=5)
        self.lbl_fila = tk.Label(step1, text="Fila: 0 Arquivos", bg=CORES["bg"], fg="red")
        self.lbl_fila.pack()

        step2 = tk.LabelFrame(self.root, text="PASSO 2: Execução", bg=CORES["bg"], font=("Arial", 9, "bold"), fg="red")
        step2.pack(fill="x", padx=10, pady=5)
        tk.Button(step2, text="🚀 MIGRAR TUDO AUTOMÁTICO", bg="red", fg="white", font=("Arial", 11, "bold"), command=self.iniciar_migracao_total_thread).pack(fill="x", padx=15, pady=10)

        dash = tk.Frame(self.root, bg=CORES["dash"], bd=1, relief="solid")
        dash.pack(fill="x", padx=10, pady=5)
        tk.Label(dash, text="📊 DASHBOARD", bg=CORES["dash"], font=("Arial", 9, "bold")).pack(pady=2)
        stat_grid = tk.Frame(dash, bg=CORES["dash"])
        stat_grid.pack(fill="x", padx=10)
        self.lbl_stat_sucesso = tk.Label(stat_grid, text="✅ Sucessos: 0", bg=CORES["dash"], font=("Arial", 9), fg="#1E8449")
        self.lbl_stat_sucesso.pack(side="left", padx=10)
        self.lbl_stat_erro = tk.Label(stat_grid, text="❌ Erros: 0", bg=CORES["dash"], font=("Arial", 9), fg="#C0392B")
        self.lbl_stat_erro.pack(side="right", padx=10)
        prog_frame = tk.Frame(dash, bg=CORES["dash"])
        prog_frame.pack(fill="x", padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate", length=200)
        self.progress_bar.pack(side="top", fill="x", pady=2)
        self.lbl_eta = tk.Label(prog_frame, text="⏱️ Estimativa: --:--", bg=CORES["dash"], font=("Arial", 9, "bold"), fg="#2980B9")
        self.lbl_eta.pack(side="bottom")

        cnt = tk.Frame(self.root, bg=CORES["bg"], pady=5)
        cnt.pack()
        tk.Button(cnt, text="🛑 PARAR TUDO", bg="black", fg="white", command=self.parar_tudo).pack(pady=5)

        self.matrix_frame = tk.Frame(self.root, bg="black", bd=2, relief="sunken")
        self.matrix_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.lbl_status_acao = tk.Label(self.matrix_frame, text="Aguardando...", bg="black", fg="#0F0", font=("Consolas", 10))
        self.lbl_status_acao.pack(fill="x")
        self.lista_hist = tk.Listbox(self.matrix_frame, bg="black", fg="#008000", height=8, bd=0, font=("Consolas", 9))
        self.lista_hist.pack(fill="both", expand=True)

        self.bar = tk.Label(self.root, textvariable=self.status_var, bg="#ECF0F1", anchor="w")
        self.bar.pack(side="bottom", fill="x")

    def ativar_atalhos(self): keyboard.add_hotkey('f9', self.iniciar_migracao_total_thread) 

    def iniciar_browser(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.driver.maximize_window()
        self.ui_set_status("Navegador aberto.")

    def parar_tudo(self): 
        self.parar_loop = True
        self.ui_set_status("🛑 Parada solicitada...")

    def bip_sucesso(self):
        if not self.silenciar.get():
            try: winsound.Beep(1200, 100)
            except: pass

    def bip_erro(self):
        if not self.silenciar.get():
            try: winsound.Beep(500, 300)
            except: pass

    def login_antigo(self): threading.Thread(target=self._login_antigo_thread).start()
    def _login_antigo_thread(self):
        try:
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(self.config["antigo_url"])
            wait = WebDriverWait(self.driver, 10)
            u = wait.until(EC.presence_of_element_located((By.NAME, "logindagestao")))
            u.send_keys(self.config["antigo_user"])
            self.driver.find_element(By.NAME, "senhadagestao").send_keys(self.config["antigo_pass"])
            self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
            self.ui_set_status("Login antigo OK")
        except: pass

    def login_novo(self): threading.Thread(target=self._login_novo_thread).start()
    def _login_novo_thread(self):
        try:
            self.driver.execute_script(f"window.open('{self.config['novo_url']}');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(self.config["novo_user"])
            p = self.driver.find_element(By.NAME, "password")
            p.send_keys(self.config["novo_pass"])
            p.send_keys(Keys.ENTER)
            self.ui_set_status("Login novo OK")
        except: pass

    # =========================================================================
    # LEITURA UNIVERSAL - O CAÇADOR DE OLHOS
    # =========================================================================
    def iniciar_varredura_thread(self): threading.Thread(target=self.varrer_lista).start()
    def varrer_lista(self):
        if not self.driver: return
        self.fila_arquivos.clear()
        self.ui_update_fila("Fila: 0 Arquivos")
        self.ui_set_status("🔍 Lendo HTML da página...")
        try:
            url_atual = self.driver.current_url
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            itens = soup.find_all('div', class_='list-item box')
            
            for item in itens:
                titulo = item.find('td', class_='subject').text.strip() if item.find('td', class_='subject') else "Sem Titulo"
                
                # A LUPA SNIPER: Procura a tag <a> que aponta EXATAMENTE para arquivoid.asp
                # Ignora modificar_arquivos e deletar_arquivo
                link_correto = None
                for a_tag in item.find_all('a', href=True):
                    if "arquivoid.asp" in a_tag['href'].lower():
                        link_correto = a_tag
                        break
                
                if link_correto: 
                    self.fila_arquivos.append({'titulo': titulo, 'url_ver': urljoin(url_atual, link_correto['href'])})
                    
            self.fila_arquivos.reverse()
            self.total_capturados = len(self.fila_arquivos)
            self.ui_update_fila(f"Fila: {self.total_capturados} Arquivos")
            self.ui_set_status("✅ Capturado de baixo para cima!")
            self.bip_sucesso()
            
        except Exception as e: 
            self.ui_set_status(f"Erro captura: {e}")

    def iniciar_migracao_total_thread(self):
        if not self.fila_arquivos: return
        self.salvar_config()
        self.parar_loop = False
        threading.Thread(target=self.loop_migracao).start()

    def loop_migracao(self):
        self.inicio_lote = time.time()
        self.feitos_lote = 0
        session = requests.Session()
        for c in self.driver.get_cookies(): session.cookies.set(c['name'], c['value'])
        
        aba_principal_antigo = self.driver.current_window_handle
        
        self.driver.execute_script("window.open('https://novo.cursoms.com.br/attachments/create', '_blank');")
        aba_fixa_novo = self.driver.window_handles[-1]
        
        PASTA_DOWNLOADS = "arquivos_migracao" 
        if not os.path.exists(PASTA_DOWNLOADS): os.makedirs(PASTA_DOWNLOADS)

        while self.fila_arquivos and not self.parar_loop:
            try:
                if aba_principal_antigo not in self.driver.window_handles:
                    self.ui_set_status("❌ Erro: Navegador fechado!")
                    break
            except: break

            dados = self.fila_arquivos[0]
            status_proc = self.processar_arquivo_completo(dados, session, aba_principal_antigo, aba_fixa_novo, PASTA_DOWNLOADS)
            
            if status_proc:
                self.fila_arquivos.pop(0)
                self.ui_update_fila(f"Fila: {len(self.fila_arquivos)} restantes")
                self.stats_sucessos += 1
            else:
                self.fila_arquivos.pop(0)
                self.ui_update_fila(f"Fila: {len(self.fila_arquivos)} restantes")
                self.stats_erros += 1
            
            self.feitos_lote += 1
            self.atualizar_dashboard()
        
        try:
            self.driver.switch_to.window(aba_fixa_novo)
            self.driver.close()
            self.driver.switch_to.window(aba_principal_antigo)
        except: pass
        
        self.ui_set_status("🎉 FIM DO PROCESSO!")

    def processar_arquivo_completo(self, dados, session, aba_principal_antigo, aba_fixa_novo, pasta_downloads):
        try:
            # =======================================================
            # 1. DOWNLOAD (Múltiplos Formatos: PPT, PDF, DOC)
            # =======================================================
            self.driver.switch_to.window(aba_principal_antigo)
            self.ui_status_acao(f"Lendo: {dados['titulo'][:20]}...")
            
            self.driver.execute_script(f"window.open('{dados['url_ver']}', '_blank');")
            time.sleep(2)
            aba_temporaria = self.driver.window_handles[-1]
            self.driver.switch_to.window(aba_temporaria)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # PROCURA QUALQUER EXTENSÃO VÁLIDA NA TELA DE VISUALIZAÇÃO
            extensoes_permitidas = ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.pps']
            link = soup.find('a', href=lambda h: h and any(ext in h.lower() for ext in extensoes_permitidas))
            
            if not link: 
                link = soup.find('a', string=re.compile(r'baixar|download|arquivo|salvar', re.IGNORECASE))
                if not link:
                    self.driver.close()
                    return False
            
            url_arq = link['href']
            if "../../" in url_arq:
                url_arq = url_arq.replace("../../", "https://cursoms.com.br/ead/")
            elif not url_arq.startswith("http"):
                url_arq = urljoin("https://cursoms.com.br/ead/", url_arq)
            
            extensao_real = ".pdf"
            for ext in extensoes_permitidas:
                if ext in url_arq.lower():
                    extensao_real = ext
                    break
            
            nome_arq = re.sub(r'[\\/*?:"<>|]', "", dados['titulo'])[:60] + extensao_real
            caminho_local = os.path.abspath(os.path.join(pasta_downloads, nome_arq))
            
            self.ui_status_acao(f"Baixando Arquivo ({extensao_real})...")
            with open(caminho_local, 'wb') as f: f.write(session.get(url_arq).content)
            self.driver.close() 

            # =======================================================
            # 2. CADASTRAR NO SITE NOVO (Aba de Trabalho)
            # =======================================================
            self.driver.switch_to.window(aba_fixa_novo)
            self.driver.get('https://novo.cursoms.com.br/attachments/create')
            
            if "login" in self.driver.current_url.lower():
                self.ui_status_acao("Sessão caiu! Refazendo login automático...")
                try:
                    self.driver.find_element(By.NAME, "email").send_keys(self.config["novo_user"])
                    p = self.driver.find_element(By.NAME, "password")
                    p.send_keys(self.config["novo_pass"])
                    p.send_keys(Keys.ENTER)
                    time.sleep(3)
                    self.driver.get('https://novo.cursoms.com.br/attachments/create')
                except:
                    pass

            wait = WebDriverWait(self.driver, 20)

            # A) UPLOAD DO ARQUIVO NO BACKGROUND
            self.ui_status_acao("Iniciando Upload do Arquivo...")
            f_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[wire\\:model="attachment.filename"]')))
            self.driver.execute_script("arguments[0].style.display='block'; arguments[0].style.visibility='visible';", f_input)
            f_input.send_keys(caminho_local)

            # B) NOME (LIMITE 65)
            self.ui_status_acao("Preenchendo nome do material...")
            titulo_limpo = dados['titulo'][:65].strip()
            input_n = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[wire\\:model="attachment.name"]')))
            input_n.clear()
            input_n.send_keys(titulo_limpo)
            
            # C) CATEGORIA E TIPO
            self.ui_status_acao("Setando Categoria e Tipo...")
            cat_val = self.var_categoria.get().split(" - ")[0]
            tip_val = self.var_tipo.get().split(" - ")[0]
            self.driver.execute_script("""
                let cat = document.querySelector('select[wire\\\\:model="attachment.type"]');
                let tip = document.querySelector('select[wire\\\\:model="attachment.attachable_type"]');
                if(cat) { cat.value = arguments[0]; cat.dispatchEvent(new Event('input', { bubbles: true })); cat.dispatchEvent(new Event('change', { bubbles: true })); }
                if(tip) { tip.value = arguments[1]; tip.dispatchEvent(new Event('input', { bubbles: true })); tip.dispatchEvent(new Event('change', { bubbles: true })); }
            """, cat_val, tip_val)
            
            time.sleep(4) 

            # D) MÓDULO 
            vinc_val = self.var_vinculo.get().strip()
            if vinc_val:
                self.ui_status_acao("Pesquisando Módulo...")
                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input.form-control[type='text']")
                for i in inputs:
                    if i.get_attribute("wire:model") != "attachment.name" and not i.get_attribute("value"):
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", i)
                        time.sleep(0.5)
                        
                        i.click()
                        time.sleep(0.5)
                        i.send_keys(vinc_val)
                        
                        self.ui_status_acao("Aguardando lista do servidor (3s)...")
                        time.sleep(3) 
                        
                        try:
                            v_safe = vinc_val.lower().replace("'", "") 
                            xpath_profundo = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}') and not(*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}')])]"
                            opcoes = self.driver.find_elements(By.XPATH, xpath_profundo)
                            clicou = False
                            
                            for opcao in opcoes:
                                if opcao.is_displayed() and opcao.tag_name.lower() not in ['input', 'html', 'body']:
                                    try:
                                        ActionChains(self.driver).move_to_element(opcao).click().perform()
                                    except:
                                        self.driver.execute_script("arguments[0].click();", opcao)
                                    clicou = True
                                    self.ui_status_acao("✅ Módulo Clicado!")
                                    time.sleep(1)
                                    break
                            
                            if not clicou:
                                i.send_keys(Keys.ARROW_DOWN)
                                time.sleep(0.5)
                                i.send_keys(Keys.TAB)
                        except Exception as ev:
                            pass
                        break

            # E) AGUARDA UPLOAD TERMINAR
            self.ui_status_acao("Aguardando confirmação de Upload (6s)...")
            time.sleep(6) 

            # F) SALVAR VIA LIVEWIRE API
            self.ui_status_acao("Salvando na plataforma...")
            try:
                self.driver.execute_script("Livewire.first().call('handleSubmit');")
            except:
                btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                self.driver.execute_script("arguments[0].click();", btn)
            
            # G) ESPERA O REDIRECIONAMENTO NATIVO DO LARAVEL
            self.ui_status_acao("Aguardando Redirecionamento...")
            time.sleep(6)

            self.driver.get("https://novo.cursoms.com.br/attachments")
            time.sleep(2)

            self.salvar_relatorio(titulo_limpo, "Sucesso")
            self.ui_add_hist(f"✅ OK: {titulo_limpo}")
            return True

        except Exception as e:
            print(f"Erro Crítico: {e}")
            self.salvar_relatorio(dados['titulo'][:65].strip(), f"Falha Crítica")
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
    root = tk.Tk(); app = MigradorPDFMaster(root); root.mainloop()