# app.py
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
import os

# ---------------------------------------------------------------------
# CARGA DE DATOS OPTIMIZADA
# ---------------------------------------------------------------------
ANEXO1 = "data/Anexo1.NoFetal2019_CE_15-03-23.xlsx"
ANEXO2 = "data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx"
DIVIPOLA = "data/Divipola_CE_.xlsx"

try:
    # Leer solo columnas necesarias para mejorar velocidad
    cols_mortalidad = ["COD_DANE", "COD_DEPARTAMENTO", "COD_MUNICIPIO", "MES"]
    df_mortalidad = pd.read_excel(ANEXO1, usecols=cols_mortalidad)

    df_codigos = pd.read_excel(ANEXO2, header=0)

    cols_divipola = ["COD_DEPARTAMENTO", "DEPARTAMENTO"]
    df_divipola = pd.read_excel(DIVIPOLA, usecols=cols_divipola)

except FileNotFoundError as e:
    raise FileNotFoundError(
        f"⚠️ No se encontró uno de los archivos. "
        f"Asegúrate de que estén en la carpeta /data del repositorio. \n{e}"
    )

# -----------------------------------------------------
