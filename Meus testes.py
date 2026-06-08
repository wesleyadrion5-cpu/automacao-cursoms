# * =============================================================================
# * ROBÔ HÍBRIDO V95 - MULTI-PLANILHAS + BANNER INTELIGENTE
# * =============================================================================

import csv
import json
import os
import queue
import re
import sqlite3
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
        self.driver = None
        self.fila_videos = []
        self.fila_arquivos = []
        self.ordem_atual = 1

    def log(self, tipo, msg):
        self.motor.log(tipo, f"[Robô {self.worker_id}] {msg}")

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
            time.sleep(3.5)
            xpath_lista = f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{nome_label.lower()}')]/following::ul[contains(@class, 'list-group')][1]/li"
            item_lista = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_lista)))
            self.driver.execute_script("arguments[0].click();", item_lista)
            time.sleep(0.5)
        except Exception:
            self.log("ERRO", f"Pesquisa de '{texto_pesquisa}' falhou.")

    def run(self):
        try:
            self.log("INFO", f"Ligando motores para o arquivo '{self.nome_arquivo}'...")

            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            self.driver.maximize_window()
            wait = WebDriverWait(self.driver, 15)

            # * --- LOGIN ANTIGO ---
            self.driver.get(self.motor.config["antigo_url"])
            wait.until(EC.element_to_be_clickable((By.NAME, "logindagestao"))).send_keys(
                self.motor.config["antigo_user"]
            )
            self.driver.find_element(By.NAME, "senhadagestao").send_keys(
                self.motor.config["antigo_pass"]
            )
            self.driver.find_element(By.XPATH, "//input[@value='Entrar']").click()
            aba_antiga = self.driver.current_window_handle

            # * --- LOGIN NOVO ---
            self.driver.execute_script(f"window.open('{self.motor.config['novo_url']}');")
            aba_nova = self.driver.window_handles[-1]
            self.driver.switch_to.window(aba_nova)
            wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(
                self.motor.config["novo_user"]
            )
            pwd = self.driver.find_element(By.NAME, "password")
            pwd.send_keys(self.motor.config["novo_pass"])
            pwd.send_keys(Keys.ENTER)
            time.sleep(3)

            self.driver.switch_to.window(aba_antiga)

            # ! INJEÇÃO DE JAVASCRIPT: BANNER INTELIGENTE (NÃO BLOQUEIA MAIS A TELA)
            script_banner = f"""
                document.title = '🤖 R{self.worker_id} - ' + document.title;
                let d = document.createElement('div');
                d.innerHTML = '<h3 style="margin:0; font-family:sans-serif; font-size: 16px;">🤖 SOU O ROBÔ {self.worker_id} | Planilha: {self.nome_arquivo}</h3>';
                d.style.cssText = 'position:relative; width:100%; background:#4F46E5; color:white; text-align:center; z-index:999999; padding:8px; border-bottom:4px solid #F59E0B; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);';
                document.body.prepend(d);
            """
            self.driver.execute_script(script_banner)

            self.log(
                "MODULO",
                f"Logins concluídos! Vá ao Chrome do Robô {self.worker_id}, abra o Curso desejado e aguarde.",
            )

            # ! PAUSA ESTRATÉGICA
            self.motor.evento_inicio_trabalho.wait()

            if self.motor.parar_loop:
                return

            self.driver.switch_to.window(aba_antiga)
            url_lista_antiga = self.driver.current_url

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
                self.fila_videos.clear()
                self.fila_arquivos.clear()
                self.ordem_atual = 1
                status_final = "Sucesso"

                # * --- 1. EXTRAÇÃO ---
                self.driver.switch_to.window(aba_antiga)
                self.driver.get(url_lista_antiga)
                time.sleep(1)
                try:
                    tds = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "td.textointernos"))
                    )
                    btn_acessar = None
                    nome_limpo = re.sub(r"[\d\W_]", "", str(nome_modulo).lower())
                    for td in tds:
                        txt_limpo = re.sub(r"[\d\W_]", "", str(td.text).lower())
                        if len(txt_limpo) > 5 and (
                            txt_limpo in nome_limpo or nome_limpo in txt_limpo
                        ):
                            btn_acessar = td.find_element(By.XPATH, "./preceding-sibling::td//a")
                            break

                    if btn_acessar:
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
                        self.log("ERRO", f"Módulo antigo não encontrado. Criando vazio.")
                        status_final = "Criado Vazio"
                except Exception as e:
                    self.log("ERRO", f"Falha ao ler {nome_modulo}")
                    status_final = "Erro Extração"

                # * --- 2. CRIAR MÓDULO ---
                self.driver.switch_to.window(aba_nova)
                self.driver.get("https://novo.cursoms.com.br/modules/create")
                time.sleep(2)
                try:
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
                    if curso and curso.lower() != "nan":
                        self._preencher_pesquisa_livewire(wait, "curso", curso)
                    if professor and professor.lower() != "nan":
                        self._preencher_pesquisa_livewire(wait, "professor", professor)

                    botoes = self.driver.find_elements(
                        By.XPATH,
                        "//button[@type='submit' and contains(translate(text(), 'SALVAR', 'salvar'), 'salvar')]",
                    )
                    btn_salvar = next((b for b in botoes if b.is_displayed()), None)
                    if btn_salvar:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", btn_salvar
                        )
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", btn_salvar)
                    else:
                        self.driver.execute_script("document.querySelector('form').submit();")
                    time.sleep(4)
                except Exception:
                    self.log("ERRO", f"Falha ao criar o módulo no site novo.")
                    status_final = "Erro Criação"

                # * --- 3. INJETAR CONTEÚDO ---
                if self.fila_videos or self.fila_arquivos:
                    self.driver.get("https://novo.cursoms.com.br/modules")
                    time.sleep(2)
                    try:
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
                        n_limpo = " ".join(nome_modulo.lower().split())
                        for h6 in self.driver.find_elements(By.TAG_NAME, "h6"):
                            t_h6 = " ".join(h6.text.lower().split())
                            if n_limpo in t_h6 or t_h6 in n_limpo:
                                tr = h6.find_element(By.XPATH, "./ancestor::tr")
                                url_aulas = tr.find_element(
                                    By.XPATH, ".//a[contains(@href, '/lessons/')]"
                                ).get_attribute("href")
                                break

                        if url_aulas:
                            if self.fila_videos:
                                self.driver.get(url_aulas)
                                time.sleep(2)
                                self._injetar_videos(wait, nome_modulo)
                            if self.fila_arquivos:
                                self._injetar_materiais(wait, nome_modulo, aba_antiga, aba_nova)
                        else:
                            self.log("ERRO", "Módulo não encontrado no painel após criação.")
                            status_final = "Erro Injeção (Não Achou)"
                    except Exception:
                        self.log("ERRO", "Falha na etapa de injeção.")
                        status_final = "Erro Injeção"

                # * --- REGISTAR NO BD ---
                self.motor.salvar_no_banco(nome_modulo, curso, professor, status_final)
                self.motor.registrar_conclusao_modulo()

        except Exception as e:
            self.motor.registrar_falha_caixa_preta(f"Frota {self.worker_id}", e)
            self.log("ERRO", f"Falha crítica no worker {self.worker_id}.")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.motor.registrar_fim_worker(self.worker_id)

    # * =========================================================================
    # * FUNÇÕES DE AUXÍLIO
    # * =========================================================================
    def _extrair_dados_ativos(self):
        d_url = self.driver.current_url
        if self.driver.find_elements(By.XPATH, "//a[contains(@href, 'videos.asp')]"):
            self.driver.get(
                self.driver.find_elements(By.XPATH, "//a[contains(@href, 'videos.asp')]")[
                    0
                ].get_attribute("href")
            )
            time.sleep(2)
            self._expandir_jplist()

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
                                for p in " ".join(et.get_attribute("value").strip().split())
                                .lower()
                                .split()
                            ]
                        )
                        vim = self.driver.find_element(By.ID, "vimeo").get_attribute("value")
                        self.fila_videos.append({"titulo": tit, "vimeo": vim})
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
                    self.driver.get(els[0].get_attribute("href"))
                    time.sleep(2)
                    self._expandir_jplist()
                    sp = BeautifulSoup(self.driver.page_source, "html.parser")
                    ls = []
                    for it in sp.find_all("div", class_="list-item box"):
                        t = (
                            it.find("td", class_="subject").text.strip()
                            if it.find("td", class_="subject")
                            else "Sem Titulo"
                        )
                        for a in it.find_all("a", href=True):
                            if "arquivoid.asp" in a["href"].lower():
                                ls.append(
                                    {
                                        "titulo": t,
                                        "url_ver": urljoin(self.driver.current_url, a["href"]),
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

    def _expandir_jplist(self):
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

    def _injetar_videos(self, wait, m_nome):
        for d in list(self.fila_videos):
            if self.motor.parar_loop:
                break
            vs = d["vimeo"].strip()
            if not vs.isdigit() or len(vs) < 5:
                self.log("ERRO", f"Vídeo Inválido: {d['titulo']}")
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Vídeo", "Item": d["titulo"], "Status": "ERRO"}
                )
                self.ordem_atual += 1
                continue
            try:
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "add_new_btn"))).click()
                time.sleep(1)
                cv = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//input[@*[name()='wire:model']='lessons.vimeo_id']")
                    )
                )
                self.preencher_input(cv, d["vimeo"])
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
                self.log("OK", f"Vídeo Subido: {d['titulo'][:15]}...")
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Vídeo", "Item": d["titulo"], "Status": "Sucesso"}
                )
                self.ordem_atual += 1
            except Exception:
                self.log("ERRO", f"Falha no vídeo {d['titulo'][:15]}")
                self.motor.auditoria.append(
                    {"Modulo": m_nome, "Tipo": "Vídeo", "Item": d["titulo"], "Status": "ERRO"}
                )
                self.ordem_atual += 1
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
                lk = bs.find("a", href=lambda h: h and any(ext in h.lower() for ext in exts))
                if not lk:
                    lk = bs.find(
                        "a", string=re.compile(r"baixar|download|arquivo|salvar", re.IGNORECASE)
                    )
                if not lk:
                    raise Exception("Sem link")
                u_arq = urljoin("https://cursoms.com.br/ead/", lk["href"].replace("../../", ""))
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
# * APP LOGIN E MOTOR (CONSTRUÇÃO DA INTERFACE)
# * =========================================================================
class AppPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Robô Híbrido V95 Login")
        self.geometry("450x650")
        self.configure(fg_color=BG_WINDOW)

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        pos_x = (largura_tela // 2) - (450 // 2)
        pos_y = (altura_tela // 2) - (650 // 2)
        self.geometry(f"450x650+{pos_x}+{pos_y}")
        self.attributes("-topmost", True)
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

        fu = ctk.CTkFrame(self.card, fg_color="transparent")
        fu.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(fu, text="Usuário", font=("Inter", 12, "bold"), text_color=TEXT_MUTED).pack(
            anchor="w", padx=5
        )
        self.ent_user = ctk.CTkEntry(
            fu,
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
            fg_color=BG_INPUT,
            border_color=BORDER_COLOR,
            text_color=TEXT_LIGHT,
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
            hover_color=BG_CARD,
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
        self.title("Robô Híbrido V95 - Enterprise Multi-Tasks")
        self.geometry("1100x800")
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

        self.inicializar_banco_dados()
        self.setup_ui()
        self.ativar_atalhos()
        self.processar_fila_gui()

    def inicializar_banco_dados(self):
        try:
            conn = sqlite3.connect("banco_frota.db")
            cursor = conn.cursor()
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS historico_modulos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_modulo TEXT, curso TEXT, professor TEXT, status TEXT, data_hora TEXT)"""
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Erro SQLite: {e}")

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

    def registrar_falha_caixa_preta(self, local_erro, excecao):
        try:
            with open("erro_log.txt", "a", encoding="utf-8") as f:
                f.write(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ERRO EM: {local_erro}\nMENSAGEM: {str(excecao)}\nRASTREAMENTO:\n{traceback.format_exc()}\n"
                    + "-" * 60
                    + "\n"
                )
        except:
            pass

    # * IA GEMINI
    def abrir_assistente_ia(self):
        self.tela_ia = ctk.CTkToplevel(self.root)
        self.tela_ia.title("🧠 Oráculo IA")
        self.tela_ia.geometry("600x700")
        self.tela_ia.configure(fg_color=BG_WINDOW)
        self.tela_ia.attributes("-topmost", True)
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
        self.txt_chat.insert("end", "🤖 Gemini Pro: Olá, Wesley!\n\n")
        self.txt_chat.configure(state="disabled")
        frame_baixo = ctk.CTkFrame(self.tela_ia, fg_color="transparent")
        frame_baixo.pack(fill="x", padx=20, pady=15)
        self.ent_pergunta = ctk.CTkEntry(
            frame_baixo, placeholder_text="Pergunte ao Gemini...", height=40, fg_color=BG_CARD
        )
        self.ent_pergunta.pack(side="left", fill="x", expand=True, padx=(0, 10))
        btn_enviar = ctk.CTkButton(
            frame_baixo,
            text="Enviar",
            width=80,
            height=40,
            fg_color=ROXO_IA,
            command=self.enviar_pergunta_gemini,
        )
        btn_enviar.pack(side="right")
        ctk.CTkButton(
            self.tela_ia,
            text="🔍 Analisar Último Erro do Robô",
            fg_color=VERDE_ACAO,
            height=40,
            command=self.pedir_gemini_analisar_erro,
        ).pack(fill="x", padx=20, pady=(0, 20))

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
            with open("erro_log.txt", "r", encoding="utf-8") as f:
                logs = f.readlines()
            ultimo_erro = "".join(logs[-15:])
            if not ultimo_erro.strip():
                return
            self.atualizar_chat_ia("Por favor, analisa o último erro da frota.", autor="👤 Você: ")
            self.chamar_api_gemini(
                f"Lê o erro do meu script de automação Python e explica-me:\n\n{ultimo_erro}"
            )
        except:
            messagebox.showerror("Erro", "Log não encontrado")

    def chamar_api_gemini(self, prompt):
        self.atualizar_chat_ia("Pensando...", autor="🤖 Gemini: ")

        def _thread_ia():
            try:
                client = genai.Client(api_key=CHAVE_GEMINI)
                response = client.models.generate_content(model="gemini-1.5-pro", contents=prompt)
                self.ui_do(lambda: self._substituir_pensando(response.text))
            except Exception as e:
                self.ui_do(lambda: self._substituir_pensando(f"Erro: {str(e)}"))

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

    def setup_ui(self):
        self.root.configure(fg_color=BG_WINDOW)
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        top_layout = ctk.CTkFrame(main_container, fg_color="transparent")
        top_layout.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(
            top_layout,
            width=280,
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
            text="AUTOMAÇÃO INDUSTRIAL + DB",
            font=("Inter", 10, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 10))

        frota_frame = ctk.CTkFrame(
            sidebar, fg_color="#1E1B4B", border_width=1, border_color="#4338CA", corner_radius=8
        )
        frota_frame.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(
            frota_frame, text="🏭 STATUS DA FROTA", font=("Inter", 12, "bold"), text_color="#A5B4FC"
        ).pack(pady=(10, 5))
        self.lbl_workers = ctk.CTkLabel(
            frota_frame, text="0 Robôs Carregados", font=("Inter", 13, "bold"), text_color="#FFFFFF"
        )
        self.lbl_workers.pack(pady=(0, 15))

        self.btn_ia = ctk.CTkButton(
            sidebar,
            text="🧠 Oráculo IA",
            font=("Inter", 13, "bold"),
            fg_color=ROXO_IA,
            height=50,
            command=self.abrir_assistente_ia,
        )
        self.btn_ia.pack(fill="x", padx=15, pady=8)

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
            text="📊 Base de Dados (Selecionar Múltiplas Planilhas)",
            font=("Inter", 16, "bold"),
            text_color="#FFFFFF",
        ).pack(side="left")

        area_excel = ctk.CTkFrame(
            content, fg_color=BG_INPUT, border_color=BORDER_COLOR, border_width=1, corner_radius=8
        )
        area_excel.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            area_excel,
            text="Selecione 1 Excel para abrir 1 Robô. Segure a tecla CTRL para selecionar\n2 ou mais arquivos de Excel e abrir múltiplos robôs ao mesmo tempo!",
            font=("Inter", 13),
            text_color="#F59E0B",
        ).pack(pady=(30, 15))

        ctk.CTkButton(
            area_excel,
            text="📂 CARREGAR PLANILHA(S) .XLSX",
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
            text="1️⃣ PREPARAR FROTA (ABRIR NAVEGADORES)",
            font=("Inter", 14, "bold"),
            fg_color="#0EA5E9",
            hover_color="#0284C7",
            height=50,
            command=self.preparar_frota,
        )
        self.btn_preparar.pack(fill="x", pady=(0, 10))
        self.btn_iniciar = ctk.CTkButton(
            actions_frame,
            text="2️⃣ INICIAR INJEÇÃO (COMEÇAR TRABALHO)",
            font=("Inter", 14, "bold"),
            fg_color="#4F46E5",
            hover_color="#4338CA",
            height=50,
            state="disabled",
            command=self.iniciar_trabalho,
        )
        self.btn_iniciar.pack(fill="x")

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
            width=80,
            height=30,
            command=self.parar_tudo,
        ).pack(side="right")

        self.txt_log = ctk.CTkTextbox(
            bottom_area, font=("Consolas", 12), fg_color="transparent", text_color="#E2E8F0"
        )
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.config_tags_log(self.txt_log)
        self.txt_log.configure(state="disabled")
        self.log("INFO", "Sistema V95 iniciado.")

    def ativar_atalhos(self):
        keyboard.add_hotkey("f12", self.parar_tudo)

    def parar_tudo(self):
        self.parar_loop = True
        self.evento_inicio_trabalho.set()
        self.log("ERRO", "PARADA DE EMERGÊNCIA SOLICITADA. Fechando tudo...")

    def carregar_excel(self):
        arquivos = filedialog.askopenfilenames(
            filetypes=[("Excel files", "*.xlsx")],
            title="Selecione 1 ou mais planilhas (Segure CTRL)",
        )
        if arquivos:
            try:
                self.lista_de_planilhas = []
                self.total_modulos = 0
                for arq in arquivos:
                    df = pd.read_excel(arq)
                    df.columns = df.columns.astype(str).str.strip().str.lower()
                    records = df.to_dict("records")
                    nome_arquivo = os.path.basename(arq)
                    self.lista_de_planilhas.append({"nome": nome_arquivo, "dados": records})
                    self.total_modulos += len(records)

                self.lbl_status_excel.configure(
                    text=f"✅ {len(arquivos)} Arquivo(s) Carregado(s)! ({self.total_modulos} módulos no total)",
                    text_color=VERDE_ACAO,
                )
                self.lbl_workers.configure(text=f"{len(arquivos)} Robô(s) Carregado(s)")
                self.log("INFO", f"{len(arquivos)} Planilha(s) carregada(s) com sucesso.")
            except Exception as e:
                messagebox.showerror("Erro", f"Planilha inválida: {e}")

    def preparar_frota(self):
        if getattr(self, "is_running", False):
            return messagebox.showwarning("Aviso", "A frota já está em operação!")
        if not self.lista_de_planilhas:
            return messagebox.showwarning("Aviso", "Carregue a(s) planilha(s) primeiro!")

        self.parar_loop = False
        self.is_running = True
        self.modulos_concluidos = 0
        self.workers_ativos = len(self.lista_de_planilhas)
        self.auditoria = []

        self.evento_inicio_trabalho.clear()
        self.log("INFO", f"⚙️ Preparando {self.workers_ativos} robôs independentes...")

        # ! MODIFICAÇÃO: ARRANQUE FASEADO PARA EVITAR TRAVAMENTOS NO WINDOWS
        for i, plan in enumerate(self.lista_de_planilhas):
            worker = FrotaWorker(self, i + 1, plan["dados"], plan["nome"])
            worker.start()
            if i < len(self.lista_de_planilhas) - 1:
                time.sleep(
                    1.5
                )  # Pausa dramática de 1.5s para o Windows respirar entre um Chrome e outro!

        self.btn_preparar.configure(state="disabled")
        self.btn_iniciar.configure(state="normal")

    def iniciar_trabalho(self):
        self.log(
            "INFO", "🚀 SINAL VERDE! Todos os robôs começaram a trabalhar na sua área designada."
        )
        self.btn_iniciar.configure(state="disabled")
        self.evento_inicio_trabalho.set()

    def registrar_conclusao_modulo(self):
        with self.progresso_lock:
            self.modulos_concluidos += 1
            pct = self.modulos_concluidos / self.total_modulos if self.total_modulos > 0 else 0
            self.ui_do(lambda: self.progress_bar.set(pct))
            self.ui_do(
                lambda: self.lbl_status_mod.configure(
                    text=f"🏭 FROTA: Injetados {self.modulos_concluidos}/{self.total_modulos} Módulos"
                )
            )

    def registrar_fim_worker(self, worker_id):
        with self.progresso_lock:
            self.workers_ativos -= 1
            if self.workers_ativos <= 0:
                if not self.parar_loop:
                    self.log("MODULO", "🎉 MISSÃO CUMPRIDA! Todas as planilhas foram injetadas.")
                    winsound.Beep(1200, 300)
                    time.sleep(0.1)
                    winsound.Beep(1200, 300)
                self.gerar_relatorio_csv()
                self.is_running = False
                self.ui_do(lambda: self.btn_preparar.configure(state="normal"))

    def gerar_relatorio_csv(self):
        if not self.auditoria:
            return
        nome_arquivo = f"Relatorio_Frota_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.csv"
        try:
            with open(nome_arquivo, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Modulo", "Tipo (Vídeo/Material)", "Item", "Status"])
                for linha in self.auditoria:
                    writer.writerow(
                        [
                            linha.get("Modulo", ""),
                            linha.get("Tipo", ""),
                            linha.get("Item", ""),
                            linha.get("Status", ""),
                        ]
                    )
        except Exception as e:
            self.registrar_falha_caixa_preta("gerar_relatorio_csv", e)


if __name__ == "__main__":
    app = AppPrincipal()
    app.mainloop()
