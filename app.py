import os
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html

# ======================================
# Cargar los datos
# ======================================
df = pd.read_csv("data/mortalidad.csv", encoding="utf-8")

# Limpiar nombres de columnas
df.columns = df.columns.str.strip().str.upper()

# Asegurar que existan columnas necesarias
if "COD_DEPARTAMENTO" not in df.columns and "COD_DANE" in df.columns:
    df["COD_DEPARTAMENTO"] = df["COD_DANE"].astype(str).str[:2]

df["COD_DEPARTAMENTO"] = df["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
df["COD_MUNICIPIO"] = df["COD_MUNICIPIO"].astype(str).str.zfill(5)
df["SEXO"] = df["SEXO"].fillna("No especificado")

# ======================================
# Crear la aplicación Dash
# ======================================
app = Dash(__name__)
server = app.server

# ======================================
# Crear las gráficas
# ======================================

# 1️⃣ Mapa: muertes por departamento
muertes_dep = df.groupby("COD_DEPARTAMENTO").size().reset_index(name="Total")
fig_mapa = px.choropleth(
    muertes_dep,
    locations="COD_DEPARTAMENTO",
    color="Total",
    color_continuous_scale="Reds",
    title="Muertes por departamento"
)

# 2️⃣ Gráfico de líneas: muertes por mes
fig_lineas = px.line(
    df.groupby("MES").size().reset_index(name="Total"),
    x="MES", y="Total",
    title="Muertes por mes"
)

# 3️⃣ Barras: 5 ciudades más violentas
homicidios = df[df["COD_MUERTE"].astype(str).str.startswith("X95")]
top_violentas = homicidios.groupby("COD_MUNICIPIO").size().nlargest(5).reset_index(name="Total")
fig_violentas = px.bar(top_violentas, x="COD_MUNICIPIO", y="Total", title="Top 5 ciudades más violentas")

# 4️⃣ Circular: 10 ciudades con menor mortalidad
menor_mortalidad = df.groupby("COD_MUNICIPIO").size().nsmallest(10).reset_index(name="Total")
fig_menor = px.pie(menor_mortalidad, names="COD_MUNICIPIO", values="Total", title="10 ciudades con menor mortalidad")

# 5️⃣ Tabla: 10 principales causas de muerte
top_causas = df.groupby("COD_MUERTE").size().reset_index(name="Total").sort_values("Total", ascending=False).head(10)

# 6️⃣ Barras apiladas: muertes por sexo y departamento
barras = df.groupby(["COD_DEPARTAMENTO", "SEXO"]).size().reset_index(name="Total")
fig_barras = px.bar(barras, x="COD_DEPARTAMENTO", y="Total", color="SEXO", title="Muertes por sexo y departamento")

# 7️⃣ Histograma: distribución por grupo de edad
fig_hist = px.histogram(df, x="GRUPO_EDAD1", title="Distribución de muertes por grupo de edad")

# ======================================
# Layout (estructura visual)
# ======================================
app.layout = html.Div([
    html.H1("Mortalidad en Colombia 2019", style={"textAlign": "center"}),

    html.H3("Mapa: Total de muertes por departamento"),
    dcc.Graph(figure=fig_mapa),

    html.H3("Gráfico de líneas: Muertes por mes"),
    dcc.Graph(figure=fig_lineas),

    html.H3("Gráfico de barras: Top 5 ciudades más violentas"),
    dcc.Graph(figure=fig_violentas),

    html.H3("Gráfico circular: 10 ciudades con menor mortalidad"),
    dcc.Graph(figure=fig_menor),

    html.H3("Tabla: 10 principales causas de muerte"),
    html.Table([
        html.Thead(html.Tr([html.Th(col) for col in top_causas.columns])),
        html.Tbody([
            html.Tr([html.Td(top_causas.iloc[i][col]) for col in top_causas.columns])
            for i in range(len(top_causas))
        ])
    ], style={"margin": "auto"}),

    html.H3("Gráfico de barras apiladas: Muertes por sexo y departamento"),
    dcc.Graph(figure=fig_barras),

    html.H3("Histograma: Distribución de muertes por grupo de edad"),
    dcc.Graph(figure=fig_hist)
])

# ======================================
# Ejecutar aplicación
# ======================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Compatible con Render
    app.run_server(host="0.0.0.0", port=port, debug=False)






