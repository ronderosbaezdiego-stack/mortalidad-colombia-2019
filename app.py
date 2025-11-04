import os
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, dash_table

# ============ CARGA DE DATOS ============
df1 = pd.read_excel("data/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
cod_muerte = pd.read_excel("data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
divipola = pd.read_excel("data/Divipola_CE_.xlsx")

# Normalizar nombres de columnas
df1.columns = df1.columns.str.strip().str.upper()
cod_muerte.columns = cod_muerte.columns.str.strip().str.upper()
divipola.columns = divipola.columns.str.strip().str.upper()

# Convertir códigos a texto
divipola["COD_DEPARTAMENTO"] = divipola["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
df1["COD_DEPARTAMENTO"] = df1["COD_DEPARTAMENTO"].astype(str).str.zfill(2)

# Unir nombre del departamento
if "NOMBRE_DEPARTAMENTO" in divipola.columns:
    df1 = df1.merge(divipola[["COD_DEPARTAMENTO", "NOMBRE_DEPARTAMENTO"]], on="COD_DEPARTAMENTO", how="left")
else:
    df1["NOMBRE_DEPARTAMENTO"] = df1["COD_DEPARTAMENTO"]

# ============ PROCESAMIENTO DE DATOS ============
muertes_depto = df1.groupby("NOMBRE_DEPARTAMENTO")["COD_DEPARTAMENTO"].count().reset_index(name="TOTAL_MUERTES")
muertes_mes = df1.groupby("MES")["COD_DEPARTAMENTO"].count().reset_index(name="TOTAL_MUERTES")

violentas = df1[df1["COD_MUERTE"].astype(str).str.startswith("X95")]
top_5_ciudades_violentas = (
    violentas.groupby("COD_MUNICIPIO")["COD_MUERTE"].count().nlargest(5).reset_index(name="TOTAL_HOMICIDIOS")
)

bajas_muertes = (
    df1.groupby("COD_MUNICIPIO")["COD_MUERTE"].count().nsmallest(10).reset_index(name="TOTAL_MUERTES")
)

top_causas = (
    df1.groupby("COD_MUERTE")["COD_DEPARTAMENTO"].count().reset_index(name="TOTAL")
    .merge(cod_muerte, on="COD_MUERTE", how="left")
    .sort_values(by="TOTAL", ascending=False)
    .head(10)
)

sexo_depto = (
    df1.groupby(["NOMBRE_DEPARTAMENTO", "SEXO"])["COD_DEPARTAMENTO"].count().reset_index(name="TOTAL")
)

df1["GRUPO_EDAD1"] = df1["GRUPO_EDAD1"].astype(str)

# ============ DASH APP ============
app = dash.Dash(__name__)
server = app.server  # Render busca esta variable

app.layout = html.Div([
    html.H1("Mortalidad en Colombia 2019", style={"textAlign": "center"}),

    html.H3("Mapa: Total de muertes por departamento"),
    dcc.Graph(
        id="mapa",
        figure=px.choropleth(
            muertes_depto,
            geojson="https://raw.githubusercontent.com/juan-garcia-01/Colombia-GeoJSON/main/colombia.json",
            featureidkey="properties.NOMBRE_DPT",
            locations="NOMBRE_DEPARTAMENTO",
            color="TOTAL_MUERTES",
            color_continuous_scale="Reds",
            title="Distribución total de muertes por departamento"
        )
    ),

    html.H3("Gráfico de líneas: Total de muertes por mes"),
    dcc.Graph(
        id="lineas",
        figure=px.line(muertes_mes, x="MES", y="TOTAL_MUERTES", markers=True,
                       title="Muertes mensuales en Colombia 2019")
    ),

    html.H3("Gráfico de barras: 5 ciudades más violentas (X95)"),
    dcc.Graph(
        id="barras_violentas",
        figure=px.bar(top_5_ciudades_violentas, x="COD_MUNICIPIO", y="TOTAL_HOMICIDIOS",
                      title="5 ciudades más violentas (Homicidios por arma de fuego)",
                      color="TOTAL_HOMICIDIOS", text_auto=True)
    ),

    html.H3("Gráfico circular: 10 ciudades con menor índice de mortalidad"),
    dcc.Graph(
        id="pie_bajo",
        figure=px.pie(bajas_muertes, values="TOTAL_MUERTES", names="COD_MUNICIPIO",
                      title="10 ciudades con menor índice de mortalidad")
    ),

    html.H3("Tabla: 10 principales causas de muerte en Colombia"),
    dash_table.DataTable(
        id="tabla_causas",
        columns=[{"name": i, "id": i} for i in top_causas.columns],
        data=top_causas.to_dict("records"),
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center"},
        page_size=10
    ),

    html.H3("Gráfico de barras apiladas: Muertes por sexo y departamento"),
    dcc.Graph(
        id="barras_sexo",
        figure=px.bar(sexo_depto, x="NOMBRE_DEPARTAMENTO", y="TOTAL", color="SEXO",
                      title="Total de muertes por sexo en cada departamento",
                      barmode="stack")
    ),

    html.H3("Histograma: Distribución de muertes por grupo de edad"),
    dcc.Graph(
        id="histograma",
        figure=px.histogram(df1, x="GRUPO_EDAD1", title="Distribución de muertes por grupo de edad")
    ),
])

# ============ PUERTO PARA RENDER ============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))  # Render asigna automáticamente el puerto
    app.run_server(host="0.0.0.0", port=port, debug=False)





