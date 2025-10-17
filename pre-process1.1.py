### pre_processamento.py
# Reescrito para melhor organização, comentários e clareza
# Lógica original mantida, apenas reorganizado

import pandas as pd
import geopandas as gpd
import os

# ---------------------------
# Função: Carregar dados do Excel
# ---------------------------
def load_data(excel_path: str = r'datasets\dados_abertos_psr_2025.xlsx') -> pd.DataFrame:
    """
    Carrega os dados de seguros do Excel e retorna um DataFrame.
    """
    df = pd.read_excel(excel_path)
    return df


# ---------------------------
# Função: Carregar shapefile dos estados
# ---------------------------
def load_geodata(shapefile_path: str = r'datasets/BR_UF_2024.shp') -> gpd.GeoDataFrame:
    """
    Carrega o shapefile dos estados e retorna um GeoDataFrame.
    """
    gdf = gpd.read_file(shapefile_path)
    return gdf


# ---------------------------
# Função: Limpeza básica e conversão de tipos
# ---------------------------
def clean_and_convert(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove colunas desnecessárias e converte valores numéricos que vieram como strings
    """
    # Colunas que não vamos usar
    drop_cols = [
        'CD_PROCESSO_SUSEP', 'NR_PROPOSTA', 'ID_PROPOSTA', 'DT_PROPOSTA',
        'DT_INICIO_VIGENCIA', 'DT_FIM_VIGENCIA', 'NM_SEGURADO', 'NR_DOCUMENTO_SEGURADO',
        'LATITUDE', 'NR_GRAU_LAT', 'NR_MIN_LAT', 'NR_SEG_LAT',
        'LONGITUDE', 'NR_GRAU_LONG', 'NR_MIN_LONG', 'NR_SEG_LONG',
        'NR_DECIMAL_LATITUDE', 'NR_DECIMAL_LONGITUDE', 'NivelDeCobertura', 'DT_APOLICE',
        'ANO_APOLICE', 'CD_GEOCMU'
    ]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # Converter colunas numéricas com vírgula para float
    numeric_cols = ['NR_AREA_TOTAL', 'VL_PREMIO_LIQUIDO']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Corrigir coluna de animais para evitar erro no Parquet
    if 'NR_ANIMAL' in df.columns:
        df['NR_ANIMAL'] = pd.to_numeric(df['NR_ANIMAL'], errors='coerce')

    return df


# ---------------------------
# Função: Agregações principais
# ---------------------------
def aggregate_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega dados por estado: área total, valor total e número de seguros.
    """
    df_estado = df.groupby('SG_UF_PROPRIEDADE').agg(
        area_total=('NR_AREA_TOTAL', 'sum'),
        valor_total=('VL_PREMIO_LIQUIDO', 'sum'),
        numero_seguros=('NR_APOLICE', 'nunique')
    ).reset_index()
    return df_estado


# ---------------------------
# Função: Simplificar geometria do GeoDataFrame
# ---------------------------
def simplify_geometry(gdf: gpd.GeoDataFrame, tolerance: float = 0.01) -> gpd.GeoDataFrame:
    """
    Simplifica a geometria do GeoDataFrame para reduzir tamanho do arquivo e melhorar performance.
    """
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=tolerance, preserve_topology=True)
    return gdf


# ---------------------------
# Executando o pré-processamento
# ---------------------------
# Carregar dados
df = load_data()
gdf = load_geodata()

# Limpar e converter colunas
df = clean_and_convert(df)

# Agregação por estado
df_estado = aggregate_by_state(df)

# Merge GeoDataFrame com dados de estado
if 'SIGLA_UF' in gdf.columns and 'SG_UF_PROPRIEDADE' in df_estado.columns:
    gdf = gdf.merge(df_estado, left_on='SIGLA_UF', right_on='SG_UF_PROPRIEDADE', how='left')

# Simplificar geometria para exportação
gdf = simplify_geometry(gdf, tolerance=0.01)

# Salvar arquivos para uso no Streamlit ou análise futura
df.to_parquet('assets/dados_v2.parquet', index=False)
gdf.to_file('assets/BR_UF_2024_simplificado.geojson', driver='GeoJSON')

# ---------------------------
# Observações:
# ---------------------------
# - df_estado: pronto para uso em dashboards (área total, valor total, número de seguros por estado)
# - gdf: pronto para plotagem no folium/plotly
# - df: dados limpos e convertidos, pronto para análises adicionais
# - Facilita manutenção futura e adição de novas métricas sem modificar lógica principal