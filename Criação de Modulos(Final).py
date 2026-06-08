import json
import os
import sqlite3
import threading
import time
import traceback  # <--- NOVA BIBLIOTECA PARA RADIOGRAFIA DE ERROS
from datetime import datetime
from tkinter import messagebox
from urllib.parse import urljoin

import customtkinter as ctk
import google.generativeai as genai
import PyPDF2
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class RoboObraPrima(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Robô Supremo V16.1 - Super Debug 🤖⚡")
        self.geometry("750x700")

        self.driver = None
        self.parar_loop = False
        self.config = {}

        # CHAVE DA API
        self.CHAVE_API = "AIzaSyDEuNX3vI2M21V4DlnJQz_1KDNU39T5UJg"
        genai.configure(api_key=self.CHAVE_API)
        self.ia_model = genai.GenerativeModel("gemini-1.5-flash")

        self.arquivo_log = "robo_obra_prima.log"
        self.arquivo_erro_grave = (
            "ERRO_GRAVE_DEBUG.log"  # <--- ARQUIVO DEDICADO PARA EU LER O SEU ERRO
        )

        with open(self.arquivo_log, "a", encoding="utf-8") as f:
            f.write(
                f"\n{'='*50}\n[SESSÃO INICIADA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}]\n{'='*50}\n"
            )

        self.carregar_config()
        self.iniciar_banco_dados()
        self.setup_ui()

    def iniciar_banco_dados(self):
        try:
            self.conn = sqlite3.connect("banco_migracao.db", check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS relatorio_migracao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT,
                    nome_antigo TEXT,
                    nome_novo TEXT,
                    professor_encontrado TEXT,
                    status TEXT
                )
            """)
            self.conn.commit()
        except:
            pass

    def registrar_no_banco(self, antigo, novo, prof, status):
        try:
            agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO relatorio_migracao (data_hora, nome_antigo, nome_novo, professor_encontrado, status) VALUES (?, ?, ?, ?, ?)",
                (agora, antigo, novo, prof, status),
            )
            self.conn.commit()
        except:
            pass

    def carregar_config(self):
        arquivo_config = "config_unificada.json"
        dados_padrao = {
            "antigo_url": "https://cursoms.com.br/ead/admin/principal.asp",
            "antigo_user": "",
            "antigo_pass": "",
            "novo_url": "https://novo.cursoms.com.br/login",
            "novo_user": "",
            "novo_pass": "",
        }
        if not os.path.exists(arquivo_config):
            with open(arquivo_config, "w", encoding="utf-8") as f:
                json.dump(dados_padrao, f, indent=4)
            self.config = dados_padrao
        else:
            try:
                with open(arquivo_config, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except:
                self.config = dados_padrao

    def setup_ui(self):
        ctk.CTkLabel(
            self,
            text="👑 A OBRA-PRIMA V16.1 (SUPER DEBUG)",
            font=("Impact", 24),
            text_color="#F1C40F",
        ).pack(pady=(15, 5))

        frm_dados = ctk.CTkFrame(self, fg_color="#17202A")
        frm_dados.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            frm_dados, text="Prefixo do Módulo (O que vai na frente):", font=("Arial", 13, "bold")
        ).pack(pady=(10, 0))
        self.ent_prefixo = ctk.CTkEntry(frm_dados, width=400, justify="center")
        self.ent_prefixo.insert(0, "(Pacatuba/CE) ")
        self.ent_prefixo.pack(pady=5)

        ctk.CTkLabel(
            frm_dados, text="Curso Destino (Nome exato no site novo):", font=("Arial", 13, "bold")
        ).pack(pady=(5, 0))
        self.ent_curso = ctk.CTkEntry(frm_dados, width=400, justify="center")
        self.ent_curso.pack(pady=(5, 10))

        frm_cmds = ctk.CTkFrame(self, fg_color="transparent")
        frm_cmds.pack(fill="x", padx=20, pady=5)

        ctk.CTkButton(
            frm_cmds,
            text="🌐 1. LOGAR NOS 2 SITES",
            fg_color="#3498DB",
            hover_color="#2980B9",
            height=45,
            command=self.iniciar_navegador,
        ).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(
            frm_cmds,
            text="🚀 2. INICIAR MÁGICA",
            fg_color="#E74C3C",
            hover_color="#C0392B",
            height=45,
            font=("Arial", 14, "bold"),
            command=self.iniciar_robo,
        ).pack(side="right", expand=True, padx=5)

        ctk.CTkButton(
            self,
            text="🛑 PARAR EMERGÊNCIA",
            fg_color="#000000",
            hover_color="#111111",
            command=self.parar_tudo,
        ).pack(pady=5)

        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 12), fg_color="#0A0A0A", height=250)
        self.txt_log.pack(fill="both", expand=True, padx=20, pady=10)
        self.txt_log.configure(state="disabled")

    def registrar_log(self, msg):
        hora = datetime.now().strftime("%H:%M:%S")
        txt = f"[{hora}] {msg}"
        try:
            with open(self.arquivo_log, "a", encoding="utf-8") as f:
                f.write(txt + "\n")
        except:
            pass

        def _atualizar_tela():
            try:
                if self.txt_log.winfo_exists():
                    self.txt_log.configure(state="normal")
                    self.txt_log.insert("end", txt + "\n")
                    self.txt_log.configure(state="disabled")
                    self.txt_log.see("end")
            except:
                pass

        try:
            self.after(0, _atualizar_tela)
        except:
            pass

    def registrar_erro_critico(self, erro_completo):
        """Salva a radiografia do erro para o Desenvolvedor analisar"""
        try:
            with open(self.arquivo_erro_grave, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{'='*50}\n[ERRO CAPTURADO EM {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}]\n"
                )
                f.write(erro_completo)
                f.write(f"\n{'='*50}\n")
        except:
            pass

    def parar_tudo(self):
        self.parar_loop = True
        self.registrar_log("⚠️ PARADA DE EMERGÊNCIA ACIONADA.")

    def iniciar_navegador(self):
        threading.Thread(target=self._processo_login_duplo).start()

    def _processo_login_duplo(self):
        try:
            self.registrar_log("Abrindo navegador Supremo...")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            self.driver.maximize_window()
            wait = WebDriverWait(self.driver, 10)

            self.registrar_log("Logando no site ANTIGO (Aba 1)...")
            self.driver.get(
                self.config.get("antigo_url", "https://cursoms.com.br/ead/admin/principal.asp")
            )
            if self.config.get("antigo_user"):
                try:
                    wait.until(
                        EC.presence_of_element_located((By.NAME, "logindagestao"))
                    ).send_keys(self.config["antigo_user"])
                    self.driver.find_element(By.NAME, "senhadagestao").send_keys(
                        self.config["antigo_pass"]
                    )
                    self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
                except:
                    pass

            self.registrar_log("Logando no site NOVO (Aba 2)...")
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.driver.get(self.config.get("novo_url", "https://novo.cursoms.com.br/login"))
            if self.config.get("novo_user"):
                try:
                    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(
                        self.config["novo_user"]
                    )
                    pwd = self.driver.find_element(By.NAME, "password")
                    pwd.send_keys(self.config["novo_pass"])
                    pwd.send_keys(Keys.ENTER)
                except:
                    pass

            self.registrar_log("✅ LOGINS CONCLUÍDOS!")
            self.registrar_log("👉 Vá para a aba Antiga, abra a lista de módulos.")
            self.registrar_log("👉 Vá para a aba Nova, fique na Lista de Módulos.")

        except Exception as e:
            self.registrar_log("ERRO NO NAVEGADOR. Verifique o ERRO_GRAVE_DEBUG.log")
            self.registrar_erro_critico(traceback.format_exc())

    def extrair_professor_do_pdf(self, caminho_pdf):
        try:
            with open(caminho_pdf, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                texto = ""
                for i in range(min(3, len(reader.pages))):
                    texto += reader.pages[i].extract_text() + "\n"

            if not texto.strip():
                return "DESCONHECIDO"

            self.registrar_log("🤖 Perguntando ao Gemini 1.5 Flash...")
            prompt = f"Analise o texto e encontre o NOME DO PROFESSOR (ou autor). Regras: 1) Responda APENAS o nome sem 'Prof', 'Dr', 'Enf'. 2) Abrevie para Nome e Sobrenome. 3) Se não achar, responda EXATAMENTE 'DESCONHECIDO'. Texto: {texto[:3000]}"

            for tentativa in range(3):
                try:
                    response = self.ia_model.generate_content(prompt)
                    nome_prof = response.text.strip().replace("\n", "").replace("*", "")
                    if len(nome_prof) > 40:
                        return "DESCONHECIDO"
                    return nome_prof
                except Exception as e:
                    if "429" in str(e):
                        self.registrar_log(
                            f"⏳ IA ocupada. Tentando novamente ({tentativa+1}/3)..."
                        )
                        time.sleep(10)
                    else:
                        raise e
            return "DESCONHECIDO"
        except Exception as e:
            self.registrar_log("⚠️ Erro ao ler PDF. Verifique o ERRO_GRAVE_DEBUG.log")
            self.registrar_erro_critico(traceback.format_exc())
            return "DESCONHECIDO"

    def expandir_paginacao_antigo(self):
        try:
            painel = self.driver.find_element(
                By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
            )
            self.driver.execute_script("arguments[0].click();", painel)
            time.sleep(0.5)
            ver_todos = self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']")
            self.driver.execute_script("arguments[0].click();", ver_todos)
            time.sleep(2)
        except:
            pass

    def preencher_pesquisa_livewire(self, wait, nome_label, texto_pesquisa):
        try:
            xpath_input = f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{nome_label.lower()}')]/following::input[contains(@class, 'form-control')][1]"
            input_elem = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_input)))

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", input_elem
            )
            time.sleep(0.5)
            input_elem.click()
            input_elem.send_keys(Keys.CONTROL + "a")
            input_elem.send_keys(Keys.DELETE)
            time.sleep(0.5)
            input_elem.send_keys(texto_pesquisa)

            time.sleep(3.5)

            xpath_lista = f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{nome_label.lower()}')]/following::ul[contains(@class, 'list-group')][1]/li"
            item_lista = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_lista)))
            self.driver.execute_script("arguments[0].click();", item_lista)
            time.sleep(0.5)
        except Exception as e:
            raise Exception(f"Falha ao pesquisar '{texto_pesquisa}' em '{nome_label}'.")

    def iniciar_robo(self):
        if not self.ent_curso.get().strip():
            return messagebox.showwarning("Aviso", "Preencha o Curso Destino!")
        if not self.driver or len(self.driver.window_handles) < 2:
            return messagebox.showwarning("Aviso", "Abra o navegador e logue nos 2 sites primeiro!")

        self.parar_loop = False
        threading.Thread(target=self._processo_obra_prima).start()

    def _processo_obra_prima(self):
        wait = WebDriverWait(self.driver, 10)
        prefixo = self.ent_prefixo.get()
        curso_destino = self.ent_curso.get().strip()

        self.registrar_log("=" * 40)
        self.registrar_log("MÁQUINA LIGADA! Iniciando varredura Fantasma...")

        aba_antiga = self.driver.window_handles[0]
        aba_nova = self.driver.window_handles[1]

        self.driver.switch_to.window(aba_antiga)
        url_lista_antigo = self.driver.current_url

        try:
            elementos_td = self.driver.find_elements(By.CSS_SELECTOR, "td.textointernos")
            qtd_modulos = len(elementos_td)
            self.registrar_log(f"🔎 {qtd_modulos} Módulos encontrados.")
        except:
            return self.registrar_log("❌ Não encontrei a lista de módulos no site antigo.")

        for i in range(qtd_modulos):
            if self.parar_loop:
                break
            nome_original = "ERRO"
            professor_ia = "DESCONHECIDO"

            try:
                # FASE 1: O ROUBO FANTASMA (Site Antigo)
                self.driver.switch_to.window(aba_antiga)
                self.driver.get(url_lista_antigo)
                time.sleep(2)

                tds = wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "td.textointernos"))
                )
                nome_original = tds[i].text.strip()
                self.registrar_log(f"\n[{i+1}/{qtd_modulos}] Lendo: {nome_original}")

                # Clica na lupa do módulo
                xpath_lupa_modulo = (
                    "./parent::tr//a[img[contains(@src, 'ver.jpg') or contains(@src, 'lupa')]]"
                )
                btn_acesso = tds[i].find_element(By.XPATH, xpath_lupa_modulo)
                self.driver.execute_script("arguments[0].click();", btn_acesso)

                btn_aula = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'aula.asp')]"))
                )
                self.driver.execute_script("arguments[0].click();", btn_aula)
                time.sleep(1.5)

                url_base_aula = self.driver.current_url
                setores_xpath = [
                    "//a[contains(@href, 'setor=2')]",
                    "//a[contains(@href, 'setor=1')]",
                    "//a[contains(@href, 'setor=4')]",
                ]
                urls_para_visitar = []

                for xp in setores_xpath:
                    btn = self.driver.find_elements(By.XPATH, xp)
                    if btn:
                        urls_para_visitar.append(btn[0].get_attribute("href"))
                if not urls_para_visitar:
                    urls_para_visitar.append(url_base_aula)

                achou_prof_perfeito = False

                for url_setor in urls_para_visitar:
                    if achou_prof_perfeito:
                        break

                    self.driver.get(url_setor)
                    time.sleep(1.5)
                    self.expandir_paginacao_antigo()

                    # PROCURA A LUPA DOS MATERIAIS
                    xpath_lupa_material = "//a[img[contains(@src, 'ver.jpg')]] | //a[contains(@href, 'arquivoid.asp')]"
                    links_materiais = self.driver.find_elements(By.XPATH, xpath_lupa_material)

                    if links_materiais:
                        for btn_mat in links_materiais[:2]:
                            try:
                                # Rouba o link sem clicar (ex: arquivoid.asp?id=40920)
                                href_cru = btn_mat.get_attribute("href")
                                url_pdf = urljoin(self.driver.current_url, href_cru)

                                if url_pdf and ("arquivoid.asp" in url_pdf or ".pdf" in url_pdf):
                                    self.registrar_log(
                                        "📄 Link interceptado! Baixando silenciosamente..."
                                    )

                                    session = requests.Session()
                                    for c in self.driver.get_cookies():
                                        session.cookies.set(c["name"], c["value"])
                                    headers = {
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
                                    }

                                    resposta = session.get(url_pdf, headers=headers)

                                    caminho_temp = "temp_leitura.pdf"
                                    with open(caminho_temp, "wb") as f:
                                        f.write(resposta.content)

                                    prof = self.extrair_professor_do_pdf(caminho_temp)
                                    try:
                                        os.remove(caminho_temp)
                                    except:
                                        pass

                                    if prof != "DESCONHECIDO":
                                        professor_ia = prof
                                        achou_prof_perfeito = True
                                        self.registrar_log(f"🎯 PROFESSOR VALIDADO: {professor_ia}")
                                        break
                            except Exception as erro_pdf:
                                self.registrar_log(
                                    "⚠️ Erro ao interceptar PDF. Veja o ERRO_GRAVE_DEBUG.log"
                                )
                                self.registrar_erro_critico(traceback.format_exc())

                if not achou_prof_perfeito:
                    self.registrar_log("⚠️ Não achei o professor nos PDFs.")

                # FASE 2: A INJEÇÃO (Site Novo)
                self.driver.switch_to.window(aba_nova)
                url_base_novo = self.driver.current_url
                nome_novo = f"{prefixo}{nome_original}"
                self.registrar_log(f"Injetando: {nome_novo}")

                # 0. Clica Adicionar
                try:
                    xpath_btn_add = "//*[self::a or self::button][contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'adicionar') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'novo') or contains(@href, 'create')]"
                    btn_add = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_btn_add)))
                    self.driver.execute_script("arguments[0].click();", btn_add)
                    time.sleep(4)
                except:
                    if "modules" in url_base_novo:
                        self.driver.get("https://novo.cursoms.com.br/modules/create")
                        time.sleep(4)

                # 1. Nome do Módulo
                xpath_nome = "//label[contains(text(), 'Nome do módulo')]/following-sibling::input"
                input_nome = wait.until(EC.presence_of_element_located((By.XPATH, xpath_nome)))
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", input_nome
                )
                input_nome.click()
                input_nome.send_keys(Keys.CONTROL + "a")
                input_nome.send_keys(Keys.DELETE)
                time.sleep(0.2)
                input_nome.send_keys(nome_novo)

                # 2. Carga Horária (0)
                xpath_tempo = "//label[contains(text(), 'Carga Horária')]/following-sibling::input"
                input_tempo = wait.until(EC.presence_of_element_located((By.XPATH, xpath_tempo)))
                input_tempo.click()
                input_tempo.send_keys(Keys.CONTROL + "a")
                input_tempo.send_keys(Keys.DELETE)
                time.sleep(0.2)
                input_tempo.send_keys("0")

                # 3. Curso e Professor
                self.preencher_pesquisa_livewire(wait, "curso", curso_destino)

                if professor_ia != "DESCONHECIDO":
                    try:
                        self.preencher_pesquisa_livewire(wait, "professor", professor_ia)
                    except:
                        self.registrar_log(
                            f"⚠️ Professor '{professor_ia}' não existe no site novo. Deixando vazio."
                        )

                # 4. Salvar
                botoes_salvar = self.driver.find_elements(
                    By.XPATH,
                    "//button[@type='submit' and contains(translate(text(), 'SALVAR', 'salvar'), 'salvar')]",
                )
                btn_salvar = next((b for b in botoes_salvar if b.is_displayed()), None)
                if btn_salvar:
                    self.driver.execute_script("arguments[0].click();", btn_salvar)
                else:
                    self.driver.execute_script("document.querySelector('form').submit();")

                time.sleep(4)
                self.driver.get(url_base_novo)
                time.sleep(2)
                self.registrar_log("✅ FEITO! Módulo salvo.")

                self.registrar_no_banco(nome_original, nome_novo, professor_ia, "SUCESSO")

            except Exception as e:
                self.registrar_log("❌ Erro Crítico no Módulo. Arquivo de log gerado.")
                self.registrar_erro_critico(traceback.format_exc())
                self.registrar_no_banco(
                    nome_original, f"{prefixo}{nome_original}", professor_ia, "ERRO"
                )
                try:
                    self.driver.switch_to.window(aba_nova)
                    self.driver.get(url_base_novo)
                    time.sleep(2)
                except:
                    self.registrar_log("💥 Navegador inoperante. Interrompendo ciclo.")
                    break

        self.registrar_log("\n🎉 OBRA-PRIMA FINALIZADA! Todos os módulos processados.")


if __name__ == "__main__":
    app = RoboObraPrima()
    app.mainloop()
