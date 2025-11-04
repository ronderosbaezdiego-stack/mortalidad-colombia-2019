# app.py
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# ---------------------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------------------
# Se asume que los tres archivos están en la carpeta /data dentro del repo

ANEXO1 = "data/Anexo1.NoFetal2019_CE_15-03-23.xlsx"
ANEXO2 = "data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx"
DIVIPOLA = "data/Divipola_CE_.xlsx"

try:
    df_mortalidad = pd.read_excel(ANEXO1)
    df_codigos = pd.read_excel(ANEXO2)
    df_divipola = pd.read_excel(DIVIPOLA)
except FileNotFoundError as e:
    raise FileNotFoundError(
        f"⚠️ No se encontró uno de los archivos. "
        f"Asegúrate de que los tres estén en la carpeta /data del repositorio. \n{e}"
    )

# ---------------------------------------------------------------------
# LIMPIEZA Y UNIÓN DE DATOS
# ---------------------------------------------------------------------

# Combinar con Divipola para obtener nombres de departamentos y municipios
df = df_mortalidad.merge(
    df_divipola[["COD_DEPARTAMENTO", "DEPARTAMENTO", "COD_MUNICIPIO", "MUNICIPIO"]],
    on=["COD_DEPARTAMENTO", "COD_MUNICIPIO"],
    how="left"
)

# Agregar descripción de causa de muerte
df = df.merge(
    df_codigos[["Código de la CIE-10 tres caracteres", "Descripción  de códigos mortalidad a tres caracteres"]],
    left_on="COD_MUERTE",
    right_on="Código de la CIE-10 tres caracteres",
    how="left"
)

df.rename(columns={"Descripción  de códigos mortalidad a tres caracteres": "CAUSA_MUERTE"}, inplace=True)

# ---------------------------------------------------------------------
# MAPA: Total de muertes por departamento
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
# GRÁFICO DE LÍNEAS: muertes por mes
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
# GRÁFICO DE BARRAS: 5 ciudades más violentas (homicidios)
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
# GRÁFICO CIRCULAR: 10 ciudades con menor mortalidad
# ---------------------------------------------------------------------
ciudades_menor = (
    df.groupby("MUNICIPIO")["COD_DANE"].count()
    .reset_index()
    .rename(columns={"COD_DANE": "TOTAL"})
    .sort_values(by="TOTAL", ascending=True)
    .head(10)
)
fig_pie = px.pie(
    ciudades_menor,
    names="MUNICIPIO",
    values="TOTAL",
    title="10 ciudades con menor índice de mortalidad (2019)"
)

# ---------------------------------------------------------------------
# TABLA: 10 principales causas de muerte
# ---------------------------------------------------------------------
causas_top10 = (
    df.groupby(["COD_MUERTE", "CAUSA_MUERTE"])["COD_DANE"].count()
    .reset_index()
    .rename(columns={"COD_DANE": "TOTAL"})
    .sort_values(by="TOTAL", ascending=False)
    .head(10)
)

# ---------------------------------------------------------------------
# BARRAS APILADAS: muertes por sexo y departamento
# ---------------------------------------------------------------------
sexo_dep = (
    df.groupby(["DEPARTAMENTO", "SEXO"])["COD_DANE"].count()
    .reset_index()
    .rename(columns={"COD_DANE": "TOTAL"})
)
fig_apiladas = px.bar(
    sexo_dep,
    x="DEPARTAMENTO",
    y="TOTAL",
    color="SEXO",
    title="Muertes por sexo y departamento (2019)"
)

# ---------------------------------------------------------------------
# HISTOGRAMA: distribución por grupo de edad
# ---------------------------------------------------------------------
fig_hist = px.histogram(
    df,
    x="GRUPO_EDAD1",
    title="Distribución de muertes por grupo de edad (2019)",
    labels={"GRUPO_EDAD1": "Grupo de edad", "count": "Número de muertes"}
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

    html.H2("4️⃣ Ciudades con menor mortalidad"),
    dcc.Graph(figure=fig_pie),

    html.H2("5️⃣ Principales causas de muerte"),
    html.Table([
        html.Tr([html.Th(col) for col in causas_top10.columns])
    ] + [
        html.Tr([html.Td(causas_top10.iloc[i][col]) for col in causas_top10.columns])
        for i in range(len(causas_top10))
    ]),

    html.H2("6️⃣ Comparación de muertes por sexo"),
    dcc.Graph(figure=fig_apiladas),

    html.H2("7️⃣ Distribución de muertes por grupo de edad"),
    dcc.Graph(figure=fig_hist),
])

# ---------------------------------------------------------------------
# EJECUCIÓN LOCAL
# ---------------------------------------------------------------------
import os

if __name__ == "__main__":
    # Render asigna el puerto a la variable de entorno PORT
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)

