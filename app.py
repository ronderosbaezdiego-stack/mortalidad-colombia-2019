import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import json
import os

# =======================
# Cargar datos
# =======================
df1 = pd.read_excel("data/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
divipola = pd.read_excel("data/Divipola_CE_.xlsx")

# =======================
# Limpieza básica
# =======================
divipola = divipola.rename(columns=lambda x: x.strip().upper())
if "COD_DPTO" in divipola.columns:
    divipola["COD_DEPARTAMENTO"] = divipola["COD_DPTO"]
divipola_departamentos = divipola[["COD_DEPARTAMENTO", "DEPARTAMENTO", "MUNICIPIO"]].drop_duplicates()

totales_departamento = df1.groupby("COD_DEPARTAMENTO")["COD_DANE"].count().reset_index()
totales_departamento = totales_departamento.merge(divipola_departamentos[["COD_DEPARTAMENTO","DEPARTAMENTO"]], on="COD_DEPARTAMENTO", how="left")

# =======================
# Cargar geojson de Colombia
# =======================
# Necesitas descargar un geojson de departamentos de Colombia
with open("data/colombia_departamentos.geojson", "r", encoding="utf-8") as f:
    geojson_col = json.load(f)

# =======================
# Crear la app
# =======================
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Mortalidad Colombia 2019", style={'textAlign': 'center'}),

    html.H2("📍 Mapa de mortalidad por departamento"),
    dcc.Graph(
        id="mapa_departamentos",
        figure=px.choropleth(
            totales_departamento,
            geojson=geojson_col,
            locations="COD_DEPARTAMENTO",
            featureidkey="properties.CODIGO_DANE",  # columna en el geojson
            color="COD_DANE",
            hover_name="DEPARTAMENTO",
            color_continuous_scale="Reds",
            title="Total de muertes por departamento (2019)"
        ).update_geos(fitbounds="locations", visible=False)
    ),

    html.H2("📊 Muertes por mes en Colombia"),
    dcc.Graph(
        figure=px.line(
            df1.groupby("MES")["COD_DANE"].count().reset_index(),
            x="MES",
            y="COD_DANE",
            markers=True,
            title="Total de muertes por mes en Colombia (2019)",
            labels={"COD_DANE": "Total de muertes"}
        )
    ),

    html.Label("Selecciona un departamento:"),
    dcc.Dropdown(
        id='departamento',
        options=[{'label': dep, 'value': cod} for cod, dep in zip(divipola_departamentos["COD_DEPARTAMENTO"], divipola_departamentos["DEPARTAMENTO"])],
        value=int(divipola_departamentos["COD_DEPARTAMENTO"].iloc[0])
    ),

    dcc.Graph(id='grafico_sexo'),
    dcc.Graph(id='grafico_municipios'),
    html.Div(id='info')
])

@app.callback(
    Output('grafico_sexo', 'figure'),
    Output('grafico_municipios', 'figure'),
    Output('info', 'children'),
    Input('departamento', 'value')
)
def actualizar(departamento):
    df_dep = df1[df1["COD_DEPARTAMENTO"] == int(departamento)]
    if df_dep.empty:
        empty = px.scatter(title="Sin datos")
        return empty, empty, "No hay datos"

    fig_sexo = px.histogram(df_dep, x="SEXO", color="SEXO", title=f"Distribución por sexo — Departamento {departamento}")

    df_mun = df_dep.groupby("COD_MUNICIPIO")["COD_DANE"].count().reset_index()
    df_mun = df_mun.merge(divipola_departamentos[["COD_MUNICIPIO","MUNICIPIO"]], on="COD_MUNICIPIO", how="left")
    df_mun = df_mun.sort_values("COD_DANE", ascending=False).head(5)
    fig_mun = px.bar(df_mun, x="MUNICIPIO", y="COD_DANE", title=f"Top 5 municipios con más muertes — Departamento {departamento}")

    total_dep = len(df_dep)
    return fig_sexo, fig_mun, f"Total registros departamento: {total_dep}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)






