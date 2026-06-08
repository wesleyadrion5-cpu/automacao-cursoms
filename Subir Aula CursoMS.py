import csv
import json
import os
import queue
import re
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
        self.title("Robô Híbrido V90 Ultimate Login")
        self.geometry("450x650")
        self.configure(fg_color=BG_WINDOW)

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
            "antigo_url": "https://cursoms.com.br/ead/admin/principal.asp",
            "antigo_user": "",
            "antigo_pass": "",
            "novo_url": "https://novo.cursoms.com.br/login",
            "novo_user": "",
            "novo_pass": "",
            "lembrar_user": "",
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

        ctk.CTkLabel(self.card, text="🧠", font=("Arial", 45), text_color=VERDE_ACAO).pack(
            pady=(30, 5)
        )
        ctk.CTkLabel(
            self.card, text="Welcome Back", font=("Inter", 24, "bold"), text_color=TEXT_LIGHT
        ).pack()
        ctk.CTkLabel(
            self.card,
            text="Secure automation login portal",
            font=("Inter", 12),
            text_color=TEXT_MUTED,
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

        card_cad = ctk.CTkFrame(
            self.tela_cad,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=16,
        )
        card_cad.pack(expand=True, fill="both", padx=30, pady=40)

        ctk.CTkLabel(card_cad, text="🤖", font=("Arial", 40), text_color=VERDE_ACAO).pack(
            pady=(20, 0)
        )
        ctk.CTkLabel(
            card_cad, text="Criar Nova Conta", font=("Inter", 22, "bold"), text_color=TEXT_LIGHT
        ).pack()
        ctk.CTkLabel(
            card_cad,
            text="Join the Hybrid V90 automation network",
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
                url_api_reg = "https://wesleyadrion.pythonanywhere.com/api/register/"
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
        self.title("Robô Híbrido V90 - Enterprise AI & Excel")
        self.geometry("1100x800")
        MotorRobo(self, self.config)


# =========================================================================
# MOTOR DO ROBÔ (INTEGRAÇÃO EXCEL + CRIAÇÃO MÓDULO + IA)
# =========================================================================
class MotorRobo:
    def __init__(self, root, config_carregada):
        self.root = root
        self.config = config_carregada
        self.gui_queue = queue.Queue()
        self.driver = None
        self.parar_loop = False
        self.is_running = False

        self.lista_excel = []  # Agora carrega a planilha
        self.fila_videos = []
        self.fila_arquivos = []
        self.memoria_lote = []
        self.auditoria = []
        self.ordem_atual = 1
        self.stats = {"v_sucesso": 0, "v_erro": 0, "a_sucesso": 0, "a_erro": 0}

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

    def registrar_falha_caixa_preta(self, local_erro, excecao):
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        trace = traceback.format_exc()
        try:
            with open("erro_log.txt", "a", encoding="utf-8") as f:
                f.write(f"[{agora}] ERRO DETECTADO EM: {local_erro}\n")
                f.write(f"MENSAGEM: {str(excecao)}\n")
                f.write(f"RASTREAMENTO COMPLETO:\n{trace}\n")
                f.write("-" * 60 + "\n")
            self.log("ERRO", f"Falha gravada no ficheiro erro_log.txt! A IA pode analisar.")
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
                    "IA", "Nenhum ficheiro de erro encontrado. O robô está a rodar perfeitamente!"
                )
            with open("erro_log.txt", "r", encoding="utf-8") as f:
                logs = f.readlines()
            ultimo_erro = "".join(logs[-15:])
            if not ultimo_erro.strip():
                return
            prompt = f"Lê o seguinte erro que ocorreu no meu script de automação Python (Selenium/Tkinter) e explica-me de forma simples, em português, qual foi o problema e como o posso resolver:\n\n{ultimo_erro}"
            self.atualizar_chat_ia("Por favor, analisa o último erro do robô.", autor="👤 Você: ")
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
    # INTERFACE PRINCIPAL DO ROBÔ
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
            header_side, text="🤖 ROBÔ HÍBRIDO", font=("Inter Black", 18), text_color=AZUL_PASSO
        ).pack(anchor="w")
        ctk.CTkLabel(
            header_side,
            text="AUTOMAÇÃO END-TO-END",
            font=("Inter", 10, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(
            sidebar, text="FLUXO DE TRABALHO", font=("Inter", 11, "bold"), text_color=TEXT_MUTED
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.btn_login_antigo = ctk.CTkButton(
            sidebar,
            text="Passo 1\nLogin Antigo",
            font=("Inter", 13, "bold"),
            fg_color=AZUL_PASSO,
            hover_color="#1E4FC2",
            height=50,
            corner_radius=8,
            command=self.login_antigo,
        )
        self.btn_login_antigo.pack(fill="x", padx=15, pady=8)

        self.btn_iniciar_nav = ctk.CTkButton(
            sidebar,
            text="🌐 Ação\nIniciar Navegador",
            font=("Inter", 13, "bold"),
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            height=50,
            corner_radius=8,
            command=self.iniciar_browser,
        )
        self.btn_iniciar_nav.pack(fill="x", padx=15, pady=8)

        self.btn_login_novo = ctk.CTkButton(
            sidebar,
            text="Passo 2\nLogin Novo",
            font=("Inter", 13, "bold"),
            fg_color="#3B4453",
            hover_color="#2A313C",
            text_color="#E2E8F0",
            height=50,
            corner_radius=8,
            command=self.login_novo,
        )
        self.btn_login_novo.pack(fill="x", padx=15, pady=8)

        self.btn_ia = ctk.CTkButton(
            sidebar,
            text="🧠 Oráculo IA",
            font=("Inter", 13, "bold"),
            fg_color=ROXO_IA,
            hover_color="#6D28D9",
            height=50,
            corner_radius=8,
            command=self.abrir_assistente_ia,
        )
        self.btn_ia.pack(fill="x", padx=15, pady=8)

        mem_frame = ctk.CTkFrame(sidebar, fg_color="#0B1119", corner_radius=8)
        mem_frame.pack(side="bottom", fill="x", padx=15, pady=20)
        self.lbl_memoria = ctk.CTkLabel(
            mem_frame, text="Memória: 0 Módulos", font=("Inter", 12, "bold"), text_color=VERDE_ACAO
        )
        self.lbl_memoria.pack(pady=15)

        content = ctk.CTkFrame(
            top_layout,
            fg_color=BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        content.pack(side="right", fill="both", expand=True)

        top_content = ctk.CTkFrame(content, fg_color="transparent")
        top_content.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(
            top_content,
            text="📊 Base de Dados (Excel)",
            font=("Inter", 16, "bold"),
            text_color="#FFFFFF",
        ).pack(side="left")

        # SUBSTITUIÇÃO DA TEXTBOX PELO EXCEL LOADER
        area_excel = ctk.CTkFrame(
            content, fg_color=BG_INPUT, border_color=BORDER_COLOR, border_width=1, corner_radius=8
        )
        area_excel.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            area_excel,
            text="Carregue a planilha Excel com as colunas:\n'Nome do Módulo', 'Curso' e 'Professor'",
            font=("Inter", 13),
            text_color=TEXT_MUTED,
        ).pack(pady=(40, 15))
        ctk.CTkButton(
            area_excel,
            text="📂 CARREGAR PLANILHA .XLSX",
            font=("Inter", 14, "bold"),
            fg_color="#F59E0B",
            hover_color="#D97706",
            height=45,
            command=self.carregar_excel,
        ).pack(pady=10)

        self.lbl_status_excel = ctk.CTkLabel(
            area_excel,
            text="Aguardando ficheiro...",
            font=("Inter", 12, "bold"),
            text_color=VERMELHO_PARAR,
        )
        self.lbl_status_excel.pack(pady=10)

        actions_frame = ctk.CTkFrame(content, fg_color="transparent")
        actions_frame.pack(fill="x", padx=20, pady=20)
        left_actions = ctk.CTkFrame(actions_frame, fg_color="transparent")
        left_actions.pack(side="left", fill="both", expand=True, padx=(0, 15))

        ctk.CTkButton(
            left_actions,
            text="1. EXTRAIR DO ANTIGO  📥",
            font=("Inter", 14, "bold"),
            fg_color="#4B5563",
            hover_color="#374151",
            height=45,
            corner_radius=8,
            command=self.iniciar_extracao_massa,
        ).pack(fill="x", pady=(0, 10))
        ctk.CTkButton(
            left_actions,
            text="📂 Carregar Backup de Extração",
            font=("Inter", 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color="#4B5563",
            text_color=TEXT_MUTED,
            hover_color="#2C333D",
            height=40,
            corner_radius=8,
            command=self.carregar_backup,
        ).pack(fill="x")

        # BOTÃO FASE 2: CRIA E INJETA
        ctk.CTkButton(
            actions_frame,
            text="2. CRIAR MÓDULOS E INJETAR 🚀",
            font=("Inter", 14, "bold"),
            fg_color=VERDE_ACAO,
            hover_color=VERDE_HOVER,
            height=95,
            corner_radius=8,
            command=self.iniciar_injecao_massa,
        ).pack(side="right", fill="both", expand=True)

        bottom_area = ctk.CTkFrame(main_container, height=200, fg_color="#0B1119", corner_radius=10)
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
            status_bar, progress_color=AZUL_PASSO, fg_color="#1F252D", height=10
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
        self.log("INFO", "Sistema V90 iniciado. Pronto para automação total.")

    def ativar_atalhos(self):
        keyboard.add_hotkey("f12", self.parar_tudo)

    def iniciar_browser(self):
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            self.driver.maximize_window()
            self.log("INFO", "Navegador aberto.")
        except Exception as e:
            self.registrar_falha_caixa_preta("iniciar_browser", e)
            messagebox.showerror("Erro", str(e))

    def parar_tudo(self):
        self.parar_loop = True
        self.log("ERRO", "PARADA DE EMERGÊNCIA SOLICITADA.")

    # =========================================================================
    # LEITURA DE DADOS
    # =========================================================================
    def carregar_excel(self):
        arquivo = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if arquivo:
            try:
                df = pd.read_excel(arquivo)
                df.columns = df.columns.astype(str).str.strip().str.lower()
                self.lista_excel = df.to_dict("records")
                self.lbl_status_excel.configure(
                    text=f"✅ PRONTO: {len(self.lista_excel)} Módulos carregados!",
                    text_color=VERDE_ACAO,
                )
                self.log("INFO", f"Excel carregado: {len(self.lista_excel)} módulos encontrados.")
            except Exception as e:
                messagebox.showerror("Erro", f"Planilha inválida: {e}")
                self.log("ERRO", f"Falha ao ler Excel: {str(e)}")

    def carregar_backup(self):
        if getattr(self, "is_running", False):
            return messagebox.showwarning("Aviso", "O robô está trabalhando, pare primeiro!")
        try:
            if os.path.exists("backup_extracao.json"):
                with open("backup_extracao.json", "r", encoding="utf-8") as f:
                    self.memoria_lote = json.load(f)
                self.ui_do(
                    lambda: self.lbl_memoria.configure(
                        text=f"Memória: {len(self.memoria_lote)} Módulos"
                    )
                )
                self.log("INFO", f"Backup carregado! {len(self.memoria_lote)} módulos na memória.")
                messagebox.showinfo(
                    "Sucesso", "Backup carregado!\nPode ir direto para o Passo 2 (Criar e Injetar)."
                )
            else:
                messagebox.showwarning(
                    "Aviso", "Nenhum ficheiro 'backup_extracao.json' encontrado."
                )
        except Exception as e:
            self.registrar_falha_caixa_preta("carregar_backup", e)

    def gerar_relatorio_csv(self):
        if not self.auditoria:
            return
        nome_arquivo = f"Relatorio_Migracao_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.csv"
        try:
            with open(nome_arquivo, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Modulo", "Tipo (Vídeo/Material)", "Nome do Item", "Status"])
                for linha in self.auditoria:
                    writer.writerow(
                        [
                            linha.get("Modulo", ""),
                            linha.get("Tipo", ""),
                            linha.get("Item", ""),
                            linha.get("Status", ""),
                        ]
                    )
            self.log("INFO", f"📊 Relatório Salvo: {nome_arquivo}")
        except Exception as e:
            self.registrar_falha_caixa_preta("gerar_relatorio_csv", e)

    # =========================================================================
    # LOGIN & CONTROLO DE NAVEGADOR
    # =========================================================================
    def login_antigo(self):
        if not self.driver:
            return messagebox.showwarning("Aviso", "Por favor, abra o Navegador primeiro!")
        threading.Thread(target=self._login_antigo_thread).start()

    def _login_antigo_thread(self):
        try:
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(self.config["antigo_url"])
            wait = WebDriverWait(self.driver, 10)
            u = wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao")))
            u.click()
            u.clear()
            u.send_keys(self.config["antigo_user"])
            s = self.driver.find_element(By.NAME, "senhadagestao")
            s.click()
            s.clear()
            s.send_keys(self.config["antigo_pass"])
            self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
            self.log("OK", "Login Antigo Realizado")
        except Exception as e:
            self.registrar_falha_caixa_preta("_login_antigo_thread", e)

    def login_novo(self):
        if not self.driver:
            return messagebox.showwarning("Aviso", "Por favor, abra o Navegador primeiro!")
        threading.Thread(target=self._login_novo_thread).start()

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
            self.log("OK", "Login Novo Realizado")
        except Exception as e:
            self.registrar_falha_caixa_preta("_login_novo_thread", e)

    # =========================================================================
    # FUNÇÕES DE DIGITAÇÃO E PESQUISA LIVEWIRE
    # =========================================================================
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

    def _preencher_pesquisa_livewire(self, wait, nome_label, texto_pesquisa):
        try:
            xpath_input = f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{nome_label.lower()}')]/following::input[contains(@*[name()='wire:model'], 'searchTerm') or contains(@*[name()='wire:model.debounce.1500ms'], 'searchTerm')][1]"
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
            time.sleep(3.5)  # Aguarda Livewire pesquisar
            xpath_lista = f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{nome_label.lower()}')]/following::ul[contains(@class, 'list-group')][1]/li"
            item_lista = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_lista)))
            self.driver.execute_script("arguments[0].click();", item_lista)
            time.sleep(0.5)
        except Exception as e:
            self.log("ERRO", f"Falha ao pesquisar '{texto_pesquisa}' em '{nome_label}'")

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
        except:
            pass

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
            self.ui_do(
                lambda: self.progress_bar.set(
                    (total - (len(self.fila_videos) + len(self.fila_arquivos))) / total
                )
            )

    # =========================================================================
    # LÓGICA DE EXTRAÇÃO E INJEÇÃO
    # =========================================================================
    def _varrer_tudo_sincrono(self, aba_antiga):
        dashboard_url = self.driver.current_url
        self.fila_videos.clear()
        self.fila_arquivos.clear()

        icone_video = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'videos.asp')]")
        if icone_video:
            self.driver.get(icone_video[0].get_attribute("href"))
            time.sleep(2)
            self.expandir_paginacao_jplist()

            def buscar_links_v():
                links = self.driver.find_elements(
                    By.XPATH, f"//a[contains(@href, 'alterar_video.asp')]"
                )
                if links:
                    return [l.get_attribute("href") for l in links]
                for q in self.driver.find_elements(
                    By.TAG_NAME, "frame"
                ) + self.driver.find_elements(By.TAG_NAME, "iframe"):
                    try:
                        self.driver.switch_to.frame(q)
                        en = buscar_links_v()
                        if en:
                            return en
                        self.driver.switch_to.parent_frame()
                    except:
                        self.driver.switch_to.parent_frame()
                return []

            urls = buscar_links_v()
            if urls:
                urls.reverse()
                janela_princ = self.driver.current_window_handle
                for url in urls:
                    janelas_antes = set(self.driver.window_handles)
                    try:
                        self.driver.execute_script(f"window.open('{url}');")
                        WebDriverWait(self.driver, 5).until(
                            lambda d: len(d.window_handles) > len(janelas_antes)
                        )
                        nova_aba = list(set(self.driver.window_handles) - janelas_antes)[0]
                        self.driver.switch_to.window(nova_aba)
                        wait = WebDriverWait(self.driver, 5)
                        elem_t = wait.until(EC.presence_of_element_located((By.ID, "assunto")))
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
                                for p in " ".join(elem_t.get_attribute("value").strip().split())
                                .lower()
                                .split()
                            ]
                        )
                        vim = self.driver.find_element(By.ID, "vimeo").get_attribute("value")
                        self.fila_videos.append({"titulo": tit, "vimeo": vim})
                        self.driver.close()
                        self.driver.switch_to.window(janela_princ)
                    except Exception as e:
                        self.registrar_falha_caixa_preta("_varrer_tudo_sincrono (Loop Vídeos)", e)
                        janelas_atuais = set(self.driver.window_handles)
                        abas_lixo = janelas_atuais - janelas_antes
                        for aba_lixo in abas_lixo:
                            self.driver.switch_to.window(aba_lixo)
                            self.driver.close()
                        self.driver.switch_to.window(janela_princ)
            self.driver.get(dashboard_url)

        links_setores = {
            "Material Impresso": {"xpath": "//a[contains(@href, 'setor=1')]", "cat_id": "1"},
            "Slides": {"xpath": "//a[contains(@href, 'setor=2')]", "cat_id": "4"},
            "Atividades": {"xpath": "//a[contains(@href, 'setor=4')]", "cat_id": "3"},
        }
        for nome, info in links_setores.items():
            elems = self.driver.find_elements(By.XPATH, info["xpath"])
            if elems:
                try:
                    self.driver.get(elems[0].get_attribute("href"))
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
                                        "url_ver": urljoin(self.driver.current_url, a_tag["href"]),
                                        "categoria_id": info["cat_id"],
                                        "nome_categoria": nome,
                                    }
                                )
                                break
                    lote_setor.reverse()
                    self.fila_arquivos.extend(lote_setor)
                except Exception as e:
                    self.registrar_falha_caixa_preta("_varrer_tudo_sincrono (Loop Materiais)", e)
                self.driver.get(dashboard_url)

    def _criar_modulo_no_site_novo(self, wait, nome_modulo, curso, professor):
        self.log("INFO", f"A Criar Módulo na Plataforma Nova: {nome_modulo}")
        self.driver.get("https://novo.cursoms.com.br/modules/create")
        time.sleep(2)

        try:
            xpath_nome = "//input[@*[name()='wire:model']='module.name']"
            input_nome = wait.until(EC.presence_of_element_located((By.XPATH, xpath_nome)))
            self.preencher_input_humano(input_nome, nome_modulo)

            xpath_tempo = "//input[@*[name()='wire:model']='module.time']"
            input_tempo = wait.until(EC.presence_of_element_located((By.XPATH, xpath_tempo)))
            self.preencher_input(input_tempo, "0")

            if curso and str(curso).lower() != "nan":
                self._preencher_pesquisa_livewire(wait, "curso", str(curso))
            if professor and str(professor).lower() != "nan":
                self._preencher_pesquisa_livewire(wait, "professor", str(professor))

            botoes_salvar = self.driver.find_elements(
                By.XPATH,
                "//button[@type='submit' and contains(translate(text(), 'SALVAR', 'salvar'), 'salvar')]",
            )
            btn_salvar = next((b for b in botoes_salvar if b.is_displayed()), None)
            if btn_salvar:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", btn_salvar
                )
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", btn_salvar)
            else:
                self.driver.execute_script("document.querySelector('form').submit();")

            time.sleep(4)
        except Exception as e:
            self.registrar_falha_caixa_preta("_criar_modulo_no_site_novo", e)
            self.log("ERRO", f"Falha ao criar o módulo {nome_modulo}.")

    def _despejar_videos(self, modulo_nome):
        wait = WebDriverWait(self.driver, 10)
        for dados in list(self.fila_videos):
            if self.parar_loop:
                break
            vimeo_str = dados["vimeo"].strip()
            if not vimeo_str.isdigit() or len(vimeo_str) < 5:
                self.log("ERRO", f"VÍDEO INVÁLIDO: {dados['titulo']}")
                self.auditoria.append(
                    {
                        "Modulo": modulo_nome,
                        "Tipo": "Vídeo",
                        "Item": dados["titulo"],
                        "Status": "ERRO (ID Inválido)",
                    }
                )
                self.ordem_atual += 1
                self.fila_videos.pop(0)
                self.stats["v_erro"] += 1
                self.atualizar_progresso()
                continue

            try:
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "add_new_btn"))).click()
                time.sleep(1)
                campo_vimeo = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//input[@*[name()='wire:model']='lessons.vimeo_id']")
                    )
                )
                self.preencher_input(campo_vimeo, dados["vimeo"])
                campo_vimeo.send_keys(Keys.TAB)
                time.sleep(3.5)

                try:
                    wait.until(
                        lambda d: d.find_element(
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
                    dados["titulo"],
                )
                time.sleep(0.5)
                self.preencher_input(
                    self.driver.find_element(
                        By.XPATH, "//input[@*[name()='wire:model']='lessons.filename']"
                    ),
                    dados["titulo"],
                )
                time.sleep(0.5)
                self.driver.find_element(
                    By.XPATH, "//input[@*[name()='wire:model']='lessons.publish_date']"
                ).send_keys(datetime.now().strftime("%d%m%Y"))
                time.sleep(1)
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Salvar')]").click()
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "add_new_btn")))
                time.sleep(0.5)

                self.log("OK", f"Vídeo Subido: {dados['titulo'][:20]}...")
                self.auditoria.append(
                    {
                        "Modulo": modulo_nome,
                        "Tipo": "Vídeo",
                        "Item": dados["titulo"],
                        "Status": "Sucesso",
                    }
                )
                self.ordem_atual += 1
                self.fila_videos.pop(0)
                self.stats["v_sucesso"] += 1
                self.atualizar_progresso()
            except Exception as e:
                self.registrar_falha_caixa_preta(f"_despejar_videos ({dados['titulo']})", e)
                self.log("ERRO", f"Falha no vídeo {dados['titulo']}")
                self.auditoria.append(
                    {
                        "Modulo": modulo_nome,
                        "Tipo": "Vídeo",
                        "Item": dados["titulo"],
                        "Status": "ERRO",
                    }
                )
                self.ordem_atual += 1
                self.fila_videos.pop(0)
                self.stats["v_erro"] += 1
                self.atualizar_progresso()
                try:
                    self.driver.refresh()
                    time.sleep(3)
                except:
                    pass

    def _despejar_materiais(self, modulo_nome, aba_antiga, aba_nova):
        session = requests.Session()
        self.driver.switch_to.window(aba_antiga)
        for c in self.driver.get_cookies():
            session.cookies.set(c["name"], c["value"])
        self.driver.switch_to.window(aba_nova)
        wait = WebDriverWait(self.driver, 15)
        PASTA = "arquivos_migracao"
        if not os.path.exists(PASTA):
            os.makedirs(PASTA)

        for dados in list(self.fila_arquivos):
            if self.parar_loop:
                break
            try:
                self.driver.switch_to.window(aba_antiga)
                janelas_antes = set(self.driver.window_handles)
                self.driver.execute_script(f"window.open('{dados['url_ver']}', '_blank');")
                WebDriverWait(self.driver, 5).until(
                    lambda d: len(d.window_handles) > len(janelas_antes)
                )
                aba_temp = list(set(self.driver.window_handles) - janelas_antes)[0]
                self.driver.switch_to.window(aba_temp)

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
                link = soup.find("a", href=lambda h: h and any(ext in h.lower() for ext in exts))
                if not link:
                    link = soup.find(
                        "a", string=re.compile(r"baixar|download|arquivo|salvar", re.IGNORECASE)
                    )
                if not link:
                    raise Exception("Sem link de download")

                url_arq = urljoin("https://cursoms.com.br/ead/", link["href"].replace("../../", ""))
                nome_arq = re.sub(r'[\\/*?:"<>|]', "", dados["titulo"])[:60] + next(
                    (ext for ext in exts if ext in url_arq.lower()), ".pdf"
                )
                cam = os.path.abspath(os.path.join(PASTA, nome_arq))
                with open(cam, "wb") as f:
                    f.write(session.get(url_arq).content)
                self.driver.close()
                self.driver.switch_to.window(aba_nova)

                self.driver.get("https://novo.cursoms.com.br/attachments/create")
                time.sleep(1)
                f_input = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'input[wire\\:model="attachment.filename"]')
                    )
                )
                self.driver.execute_script(
                    "arguments[0].style.display='block'; arguments[0].style.visibility='visible';",
                    f_input,
                )
                f_input.send_keys(cam)
                input_n = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, 'input[wire\\:model="attachment.name"]')
                    )
                )
                self.preencher_input_humano(input_n, dados["titulo"][:65].strip())

                cat_val = dados.get("categoria_id", "1")
                self.driver.execute_script(
                    """
                    let cat = document.querySelector('select[wire\\\\:model="attachment.type"]'); let tip = document.querySelector('select[wire\\\\:model="attachment.attachable_type"]');
                    if(cat) { cat.value = arguments[0]; cat.dispatchEvent(new Event('change', { bubbles: true })); } if(tip) { tip.value = 'Module'; tip.dispatchEvent(new Event('change', { bubbles: true })); }
                """,
                    cat_val,
                )
                time.sleep(2.5)

                inputs = self.driver.find_elements(
                    By.XPATH, "//input[@type='text' and contains(@class, 'form-control')]"
                )
                for i in inputs:
                    if i.get_attribute("wire:model") == "attachment.name":
                        continue
                    if not i.get_attribute("value"):
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", i
                        )
                        time.sleep(0.5)
                        self.preencher_input_humano(i, modulo_nome)
                        time.sleep(4.5)
                        v_safe = modulo_nome.lower().replace("'", "")
                        xp = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}') and not(*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{v_safe}')])]"
                        for opcao in self.driver.find_elements(By.XPATH, xp):
                            if opcao.is_displayed() and opcao.tag_name.lower() not in [
                                "input",
                                "html",
                                "body",
                            ]:
                                try:
                                    ActionChains(self.driver).move_to_element(
                                        opcao
                                    ).click().perform()
                                except:
                                    self.driver.execute_script("arguments[0].click();", opcao)
                                break
                        break
                time.sleep(6)
                try:
                    botoes = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
                    clicou = False
                    for btn in botoes:
                        if btn.is_displayed():
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});", btn
                            )
                            time.sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", btn)
                            clicou = True
                            break
                    if not clicou:
                        self.driver.execute_script("Livewire.first().call('handleSubmit');")
                except:
                    pass

                time.sleep(5)
                self.driver.get("https://novo.cursoms.com.br/attachments")
                time.sleep(2)
                try:
                    os.remove(cam)
                except:
                    pass

                self.log("OK", f"Arquivo Subido: {dados['titulo'][:20]}...")
                self.auditoria.append(
                    {
                        "Modulo": modulo_nome,
                        "Tipo": "Material",
                        "Item": dados["titulo"],
                        "Status": "Sucesso",
                    }
                )
                self.fila_arquivos.pop(0)
                self.stats["a_sucesso"] += 1
                self.atualizar_progresso()
            except Exception as e:
                self.registrar_falha_caixa_preta(f"_despejar_materiais ({dados['titulo']})", e)
                self.log("ERRO", f"Arquivo {dados['titulo'][:20]}")
                self.auditoria.append(
                    {
                        "Modulo": modulo_nome,
                        "Tipo": "Material",
                        "Item": dados["titulo"],
                        "Status": "ERRO",
                    }
                )
                self.fila_arquivos.pop(0)
                self.stats["a_erro"] += 1
                self.atualizar_progresso()
                try:
                    janelas_atuais = self.driver.window_handles
                    for aba in janelas_atuais:
                        if aba != aba_antiga and aba != aba_nova:
                            self.driver.switch_to.window(aba)
                            self.driver.close()
                    self.driver.switch_to.window(aba_nova)
                except:
                    pass

    # =========================================================================
    # FASE 1: EXTRAÇÃO LENDO DO EXCEL
    # =========================================================================
    def iniciar_extracao_massa(self):
        if getattr(self, "is_running", False):
            return messagebox.showwarning("Aviso", "O robô já está a rodar!")
        if not self.driver:
            return messagebox.showwarning("Aviso", "Inicie o navegador e faça os logins primeiro!")
        if not self.lista_excel:
            return messagebox.showwarning("Aviso", "Carregue a planilha Excel primeiro!")

        self.parar_loop = False
        self.is_running = True
        threading.Thread(target=self._extracao_massa_thread).start()

    def _extracao_massa_thread(self):
        try:
            aba_antiga = None
            for aba in self.driver.window_handles:
                self.driver.switch_to.window(aba)
                if (
                    "cursoms.com.br" in self.driver.current_url
                    and "novo." not in self.driver.current_url
                ):
                    aba_antiga = aba
                    break

            if not aba_antiga:
                return self.log("ERRO", "Site antigo não encontrado.")

            self.driver.switch_to.window(aba_antiga)
            url_lista = self.driver.current_url
            self.memoria_lote = []
            self.ui_do(
                lambda: self.lbl_status_mod.configure(
                    text=f"FASE 1: Extraindo 0/{len(self.lista_excel)}", text_color="#F59E0B"
                )
            )

            for i, dados_linha in enumerate(self.lista_excel):
                if self.parar_loop:
                    break

                nome_modulo = str(
                    dados_linha.get(
                        "nome do módulo",
                        dados_linha.get(
                            "nome do modulo",
                            dados_linha.get("modulo", dados_linha.get("módulo", "")),
                        ),
                    )
                ).strip()
                if not nome_modulo or nome_modulo.lower() == "nan":
                    continue

                self.log("MODULO", f"EXTRAINDO: {nome_modulo}")
                self.driver.switch_to.window(aba_antiga)
                self.driver.get(url_lista)
                time.sleep(1)

                try:
                    wait = WebDriverWait(self.driver, 10)
                    tds = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "td.textointernos"))
                    )
                    btn_acessar_modulo = None
                    nome_lista_limpo = re.sub(r"[\d\W_]", "", str(nome_modulo).lower())

                    for td in tds:
                        texto_site_limpo = re.sub(r"[\d\W_]", "", str(td.text).lower())
                        if len(texto_site_limpo) > 5 and (
                            texto_site_limpo in nome_lista_limpo
                            or nome_lista_limpo in texto_site_limpo
                        ):
                            btn_acessar_modulo = td.find_element(
                                By.XPATH, "./preceding-sibling::td//a"
                            )
                            break

                    if btn_acessar_modulo:
                        self.driver.execute_script("arguments[0].click();", btn_acessar_modulo)
                        try:
                            btn_aula = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, "//a[contains(@href, 'aula.asp')]")
                                )
                            )
                            self.driver.execute_script("arguments[0].click();", btn_aula)
                        except:
                            pass

                        self._varrer_tudo_sincrono(aba_antiga)
                        self.log(
                            "INFO",
                            f"Guardado: {len(self.fila_videos)} vídeos e {len(self.fila_arquivos)} materiais.",
                        )
                    else:
                        self.log(
                            "ERRO", f"Módulo não encontrado no antigo. (Será criado vazio no novo)"
                        )
                except Exception as e:
                    self.registrar_falha_caixa_preta(f"_extracao_massa_thread ({nome_modulo})", e)
                    self.log("ERRO", f"Falha ao ler {nome_modulo}")

                # Guarda SEMPRE em memória (mesmo vazio), para poder Criar na Fase 2
                self.memoria_lote.append(
                    {
                        "dados_excel": dados_linha,
                        "nome_modulo": nome_modulo,
                        "videos": list(self.fila_videos),
                        "arquivos": list(self.fila_arquivos),
                    }
                )

                try:
                    with open("backup_extracao.json", "w", encoding="utf-8") as f:
                        json.dump(self.memoria_lote, f, indent=4, ensure_ascii=False)
                except Exception:
                    pass

                pct = (i + 1) / len(self.lista_excel)
                self.ui_do(lambda: self.progress_bar.set(pct))
                self.ui_do(
                    lambda: self.lbl_memoria.configure(
                        text=f"Memória: {len(self.memoria_lote)} Módulos"
                    )
                )
                self.ui_do(
                    lambda: self.lbl_status_mod.configure(
                        text=f"FASE 1: Extraindo {i+1}/{len(self.lista_excel)}"
                    )
                )

            if not self.parar_loop:
                self.log("MODULO", "✅ EXTRAÇÃO CONCLUÍDA! Pronto para Injetar.")
                winsound.Beep(1000, 300)

        except Exception as e:
            self.registrar_falha_caixa_preta("_extracao_massa_thread (Geral)", e)
        finally:
            self.is_running = False

    # =========================================================================
    # FASE 2: CRIAÇÃO DO MÓDULO E INJEÇÃO (TUDO DE UMA VEZ)
    # =========================================================================
    def iniciar_injecao_massa(self):
        if getattr(self, "is_running", False):
            return messagebox.showwarning("Aviso", "O robô já está a rodar!")
        if not self.memoria_lote:
            return messagebox.showwarning(
                "Aviso", "A memória está vazia. Faça a Extração do Passo 1 primeiro!"
            )

        self.parar_loop = False
        self.is_running = True
        threading.Thread(target=self._injecao_massa_thread).start()

    def _injecao_massa_thread(self):
        try:
            aba_nova = None
            aba_antiga = self.driver.window_handles[0]
            for aba in self.driver.window_handles:
                self.driver.switch_to.window(aba)
                if "novo.cursoms" in self.driver.current_url:
                    aba_nova = aba
                    break

            if not aba_nova:
                return self.log("ERRO", "Site novo não encontrado. Faça o login.")

            self.ui_do(
                lambda: self.lbl_status_mod.configure(
                    text=f"FASE 2: Criando/Injetando 0/{len(self.memoria_lote)}",
                    text_color=VERMELHO_PARAR,
                )
            )
            self.auditoria = []

            for i, dados_memoria in enumerate(self.memoria_lote):
                if self.parar_loop:
                    break

                nome_modulo = dados_memoria["nome_modulo"]
                self.fila_videos = list(dados_memoria["videos"])
                self.fila_arquivos = list(dados_memoria["arquivos"])
                self.ordem_atual = 1
                dados_excel = dados_memoria.get("dados_excel", {})
                curso = str(dados_excel.get("curso", "")).strip()
                professor = str(
                    dados_excel.get("professor", dados_excel.get("professor(a)", ""))
                ).strip()

                self.log("MODULO", f"INJETANDO LOTE: {nome_modulo}")
                self.driver.switch_to.window(aba_nova)
                wait_nova = WebDriverWait(self.driver, 15)

                # 1. CRIA O MÓDULO DO ZERO LENDO OS DADOS DO EXCEL
                self._criar_modulo_no_site_novo(wait_nova, nome_modulo, curso, professor)

                # 2. SE TIVER ALGO PARA INJETAR, PROCURA-O E INJETA
                if self.fila_videos or self.fila_arquivos:
                    try:
                        self.driver.get("https://novo.cursoms.com.br/modules")
                        time.sleep(2)
                        search_input = wait_nova.until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//input[@type='text' and contains(@class, 'form-control')]",
                                )
                            )
                        )
                        self.preencher_input(search_input, nome_modulo)
                        time.sleep(4)

                        modulos_h6 = self.driver.find_elements(By.TAG_NAME, "h6")
                        url_aulas = None
                        nome_limpo = " ".join(nome_modulo.lower().split())
                        for h6 in modulos_h6:
                            texto_h6 = " ".join(h6.text.lower().split())
                            if nome_limpo in texto_h6 or texto_h6 in nome_limpo:
                                tr = h6.find_element(By.XPATH, "./ancestor::tr")
                                btn_aulas = tr.find_element(
                                    By.XPATH, ".//a[contains(@href, '/lessons/')]"
                                )
                                url_aulas = btn_aulas.get_attribute("href")
                                break

                        if url_aulas:
                            if self.fila_videos:
                                self.driver.get(url_aulas)
                                time.sleep(2)
                                self._despejar_videos(nome_modulo)
                            if self.fila_arquivos:
                                self._despejar_materiais(nome_modulo, aba_antiga, aba_nova)
                        else:
                            self.log("ERRO", "Módulo não encontrado no painel após criação.")
                            self.auditoria.append(
                                {
                                    "Modulo": nome_modulo,
                                    "Tipo": "Geral",
                                    "Item": "Módulo",
                                    "Status": "ERRO (Não encontrado para injeção)",
                                }
                            )
                    except Exception as e:
                        self.registrar_falha_caixa_preta(
                            f"_injecao_massa_thread (Injeção de {nome_modulo})", e
                        )
                        self.log("ERRO", f"Erro ao injetar conteúdo.")

                pct = (i + 1) / len(self.memoria_lote)
                self.ui_do(lambda: self.progress_bar.set(pct))
                self.ui_do(
                    lambda: self.lbl_status_mod.configure(
                        text=f"FASE 2: Concluído {i+1}/{len(self.memoria_lote)}"
                    )
                )

            if not self.parar_loop:
                self.log("MODULO", "🎉 PROCESSO FINALIZADO! Todos os módulos criados e migrados.")
                winsound.Beep(1200, 300)
                time.sleep(0.1)
                winsound.Beep(1200, 300)
            self.gerar_relatorio_csv()

        except Exception as e:
            self.registrar_falha_caixa_preta("_injecao_massa_thread (Geral)", e)
        finally:
            self.is_running = False


if __name__ == "__main__":
    app_login = AppPrincipal()
    app_login.mainloop()
