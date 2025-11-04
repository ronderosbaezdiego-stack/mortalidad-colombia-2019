import os
import pandas as pd
import plotly.express as px
import dash
from dash import Dash, dcc, html, dash_table, Input, Output

# --------------------------
# Cargar los datos
# --------------------------
df = pd.read_excel("data/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
codigos = pd.read_excel("data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
divipola = pd.read_excel("data/Divipola_CE_.xlsx")

# Limpieza básica
df.columns = df.columns.str.strip().str.upper()
codigos.columns = codigos.columns.str.strip().str.upper()
divipola.columns = divipola.columns.str.strip().str.upper()

# Asegurar tipos
df["COD_DEPARTAMENTO"] = df["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
divipola["COD_DEPTO"] = divipola["COD_DEPTO"].astype(str).str.zfill(2)

# Merge con nombres de departamento
df = df.merge(divipola[["COD_DEPTO", "NOM_DEPTO"]], left_on="COD_DEPARTAMENTO", right_on="COD_DEPTO", how="left")

# --------------------------
# Inicializar la app Dash
# --------------------------
app = Dash(__name__)
server = app.server
app.title = "Mortalidad en Colombia 2019"

# --------------------------
# Componentes de la app
# --------------------------
app.layout = html.Div([
    html.H1("Análisis de Mortalidad en Colombia - 2019", style={'textAlign': 'center'}),
    html.P("Fuente: DANE - Estadísticas Vitales No Fetales 2019", style={'textAlign': 'center'}),

    dcc.Tabs([
        # 1️⃣ Mapa
        dcc.Tab(label='Mapa de Mortalidad por Departamento', children=[
            dcc.Graph(id='mapa-mortalidad',
                      figure=px.choropleth(
                          df.groupby(["NOM_DEPTO"], as_index=False).size(),
                          geojson="https://raw.githubusercontent.com/CodeforColombia/geojson-departamentos-colombia/master/departamentos.geojson",
                          locations="NOM_DEPTO",
                          featureidkey="properties.NOMBRE_DPT",
                          color="size",
                          color_continuous_scale="Reds",
                          title="Distribución total de muertes por departamento (2019)"
                      ))
        ]),

        # 2️⃣ Gráfico de líneas
        dcc.Tab(label='Muertes por Mes', children=[
            dcc.Graph(id='muertes-mes', figure=px.line(
                df.groupby("MES", as_index=False).size(),
                x="MES", y="size",
                markers=True,
                title="Total de muertes por mes en Colombia (2019)"
            ))
        ]),

        # 3️⃣ 5 ciudades más violentas
        dcc.Tab(label='Ciudades más violentas (Homicidios)', children=[
            dcc.Graph(id='ciudades-violentas', figure=px.bar(
                df[df["COD_MUERTE"].isin(["X95", "X96", "X97"])].groupby("COD_MUNICIPIO", as_index=False).size().nlargest(5, "size"),
                x="COD_MUNICIPIO", y="size",
                title="5 ciudades más violentas (Homicidios por armas de fuego)"
            ))
        ]),

        # 4️⃣ 10 ciudades con menor mortalidad
        dcc.Tab(label='Ciudades con menor mortalidad', children=[
            dcc.Graph(id='ciudades-menor', figure=px.pie(
                df.groupby("COD_MUNICIPIO", as_index=False).size().nsmallest(10, "size"),
                names="COD_MUNICIPIO", values="size",
                title="10 ciudades con menor índice de mortalidad"
            ))
        ]),

        # 5️⃣ Principales causas de muerte
        dcc.Tab(label='Principales Causas de Muerte', children=[
            dash_table.DataTable(
                id='tabla-causas',
                columns=[{"name": i, "id": i} for i in ["COD_MUERTE", "CAUSA", "TOTAL"]],
                data=pd.merge(
                    df.groupby("COD_MUERTE", as_index=False).size(),
                    codigos.rename(columns={"CÓDIGO": "COD_MUERTE", "NOMBRE": "CAUSA"}),
                    on="COD_MUERTE",
                    how="left"
                ).nlargest(10, "size").rename(columns={"size": "TOTAL"}).to_dict("records"),
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'center'}
            )
        ]),

        # 6️⃣ Barras apiladas por sexo
        dcc.Tab(label='Muertes por Sexo y Departamento', children=[
            dcc.Graph(id='muertes-sexo', figure=px.bar(
                df.groupby(["NOM_DEPTO", "SEXO"], as_index=False).size(),
                x="NOM_DEPTO", y="size", color="SEXO",
                title="Comparación del total de muertes por sexo en cada departamento",
                barmode="stack"
            ))
        ]),

        # 7️⃣ Histograma por grupo de edad
        dcc.Tab(label='Distribución por Grupo de Edad', children=[
            dcc.Graph(id='histograma', figure=px.histogram(
                df, x="GRUPO_EDAD1",
                title="Distribución de muertes por grupo de edad (GRUPO_EDAD1)",
                nbins=20
            ))
        ]),
    ])
])

# --------------------------
# Despliegue Render
# --------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)

