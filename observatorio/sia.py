# pip install dash pandas plotly

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output

# -----------------------------------------------------------
# Paleta de cores
# -----------------------------------------------------------
AZUL_ACO = "#4A5B79"
TERRACOTA = "#A05D22"
DOURADO = "#CEAD63"
MARROM = "#604442"
CINZA = "#66727C"
PALETA_LINHAS = [AZUL_ACO, TERRACOTA, DOURADO, "#7A8B6F", "#8C6E5A", "#5C7A8A", "#B08968", "#3F5765"]

# -----------------------------------------------------------
# Dados
# -----------------------------------------------------------
df = pd.read_csv("resultado_final.csv", dtype={"CNES": str})
df["COMPETENCIA"] = df["ANO"].astype(str) + "-" + df["MES"].astype(str).str.zfill(2)


lista_ubs = sorted(df["NOME_ESTABELECIMENTO"].dropna().unique())
lista_anos = sorted(df["ANO"].dropna().unique().tolist())

# Estabelecimentos que devem vir marcados por padrão ao abrir a página
UBS_PADRAO = ["UBS NOVO CAMINHO", "UBS VILA DAS BELEZAS ALBERTO AMBROSIO"]
ubs_padrao_validas = [u for u in UBS_PADRAO if u in lista_ubs]

if len(ubs_padrao_validas) < len(UBS_PADRAO):
    faltando = set(UBS_PADRAO) - set(ubs_padrao_validas)
    print(f"Aviso: não encontrei na base os nomes: {faltando}")
    print("Nomes parecidos disponíveis:",
          [u for u in lista_ubs if any(termo.split()[1].lower() in u.lower() for termo in faltando)])

def competencias_completas(dados):
    periodos = pd.to_datetime(dados["COMPETENCIA"], format="%Y-%m")
    intervalo = pd.period_range(periodos.min(), periodos.max(), freq="M")
    return [p.strftime("%Y-%m") for p in intervalo]


def abreviar(texto, limite=35):
    if len(texto) <= limite:
        return texto
    cortado = texto[:limite].rsplit(" ", 1)[0]
    return cortado + "…"


def aplicar_filtros(ubs_selecionadas, anos_selecionados):
    dados = df.copy()
    if ubs_selecionadas:
        dados = dados[dados["NOME_ESTABELECIMENTO"].isin(ubs_selecionadas)]
    if anos_selecionados:
        dados = dados[dados["ANO"].isin(anos_selecionados)]
    return dados


# -----------------------------------------------------------
# App
# -----------------------------------------------------------
app = Dash(__name__)
app.title = "Produção SIA — Evolução de Procedimentos"

ESTILO_CARD = {
    "background": "#ffffff", "borderRadius": "12px", "padding": "20px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.08)", "marginBottom": "20px",
}

app.layout = html.Div(
    style={"fontFamily": "'Segoe UI', Arial, sans-serif", "background": "#f4f5f7",
           "minHeight": "100vh", "padding": "32px"},
    children=[
        html.Div(style={"maxWidth": "1200px", "margin": "0 auto"}, children=[

            html.Div(children=[
                html.H1("Evolução de Procedimentos", style={"color": MARROM, "marginBottom": "4px"}),
                html.H3("SIA-SUS (Sistema de Informações Ambulatoriais do SUS)", style={"color": MARROM, "marginBottom": "2px"}),
                
                html.P("Como a produção variou no tempo e quais procedimentos mais mudaram — "
                       "meses sem dado aparecem como zero",
                       style={"color": CINZA, "fontSize": "15px", "marginTop": "0"}),
            ], style={"marginBottom": "24px"}),

            # Filtros
            html.Div(style={**ESTILO_CARD, "display": "flex", "gap": "24px", "flexWrap": "wrap"}, children=[
                html.Div(style={"flex": "2", "minWidth": "280px"}, children=[
                    html.Label("Estabelecimento(s)", style={"fontWeight": "600", "color": MARROM}),
                    dcc.Dropdown(
                        id="filtro-ubs",
                        options=[{"label": u, "value": u} for u in lista_ubs],
                        value=ubs_padrao_validas,
                        multi=True,
                        placeholder="Selecione um ou mais estabelecimentos",
                    ),
                ]),
                html.Div(style={"flex": "1", "minWidth": "180px"}, children=[
                    html.Label("Ano", style={"fontWeight": "600", "color": MARROM}),
                    dcc.Checklist(
                        id="filtro-ano",
                        options=[{"label": f" {a}", "value": a} for a in lista_anos],
                        value=lista_anos,  # todos marcados por padrão
                        inline=True,
                        style={"marginTop": "8px"},
                        inputStyle={"marginRight": "4px", "marginLeft": "8px"},
                    ),
                ]),
            ]),

            # Legenda explicativa
            html.Div(
                style={**ESTILO_CARD, "background": "#fbf8f2", "borderLeft": f"4px solid {DOURADO}",
                       "padding": "14px 20px"},
                children=[
                    html.Span("\"quantidade\": ", style={"fontWeight": "700", "color": MARROM}),
                    html.Span(
                        "Quantidade de procedimentos.",
                        style={"color": CINZA, "fontSize": "13.5px"},
                    ),
                ],
            ),

            html.Div(style=ESTILO_CARD, children=[
                html.H3("Tendência geral por estabelecimento", style={"color": MARROM, "marginTop": "0"}),
                dcc.Graph(id="grafico-tendencia-geral"),
            ]),

            html.Div(style=ESTILO_CARD, children=[
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                    children=[
                        html.H3("Procedimentos mais impactados (variação absoluta)",
                                style={"color": MARROM, "marginTop": "0"}),
                        dcc.Slider(id="top-n", min=5, max=15, step=5, value=10,
                                   marks={5: "5", 10: "10", 15: "15"}),
                    ],
                ),
                dcc.Graph(id="grafico-ranking-impacto"),
            ]),

            html.Div(style=ESTILO_CARD, children=[
                html.H3("Tendência individual dos mais impactados", style={"color": MARROM, "marginTop": "0"}),
                dcc.Graph(id="grafico-small-multiples"),
            ]),
        ]),
    ],
)


def calcular_impacto(dados, meses_completos):
    serie = (
        dados.groupby(["NO_PROCEDIMENTO", "COMPETENCIA"])["QTD_APROVADA"]
        .sum().reset_index()
    )
    resultado = []
    for proc, grupo in serie.groupby("NO_PROCEDIMENTO"):
        grupo_completo = (
            grupo.set_index("COMPETENCIA")["QTD_APROVADA"]
            .reindex(meses_completos, fill_value=0)
        )
        primeiro, ultimo = grupo_completo.iloc[0], grupo_completo.iloc[-1]
        resultado.append({"NO_PROCEDIMENTO": proc, "DIFF_ABS": ultimo - primeiro})
    return pd.DataFrame(resultado)


@app.callback(
    Output("grafico-tendencia-geral", "figure"),
    Input("filtro-ubs", "value"), Input("filtro-ano", "value"),
)
def atualizar_tendencia_geral(ubs_selecionadas, anos_selecionados):
    dados = aplicar_filtros(ubs_selecionadas, anos_selecionados)
    if dados.empty:
        return go.Figure()
    meses = competencias_completas(dados)

    fig = go.Figure()
    for i, ubs in enumerate(ubs_selecionadas or []):
        serie = (
            dados[dados["NOME_ESTABELECIMENTO"] == ubs]
            .groupby("COMPETENCIA")["QTD_APROVADA"].sum()
            .reindex(meses, fill_value=0).reset_index()
        )
        serie.columns = ["COMPETENCIA", "QTD_APROVADA"]
        cor = PALETA_LINHAS[i % len(PALETA_LINHAS)]
        fig.add_trace(go.Scatter(
            x=serie["COMPETENCIA"], y=serie["QTD_APROVADA"],
            mode="lines+markers", name=ubs,
            line=dict(color=cor, width=2.5), marker=dict(size=6),
        ))

    fig.update_layout(
        template="plotly_white", height=420, hovermode="x unified",
        xaxis_title="Competência", yaxis_title="Quantidade",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


@app.callback(
    Output("grafico-ranking-impacto", "figure"),
    Input("filtro-ubs", "value"), Input("filtro-ano", "value"), Input("top-n", "value"),
)
def atualizar_ranking(ubs_selecionadas, anos_selecionados, top_n):
    dados = aplicar_filtros(ubs_selecionadas, anos_selecionados)
    if dados.empty:
        return go.Figure()
    meses = competencias_completas(dados)
    impacto = calcular_impacto(dados, meses)

    if impacto.empty:
        return go.Figure()

    top = impacto.reindex(impacto["DIFF_ABS"].abs().sort_values(ascending=False).index).head(top_n)
    top = top.sort_values("DIFF_ABS")
    top["NOME_ABREVIADO"] = top["NO_PROCEDIMENTO"].apply(lambda t: abreviar(t, limite=45))

    cores = [TERRACOTA if v >= 0 else AZUL_ACO for v in top["DIFF_ABS"]]

    fig = go.Figure(go.Bar(
        x=top["DIFF_ABS"], y=top["NOME_ABREVIADO"], orientation="h",
        marker_color=cores,
        text=[f"{v:+.0f}" for v in top["DIFF_ABS"]], textposition="outside",
        customdata=top["NO_PROCEDIMENTO"],
        hovertemplate="<b>%{customdata}</b><br>Variação: %{x:+.0f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", height=100 + top_n * 35,
        margin=dict(l=20, r=20, t=10, b=20), showlegend=False,
        xaxis_title="Variação absoluta (último mês − primeiro mês)",
    )
    return fig


@app.callback(
    Output("grafico-small-multiples", "figure"),
    Input("filtro-ubs", "value"), Input("filtro-ano", "value"), Input("top-n", "value"),
)
def atualizar_small_multiples(ubs_selecionadas, anos_selecionados, top_n):
    dados = aplicar_filtros(ubs_selecionadas, anos_selecionados)
    if dados.empty:
        return go.Figure()
    meses = competencias_completas(dados)
    impacto = calcular_impacto(dados, meses)

    if impacto.empty:
        return go.Figure()

    top_procs = impacto.reindex(
        impacto["DIFF_ABS"].abs().sort_values(ascending=False).index
    ).head(min(top_n, 8))["NO_PROCEDIMENTO"].tolist()

    n_cols = 4
    n_rows = (len(top_procs) + n_cols - 1) // n_cols

    fig = make_subplots(rows=n_rows, cols=n_cols,
                         subplot_titles=[abreviar(p, limite=28) for p in top_procs])

    for i, proc in enumerate(top_procs):
        serie = (
            dados[dados["NO_PROCEDIMENTO"] == proc]
            .groupby("COMPETENCIA")["QTD_APROVADA"].sum()
            .reindex(meses, fill_value=0).reset_index()
        )
        serie.columns = ["COMPETENCIA", "QTD_APROVADA"]
        row, col = (i // n_cols) + 1, (i % n_cols) + 1
        fig.add_trace(
            go.Scatter(x=serie["COMPETENCIA"], y=serie["QTD_APROVADA"],
                       mode="lines+markers", line=dict(color=DOURADO, width=2),
                       marker=dict(size=4), showlegend=False),
            row=row, col=col,
        )

    fig.update_layout(template="plotly_white", height=200 * n_rows, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_annotations(font_size=11)
    fig.update_xaxes(showticklabels=False)
    return fig


if __name__ == "__main__":
    server = app.server