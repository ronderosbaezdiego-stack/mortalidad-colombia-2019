# app.py
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
import os

# ---------------------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------------------
ANEXO1 = "data/Anexo1.NoFetal2019_CE_15-03-23.xlsx"
ANEXO2 = "data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx"
DIVIPOLA = "data/Divipola_CE_.xlsx"

try:
    df_mortalidad = pd.read_excel(ANEXO1)
    df_codigos = pd.read_excel(ANEXO2, header=0)
    df_divipola = pd.read_excel(DIVIPOLA)
except FileNotFoundError as e:
    raise FileNotFoundError(
        f"⚠️ No se encontró uno de los archivos. "
        f"Asegúrate de que los tres estén en la carpeta /data del repositorio. \n{e}"
    )

# ---------------------------------------------------------------------
# LIMPIEZA DE COLUMNAS EN df_codigos
# ---------------------------------------------------------------------
df_codigos.columns = df_codigos.columns.str.strip()
df_codigos.columns = df_codigos.columns.str.replace('\s+', ' ', regex=True)
df_codigos.columns = df_codigos.columns.str.lower()
df_codigos.columns = df_codigos.columns.str.normalize('NFKD')\
                                     .str.encode('ascii', errors='ignore')\
                                     .str.decode('utf-8')

df_codigos.rename(columns={
    'codigo de la cie-10 tres caracteres': 'cod_cie3',
    'descripcion de codigos mortalidad a tres caracteres': 'causa_muerte'
}, inplace=True)

# ---------------------------------------------------------------------
# UNIÓN DE DATOS
# ---------------------------------------------------------------------
df = df_mortalidad.merge(
    df_divipola[["COD_DEPARTAMENTO", "DEPARTAMENTO", "COD_MUNICIPIO", "MUNICIPIO"]],
    on=["COD_DEPARTAMENTO", "COD_MUNICIPIO"],
    how="left"
)

df = df.merge(
    df_codigos[["cod_cie3", "causa_muerte"]],
    left_on="COD_MUERTE",
    right_on="cod_cie3",
    how="left"
)

df.rename(columns={"causa_muerte": "CAUSA_MUERTE"}, inplace=True)

# ---------------------------------------------------------------------
# 1️⃣ MAPA: Total de muertes por departamento
# ---------------------------------------------------------------------
mapa_data = df.groupby("DEPARTAMENTO")["COD_DANE"].count().reset_index()
mapa_data.rename(columns={"COD_DANE": "TOTAL_MUERTES"}, inplace=True)

mapa = px.choropleth(
    mapa_data,
    locations="DEPARTAMENTO",
    locationmode="geojson-id",
    color="TOTAL_MUERTES",
    hover_name="DEPARTAMENTO",
    color_continuous_scale="Reds",
    title="Distribución total de muertes por departamento (2019)"
)

# ---------------------------------------------------------------------
# 2️⃣ GRÁFICO DE LÍNEAS: Muertes por mes
# ---------------------------------------------------------------------
linea_data = df.groupby("MES")["COD_DANE"].count().reset_index()
fig_lineas = px.line(
    linea_data,
    x="MES",
    y="COD_DANE",
    markers=True,
    title="Muertes por mes en Colombia (2019)",
    labels={"MES": "Mes", "COD_DANE": "Total de muertes"}
)

# ---------------------------------------------------------------------
# 3️⃣ GRÁFICO DE BARRAS: 5 ciudades más violentas (homicidios)
# ---------------------------------------------------------------------
homicidios_codigos = ["X95", "X93", "X94"]  # disparo, agresión, no especificado
violentas = df[df["COD_MUERTE"].isin(homicidios_codigos)]
ciudades_violentas = (
    violentas.groupby("MUNICIPIO")["COD_DANE"].count()
    .reset_index()
    .rename(columns={"COD_DANE": "TOTAL"})
    .sort_values(by="TOTAL", ascending=False)
    .head(5)
)
fig_barras = px.bar(
    ciudades_violentas,
    x="MUNICIPIO",
    y="TOTAL",
    title="5 ciudades más violentas de Colombia (2019)",
    color="TOTAL"
)

# ---------------------------------------------------------------------
# INTERFAZ DASH
# ---------------------------------------------------------------------
app = dash.Dash(__name__)
server = app.server  # necesario para Render

app.layout = html.Div([
    html.H1("Análisis de Mortalidad en Colombia - 2019", style={'textAlign': 'center'}),

    html.H2("1️⃣ Mapa de mortalidad por departamento"),
    dcc.Graph(figure=mapa),

    html.H2("2️⃣ Variación mensual de muertes"),
    dcc.Graph(figure=fig_lineas),

    html.H2("3️⃣ Ciudades más violentas"),
    dcc.Graph(figure=fig_barras),
])

# ---------------------------------------------------------------------
# EJECUCIÓN LOCAL / RENDER
# ---------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)
