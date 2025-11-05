import pandas as pd
from dash import Dash, dcc, html, Input, Output, dash_table
import plotly.express as px
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

    html.H2(" Mapa de mortalidad por departamento"),
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

    html.H2(" Muertes por mes en Colombia"),
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

    # Gráficas dinámicas
    dcc.Graph(id='grafico_sexo'),
    dcc.Graph(id='grafico_municipios'),
    dcc.Graph(id='grafico_menor'),

    html.H2(" Tabla: 10 principales causas de muerte"),
    dash_table.DataTable(
        id='tabla_causas',
        columns=[
            {"name": "Código CIE-10", "id": "COD_MUERTE"},
            {"name": "Descripción", "id": "DESCRIPCION"},
            {"name": "Total de casos", "id": "TOTAL"}
        ],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
    ),

    html.H2(" 📊 Comparación de muertes por sexo en cada departamento"),
    dcc.Graph(id='grafico_sexo_departamento'),

    html.H2(" 📈 Distribución de muertes por rango de edad"),
    dcc.Graph(id='histograma_edad'),

    html.Div(id='info')
])

# =======================
# Callback
# =======================
@app.callback(
    Output('grafico_sexo', 'figure'),
    Output('grafico_municipios', 'figure'),
    Output('grafico_menor', 'figure'),
    Output('tabla_causas', 'data'),
    Output('grafico_sexo_departamento', 'figure'),
    Output('histograma_edad', 'figure'),
    Output('info', 'children'),
    Input('departamento', 'value')
)
def actualizar(departamento):
    df_filtrado = df1[df1["COD_DEPARTAMENTO"] == int(departamento)]

    if df_filtrado.empty:
        empty_fig = px.scatter(title="Sin datos para este departamento")
        return empty_fig, empty_fig, empty_fig, [], empty_fig, empty_fig, "No hay datos disponibles."

    # Gráfico 1: Muertes por sexo
    fig_sexo = px.histogram(
        df_filtrado,
        x="SEXO",
        color="SEXO",
        title=f"Distribución de muertes por sexo — Departamento {departamento}"
    )

    # Gráfico 2: Top 5 municipios con más homicidios
    codigos_homicidio = ["X95"]  # Añade más códigos si los tienes
    df_homicidios = df_filtrado[df_filtrado["COD_MUERTE"].isin(codigos_homicidio)]
    df_mun = df_homicidios.groupby("COD_MUNICIPIO")["COD_DANE"].count().reset_index()
    df_mun = df_mun.sort_values(by="COD_DANE", ascending=False).head(5)
    df_mun = df_mun.merge(divipola_municipios, on="COD_MUNICIPIO", how="left")
    fig_mun = px.bar(
        df_mun,
        x="MUNICIPIO",
        y="COD_DANE",
        title=f"Top 5 municipios con más homicidios — Departamento {departamento}",
        labels={"COD_DANE": "Total de homicidios", "MUNICIPIO": "Municipio"}
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

    # Tabla: Top 10 causas de muerte
    df_causas = df1.groupby("COD_MUERTE")["COD_DANE"].count().reset_index()
    df_causas = df_causas.rename(columns={"COD_DANE": "TOTAL"})
    # Si tienes columna de descripción, hacer merge con df2
    # df_causas = df_causas.merge(df2[['COD_MUERTE','DESCRIPCION']], on='COD_MUERTE', how='left')
    df_causas = df_causas.sort_values(by="TOTAL", ascending=False).head(10)
    df_causas["DESCRIPCION"] = df_causas["COD_MUERTE"]  # Si no hay descripción
    tabla_data = df_causas.to_dict('records')

    # Gráfico de barras apiladas por sexo y departamento
    df_sexo_depto = df1.groupby(["DEPARTAMENTO", "SEXO"])["COD_DANE"].count().reset_index()
    fig_sexo_departamento = px.bar(
        df_sexo_depto,
        x="DEPARTAMENTO",
        y="COD_DANE",
        color="SEXO",
        barmode='stack',
        title="Comparación de muertes por sexo en cada departamento"
    )

    # Histograma de muertes por rango de edad
    fig_hist_edad = px.histogram(
        df_filtrado,
        x="GRUPO_EDAD1",
        nbins=10,
        title=f"Distribución de muertes por rango de edad — Departamento {departamento}",
        labels={"GRUPO_EDAD1": "Rango de edad", "COD_DANE": "Total de muertes"}
    )

    total_dep = len(df_filtrado)
    return fig_sexo, fig_mun, fig_menor, tabla_data, fig_sexo_departamento, fig_hist_edad, f"Total de registros en este departamento: {total_dep} | Total nacional: {totales_nacional}"

# =======================
# Run
# =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)

