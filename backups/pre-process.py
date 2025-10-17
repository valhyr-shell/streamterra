### pre processamento

import pandas as pd
import geopandas as gpd

########################
### FUNCAO CSV EXCEL ALVO
def load_data():
    df = pd.read_excel(r'datasets\dados_abertos_psr_2025.xlsx')
    return df

df = load_data()

df.drop(columns=[
    'CD_PROCESSO_SUSEP', 'NR_PROPOSTA', 'ID_PROPOSTA', 'DT_PROPOSTA',
    'DT_INICIO_VIGENCIA', 'DT_FIM_VIGENCIA', 'NM_SEGURADO', 'NR_DOCUMENTO_SEGURADO',
    'LATITUDE', 'NR_GRAU_LAT', 'NR_MIN_LAT', 'NR_SEG_LAT',
    'LONGITUDE', 'NR_GRAU_LONG', 'NR_MIN_LONG', 'NR_SEG_LONG',
    'NR_DECIMAL_LATITUDE', 'NR_DECIMAL_LONGITUDE', 'NivelDeCobertura', 'DT_APOLICE',
    'ANO_APOLICE', 'CD_GEOCMU'
], inplace=True)

df.columns

cols = ['NR_AREA_TOTAL', 'VL_PREMIO_LIQUIDO']
df[cols] = df[cols].replace(',', '.', regex=True).astype(float)

#### agrupamento dos dados por estado
df_estado = df.groupby('SG_UF_PROPRIEDADE').agg(
    area_total = ('NR_AREA_TOTAL', 'sum'),
    valor_total = ('VL_PREMIO_LIQUIDO', 'sum'),
    numero_seguros = ('NR_APOLICE', 'nunique')
).reset_index()

#### unir o gdf com o df
gdf = gdf.merge (df_estado, left_on'SIGLA_UF', right='SG_UF_PROPRIEDADE', how='left')


# Conserta a coluna NR_ANIMAL para evitar erro no Parquet
if 'NR_ANIMAL' in df.columns:
    df['NR_ANIMAL'] = pd.to_numeric(df['NR_ANIMAL'], errors='coerce')

df.to_parquet('assets/dados_v2.parquet')

#########################
### FUNCAO ESTADOS BRASIL
def load_geodata():
    return gpd.read_file('datasets/BR_UF_2024.shp')
 
gdf = load_geodata()

tolerancia = 0.01

gdf['geometry'] = gdf['geometry'].simplify(tolerance=tolerancia,
                                        preserve_topology=True)

gdf.to_file('assets/teste.geojson', driver= 'GeoJSON')