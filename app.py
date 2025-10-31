import os
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# Crear la app y el servidor (Render usa "server")
app = Dash(__name__)
server = app.server  # necesario para Gunicorn/Render

# Rutas relativas
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

# Cargar datos (Excel)
df = pd.read_excel(os.path.join(DATA_DIR, "Anexo1.NoFetal2019_CE_15-03-23.xlsx"))
codigos = pd.read_excel(os.path.join(DATA_DIR, "Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx"))
divipola = pd.read_excel(os.path.join(DATA_DIR, "Divipola_CE_.xlsx"))

# Normalizar y preparar
# Asegurarse de que exista la columna COD_DEPARTAMENTO en df
if "COD_DEPARTAMENTO" not in df.columns:
    # intentar otras variantes comunes
    possible = [c for c in df.columns if "DEPART" in c.upper() or "COD" in c.upper()]
    if possible:
        df = df.rename(columns={possible[0]: "COD_DEPARTAMENTO"})

# Preparar nombres de departamento
divipola = divipola[['COD_DEPARTAMENTO', 'DEPARTAMENTO']].drop_duplicates()

# Unir nombres al dataframe principal
df = df.merge(divipola, on='COD_DEPARTAMENTO', how='left')

# Crear lista de causas disponibles (desde Anexo2 o desde df si no se encontró)
if 'COD_CAUSA' in df.columns and 'DESCRIPCION' in df.columns:
    causas = df[['COD_CAUSA', 'DESCRIPCION']].drop_duplicates().sort_values('DESCRIPCION')
else:
    # intentar sacar una columna de texto relacionada con la causa en df
    text_cols = [c for c in df.columns if 'CAUSA' in c.upper() or 'MOTIVO' in c.upper() or 'DESCRIP' in c.upper()]
    if text_cols:
        causas = df[[text_cols[0]]].drop_duplicates().rename(columns={text_cols[0]:'DESCRIPCION'})
        causas['COD_CAUSA'] = causas.index.astype(str)
    else:
        # fallback a codigos en Anexo2 si existe
        if 'COD' in codigos.columns and 'NOMBRE' in codigos.columns:
            causas = codigos[['COD','NOMBRE']].rename(columns={'COD':'COD_CAUSA','NOMBRE':'DESCRIPCION'}).drop_duplicates()
        else:
            causas = pd.DataFrame([{'COD_CAUSA': 'Todas', 'DESCRIPCION': 'Todas las causas'}])

# Asegurar columnas esperadas para el dashboard
df['DEPARTAMENTO'] = df['DEPARTAMENTO'].fillna('Sin departamento')
if 'DESCRIPCION' not in df.columns and 'COD_CAUSA' in df.columns:
    # intentar mapear desde codigos
    if 'COD' in codigos.columns and 'NOMBRE' in codigos.columns:
        map_cod = dict(zip(codigos['COD'], codigos['NOMBRE']))
        df['DESCRIPCION'] = df['COD_CAUSA'].map(map_cod)
    else:
        df['DESCRIPCION'] = df.get('DESCRIPCION', 'No especificada')

# Layout
app.layout = html.Div([
    html.H1("Dashboard Mortalidad 2019", style={'textAlign':'center'}),
    html.Div([
        html.Label("Selecciona causa de muerte:"),
        dcc.Dropdown(
            id='causa-dropdown',
            options=[{'label': r['DESCRIPCION'], 'value': r['COD_CAUSA']} for _, r in causas.iterrows()],
            value=causas['COD_CAUSA'].iloc[0] if not causas.empty else None,
            clearable=False,
            style={'width':'70%'})
    ], style={'padding':'10px 20px'}),
    dcc.Graph(id='barras-departamentos')
], style={'fontFamily':'Arial, sans-serif'})


@app.callback(
    Output('barras-departamentos', 'figure'),
    Input('causa-dropdown', 'value')
)
def update_graph(causa_sel):
    # Filtrar por causa si es posible
    dff = df.copy()
    # intentar filtrar por código o por descripción
    if causa_sel is not None:
        if 'COD_CAUSA' in dff.columns and str(causa_sel) in dff['COD_CAUSA'].astype(str).unique():
            dff = dff[dff['COD_CAUSA'].astype(str) == str(causa_sel)]
        else:
            # intentar filtrar por descripción
            if 'DESCRIPCION' in dff.columns:
                dff = dff[dff['DESCRIPCION'].astype(str) == str(causa_sel)]

    muertes_dep = dff.groupby('DEPARTAMENTO').size().reset_index(name='Total_muertes')
    muertes_dep = muertes_dep.sort_values('Total_muertes', ascending=False)

    fig = px.bar(muertes_dep, x='Total_muertes', y='DEPARTAMENTO', orientation='h',
                 title='Total de muertes por departamento - Colombia 2019',
                 labels={'DEPARTAMENTO':'Departamento', 'Total_muertes':'Total de muertes'})
    fig.update_layout(yaxis={'categoryorder':'total ascending'}, margin={'l':200})
    return fig


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=True)
