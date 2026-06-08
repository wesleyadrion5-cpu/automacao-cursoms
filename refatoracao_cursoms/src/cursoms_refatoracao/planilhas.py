import os

import pandas as pd

from .matching import normalize_text


MODULE_COLUMNS = {
    "nome do modulo",
    "nome do modulo ",
    "nome do módulo",
    "modulo",
    "módulo",
}


def normalize_dataframe_columns(df):
    df.columns = [normalize_text(coluna) for coluna in df.columns]
    return df


def validate_dataframe(df, file_name):
    if df.empty:
        raise ValueError(f"A planilha '{file_name}' está vazia.")

    colunas = set(df.columns)
    if not colunas.intersection(MODULE_COLUMNS):
        raise ValueError(
            f"A planilha '{file_name}' não possui coluna de módulo. Use uma coluna como "
            "'Nome do Módulo' ou 'Módulo'."
        )


def load_excel_records(path):
    df = pd.read_excel(path)
    df = normalize_dataframe_columns(df)
    validate_dataframe(df, os.path.basename(path))
    registros = df.to_dict("records")
    return {
        "nome": os.path.basename(path),
        "dados": registros,
        "total": len(registros),
    }
