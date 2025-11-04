# app.py
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
import os

# ---------------------------------------------------------------------
# RUTAS DE ARCHIVOS
# ---------------------------------------------------------------------
ANEXO1 = "data/Anexo1.NoFetal2019_CE_15-03-23.xlsx"
DIVIPOLA = "data/Divipola_CE_.xlsx"

# ---------------------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------------------
try:
    # Leer solo columnas esenciales para agilizar carga
    df_mortalidad = pd.read_excel(
        ANEXO1,
        usecols=["COD_DANE", "COD_DEPARTAMENTO", "COD_MUNICIPIO", "MES"]
    )

    df_divipola = pd.read_excel(
        DIVIPOLA,
        usecols=["COD_DEPARTAMENTO", "DEPARTAMENTO"]
    )

except FileNotFoundError as e:
    raise FileNotFoundError(
        f"⚠️ No se encontró uno de los archivos en /data. \n{e}"
    )

# ---------------------------------------------------------------------
# UNIÓN DE DATOS
# ---------------------------------------------------------------------
df = df_mortalidad.merge(
    df_divipola,
    on="COD_DEPARTAMENTO",
    how="left"
)

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
# DASH APP
# ---------------------------------------------------------------------
app = dash.Dash(__name__)
server = app.server  # necesario para Render

app.layout = html.Div([
    html.H1("Análisis de Mortalidad en Colombia - 2019", style={'textAlign': 'center'}),

    html.H2("1️⃣ Mapa de mortalidad por departamento"),
    dcc.Graph(figure=mapa),

    html.H2("2️⃣ Variación mensual de muertes"),
    dcc.Graph(figure=fig_lineas),
])

# ---------------------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)
