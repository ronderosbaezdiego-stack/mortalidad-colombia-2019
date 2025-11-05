import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import dash_table
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

if "COD_DEPARTAMENTO" not in df1.columns:
    raise Exception("No se encontró la columna COD_DEPARTAMENTO en el archivo principal.")

if "COD_DPTO" in divipola.columns:
    divipola["COD_DEPARTAMENTO"] = divipola["COD_DPTO"]

divipola_departamentos = divipola[["COD_DEPARTAMENTO", "DEPARTAMENTO"]].drop_duplicates()
divipola_municipios = divipola[["COD_MUNICIPIO", "MUNICIPIO"]].drop_duplicates()

# =======================
# Merge para agregar nombre del departamento a df1
# =======================
df1 = df1.merge(divipola_departamentos, on="COD_DEPARTAMENTO", how="left")

# =======================
# Preprocesar totales nacionales
# =======================
totales_departamento = df1.groupby("COD_DEPARTAMENTO")["COD_DANE"].count().reset_index()
totales_departamento = totales_departamento.merge(
    divipola_departamentos,
    on="COD_DEPARTAMENTO",
    how="left"
)
totales_nacional = df1.shape[0]

# =======================
# Crear la app Dash
# =======================
app = Dash(__name__)
server = app.server

# =======================
# Layout
# =======================
app.layout = html.Div([
    html.H1("Mortalidad Colombia 2019", style={'textAlign': 'center'}),

    html.H2("Mapa de mortalidad por departamento"),
    dcc.Graph(
        figure=px.choropleth(
            totales_departamento,
            locations="DEPARTAMENTO",
            locationmode="geojson-id",
            color="COD_DANE",
            hover_name="DEPARTAMENTO",
            color_continuous_scale="Reds",
            title="Total de muertes por departamento (2019)"
        )
    ),

    html.H2("Muertes por mes en Colombia"),
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
        options=[
            {'label': dep, 'value': cod}
            for cod, dep in zip(divipola_departamentos["COD_DEPARTAMENTO"], divipola_departamentos["DEPARTAMENTO"])
        ],
        value=int(divipola_departamentos["COD_DEPARTAMENTO"].iloc[0])
    ),

    dcc.Graph(id='grafico_sexo'),
    dcc.Graph(id='grafico_municipios'),
    dcc.Graph(id='grafico_menor'),
    dcc.Graph(id='grafico_apilado_sexo'),
    dcc.Graph(id='grafico_histograma_edad'),
    dash_table.DataTable(id='tabla_causas'),

    html.Div(id='info')
])

# =======================
# Callback
# =======================
@app.callback(
    Output('grafico_sexo', 'figure'),
    Output('grafico_municipios', 'figure'),
    Output('grafico_menor', 'figure'),
    Output('grafico_apilado_sexo', 'figure'),
    Output('grafico_histograma_edad', 'figure'),
    Output('tabla_causas', 'data'),
    Output('tabla_causas', 'columns'),
    Output('info', 'children'),
    Input('departamento', 'value')
)
def actualizar(departamento):
    df_filtrado = df1[df1["COD_DEPARTAMENTO"] == int(departamento)]

    if df_filtrado.empty:
        empty_fig = px.scatter(title="Sin datos para este departamento")
        return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, [], [], "No hay datos disponibles."

    # Gráfico 1: Muertes por sexo
    fig_sexo = px.histogram(
        df_filtrado,
        x="SEXO",
        color="SEXO",
        title=f"Distribución de muertes por sexo — Departamento {departamento}"
    )

    # Gráfico 2: Top 5 municipios con más muertes
    df_mun = df_filtrado.groupby("COD_MUNICIPIO")["COD_DANE"].count().reset_index()
    df_mun = df_mun.sort_values(by="COD_DANE", ascending=False).head(5)
    df_mun = df_mun.merge(divipola_municipios, on="COD_MUNICIPIO", how="left")
    fig_mun = px.bar(
        df_mun,
        x="MUNICIPIO",
        y="COD_DANE",
        title=f"Top 5 municipios con más muertes — Departamento {departamento}",
        labels={"COD_DANE": "Total de muertes", "MUNICIPIO": "Municipio"}
    )

    # Gráfico 3: Top 10 municipios con menor mortalidad
    df_menor = df_filtrado.groupby("COD_MUNICIPIO")["COD_DANE"].count().reset_index()
    df_menor = df_menor.merge(divipola_municipios, on="COD_MUNICIPIO", how="left")
    df_menor = df_menor.sort_values(by="COD_DANE", ascending=True).head(10)
    fig_menor = px.pie(
        df_menor,
        names="MUNICIPIO",
        values="COD_DANE",
        title=f"10 municipios con menor mortalidad — Departamento {departamento}"
    )

    # Gráfico 4: Barras apiladas por sexo en cada departamento
    df_apilado = df1.groupby(["DEPARTAMENTO", "SEXO"])["COD_DANE"].count().reset_index()
    fig_apilado = px.bar(
        df_apilado,
        x="DEPARTAMENTO",
        y="COD_DANE",
        color="SEXO",
        title="Comparación de muertes por sexo en cada departamento"
    )

    # Gráfico 5: Histograma por grupo de edad
    if "GRUPO_EDAD1" in df_filtrado.columns:
        fig_hist = px.histogram(
            df_filtrado,
            x="GRUPO_EDAD1",
            nbins=len(df_filtrado["GRUPO_EDAD1"].unique()),
            title=f"Distribución de muertes por grupo de edad — Departamento {departamento}",
            labels={"GRUPO_EDAD1": "Grupo de edad", "COD_DANE": "Cantidad de muertes"}
        )
    else:
        fig_hist = px.scatter(title="No hay columna GRUPO_EDAD1 para este departamento")

    # Tabla 6: 10 principales causas de muerte
    df_causas = df_filtrado.groupby(["CIE10_3_CARACTERES", "DESCRIPCION"]).size().reset_index(name="Total")
    df_causas = df_causas.sort_values(by="Total", ascending=False).head(10)
    tabla_data = df_causas.to_dict('records')
    tabla_columns = [{"name": i, "id": i} for i in df_causas.columns]

    total_dep = len(df_filtrado)
    info_text = f"Total de registros en este departamento: {total_dep} | Total nacional: {totales_nacional}"

    return fig_sexo, fig_mun, fig_menor, fig_apilado, fig_hist, tabla_data, tabla_columns, info_text

# =======================
# Run
# =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)


