import csv
import json
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
import traceback
import winsound
from datetime import datetime
from tkinter import filedialog, messagebox
from urllib.parse import urljoin

import customtkinter as ctk
import keyboard
import pandas as pd
import requests
from bs4 import BeautifulSoup
from google import genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# =============================================================================
# FUNÇÃO PARA LER O ÍCONE DENTRO DO .EXE
# =============================================================================
def resource_path(relative_path):
    """Pega o caminho absoluto do recurso, funciona no VSCode e no .EXE compilado"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# =============================================================================
# CONFIGURAÇÃO DO TEMA PREMIUM & CHAVES
# =============================================================================
CHAVE_GEMINI = "AIzaSyDEuNX3vI2M21V4DlnJQz_1KDNU39T5UJg"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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


class AppPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pedagógico CursoMS - Acesso Restrito")
        self.geometry("450x650")
        self.configure(fg_color=BG_WINDOW)

        # --- CARREGA O ÍCONE NA JANELA PRINCIPAL ---
        try:
            self.iconbitmap(resource_path("Play Branco.ico"))
        except:
            pass
        # -------------------------------------------

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = (largura_tela // 2) - (450 // 2)
        pos_y = (altura_tela // 2) - (650 // 2)
        self.geometry(f"450x650+{pos_x}+{pos_y}")
        self.attributes("-topmost", True)
        self.autenticado = False

        self.carregar_dados_login()
        self.construir_tela_login()

    def carregar_dados_login(self):
        self.arquivo_config = "config_unificada.json"
        self.dados_padrao = {
            "origem_url": "https://cursoms.com.br/ead/admin/principal.asp",
            "origem_user": "",
            "origem_pass": "",
            "destino_url": "https://cursoms.com.br/ead/admin/principal.asp",
            "destino_user": "",
            "destino_pass": "",
            "lembrar_user": "",
            "ultima_ordem": 1,
            "ultimo_destino": "",
        }
        if os.path.exists(self.arquivo_config):
            try:
                with open(self.arquivo_config, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
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
        self.card = ctk.CTkFrame(
            self, fg_color=BG_CARD, border_width=1, border_color=BORDER_COLOR, corner_radius=16
        )
        self.card.pack(expand=True, fill="both", padx=40, pady=60)

        ctk.CTkLabel(self.card, text="🎓", font=("Arial", 45), text_color=VERDE_ACAO).pack(
            pady=(30, 5)
        )
        ctk.CTkLabel(
            self.card, text="Welcome Back", font=("Inter", 24, "bold"), text_color=TEXT_LIGHT
        ).pack()
        ctk.CTkLabel(
            self.card, text="Pedagógico Secure Portal", font=("Inter", 12), text_color=TEXT_MUTED
        ).pack(pady=(0, 25))

        frame_user = ctk.CTkFrame(self.card, fg_color="transparent")
        frame_user.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(
            frame_user, text="Usuário", font=("Inter", 12, "bold"), text_color=TEXT_MUTED
        ).pack(anchor="w", padx=5)
        self.ent_user = ctk.CTkEntry(
            frame_user,
            placeholder_text="Digite seu usuário",
            height=45,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_LIGHT,
            corner_radius=8,
        )
        self.ent_user.pack(fill="x", pady=(2, 0))
        if self.config.get("lembrar_user"):
            self.ent_user.insert(0, self.config.get("lembrar_user"))

        frame_pass = ctk.CTkFrame(self.card, fg_color="transparent")
        frame_pass.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(
            frame_pass, text="Senha", font=("Inter", 12, "bold"), text_color=TEXT_MUTED
        ).pack(anchor="w", padx=5)
        self.ent_pass = ctk.CTkEntry(
            frame_pass,
            placeholder_text="Digite sua senha",
            show="•",
            height=45,
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_LIGHT,
            corner_radius=8,
        )
        self.ent_pass.pack(fill="x", pady=(2, 0))

        frame_opcoes = ctk.CTkFrame(self.card, fg_color="transparent")
        frame_opcoes.pack(fill="x", padx=30, pady=5)
        self.var_lembrar = ctk.BooleanVar(value=bool(self.config.get("lembrar_user")))
        chk_lembrar = ctk.CTkCheckBox(
            frame_opcoes,
            text="Lembrar de mim",
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
        chk_lembrar.pack(side="left")

        btn_esqueceu = ctk.CTkButton(
            frame_opcoes,
            text="Esqueceu a senha?",
            font=("Inter", 12, "bold"),
            text_color=VERDE_ACAO,
            fg_color="transparent",
            hover_color=BG_CARD,
            width=10,
            command=self.recuperar_senha,
        )
        btn_esqueceu.pack(side="right")

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
        ctk.CTkButton(
            self.card,
            text="Não tem uma conta? Criar nova conta",
            font=("Inter", 12),
            text_color=TEXT_MUTED,
            fg_color="transparent",
            hover_color=BG_CARD,
            command=self.abrir_tela_cadastro,
        ).pack(pady=5)

        self.lbl_status = ctk.CTkLabel(
            self.card, text="", text_color=VERMELHO_PARAR, font=("Inter", 12, "bold")
        )
        self.lbl_status.pack()

        ctk.CTkLabel(
            self, text="Criado por Wesley Adrion", font=("Inter", 10), text_color="#1F2937"
        ).pack(side="bottom", pady=15)

    def recuperar_senha(self):
        messagebox.showinfo(
            "Recuperação",
            "Por favor, entre em contato com o administrador (Wesley Adrion) para redefinir sua senha.",
        )

    def abrir_tela_cadastro(self):
        self.tela_cad = ctk.CTkToplevel(self)
        self.tela_cad.title("Criar Nova Conta")
        self.tela_cad.geometry("450x680")
        self.tela_cad.configure(fg_color=BG_WINDOW)
        self.tela_cad.attributes("-topmost", True)
        self.tela_cad.grab_set()

        try:
            self.tela_cad.iconbitmap(resource_path("Play Branco.ico"))
        except:
            pass

        card_cad = ctk.CTkFrame(
            self.tela_cad,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=16,
        )
        card_cad.pack(expand=True, fill="both", padx=30, pady=40)

        ctk.CTkLabel(card_cad, text="📝", font=("Arial", 40), text_color=VERDE_ACAO).pack(
            pady=(20, 0)
        )
        ctk.CTkLabel(
            card_cad, text="Criar Nova Conta", font=("Inter", 22, "bold"), text_color=TEXT_LIGHT
        ).pack()
        ctk.CTkLabel(
            card_cad,
            text="Solicite acesso ao Pedagógico",
            font=("Inter", 11),
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 20))

        def criar_campo(pai, texto, placeholder, is_pass=False):
            f = ctk.CTkFrame(pai, fg_color="transparent")
            f.pack(fill="x", padx=25, pady=5)
            ctk.CTkLabel(f, text=texto, font=("Inter", 11, "bold"), text_color=TEXT_MUTED).pack(
                anchor="w", padx=5
            )
            ent = ctk.CTkEntry(
                f,
                placeholder_text=placeholder,
                show="•" if is_pass else "",
                height=40,
                fg_color=BG_INPUT,
                border_color=BORDER_COLOR,
                text_color=TEXT_LIGHT,
                corner_radius=8,
            )
            ent.pack(fill="x", pady=(2, 0))
            return ent

        ent_nome = criar_campo(card_cad, "Nome Completo", "Seu nome completo")
        ent_email = criar_campo(card_cad, "E-mail", "seu.email@exemplo.com")
        ent_user = criar_campo(card_cad, "Usuário", "Escolha um usuário")
        ent_senha = criar_campo(card_cad, "Senha", "Crie uma senha forte", True)

        lbl_status_cad = ctk.CTkLabel(
            card_cad, text="", text_color=VERMELHO_PARAR, font=("Inter", 11, "bold")
        )
        lbl_status_cad.pack(pady=5)

        def enviar_cadastro():
            n = ent_nome.get().strip()
            e = ent_email.get().strip()
            u = ent_user.get().strip()
            s = ent_senha.get().strip()
            if not n or not e or not u or not s:
                return lbl_status_cad.configure(
                    text="⚠️ Preencha todos os campos!", text_color="#F59E0B"
                )
            lbl_status_cad.configure(text="Enviando...", text_color=AZUL_PASSO)
            self.tela_cad.update()
            try:
                url_api_reg = "https://WesleyAdrion.pythonanywhere.com/api/register/"
                resposta = requests.post(
                    url_api_reg,
                    json={"username": u, "password": s, "email": e, "nome": n},
                    timeout=10,
                )
                try:
                    dados = resposta.json()
                except ValueError:
                    return lbl_status_cad.configure(
                        text=f"Erro HTML do Servidor!", text_color=VERMELHO_PARAR
                    )

                if resposta.status_code != 200:
                    return lbl_status_cad.configure(
                        text=f"Erro Servidor: {resposta.status_code}", text_color=VERMELHO_PARAR
                    )
                if dados.get("status") == "sucesso":
                    lbl_status_cad.configure(
                        text="✅ Conta criada! Aguarde liberação.", text_color=VERDE_ACAO
                    )
                    ent_nome.delete(0, "end")
                    ent_email.delete(0, "end")
                    ent_user.delete(0, "end")
                    ent_senha.delete(0, "end")
                else:
                    lbl_status_cad.configure(
                        text=f"❌ {dados.get('mensagem')}", text_color=VERMELHO_PARAR
                    )
            except requests.exceptions.RequestException:
                lbl_status_cad.configure(
                    text="⚠️ Servidor offline ou sem internet!", text_color=VERMELHO_PARAR
                )
            except Exception as ex:
                lbl_status_cad.configure(
                    text=f"⚠️ Erro: {str(ex)[:15]}...", text_color=VERMELHO_PARAR
                )

        ctk.CTkButton(
            card_cad,
            text="CRIAR CONTA",
            font=("Inter", 14, "bold"),
            height=45,
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            corner_radius=8,
            command=enviar_cadastro,
        ).pack(fill="x", padx=25, pady=15)

    def fazer_login(self):
        user = self.ent_user.get().strip()
        senha = self.ent_pass.get().strip()
        lembrar = self.var_lembrar.get()
        if not user or not senha:
            return self.lbl_status.configure(
                text="⚠️ Preencha usuário e senha!", text_color="#F59E0B"
            )
        self.salvar_dados_login(user, lembrar)
        self.lbl_status.configure(text="Conectando ao servidor...", text_color=VERDE_ACAO)
        self.update()
        try:
            url_api = "https://WesleyAdrion.pythonanywhere.com/api/login/"
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
                    text=f"❌ Erro {resposta.status_code} no Servidor.", text_color=VERMELHO_PARAR
                )
            if dados.get("status") == "sucesso":
                self.iniciar_robo_principal()
            else:
                self.lbl_status.configure(
                    text=f"❌ {dados.get('mensagem', 'Usuário ou senha incorretos!')}",
                    text_color=VERMELHO_PARAR,
                )
        except requests.exceptions.RequestException:
            self.lbl_status.configure(text="⚠️ Servidor offline!", text_color=VERMELHO_PARAR)
        except Exception as e:
            self.lbl_status.configure(
                text=f"⚠️ Erro inesperado: {str(e)[:15]}...", text_color=VERMELHO_PARAR
            )

    def iniciar_robo_principal(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.title("Pedagógico CursoMS ♻️")
        self.geometry("1100x800")
        MotorRobo(self, self.config)


# =========================================================================
# MOTOR DO ROBÔ
# =========================================================================
class MotorRobo:
    def __init__(self, root, config_carregada):
        self.root = root
        self.config = config_carregada
        self.gui_queue = queue.Queue()
        self.driver = None
        self.parar_loop = False
        self.is_running = False

        self.fila_videos = []
        self.fila_arquivos = []
        self.ordem_atual = self.config.get("ultima_ordem", 1)
        self.stats = {"v_sucesso": 0, "v_erro": 0, "a_sucesso": 0, "a_erro": 0}
        self.total_para_migrar = 0
        self.processados_agora = 0
        self.tempo_inicio_migracao = 0

        self.var_url_destino = ctk.StringVar(value=self.config.get("ultimo_destino", ""))
        self.var_origem_url = ctk.StringVar(value=self.config.get("origem_url", ""))
        self.var_origem_user = ctk.StringVar(value=self.config.get("origem_user", ""))
        self.var_origem_pass = ctk.StringVar(value=self.config.get("origem_pass", ""))
        self.var_destino_url = ctk.StringVar(value=self.config.get("destino_url", ""))
        self.var_destino_user = ctk.StringVar(value=self.config.get("destino_user", ""))
        self.var_destino_pass = ctk.StringVar(value=self.config.get("destino_pass", ""))

        self.setup_ui()
        self.ativar_atalhos()
        self.processar_fila_gui()

    def processar_fila_gui(self):
        try:
            while True:
                self.gui_queue.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(100, self.processar_fila_gui)

    def ui_do(self, acao):
        self.gui_queue.put(acao)

    def salvar_config(self):
        try:
            self.config["ultima_ordem"] = self.ordem_atual
            self.config["ultimo_destino"] = self.var_url_destino.get()
            self.config["origem_url"] = self.var_origem_url.get()
            self.config["origem_user"] = self.var_origem_user.get()
            self.config["origem_pass"] = self.var_origem_pass.get()
            self.config["destino_url"] = self.var_destino_url.get()
            self.config["destino_user"] = self.var_destino_user.get()
            self.config["destino_pass"] = self.var_destino_pass.get()
            with open("config_unificada.json", "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except:
            pass

    def config_tags_log(self, txt_widget):
        txt_widget.tag_config("hora", foreground=TEXT_MUTED)
        txt_widget.tag_config("ok", foreground=VERDE_ACAO)
        txt_widget.tag_config("erro", foreground=VERMELHO_PARAR)
        txt_widget.tag_config("info", foreground=AZUL_PASSO)
        txt_widget.tag_config("texto", foreground="#E2E8F0")
        txt_widget.tag_config("aviso", foreground="#F59E0B")

    def log(self, tipo, msg):
        def _inserir():
            hora = datetime.now().strftime("%H:%M:%S")
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"[{hora}] ", "hora")
            if tipo == "OK":
                self.txt_log.insert("end", "SUCESSO ", "ok")
            elif tipo == "ERRO":
                self.txt_log.insert("end", "ERRO ", "erro")
            elif tipo == "AVISO":
                self.txt_log.insert("end", "AVISO ", "aviso")
            else:
                self.txt_log.insert("end", "INFO ", "info")
            self.txt_log.insert("end", f"- {msg}\n", "texto")
            self.txt_log.configure(state="disabled")
            self.txt_log.see("end")

        self.ui_do(_inserir)

    def registrar_falha_caixa_preta(self, local_erro, excecao):
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        trace = traceback.format_exc()
        try:
            with open("erro_log.txt", "a", encoding="utf-8") as f:
                f.write(f"[{agora}] ERRO DETECTADO EM: {local_erro}\n")
                f.write(f"MENSAGEM: {str(excecao)}\n")
                f.write(f"RASTREAMENTO COMPLETO:\n{trace}\n")
                f.write("-" * 60 + "\n")
            self.log("ERRO", f"Falha gravada no log! Peça para a IA analisar.")
        except:
            pass

    # =========================================================================
    # ORÁCULO IA (GEMINI PRO)
    # =========================================================================
    def abrir_assistente_ia(self):
        self.tela_ia = ctk.CTkToplevel(self.root)
        self.tela_ia.title("🧠 Oráculo IA - Gemini Pro")
        self.tela_ia.geometry("600x700")
        self.tela_ia.configure(fg_color=BG_WINDOW)
        self.tela_ia.attributes("-topmost", True)

        try:
            self.tela_ia.iconbitmap(resource_path("Play Branco.ico"))
        except:
            pass

        ctk.CTkLabel(
            self.tela_ia,
            text="Assistente de Inteligência Artificial",
            font=("Inter", 20, "bold"),
            text_color=ROXO_IA,
        ).pack(pady=(20, 5))
        ctk.CTkLabel(
            self.tela_ia,
            text="Tire dúvidas ou peça para a IA analisar os erros do robô.",
            font=("Inter", 12),
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 20))

        self.txt_chat = ctk.CTkTextbox(
            self.tela_ia,
            font=("Consolas", 13),
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=8,
            text_color=TEXT_LIGHT,
            wrap="word",
        )
        self.txt_chat.pack(fill="both", expand=True, padx=20, pady=10)
        self.txt_chat.insert(
            "end",
            "🤖 Gemini Pro: Olá, Wesley! Sou o seu assistente inteligente. Em que posso ajudar hoje?\n\n",
        )
        self.txt_chat.configure(state="disabled")

        frame_baixo = ctk.CTkFrame(self.tela_ia, fg_color="transparent")
        frame_baixo.pack(fill="x", padx=20, pady=15)
        self.ent_pergunta = ctk.CTkEntry(
            frame_baixo,
            placeholder_text="Pergunte ao Gemini...",
            height=40,
            fg_color=BG_CARD,
            border_color=BORDER_COLOR,
        )
        self.ent_pergunta.pack(side="left", fill="x", expand=True, padx=(0, 10))
        btn_enviar = ctk.CTkButton(
            frame_baixo,
            text="Enviar",
            width=80,
            height=40,
            font=("Inter", 12, "bold"),
            fg_color=ROXO_IA,
            hover_color="#6D28D9",
            command=self.enviar_pergunta_gemini,
        )
        btn_enviar.pack(side="right")
        btn_analisar_erro = ctk.CTkButton(
            self.tela_ia,
            text="🔍 Analisar Último Erro do Robô",
            font=("Inter", 13, "bold"),
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            height=40,
            command=self.pedir_gemini_analisar_erro,
        )
        btn_analisar_erro.pack(fill="x", padx=20, pady=(0, 20))

    def atualizar_chat_ia(self, texto, autor=""):
        self.txt_chat.configure(state="normal")
        if autor:
            self.txt_chat.insert("end", f"\n{autor}")
        self.txt_chat.insert("end", f"{texto}\n")
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")

    def enviar_pergunta_gemini(self):
        pergunta = self.ent_pergunta.get().strip()
        if not pergunta:
            return
        self.ent_pergunta.delete(0, "end")
        self.atualizar_chat_ia(f"{pergunta}", autor="👤 Você: ")
        self.chamar_api_gemini(pergunta)

    def pedir_gemini_analisar_erro(self):
        try:
            if not os.path.exists("erro_log.txt"):
                return messagebox.showinfo(
                    "IA",
                    "Nenhum ficheiro de erro encontrado. O sistema está a rodar perfeitamente!",
                )
            with open("erro_log.txt", "r", encoding="utf-8") as f:
                logs = f.readlines()
            ultimo_erro = "".join(logs[-15:])
            if not ultimo_erro.strip():
                return
            prompt = f"Lê o seguinte erro que ocorreu no meu script de automação Python (Selenium) e explica-me de forma simples, em português, qual foi o problema e como o posso resolver:\n\n{ultimo_erro}"
            self.atualizar_chat_ia(
                "Por favor, analisa o último erro do Pedagógico.", autor="👤 Você: "
            )
            self.chamar_api_gemini(prompt)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler o log: {e}")

    def chamar_api_gemini(self, prompt):
        self.atualizar_chat_ia("Pensando...", autor="🤖 Gemini: ")

        def _thread_ia():
            try:
                client = genai.Client(api_key=CHAVE_GEMINI)
                response = client.models.generate_content(model="gemini-1.5-pro", contents=prompt)
                self.ui_do(lambda: self._substituir_pensando(response.text))
            except Exception as e:
                erro_msg = f"Erro na API do Google: {e}"
                self.ui_do(lambda msg=erro_msg: self._substituir_pensando(msg))

        threading.Thread(target=_thread_ia).start()

    def _substituir_pensando(self, texto_real):
        self.txt_chat.configure(state="normal")
        texto_atual = self.txt_chat.get("1.0", "end")
        if "Pensando..." in texto_atual:
            novo_texto = texto_atual.rsplit("Pensando...", 1)
            self.txt_chat.delete("1.0", "end")
            self.txt_chat.insert("1.0", novo_texto[0] + texto_real + novo_texto[1])
        else:
            self.txt_chat.insert("end", f"{texto_real}\n")
        self.txt_chat.see("end")
        self.txt_chat.configure(state="disabled")

    # =========================================================================
    # INTERFACE PRINCIPAL
    # =========================================================================
    def setup_ui(self):
        self.root.configure(fg_color=BG_WINDOW)
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        top_layout = ctk.CTkFrame(main_container, fg_color="transparent")
        top_layout.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(
            top_layout,
            width=260,
            fg_color=BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        sidebar.pack(side="left", fill="y", padx=(0, 20))
        sidebar.pack_propagate(False)

        header_side = ctk.CTkFrame(sidebar, fg_color="transparent")
        header_side.pack(fill="x", pady=20, padx=15)
        ctk.CTkLabel(
            header_side,
            text="🤖 PEDAGÓGICO CURSOMS",
            font=("Inter Black", 16),
            text_color=AZUL_PASSO,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header_side,
            text="AUTOMAÇÃO DE MIGRAÇÃO",
            font=("Inter", 10, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(
            sidebar, text="CONTROLES PRINCIPAIS", font=("Inter", 11, "bold"), text_color=TEXT_MUTED
        ).pack(anchor="w", padx=20, pady=(10, 5))

        ctk.CTkButton(
            sidebar,
            text="🌐 Iniciar Navegador",
            font=("Inter", 13, "bold"),
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            height=45,
            corner_radius=8,
            command=self.iniciar_browser,
        ).pack(fill="x", padx=15, pady=8)
        ctk.CTkButton(
            sidebar,
            text="1. Login Origem",
            font=("Inter", 13, "bold"),
            fg_color=AZUL_PASSO,
            hover_color="#1E4FC2",
            height=45,
            corner_radius=8,
            command=self.login_origem,
        ).pack(fill="x", padx=15, pady=8)
        ctk.CTkButton(
            sidebar,
            text="2. Login Destino",
            font=("Inter", 13, "bold"),
            fg_color="#8E44AD",
            hover_color="#732D91",
            height=45,
            corner_radius=8,
            command=self.login_destino,
        ).pack(fill="x", padx=15, pady=8)
        ctk.CTkButton(
            sidebar,
            text="🧹 Limpar Filas",
            font=("Inter", 13, "bold"),
            fg_color="#4B5563",
            hover_color="#374151",
            height=45,
            corner_radius=8,
            command=self.resetar_modulo,
        ).pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(
            sidebar, text="SUPORTE", font=("Inter", 11, "bold"), text_color=TEXT_MUTED
        ).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkButton(
            sidebar,
            text="🧠 Oráculo IA",
            font=("Inter", 13, "bold"),
            fg_color=ROXO_IA,
            hover_color="#6D28D9",
            height=45,
            corner_radius=8,
            command=self.abrir_assistente_ia,
        ).pack(fill="x", padx=15, pady=8)

        content = ctk.CTkFrame(
            top_layout,
            fg_color=BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        content.pack(side="right", fill="both", expand=True)

        self.tabview = ctk.CTkTabview(content, width=720)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_migracao = self.tabview.add("🚀 Migração de Aulas")
        self.tab_config = self.tabview.add("⚙️ Configurações (Logins)")

        self.construir_aba_config()
        self.construir_aba_migracao()

        bottom_area = ctk.CTkFrame(main_container, height=200, fg_color="#0B1119", corner_radius=10)
        bottom_area.pack(fill="x", side="bottom", pady=(15, 0))
        bottom_area.pack_propagate(False)

        status_bar = ctk.CTkFrame(bottom_area, fg_color="transparent")
        status_bar.pack(fill="x", padx=15, pady=(15, 5))
        self.lbl_tempo = ctk.CTkLabel(
            status_bar,
            text="Tempo Estimado: --m --s",
            font=("Inter", 12, "bold"),
            text_color="#F1C40F",
        )
        self.lbl_tempo.pack(side="left")
        self.progress_bar = ctk.CTkProgressBar(
            status_bar, progress_color=AZUL_PASSO, fg_color="#1F252D", height=10
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=20)
        self.progress_bar.set(0)
        ctk.CTkButton(
            status_bar,
            text="🛑 PARAR TUDO",
            font=("Inter", 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=VERMELHO_PARAR,
            text_color=VERMELHO_PARAR,
            hover_color="#3A171C",
            width=80,
            height=30,
            corner_radius=5,
            command=self.parar_tudo,
        ).pack(side="right")

        self.txt_log = ctk.CTkTextbox(
            bottom_area, font=("Consolas", 12), fg_color="transparent", text_color="#E2E8F0"
        )
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.config_tags_log(self.txt_log)
        self.txt_log.configure(state="disabled")

    def construir_aba_config(self):
        scroll_cfg = ctk.CTkScrollableFrame(self.tab_config, fg_color="transparent")
        scroll_cfg.pack(fill="both", expand=True, padx=5, pady=5)
        ctk.CTkLabel(
            scroll_cfg, text="Gerencie aqui os acessos das duas plataformas", font=("Inter", 14)
        ).pack(pady=10)

        frm_origem = ctk.CTkFrame(scroll_cfg, fg_color=BG_INPUT)
        frm_origem.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(
            frm_origem,
            text="📥 CREDENCIAIS DE ORIGEM (Guia 1)",
            font=("Inter", 14, "bold"),
            text_color="#F39C12",
        ).pack(pady=10)
        ctk.CTkLabel(frm_origem, text="Link:").pack()
        ctk.CTkEntry(frm_origem, textvariable=self.var_origem_url, width=500).pack(pady=(0, 5))
        ctk.CTkLabel(frm_origem, text="Usuário:").pack()
        ctk.CTkEntry(frm_origem, textvariable=self.var_origem_user, width=300).pack(pady=(0, 5))
        ctk.CTkLabel(frm_origem, text="Senha:").pack()
        ctk.CTkEntry(frm_origem, textvariable=self.var_origem_pass, width=300, show="*").pack(
            pady=(0, 10)
        )

        frm_destino = ctk.CTkFrame(scroll_cfg, fg_color=BG_INPUT)
        frm_destino.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(
            frm_destino,
            text="📤 CREDENCIAIS DE DESTINO (Guia 2)",
            font=("Inter", 14, "bold"),
            text_color="#8E44AD",
        ).pack(pady=10)
        ctk.CTkLabel(frm_destino, text="Link:").pack()
        ctk.CTkEntry(frm_destino, textvariable=self.var_destino_url, width=500).pack(pady=(0, 5))
        ctk.CTkLabel(frm_destino, text="Usuário:").pack()
        ctk.CTkEntry(frm_destino, textvariable=self.var_destino_user, width=300).pack(pady=(0, 5))
        ctk.CTkLabel(frm_destino, text="Senha:").pack()
        ctk.CTkEntry(frm_destino, textvariable=self.var_destino_pass, width=300, show="*").pack(
            pady=(0, 10)
        )

        ctk.CTkButton(
            scroll_cfg,
            text="💾 SALVAR CREDENCIAIS",
            font=("Inter", 14, "bold"),
            height=45,
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            command=self._salvar_config_btn,
        ).pack(pady=20)

    def _salvar_config_btn(self):
        self.salvar_config()
        messagebox.showinfo("Sucesso", "Credenciais salvas!")

    def construir_aba_migracao(self):
        cfg = ctk.CTkFrame(self.tab_migracao, fg_color=BG_INPUT)
        cfg.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(
            cfg,
            text="🎯 Cole a URL do Dashboard/Módulo de DESTINO:",
            font=("Inter", 14, "bold"),
            text_color="#F39C12",
        ).pack(pady=(15, 5))
        ctk.CTkEntry(
            cfg,
            textvariable=self.var_url_destino,
            font=("Inter", 12),
            justify="center",
            height=45,
            width=500,
        ).pack(pady=(0, 15))

        step1 = ctk.CTkFrame(self.tab_migracao, fg_color="transparent")
        step1.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(
            step1,
            text="🔍 PASSO 1: LER TUDO (Dashboard de Origem)",
            font=("Inter", 15, "bold"),
            height=55,
            fg_color="#D68910",
            hover_color="#B9770E",
            command=self.iniciar_varredura_universal,
        ).pack(fill="x")

        filas = ctk.CTkFrame(step1, fg_color="transparent")
        filas.pack(fill="x", pady=5)
        self.lbl_fila_v = ctk.CTkLabel(
            filas, text="▶️ Vídeos: 0", font=("Inter", 14, "bold"), text_color="#3498DB"
        )
        self.lbl_fila_v.pack(side="left", expand=True)
        self.lbl_fila_a = ctk.CTkLabel(
            filas, text="📄 Materiais: 0", font=("Inter", 14, "bold"), text_color="#8E44AD"
        )
        self.lbl_fila_a.pack(side="right", expand=True)

        step2 = ctk.CTkFrame(self.tab_migracao, fg_color="transparent")
        step2.pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(
            step2,
            text="🚀 PASSO 2: MIGRAR PARA O DESTINO",
            font=("Inter", 16, "bold"),
            height=70,
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            command=self.iniciar_migracao_interna,
        ).pack(fill="x")

    def ativar_atalhos(self):
        keyboard.add_hotkey("f10", self.iniciar_migracao_interna)
        keyboard.add_hotkey("f12", self.parar_tudo)

    def checar_navegador(self):
        if self.driver is None:
            return False
        try:
            _ = self.driver.title
            return True
        except:
            return False

    def resetar_modulo(self):
        self.fila_videos.clear()
        self.fila_arquivos.clear()
        self.stats = {"v_sucesso": 0, "v_erro": 0, "a_sucesso": 0, "a_erro": 0}
        self.ui_do(lambda: self.progress_bar.set(0))
        self.ui_do(lambda: self.lbl_fila_v.configure(text="▶️ Vídeos: 0"))
        self.ui_do(lambda: self.lbl_fila_a.configure(text="📄 Materiais: 0"))
        self.ui_do(lambda: self.lbl_tempo.configure(text="Tempo Estimado: --m --s"))
        self.log("INFO", "Filas e memória zeradas!")

    def iniciar_browser(self):
        if self.checar_navegador():
            return self.log("INFO", "O navegador já está aberto e respondendo.")
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            self.driver.maximize_window()
            self.log("INFO", "Navegador iniciado com sucesso.")
        except Exception as e:
            self.registrar_falha_caixa_preta("iniciar_browser", e)
            messagebox.showerror("Erro", str(e))

    def parar_tudo(self):
        self.parar_loop = True
        self.log("ERRO", "PARADA DE EMERGÊNCIA SOLICITADA.")

    def login_origem(self):
        threading.Thread(target=self._login_origem_thread).start()

    def _login_origem_thread(self):
        if not self.checar_navegador():
            return self.log("ERRO", "Abra o navegador primeiro!")
        try:
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.get(self.var_origem_url.get())
            wait = WebDriverWait(self.driver, 10)
            u = wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao")))
            u.click()
            u.clear()
            u.send_keys(self.var_origem_user.get())
            s = self.driver.find_element(By.NAME, "senhadagestao")
            s.click()
            s.clear()
            s.send_keys(self.var_origem_pass.get())
            self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
            self.log("OK", "Login na ORIGEM Realizado (Guia 1)")
        except Exception as e:
            self.registrar_falha_caixa_preta("login_origem", e)

    def login_destino(self):
        threading.Thread(target=self._login_destino_thread).start()

    def _login_destino_thread(self):
        if not self.checar_navegador():
            return self.log("ERRO", "Abra o navegador primeiro!")
        try:
            if len(self.driver.window_handles) == 1:
                self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.driver.get(self.var_destino_url.get())
            wait = WebDriverWait(self.driver, 10)
            u = wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao")))
            u.click()
            u.clear()
            u.send_keys(self.var_destino_user.get())
            s = self.driver.find_element(By.NAME, "senhadagestao")
            s.click()
            s.clear()
            s.send_keys(self.var_destino_pass.get())
            self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
            self.log("OK", "Login no DESTINO Realizado (Guia 2)")
        except Exception as e:
            self.registrar_falha_caixa_preta("login_destino", e)

    def expandir_paginacao_jplist(self):
        try:
            self.driver.switch_to.default_content()
            painel = self.driver.find_element(
                By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
            )
            self.driver.execute_script("arguments[0].click();", painel)
            time.sleep(0.5)
            ver_todos = self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']")
            self.driver.execute_script("arguments[0].click();", ver_todos)
            time.sleep(2.5)
            return True
        except:
            return False

    def atualizar_progresso(self):
        total = (
            len(self.fila_videos)
            + len(self.fila_arquivos)
            + self.stats["v_sucesso"]
            + self.stats["v_erro"]
            + self.stats["a_sucesso"]
            + self.stats["a_erro"]
        )
        if total > 0:
            feitos = total - (len(self.fila_videos) + len(self.fila_arquivos))
            self.ui_do(lambda: self.progress_bar.set(feitos / total))
        self.ui_do(lambda: self.lbl_fila_v.configure(text=f"▶️ Vídeos: {len(self.fila_videos)}"))
        self.ui_do(
            lambda: self.lbl_fila_a.configure(text=f"📄 Materiais: {len(self.fila_arquivos)}")
        )

    def atualizar_eta(self):
        if self.total_para_migrar == 0 or self.processados_agora == 0:
            return
        tempo_decorrido = time.time() - self.tempo_inicio_migracao
        tempo_medio = tempo_decorrido / self.processados_agora
        restantes = self.total_para_migrar - self.processados_agora

        if restantes > 0:
            minutos, segundos = divmod(int(tempo_medio * restantes), 60)
            texto_tempo = f"Tempo Estimado: {minutos:02d}m {segundos:02d}s"
        else:
            texto_tempo = "Concluído!"
            self.ui_do(lambda: self.lbl_tempo.configure(text=texto_tempo))

    def iniciar_varredura_universal(self):
        threading.Thread(target=self._varredura_universal_thread).start()

    def _varredura_universal_thread(self):
        if not self.checar_navegador():
            return self.log("ERRO", "Navegador fechado. Clique em 'Iniciar Navegador'.")
        self.driver.switch_to.window(self.driver.window_handles[0])
        self.fila_videos.clear()
        self.fila_arquivos.clear()
        self.atualizar_progresso()
        self.log("INFO", "Iniciando Leitura no Dashboard de Origem (Guia 1)...")
        dashboard_url = self.driver.current_url

        try:
            wait = WebDriverWait(self.driver, 5)
            try:
                icone_video = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//a[contains(@href, 'videos.asp')]")
                    )
                )
            except:
                icone_video = []

            if icone_video:
                self.log("INFO", "Acessando Vídeos...")
                self.driver.get(icone_video[0].get_attribute("href"))
                time.sleep(2)
                self.expandir_paginacao_jplist()

                def buscar_links_v():
                    links = self.driver.find_elements(
                        By.XPATH, f"//a[contains(@href, 'alterar_video.asp')]"
                    )
                    if links:
                        return [l.get_attribute("href") for l in links]
                    for iframe in self.driver.find_elements(By.TAG_NAME, "iframe"):
                        try:
                            self.driver.switch_to.frame(iframe)
                            vimeo_input = self.driver.find_elements(By.ID, "vimeo")
                            assunto_input = self.driver.find_elements(By.ID, "assunto")
                            if vimeo_input and assunto_input:
                                texto = " ".join(
                                    assunto_input[0].get_attribute("value").strip().split()
                                )
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
                                        for p in texto.lower().split()
                                    ]
                                )
                                vim = vimeo_input[0].get_attribute("value")
                                self.driver.switch_to.default_content()
                                return [{"titulo": tit, "vimeo": vim}]
                            self.driver.switch_to.default_content()
                        except:
                            self.driver.switch_to.default_content()
                    return []

                resultados = buscar_links_v()
                if resultados:
                    if isinstance(resultados[0], dict):
                        for res in resultados:
                            self.fila_videos.append(res)
                            self.atualizar_progresso()
                    else:
                        urls = resultados
                        urls.reverse()
                        janela_princ = self.driver.current_window_handle
                        for url in urls:
                            try:
                                self.driver.execute_script(f"window.open('{url}');")
                                self.driver.switch_to.window(self.driver.window_handles[-1])
                                wait_vid = WebDriverWait(self.driver, 5)
                                try:
                                    elem_t = wait_vid.until(
                                        EC.presence_of_element_located((By.ID, "assunto"))
                                    )
                                    texto = " ".join(elem_t.get_attribute("value").strip().split())
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
                                            for p in texto.lower().split()
                                        ]
                                    )
                                    vim = self.driver.find_element(By.ID, "vimeo").get_attribute(
                                        "value"
                                    )
                                    self.fila_videos.append({"titulo": tit, "vimeo": vim})
                                    self.atualizar_progresso()
                                except:
                                    self.log("AVISO", f"Dados não encontrados na aba do vídeo.")
                                self.driver.close()
                                self.driver.switch_to.window(janela_princ)
                            except:
                                try:
                                    self.driver.close()
                                    self.driver.switch_to.window(janela_princ)
                                except:
                                    pass
                self.log("OK", f"{len(self.fila_videos)} Vídeos Capturados!")
                self.driver.get(dashboard_url)

            # MATERIAIS
            links_setores = {
                "Material Impresso": {"xpath": "//a[contains(@href, 'setor=1')]", "setor": "1"},
                "Slides": {"xpath": "//a[contains(@href, 'setor=2')]", "setor": "2"},
                "Atividades": {"xpath": "//a[contains(@href, 'setor=4')]", "setor": "4"},
            }
            urls_para_visitar = []
            for nome, info in links_setores.items():
                elems = self.driver.find_elements(By.XPATH, info["xpath"])
                if elems:
                    urls_para_visitar.append((nome, elems[0].get_attribute("href"), info["setor"]))

            for nome, url_setor, setor_id in urls_para_visitar:
                self.log("INFO", f"Acessando {nome}...")
                self.driver.get(url_setor)
                time.sleep(2)
                self.expandir_paginacao_jplist()
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                lote_setor = []
                for item in soup.find_all("div", class_="list-item box"):
                    titulo = (
                        item.find("td", class_="subject").text.strip()
                        if item.find("td", class_="subject")
                        else "Sem Titulo"
                    )
                    for a_tag in item.find_all("a", href=True):
                        if "arquivoid.asp" in a_tag["href"].lower():
                            lote_setor.append(
                                {
                                    "titulo": titulo,
                                    "url_ver": urljoin(url_setor, a_tag["href"]),
                                    "setor": setor_id,
                                    "nome_categoria": nome,
                                }
                            )
                            break
                lote_setor.reverse()
                self.fila_arquivos.extend(lote_setor)
                self.atualizar_progresso()
                self.log("OK", f"{len(lote_setor)} {nome} Capturados!")

            self.driver.get(dashboard_url)
            self.log("INFO", "🎉 SUPER VARREDURA CONCLUÍDA! Pronto para o Passo 2.")

        except Exception as e:
            self.registrar_falha_caixa_preta("_varredura_universal_thread", e)
            self.log("ERRO", f"Falha na varredura. Peça análise para a IA.")

    def iniciar_migracao_interna(self):
        if not self.fila_videos and not self.fila_arquivos:
            return messagebox.showwarning("Aviso", "Filas vazias! Faça a varredura primeiro.")
        if not self.checar_navegador():
            return messagebox.showerror("Erro", "O navegador foi fechado.")
        if len(self.driver.window_handles) < 2:
            return messagebox.showerror(
                "Erro", "A Guia 2 (Destino) não está aberta! Faça o Login 2."
            )
        url_destino = self.var_url_destino.get().strip()
        if not url_destino or "cursoms" not in url_destino.lower():
            return messagebox.showerror("Erro", "Cole uma URL válida do Módulo de destino!")

        self.salvar_config()
        self.parar_loop = False
        self.total_para_migrar = len(self.fila_videos) + len(self.fila_arquivos)
        self.processados_agora = 0
        self.tempo_inicio_migracao = time.time()
        threading.Thread(target=self._execucao_migracao_thread, args=(url_destino,)).start()

    def _execucao_migracao_thread(self, url_destino):
        aba_origem = self.driver.window_handles[0]
        aba_destino = self.driver.window_handles[1]

        self.driver.switch_to.window(aba_origem)
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c["name"], c["value"])

        self.driver.switch_to.window(aba_destino)
        self.driver.get(url_destino)
        wait = WebDriverWait(self.driver, 10)
        time.sleep(2)

        if self.fila_videos and not self.parar_loop:
            self.log("INFO", "--- INICIANDO MIGRAÇÃO DE VÍDEOS ---")
            btn_video = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'videos.asp')]")
            if btn_video:
                self.driver.get(btn_video[0].get_attribute("href"))
                time.sleep(2)
                url_lista_videos = self.driver.current_url

                while self.fila_videos and not self.parar_loop:
                    dados = self.fila_videos[0]
                    try:
                        try:
                            btn_cad = wait.until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, "//a[contains(@href, 'cadastrar_video.asp')]")
                                )
                            )
                            btn_cad.click()
                        except:
                            self.driver.get(url_lista_videos)
                            time.sleep(2)
                            btn_cad = wait.until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, "//a[contains(@href, 'cadastrar_video.asp')]")
                                )
                            )
                            btn_cad.click()

                        campo_assunto = wait.until(
                            EC.presence_of_element_located((By.NAME, "assunto"))
                        )
                        campo_assunto.clear()
                        campo_assunto.send_keys(dados["titulo"][:70])
                        campo_vimeo = self.driver.find_element(By.NAME, "vimeo")
                        campo_vimeo.clear()
                        campo_vimeo.send_keys(dados["vimeo"])
                        self.driver.find_element(
                            By.XPATH, "//input[@type='submit' and @value='Criar']"
                        ).click()

                        try:
                            wait.until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        "//*[contains(translate(text(), 'SUCESSO', 'sucesso'), 'sucesso')] | //img[contains(@src, 'botao-voltar')]",
                                    )
                                )
                            )
                        except:
                            pass

                        self.driver.get(url_lista_videos)
                        wait.until(
                            EC.presence_of_element_located(
                                (By.XPATH, "//a[contains(@href, 'cadastrar_video.asp')]")
                            )
                        )
                        time.sleep(1)

                        self.log("OK", f"VÍDEO CRIADO: {dados['titulo'][:30]}")
                        self.fila_videos.pop(0)
                        self.stats["v_sucesso"] += 1
                    except Exception as e:
                        self.registrar_falha_caixa_preta(f"Migrar Vídeo ({dados['titulo']})", e)
                        self.log("ERRO", f"FALHA NO VÍDEO: {dados['titulo'][:30]}")
                        self.fila_videos.pop(0)
                        self.stats["v_erro"] += 1
                        try:
                            self.driver.get(url_lista_videos)
                            time.sleep(2)
                        except:
                            pass

                    self.processados_agora += 1
                    self.atualizar_progresso()
                    self.atualizar_eta()

        if self.fila_arquivos and not self.parar_loop:
            self.log("INFO", "--- INICIANDO MIGRAÇÃO DE MATERIAIS ---")
            PASTA_DOWNLOADS = "arquivos_migracao"
            if not os.path.exists(PASTA_DOWNLOADS):
                os.makedirs(PASTA_DOWNLOADS)

            self.driver.switch_to.window(aba_destino)
            self.driver.get(url_destino)
            time.sleep(2)

            urls_setores_destino = {}
            for setor_id in ["1", "2", "4"]:
                elems = self.driver.find_elements(
                    By.XPATH, f"//a[contains(@href, 'setor={setor_id}')]"
                )
                if elems:
                    urls_setores_destino[setor_id] = elems[0].get_attribute("href")

            while self.fila_arquivos and not self.parar_loop:
                dados = self.fila_arquivos[0]
                try:
                    setor_alvo = dados["setor"]
                    if setor_alvo not in urls_setores_destino:
                        raise Exception(f"Setor {setor_alvo} não existe no destino.")

                    self.log("INFO", f"Baixando (Lendo da Guia 1): {dados['titulo'][:30]}...")
                    self.driver.switch_to.window(aba_origem)
                    self.driver.get(dados["url_ver"])

                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    soup = BeautifulSoup(self.driver.page_source, "html.parser")
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
                    link = soup.find(
                        "a", href=lambda h: h and any(ext in h.lower() for ext in exts)
                    )
                    if not link:
                        link = soup.find(
                            "a", string=re.compile(r"baixar|download|arquivo|salvar", re.IGNORECASE)
                        )
                    if not link:
                        raise Exception("Link de download não encontrado")

                    url_arq = urljoin(
                        "https://cursoms.com.br/ead/", link["href"].replace("../../", "")
                    )
                    extensao_real = next((ext for ext in exts if ext in url_arq.lower()), ".pdf")
                    nome_arq = re.sub(r'[\\/*?:"<>|]', "", dados["titulo"])[:60] + extensao_real
                    caminho_local = os.path.abspath(os.path.join(PASTA_DOWNLOADS, nome_arq))

                    with open(caminho_local, "wb") as f:
                        f.write(session.get(url_arq).content)

                    self.log("INFO", "Enviando para a Guia 2...")
                    self.driver.switch_to.window(aba_destino)
                    url_lista_arquivos = urls_setores_destino[setor_alvo]
                    self.driver.get(url_lista_arquivos)
                    time.sleep(1)

                    try:
                        btn_cad_arq = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//a[contains(@href, 'cadastrar_arquivos.asp')]")
                            )
                        )
                        btn_cad_arq.click()
                    except:
                        self.driver.get(url_lista_arquivos)
                        time.sleep(2)
                        btn_cad_arq = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//a[contains(@href, 'cadastrar_arquivos.asp')]")
                            )
                        )
                        btn_cad_arq.click()

                    campo_assunto = wait.until(EC.presence_of_element_located((By.NAME, "assunto")))
                    campo_assunto.clear()
                    campo_assunto.send_keys(dados["titulo"][:110])
                    self.driver.find_element(By.NAME, "foto").send_keys(caminho_local)
                    self.driver.find_element(
                        By.XPATH, "//input[@type='submit' and @value='Criar']"
                    ).click()

                    try:
                        wait.until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//*[contains(translate(text(), 'SUCESSO', 'sucesso'), 'sucesso')] | //img[contains(@src, 'botao-voltar')]",
                                )
                            )
                        )
                    except:
                        pass

                    self.driver.get(url_lista_arquivos)
                    wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[contains(@href, 'cadastrar_arquivos.asp')]")
                        )
                    )
                    time.sleep(1)

                    try:
                        os.remove(caminho_local)
                    except:
                        pass

                    self.log("OK", f"[{dados['nome_categoria']}] CRIADO: {dados['titulo'][:30]}")
                    self.fila_arquivos.pop(0)
                    self.stats["a_sucesso"] += 1
                except Exception as e:
                    self.registrar_falha_caixa_preta(f"Migrar Arquivo ({dados['titulo']})", e)
                    self.log("ERRO", f"FALHA NO ARQUIVO: {dados['titulo'][:30]}")
                    self.fila_arquivos.pop(0)
                    self.stats["a_erro"] += 1
                    try:
                        self.driver.switch_to.window(aba_destino)
                    except:
                        pass

                self.processados_agora += 1
                self.atualizar_progresso()
                self.atualizar_eta()

        if not self.parar_loop:
            self.log("INFO", "🎉 MIGRAÇÃO INTERNA 100% CONCLUÍDA!")
            self.ui_do(lambda: self.lbl_tempo.configure(text="Processo Concluído!"))
            winsound.Beep(1200, 300)
            time.sleep(0.1)
            winsound.Beep(1200, 300)


if __name__ == "__main__":
    app_login = AppPrincipal()
    app_login.mainloop()
