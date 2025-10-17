# app.py
# Reescrito e organizado por ChatGPT — versão pronta para colar no VS Code
# Mantive a lógica original e corrigi problemas de sintaxe e propriedades inválidas.

import os
import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
import matplotlib.cm as cm
import matplotlib.colors as mcolors

# ---------------------------
# Configuração inicial
# ---------------------------
st.set_page_config(layout="wide")
# 🔧 Editável: caminho do logo (relativo à pasta do app)
if os.path.exists("assets/logo.jpg"):
    st.sidebar.image("assets/logo.jpg")
st.title("Super teste")

# ---------------------------
# Carregamento de dados
# ---------------------------

#Carregar CSV EXCEL

@st.cache_data
def load_data(parquet_path: str = r"assets/dados_filtrados.parquet") -> pd.DataFrame:
    """Carrega o dataframe principal (parquet)."""
    df = pd.read_parquet(parquet_path)
    return df


#Carregar Shapefile estados

@st.cache_data
def load_geodata(geojson_path: str = "assets/BR_UF_2024_Filtrado.geojson") -> gpd.GeoDataFrame:
    """Carrega o GeoDataFrame dos estados (GeoJSON)."""
    return gpd.read_file(geojson_path)

#Editável: altere os caminhos se necessário
df = load_data()
gdf = load_geodata()

# Mostrar um preview (você pode comentar se não quiser exibir)
#st.dataframe(df.head(200))

# ---------------------------
# Pré-processamento e agregações
# ---------------------------

# 1) Agregação por estado
df_estado = df.groupby("SG_UF_PROPRIEDADE").agg(
    area_total=("NR_AREA_TOTAL", "sum"),
    valor_total=("VL_PREMIO_LIQUIDO", "sum"),
    numero_seguros=("NR_APOLICE", "nunique"),
).reset_index()

# 2) Merge do GeoDataFrame com a tabela agregada por UF
#Editável: se o seu geojson usa outra propriedade para sigla, ajuste 'SIGLA_UF'
gdf = gdf.merge(df_estado, left_on="SIGLA_UF", right_on="SG_UF_PROPRIEDADE", how="left")

# 3) Agregação por razão social
df_razao_social = df.groupby("NM_RAZAO_SOCIAL").agg(
    numero_seguros=("NR_APOLICE", "nunique"),
    area_total=("NR_AREA_TOTAL", "sum"),
    valor_total=("VL_PREMIO_LIQUIDO", "sum"),
    estados=("SG_UF_PROPRIEDADE", "unique"),
).reset_index()
df_razao_social["contagem_estados"] = df_razao_social["estados"].apply(len)

# 4) Agregação por razão social + estado (caso precise)
df_razao_social_estado = df.groupby(["NM_RAZAO_SOCIAL", "SG_UF_PROPRIEDADE"]).agg(
    numero_seguros=("NR_APOLICE", "sum"),
    area_total=("NR_AREA_TOTAL", "sum"),
    valor_total=("VL_PREMIO_LIQUIDO", "sum"),
).reset_index()

# 5) Conversão de colunas numéricas que vêm com vírgula (se houver)
correlation_columns = [
    "NR_AREA_TOTAL",
    "VL_PREMIO_LIQUIDO",
    "VL_LIMITE_GARANTIA",
    "NR_PRODUTIVIDADE_ESTIMADA",
    "NR_PRODUTIVIDADE_SEGURADA",
    "VL_SUBVENCAO_FEDERAL",
]
for col in correlation_columns:
    if col in df.columns:
        # tentar converter, ignorando valores que já são numéricos
        df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Matriz de correlação (apenas entre as colunas disponíveis)
available_corr_cols = [c for c in correlation_columns if c in df.columns]
if available_corr_cols:
    correlation_matrix = df[available_corr_cols].corr().round(2)
else:
    correlation_matrix = pd.DataFrame()  # vazio, caso não existam colunas

# ---------------------------
# Layout principal do Streamlit
# ---------------------------

st.title("Avaliações Rurais - Terra Soluções")
st.markdown(
    """A Terra Soluções é fruto de uma sociedade de dois grandes engenheiros agrônomos,
    apadrinhados e apresentados por um dos mais renomados especialistas na Avaliação de Imóveis Rurais,
    o **Eng. Agrônomo e Prof. Doutor Valdemar Antônio Demétrio**, da Escola Superior de Agricultura “Luiz de Queiroz” (ESALQ/USP)."""
)
st.markdown(
    """Em 06/04/2011, os Engenheiros Agrônomos Henrique Sundfeld Barbin e Luis Augusto Calvo de Moura Andrade,
    que já trabalhavam na área de avaliações há 8 anos, inauguraram a **Terra Soluções Ambientais e Agrárias**."""
)

st.divider()

# ---------------------------
# Sidebar de controles
# ---------------------------
with st.sidebar:
    st.subheader("SISSER - Sistema de Subvenção Econômica ao Prêmio do Seguro Rural.")
    analise_tipo = st.selectbox("Selecione o tipo de análise", ["Razão Social", "Estado"])

# ---------------------------
# Lógica de exibição: Razão Social
# ---------------------------
if analise_tipo == "Razão Social":
    st.header("Análise por Razão Social")

    # Dicionário de métricas
    metric_options = {
        "Número de Seguros": "numero_seguros",
        "Contagem de Estados": "contagem_estados",
        "Área Total": "area_total",
    }

    # Top estados (defensivo: verifica existência)
    top_estado_num_apolice= df_estado.loc[df_estado['numero_seguros'].idxmax()]
    top_estado_area_total = df_estado.loc[df_estado['area_total'].idxmax()]
    top_estado_valor_total = df_estado.loc[df_estado['valor_total'].idxmax()]

    # Exibir resumo na sidebar (defensivo: checa None)
    with st.sidebar:
        if top_estado_num_apolice is not None:
            st.markdown(
                f"**Estado com maior número de Avaliações:** {top_estado_num_apolice['SG_UF_PROPRIEDADE']} "
                f"com {int(top_estado_num_apolice['numero_seguros'])} apólices.\n\n"
            )
        if top_estado_area_total is not None:
            st.markdown(
                f"**Estado com maior área total assegurada:** {top_estado_area_total['SG_UF_PROPRIEDADE']} "
                f"com {top_estado_area_total['area_total']:.2f} ha.\n\n"
            )
        if top_estado_valor_total is not None:
            st.markdown(
                f"**Estado com maior valor total assegurado:** {top_estado_valor_total['SG_UF_PROPRIEDADE']} "
                f"com R$ {top_estado_valor_total['valor_total']:.2f}.\n\n"
            )

    # Dropdown de métricas
    selected_metric = st.selectbox("Selecione a Métrica", options=list(metric_options.keys()))
    metric_column = metric_options[selected_metric]

    # Ordenar dataframe por métrica selecionada
    df_sorted = df_razao_social.sort_values(by=metric_column, ascending=False)

    # ---------------------------
    # Gráfico de barras (Razão social)
    # ---------------------------
    #Editável: palette/scale. Usar 'Viridis' ou 'Blues' se preferir.
    fig_bar = px.bar(
        df_sorted,
        x="NM_RAZAO_SOCIAL",
        y=metric_column,
        title=f"{selected_metric} por razão social",
        labels={"NM_RAZAO_SOCIAL": "Razão Social", metric_column: selected_metric},
        color=metric_column,
        color_continuous_scale="Viridis",
    )

    fig_bar.update_layout(
        template="plotly_white",
        title=dict(text=f"{selected_metric} por Razão Social", x=0.5, font=dict(size=18)),
        xaxis=dict(tickangle=45, automargin=True, tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11), gridcolor="rgba(200,200,200,0.3)"),
        coloraxis=dict(
            colorbar=dict(
                title=dict(text=selected_metric, font=dict(size=12, color="#333")),
                tickfont=dict(size=11, color="#555"),
            )
        ),
        bargap=0.25,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, b=150),
    )

    fig_bar.update_traces(
        texttemplate="%{y:.2f}",
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>" + selected_metric + ": %{y:.2f}<extra></extra>",
    )

    st.plotly_chart(fig_bar, use_container_width=True)
    st.divider()

    # ---------------------------
    # Métricas (cards)
    # ---------------------------
    # Calcula top/mean/var para exibir nos cards (defensivo)
    max_num_seguros = df_razao_social['numero_seguros'].max()
    mean_num_seguros = df_razao_social['numero_seguros'].mean()
    var_num_seguros = ((max_num_seguros - mean_num_seguros) / mean_num_seguros) * 100
    top_razao_num_seguros = df_razao_social.loc[
        df_razao_social['numero_seguros'] == max_num_seguros, 'NM_RAZAO_SOCIAL'
    ].values[0]

    # Cálculos para contagem de estados
    max_count_estados = df_razao_social['contagem_estados'].max()
    mean_count_estados = df_razao_social['contagem_estados'].mean()
    var_count_estados = ((max_count_estados - mean_count_estados) / mean_count_estados) * 100
    top_razao_count_estados = df_razao_social.loc[
        df_razao_social['contagem_estados'] == max_count_estados, 'NM_RAZAO_SOCIAL'
    ].values[0]

    # Cálculos para área total
    max_area_total = df_razao_social['area_total'].max()
    mean_area_total = df_razao_social['area_total'].mean()
    var_area_total = ((max_area_total - mean_area_total) / mean_area_total) * 100
    top_razao_area_total = df_razao_social.loc[
    df_razao_social['area_total'] == max_area_total, 'NM_RAZAO_SOCIAL'
    ].values[0]

    ### cartoes metricas
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric(
                label = f"Máximo número de seguros - {top_razao_num_seguros}",
                value = f"{max_num_seguros:.0f}",
                delta = f"{var_num_seguros:.2f}% em relação à média"

            )
    with col2:
        with st.container(border=True):
            st.metric(
                label = f"Maximo Contagem Estados- {top_razao_count_estados}",
                value = f"{max_count_estados:.0f}",
                delta = f"{var_count_estados:.2f}% em relação à média"

            )
    with col3:
        with st.container(border=True):
            st.metric(
                label = f"Maximo Area Total - {top_razao_area_total}",
                value = f"{max_area_total:.0f}",
                delta = f"{var_area_total:.2f}% em relação à média"

            )

    st.divider()

    # Heatmap de correlação
    # ---------------------------
    st.subheader('çorrelacao entre parametros')
    fig_heatmap = px.imshow(correlation_matrix, text_auto='True',
                                color_continuous_scale='Blues',
                                title='çorrelacao entre parametros',
                                width=400, height=800)
    st.plotly_chart(fig_heatmap, use_container_width=True)

# ============================================================
# MAPAS E GRÁFICO DE PIZZA — BLOCO VISUAL PRINCIPAL
# ============================================================

# Cria duas colunas de tamanho igual
    col1, col2 = st.columns([1, 1])

# ---------------------------
# Coluna 1 — Mapa de área total assegurada
# ---------------------------
    with col1:
        st.subheader('Área Total Assegurada por Estado')

        m_area = folium.Map(location=[-15.78, -47.93], zoom_start=3)

        folium.Choropleth(
            geo_data=gdf,
            name='Área Total',
            data=df_estado,
            columns=['SG_UF_PROPRIEDADE', 'area_total'],
            key_on='feature.properties.SIGLA_UF',
            fill_color='BuPu',
            fill_opacity=0.7,
            line_opacity=0.4,
            line_color='black',
            legend_name='Área total assegurada (ha)',
            bins=4,
            reset=True
        ).add_to(m_area)

        folium_static(m_area, width=880, height=600)

# ---------------------------
# Coluna 2 — Mapa + Gráfico de Pizza
# ---------------------------
    with col2:
        st.subheader('Número de Seguros por Estado')

        m_seguros = folium.Map(location=[-15.78, -47.93], zoom_start=3)

        folium.Choropleth(
            geo_data=gdf,
            name='Número de Seguros',
            data=df_estado,
            columns=['SG_UF_PROPRIEDADE', 'numero_seguros'],
            key_on='feature.properties.SIGLA_UF',
            fill_color='YlGnBu',
            fill_opacity=0.7,
            line_opacity=0.4,
            line_color='white',
            legend_name='Número de Seguros',
            bins=4,
            reset=True
        ).add_to(m_seguros)

        folium_static(m_seguros, width=880, height=600)

        # ---------------------------
        # Gráfico de Pizza
        # ---------------------------
        st.markdown("---")
        st.subheader('Distribuição do Valor Total Assegurado por Razão Social')

        fig_pie_valor = px.pie(
            df_razao_social,
            names='NM_RAZAO_SOCIAL',
            values='valor_total',
            title='Distribuição do Valor Total Assegurado',
        )

        # Layout da legenda e estética do gráfico
        fig_pie_valor.update_layout(
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.4,
                xanchor="center",
                x=0.5,
                itemsizing='constant',
                traceorder='normal',
                itemclick='toggle',
                font=dict(size=9),
                title=None,
                bgcolor='rgba(255,255,255,0)'
            ),
            title=dict(x=0.5, font=dict(size=16)),
        )

        st.plotly_chart(fig_pie_valor, use_container_width=True, key="grafico_pizza_valor_total")

# ============================================================
# Análise por Estado
# ============================================================

else:
    st.header('Análise por Estado')

    # seletor de estado 
    estado_escolhido = st.sidebar.selectbox("Selecione um Estado", df["SG_UF_PROPRIEDADE"].unique())

    # Filtrar os dados para o estado selecionado
    df_estado = df_razao_social_estado[df_razao_social_estado['SG_UF_PROPRIEDADE'] == estado_escolhido]

    # Ajustar por município no estado selecionado (top 10)
    df_municipio = (df[df['SG_UF_PROPRIEDADE'] == estado_escolhido].groupby('NM_MUNICIPIO_PROPRIEDADE', as_index=False).agg(
        area_total=('NR_AREA_TOTAL', 'sum'),
        valor_total=('VL_PREMIO_LIQUIDO', 'sum')
    )).reset_index(drop=True)

    #selecionando os top 10
    df_top_area = df_municipio.nlargest(10, 'area_total')
    df_top_valor = df_municipio.nlargest(10, 'valor_total')

    #combinar os top 10 de area para uma lista unica
    df_top_combined = pd.concat([df_top_area, df_top_valor]).drop_duplicates()
                                        
    #correlacao entre ara total e valor total
    correlation_top_municipios = df_top_combined[['area_total', 'valor_total']].corr().iloc[0,1]

    #divisores
    st.sidebar.divider()
    st.sidebar.subheader('Analise exploratoria dos dados')
    st.sidebar.markdown(f'Analisando os dados de area total e premio liquido')
    st.sidebar.divider()

# Cria duas colunas de tamanho igual

    col1, col2 = st.columns(2)
# ------------------------------------------
# Coluna 1 — Top 10 Municípios com Maior Área
# ------------------------------------------
    with col1:
        fig_top_area = px.bar(df_top_area, x='NM_MUNICIPIO_PROPRIEDADE', y='area_total',
                            title=f'Top 10 Municípios com Maior Área em {estado_escolhido}',
                            labels={'NM_MUNICIPIO_PROPRIEDADE': 'Município','area_total': 'Área Total (ha)'},
                            text_auto='.2s')
        fig_top_area.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_top_area, use_container_width=True, key="grafico_top_area")

# ------------------------------------------
# Coluna 2 — Top 10 Municípios com Maior Valor Total
# ------------------------------------------
    with col2:
        fig_top_valor = px.bar(df_top_valor, x='NM_MUNICIPIO_PROPRIEDADE', y='valor_total',
                            title=f'Top 10 Municípios com Maior Valor Total em {estado_escolhido}',
                            labels={'NM_MUNICIPIO_PROPRIEDADE': 'Município','valor_total': 'Valor Total (R$)'            },
                            text_auto='.2s')
        fig_top_valor.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_top_valor, use_container_width=True, key="grafico_top_valor")


# ------------------------------------------
# Coluna 2 — Top 10 Municípios com Maior Valor Total
# ------------------------------------------

    fig_bar_estados_seguros = px.bar(df_estado, x='NM_RAZAO_SOCIAL', y='numero_seguros',
                                      title=f'Numero de seguros em {estado_escolhido} por razao social',
                                      labels={'NM_RAZAO_SOCIAL': 'Razao Social', 'numero_seguros': 'numero de seguros'},
                                      text_auto='.2s')
    fig_bar_estados_seguros.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_bar_estados_seguros, use_container_width=True, key="grafico_estados_seguros")