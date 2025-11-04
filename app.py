import os
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, dash_table

# =============================
# CARGA DE DATOS
# =============================
anexo1 = pd.read_excel("data/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
anexo2 = pd.read_excel("data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
divipola = pd.read_excel("data/Divipola_CE_.xlsx")

# Normalizar nombres de columnas
anexo1.columns = anexo1.columns.str.upper().str.strip()
anexo2.columns = anexo2.columns.str.upper().str.strip()
divipola.columns = divipola.columns.str.upper().str.strip()

# Convertir códigos a texto con ceros a la izquierda
divipola["COD_DEPTO"] = divipola["COD_DEPTO"].astype(str).str.zfill(2)
divipola["COD_MPIO"] = divipola["COD_MPIO"].astype(str).str.zfill(3)
anexo1["COD_DEPARTAMENTO"] = anexo1["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
anexo1["COD_MUNICIPIO"] = anexo1["COD_MUNICIPIO"].astype(str).str.zfill(3)

# Unir tablas
df = anexo1.merge(anexo2, on="COD_MUERTE", how="left")
df = df.merge(divipola, left_on=["COD_DEPARTAMENTO", "COD_MUNICIPIO"],
              right_on=["COD_DEPTO", "COD_MPIO"], how="left")

# =============================
# GRAFICOS
# =============================

# 1. Mapa: Muertes por departamento
mapa = df.groupby("NOMBRE_DPT").size().reset_index(name="TOTAL_MUERTES")
fig_mapa = px.choropleth(
    mapa,
    locations="NOMBRE_DPT",
    locationmode="geojson-id",
    color="TOTAL_MUERTES",
    title="Distribución de muertes por departamento (2019)",
    color_continuous_scale="Reds"
)

# 2. Gráfico de líneas: muertes por mes
muertes_mes = df.groupby("MES").size().reset_index(name="TOTAL")
fig_lineas = px.line(muertes_mes, x="MES", y="TOTAL", title="Muertes por mes en 2019")

# 3. Barras: 5 ciudades más violentas (homicidios X95)
violentas = df[df["COD_MUERTE"] == "X95"].groupby("NOMBRE_MPIO").size().nlargest(5).reset_index(name="TOTAL")
fig_barras = px.bar(violentas, x="NOMBRE_MPIO", y="TOTAL",
                    title="5 ciudades más violentas (homicidios por arma de fuego)")

# 4. Circular: 10 ciudades con menor índice de mortalidad
menor_mortalidad = df.groupby("NOMBRE_MPIO").size().nsmallest(10).reset_index(name="TOTAL")
fig_pie = px.pie(menor_mortalidad, names="NOMBRE_MPIO", values="TOTAL",
                 title="10 ciudades con menor índice de mortalidad")

# 5. Tabla: 10 principales causas de muerte
causas = df.groupby(["COD_MUERTE", "DESCRIPCION"]).size().reset_index(name="TOTAL")
top_causas = causas.sort_values("TOTAL", ascending=False).head(10)

# 6. Barras apiladas: muertes por sexo y departamento
sexo_dep = df.groupby(["NOMBRE_DPT", "SEXO"]).size().reset_index(name="TOTAL")
fig_apiladas = px.bar(sexo_dep, x="NOMBRE_DPT", y="TOTAL", color="SEXO",
                      title="Muertes por sexo y departamento", barmode="stack")

# 7. Histograma: distribución por grupo de edad
fig_hist = px.histogram(df, x="GRUPO_EDAD1", title="Distribución de muertes por grupo de edad")

# =============================
# DASH APP
# =============================
app = dash.Dash(__name__)
server = app.server  # Necesario para Render

app.layout = html.Div([
    html.H1("Análisis de Mortalidad en Colombia - 2019", style={"textAlign": "center"}),

    dcc.Graph(figure=fig_mapa),
    dcc.Graph(figure=fig_lineas),
    dcc.Graph(figure=fig_barras),
    dcc.Graph(figure=fig_pie),

    html.H3("10 Principales causas de muerte en Colombia (2019)"),
    dash_table.DataTable(
        data=top_causas.to_dict("records"),
        columns=[{"name": i, "id": i} for i in top_causas.columns],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left"}
    ),

    dcc.Graph(figure=fig_apiladas),
    dcc.Graph(figure=fig_hist)
])

# =============================
# SERVIDOR
# =============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)





