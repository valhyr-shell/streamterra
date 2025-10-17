import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import mapclassify
import os
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt


###Configurar pagina
st.set_page_config(layout='wide')
st.sidebar.image('assets/logo.jpg')
st.title('Super teste')

###Carregar arquivos

#Carregar CSV EXCEL
@st.cache_data
def load_data():
    df = pd.read_parquet(r'assets/dados_filtrados.parquet')
    return df

df = load_data()
st.dataframe(df)

#Carregar Shapefile
@st.cache_data
def load_geodata():
    return gpd.read_file('assets/BR_UF_2024_Filtrado.geojson')
 
gdf = load_geodata()

### Tratando os Dados

#### agrupamento dos dados por estado
df_estado = df.groupby('SG_UF_PROPRIEDADE').agg(
    area_total = ('NR_AREA_TOTAL', 'sum'),
    valor_total = ('VL_PREMIO_LIQUIDO', 'sum'),
    numero_seguros = ('NR_APOLICE', 'nunique')
).reset_index()

#### unir o gdf com o df
gdf = gdf.merge(df_estado, left_on='SIGLA_UF', right_on='SG_UF_PROPRIEDADE', how='left')

#### agrupamento dos dados por razao social
df_razao_social = df.groupby('NM_RAZAO_SOCIAL').agg(
    numero_seguros = ('NR_APOLICE', 'nunique'),
    area_total = ('NR_AREA_TOTAL', 'sum'),
    valor_total = ('VL_PREMIO_LIQUIDO', 'sum'),
    estados = ('SG_UF_PROPRIEDADE', 'unique')
).reset_index()

df_razao_social['contagem_estados'] = df_razao_social['estados'].apply(len)

#### agrupamento dos dados por razao social estado
df_razao_social_estado = df.groupby(['NM_RAZAO_SOCIAL','SG_UF_PROPRIEDADE']).agg(
    numero_seguros = ('NR_APOLICE', 'sum'),
    area_total = ('NR_AREA_TOTAL', 'sum'),
    valor_total = ('VL_PREMIO_LIQUIDO', 'sum'),
).reset_index()

correlation_columns = [
    'NR_AREA_TOTAL', 'VL_PREMIO_LIQUIDO',
    'VL_LIMITE_GARANTIA', 'NR_PRODUTIVIDADE_ESTIMADA',
    'NR_PRODUTIVIDADE_SEGURADA', 'VL_SUBVENCAO_FEDERAL']

for col in correlation_columns:
    df[col] = df[col].replace(',', '.', regex=True).astype(float)

#Gerar a matriz de correlacao arredondada
correlation_matrix = df[correlation_columns].corr().round(2)

#####################################################################################
#####################################################################################
## MONTAGEM DO STREAMLIT
#####################################################################################
#####################################################################################

st.title('Avaliaçoes Rurais - Terra Solucoes')
st.markdown('''A Terra Soluções é fruto de uma sociedade de dois grandes engenheiros agrônomos, 
            apadrinhados e apresentados por um dos mais renomados especialistas na Avaliação de Imóveis Rurais, 
            o **Eng. Agrônomo e Prof. Doutor Valdemar Antônio Demétrio**, da Escola Superior de Agricultura “Luiz de Queiroz” (ESALQ/USP).''')

st.markdown('''Em 06/04/2011, os Engenheiros Agrônomos Henrique Sundfeld Barbin e Luis Augusto Calvo de Moura Andrade, que já trabalhavam na área de avaliações há 8 anos, 
            inauguraram a **Terra Soluções Ambientais e Agrárias**, 
            empresa que com muito orgulho, trabalho, honestidade e ética, prosperaram neste mercado das avaliações e perícias por todo Brasil.''')

st.divider()

with st.sidebar:
    st.subheader("SISSER - Sistema de Subvenção Econômica ao Prêmio do Seguro Rural.")
    analise_tipo = st.selectbox("Selecione o tipo de análise", ["Razão Social", "Estado"])

#####################################################################################
#####################################################################################
# Analise por razao social

if analise_tipo =='Razão Social':
    st.header('Ánalise por Razao Social')

    #Dicionário de metricas (opcoes que o usuario pode selecionar)
    metric_options = {
    'Número de Seguros': 'numero_seguros',
    'Contagem de Estados': 'contagem_estados',
    'Área Total': 'area_total'
    }

    top_estado_num_apolice= df_estado.loc[df_estado['numero_seguros'].idxmax()]
    top_estado_area_total = df_estado.loc[df_estado['area_total'].idxmax()]
    top_estado_valor_total = df_estado.loc[df_estado['valor_total'].idxmax()]



    with st.sidebar:
        st.markdown(
            f"**Estado com maior numero de Avaliacoes:** {top_estado_num_apolice['SG_UF_PROPRIEDADE']}"
            f"com {top_estado_num_apolice['numero_seguros']} apolices.\n\n"

            f"**Estado com maior área total assegurada:** {top_estado_area_total['SG_UF_PROPRIEDADE']} "
            f",com {top_estado_area_total['area_total']:.2f} ha.\n\n"

            f"**Estado com maior valor total assegurada:** {top_estado_area_total['SG_UF_PROPRIEDADE']} "
            f",com R$ {top_estado_area_total['valor_total']:.2f} ha."
        )

        ### Menu dropdown para o usuario selecionar as metricas desejadas
    selected_metric = st.selectbox("Selecione a Métrica", options=list(metric_options.keys()))
    metric_column = metric_options[selected_metric]

    #ordenar os dados do dataframe por ordem decrescente com base na metrica selecinada
    df_sorted = df_razao_social.sort_values(by=metric_column, ascending=False)

    #################################################################################
    #graficos razao social

    fig_bar = px.bar(
        df_sorted, x= 'NM_RAZAO_SOCIAL', y=metric_column,
        title=f'{selected_metric} por razao social',
        labels={'NM_RAZAO_SOCIAL': 'razao social', metric_column:selected_metric},
        
        color=metric_column,
        color_continuous_scale='Tealgrn'
    )

    fig_bar.update_layout(
        template='plotly_white',
        title=dict(
            text=f"{selected_metric} por Razão Social",
            x=0.5,
            font=dict(size=20, color='#333', family='Arial')
        ),
        xaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=11, color='#555'),
            tickangle=45,
            automargin=True
        ),
        yaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=11, color='#555'),
            gridcolor='rgba(200,200,200,0.3)'
        ),
        coloraxis=dict(
            colorbar=dict(
                title=dict(
                    text=selected_metric,
                    font=dict(size=12, color='#333')
                ),
                tickfont=dict(size=11, color='#555')
            )
        ),
        bargap=0.3,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    fig_bar.update_traces(
        texttemplate='%{y:.2f}',
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>' + selected_metric + ': %{y:.2f}<extra></extra>'
    )

    st.plotly_chart(fig_bar, use_container_width=True)
    st.divider()

    #################################################################################
    #          Metricas
    
    # Cálculos para número de seguros
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

    #################################################################################
    #         Grafico Correlacao

    st.subheader('çorrelacao entre parametros')
    fig_heatmap = px.imshow(correlation_matrix, text_auto='True',
                            color_continuous_scale='Blues',
                            title='çorrelacao entre parametros',
                            width=400, height=800)
    st.plotly_chart(fig_heatmap, use_container_width=True)

    3#################################################################################
    #        Mapa e grafico de pizza

    col1, col2 = st.columns([1,1])

    # Coluna 1
    with col1:
        m_valor = folium.Map(location=[-15.78, -47.93], zoom_start=3)

        folium.Choropleth(
            geo_data=gdf,
            name='choropleth',
            data=df_estado,
            columns=['SG_UF_PROPRIEDADE', 'area_total'],
            key_on='feature.properties.SIGLA_UF',
            fill_color='BuPu',
            fill_opacity=0.7,
            line_opacity=0.4,
            line_color='black',
            legend_name='Valor Total Assegurado',
            bins=4,
            reset=True
        ).add_to(m_valor)

        st.subheader('Area total Asseguradao')
        folium_static(m_valor, width=880, height=600)

    # Coluna 2
    with col2:
        m_valor = folium.Map(location=[-15.78, -47.93], zoom_start=3)

        folium.Choropleth(
            geo_data=gdf,
            name='choropleth',
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
        ).add_to(m_valor)

        st.subheader('Numero Seguros')
        folium_static(m_valor, width=880, height=600)

    #grafico de pizza
    with col2:
        with st.container(border=True):
            fig_pie_valor = px.pie(
                df_razao_social,
                names='NM_RAZAO_SOCIAL',
                values='valor_total',
                title='distribuicao do valor total assegurado por razao social'
            )

            ## layout graficao de pizza
            fig_pie_valor.update_layout(
                legend=dict(
                    orientation="h",        # legenda horizontal
                    yanchor="top",          # ancoragem vertical
                    y=-0.4,                 # posição vertical
                    xanchor="center",       # ancoragem horizontal
                    x=0.5,                  # posição horizontal
                    itemsizing='constant',  # tamanho constante dos itens
                    traceorder='normal',    # ordem normal de exibição
                    itemclick='toggle',     # clicável para esconder/mostrar
                    font=dict(size=9),      # tamanho da fonte
                    title=None,             # sem título
                    bgcolor='rgba(255,255,255,0)'  # fundo transparente
                )
            )
            
            st.plotly_chart(fig_pie_valor, use_container_width=True)

#####################################################################################
#####################################################################################
# Analise por estado
else:
    st.header('Ánalise por Estado')