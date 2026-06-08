import os
import re
import threading
import tkinter as tk
import unicodedata
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from docling.document_converter import DocumentConverter

# * ==========================================
# * FUNÇÕES AUXILIARES DE PROCESSAMENTO
# * ==========================================


def normalizar_texto(texto: str) -> str:
    """
    Normaliza o texto bruto para comparação (caixa alta, sem acentos, sem símbolos).
    """
    if not isinstance(texto, str):
        return ""

    try:
        texto = texto.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    texto = texto.upper()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    texto_limpo = re.sub(r"[^A-Z\s]", " ", texto)
    return " ".join(texto_limpo.split())


# * ==========================================
# * LÓGICA PRINCIPAL (DOCLING + CONTEXTO)
# * ==========================================


def processar_dados() -> None:
    btn_iniciar.config(state="disabled")

    path_pdf: str = filedialog.askopenfilename(
        title="Selecione o PDF do Concurso (Qualquer Banca/Diário)", filetypes=[("PDF", "*.pdf")]
    )
    if not path_pdf:
        btn_iniciar.config(state="normal")
        return

    path_excel: str = filedialog.askopenfilename(
        title="Selecione sua Lista de Alunos", filetypes=[("Excel/CSV", "*.xlsx *.csv")]
    )
    if not path_excel:
        btn_iniciar.config(state="normal")
        return

    def tarefa_pesada() -> None:
        try:
            # * --- 1. LER LISTA DE ALUNOS ---
            lbl_status.config(text="Carregando lista de alunos...")
            root.update()

            if path_excel.endswith(".csv"):
                try:
                    df_alunos = pd.read_csv(
                        path_excel, sep=";", encoding="utf-8", on_bad_lines="skip"
                    )
                except Exception:
                    df_alunos = pd.read_csv(
                        path_excel, sep=",", encoding="latin1", on_bad_lines="skip"
                    )
            else:
                df_alunos = pd.read_excel(path_excel)

            coluna_nome: str = df_alunos.columns[0]
            for col in df_alunos.columns:
                if "nome" in str(col).lower():
                    coluna_nome = col
                    break

            alunos_dict: dict = {}
            for nome_original in df_alunos[coluna_nome].dropna().astype(str):
                nome_limpo: str = normalizar_texto(nome_original)
                if len(nome_limpo) > 4:
                    alunos_dict[nome_limpo] = nome_original

            # ! --- 2. EXTRAÇÃO COM IA (DOCLING) ---
            lbl_status.config(text="Docling lendo o PDF (Extraindo Tabelas e Textos)...")
            progress.start(10)
            root.update()

            converter = DocumentConverter()
            resultado = converter.convert(path_pdf)

            # O Segredo Universal: Exportar como Markdown preserva tabelas e parágrafos!
            md_text: str = resultado.document.export_to_markdown()

            progress.stop()
            progress["value"] = 100

            # * --- 3. RADAR DE BUSCA E CONTEXTO ---
            lbl_status.config(text="Cruzando dados e extraindo Cargo/Notas...")
            root.update()

            linhas_md: list = md_text.split("\n")
            resultados_finais: list = []

            for nome_limpo, nome_original in alunos_dict.items():

                # Memória temporária para guardar o título/cargo acima do nome
                ultimo_bloco_texto: str = "Cargo/Vaga não identificado"

                for linha in linhas_md:
                    linha_original_limpa = linha.strip()
                    linha_busca = normalizar_texto(linha)

                    if not linha_original_limpa:
                        continue

                    # ? Se a linha NÃO for uma tabela (não tem '|'), possivelmente é um Cargo/Vaga
                    # Guardamos isso na memória. Quando acharmos o aluno, sabemos de qual cargo ele é.
                    if "|" not in linha_original_limpa and len(linha_busca) > 10:
                        # Limpa os '#' do Markdown para ficar legível
                        ultimo_bloco_texto = linha_original_limpa.replace("#", "").strip()

                    # * ACHOU O ALUNO!
                    if f" {nome_limpo} " in f" {linha_busca} " or nome_limpo in linha_busca:
                        resultados_finais.append(
                            {
                                "Aluno (Sua Lista)": nome_original,
                                "Contexto Acima (Possível Cargo/Vaga)": ultimo_bloco_texto,
                                "Linha Completa no PDF (Nota/Classificação/Cotas)": linha_original_limpa,
                            }
                        )
                        break  # Achou o aluno, vai para o próximo da lista

            # * --- 4. EXPORTAÇÃO ---
            if resultados_finais:
                df_final = pd.DataFrame(resultados_finais)
                saida: str = "Relatorio_Universal_Docling.xlsx"
                df_final.to_excel(saida, index=False)

                msg: str = (
                    f"VERIFICAÇÃO UNIVERSAL CONCLUÍDA!\n\n"
                    f"Alunos pesquisados: {len(alunos_dict)}\n"
                    f"Encontrados no PDF: {len(resultados_finais)}\n\n"
                    f"Arquivo salvo: {saida}"
                )
                messagebox.showinfo("Sucesso", msg)
                os.startfile(saida)
            else:
                messagebox.showwarning("Resultado", "Nenhum aluno foi encontrado neste PDF.")

        except Exception as e:
            progress.stop()
            messagebox.showerror("Erro Crítico", f"Detalhes: {str(e)}")

        finally:
            btn_iniciar.config(state="normal")
            lbl_status.config(text="Pronto para nova consulta.")
            progress["value"] = 0

    threading.Thread(target=tarefa_pesada).start()


# * ==========================================
# * INTERFACE GRÁFICA
# * ==========================================

root = tk.Tk()
root.title("Robô Docling Inteligente v9.0")
root.geometry("450x250")

tk.Label(root, text="Rastreador Universal (Com Contexto)", font=("Arial", 13, "bold")).pack(pady=10)
tk.Label(
    root, text="Extrai: Nome, Cargo e a Linha da Tabela (Notas/Cotas)", font=("Arial", 9)
).pack()

btn_iniciar = tk.Button(
    root,
    text="SELECIONAR ARQUIVOS",
    command=processar_dados,
    height=2,
    bg="#6200EA",
    fg="white",
    font=("Arial", 10, "bold"),
)
btn_iniciar.pack(pady=20)

progress = ttk.Progressbar(root, length=350, mode="indeterminate")
progress.pack(pady=5)

lbl_status = tk.Label(root, text="Aguardando...", fg="gray")
lbl_status.pack()

root.mainloop()
