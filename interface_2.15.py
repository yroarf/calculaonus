import folium
import pandas as pd
import streamlit as st
import locale
import geopandas as gpd
from streamlit_folium import st_folium
import datetime as dt

st.set_page_config(layout='wide')
pd.options.mode.copy_on_write = True

st.title("Cálculo do Ônus Contratual :vibration_mode:")
st.divider()
df_AuxAreaExcl = pd.DataFrame()

listaOP = ['ALGAR', 'BRISANET', 'CLARO', 'LIGGA TELECOM', 'LIGUE','OI','SERCOMTEL', 'TIM', 'VIVO', 'WINITY']

listaAno = list(range(2005, dt.date.today().year))


# ''' _________________________________________________
#           funções de carregamento de dados
# _____________________________________________________'''

##''' carrega na memória cache os dados sobre as áreas de prestação associadas com as populações dos municípios'''

@st.cache_data
def uploadFiles():
    dfAreaPrest_0 = pd.read_csv("df_Mun_UF_Area.csv", dtype=str)
    dfBasePop_0 = pd.read_csv("pop_2014_2021.csv", dtype=str)
    return dfAreaPrest_0, dfBasePop_0


dfAreaPrest = uploadFiles()[0]  # dataframe com a associação dos códigos de município com as áreas de prestação
dfBasePop = uploadFiles()[1]  # dataframe com os quantitativos populacionais associados aos códigos de município

dfAreaPrest.drop('Unnamed: 0', inplace=True, axis=1)
dfBasePop.drop('Unnamed: 0', inplace=True, axis=1)

##### a função geraDF_Final é utilizada para associar o termos aos municipios das áres de prestação

DF_TERMOS = pd.DataFrame(
    columns=['AnoBase', 'Entidade', 'NumTermo', 'AnoTermo', 'UF', 'APrest', 'AExcl', 'MunExcl', 'FreqIni', 'FreqFin',
             'Freq',
             'Banda', 'Tipo'])


def geraDF_Final(
        AnoBase, Entidade, NumTermo, AnoTermo, UF, APrest, AExcl, MunExcl, FreqIni, FreqFin, Freq, BW, Tipo
):
    global DF_TERMOS
    
    ### carrega os municípios do ano base e da UF
    
    DF_ANO_BASE = dfBasePop[dfBasePop['AnoBase'] == AnoBase]
    DF_ANO_BASE_UF = DF_ANO_BASE[DF_ANO_BASE['UF'] == UF]
    DF_AREA_PREST_UF = dfAreaPrest[dfAreaPrest['UF'] == UF]
    DF_AREA_POP = DF_AREA_PREST_UF.merge(DF_ANO_BASE_UF, how='left', on='codMun')
    DF_AREA_POP.drop_duplicates(inplace=True)
    DF_AREA_POP.drop('UF_x', axis=1, inplace=True)
    DF_AREA_POP.rename(columns={'UF_y': 'UF'}, inplace=True)
    
    ### carrega os municípios da área de prestação
    DF_TERMOS_UF_APREST = DF_AREA_POP[DF_AREA_POP['AreaPrestacao'] == APrest]
    
    ############# etapa para excluir os municípios das áeras de exclusão caso existam ####
    
    if AExcl != []:
        
        DFAreaExcl = pd.DataFrame()
        for NomeAreaExc in AExcl:
            #### gera o dataframe com as áreas de exclusão já com os municípios de exclusão
            DFAreaExcl = pd.concat(
                [DFAreaExcl, DF_AREA_POP[DF_AREA_POP['AreaPrestacao'] == NomeAreaExc]])
        
        ###### gera a lista de municípios a serem excluídos
        lista_AExcl_CodMUN = DFAreaExcl['codMun'].unique()
        
        ###### exclui os municípios da área de prestação.
        DF_TERMOS_UF_APREST_AEXCL = DF_TERMOS_UF_APREST.loc[
            ~DF_TERMOS_UF_APREST['codMun'].isin(lista_AExcl_CodMUN)]
    else:
        ##### se não tiver áreas ou municípios de exclusão, o dataframe considera a área de prestação integral
        DF_TERMOS_UF_APREST_AEXCL = DF_TERMOS_UF_APREST
    
    ############# etapa para excluir os municípios individualmente ####
    
    if MunExcl != []:
        DFMunExcl = pd.DataFrame()
        for NomeMunExcl in MunExcl:
            DFMunExcl = pd.concat(
                [DFMunExcl, DF_TERMOS_UF_APREST_AEXCL[DF_TERMOS_UF_APREST_AEXCL['Municipio'] == NomeMunExcl]])
        
        lista_MunExcl_CodMUN_Excl = DFMunExcl['codMun'].unique()
        DF_TERMOS_UF_APREST_AEXCL_MUNEXCL = DF_TERMOS_UF_APREST_AEXCL.loc[
            ~DF_TERMOS_UF_APREST_AEXCL['codMun'].isin(lista_MunExcl_CodMUN_Excl)]
    else:
        DF_TERMOS_UF_APREST_AEXCL_MUNEXCL = DF_TERMOS_UF_APREST_AEXCL
    
    DF_TERMOS = DF_TERMOS_UF_APREST_AEXCL_MUNEXCL
    # print(DF_TERMOS_UF_APREST_AEXCL_MUNEXCL)
    
    DF_TERMOS['AreaExclusao'] = str(AExcl)
    DF_TERMOS['MunExclusao'] = str(MunExcl)
    DF_TERMOS['AnoBase'] = AnoBase
    DF_TERMOS['Entidade'] = Entidade
    DF_TERMOS['NumTermo'] = NumTermo
    DF_TERMOS['AnoTermo'] = AnoTermo
    DF_TERMOS['FreqIni'] = FreqIni
    DF_TERMOS['FreqFin'] = FreqFin
    DF_TERMOS['Freq'] = Freq
    DF_TERMOS['Banda'] = BW
    DF_TERMOS['TIPO'] = Tipo
    
    return DF_TERMOS


### Função para o cálculo do ônus ###

def calculaOnus(AnoBasePop, Entidade, UF, NumTermo, AnoTermo, ROL_UF, dfDadosOnus):
    ### Gera os dataframes com Termo prorrogado e sem o Termo prorrogado para execução do cálculo dos coefientes.
    ################ Seleciona os dados do termo objeto do cálculo do ônus ####################
        
    dfDadosOnus.drop_duplicates(inplace=True)
    dfDadosOnusAnoBase = dfDadosOnus[dfDadosOnus['AnoBase'] == AnoBasePop]

    popTotalPrest = dfDadosOnusAnoBase[['Municipio','popMun']].drop_duplicates()['popMun'].sum()
    
    dfCountFreq = pd.DataFrame(dfDadosOnusAnoBase.Freq.value_counts())
    dfDadosCountFreq = dfDadosOnusAnoBase.merge(dfCountFreq, how='inner', on='Freq') # linha para informar contagem de frequência - auxiliar verificação
    dfTermoOnus_Entidade = dfDadosCountFreq[dfDadosCountFreq['Entidade'] == Entidade]
        
    dfTermoOnus_UF = dfTermoOnus_Entidade[dfTermoOnus_Entidade['UF'] == UF]
    dfTermoOnus_NumTermo = dfTermoOnus_UF[dfTermoOnus_UF['NumTermo'] == NumTermo]
    dfTermoOnus = dfTermoOnus_NumTermo[dfTermoOnus_NumTermo['AnoTermo'] == AnoTermo]
        
    dfTermoOnus['BW_Freq'] = (dfTermoOnus['Banda'] / dfTermoOnus['Freq'])
    
    listaCodMunOnus = list(dfTermoOnus['codMun'].unique())  # gera lista de mun do ônus
    
    ################ Seleciona os demais termos para o cálculo de prorrogação ####################
    
    dfTermoOutros_Entidade = dfDadosCountFreq[dfDadosCountFreq['Entidade'] == Entidade]
    dfTermoOutros_UF = dfTermoOutros_Entidade[dfTermoOnus_Entidade['UF'] == UF]
    dfTermoOutros = dfTermoOutros_UF[dfTermoOnus_UF['NumTermo'] != NumTermo]
    dfTermoOutros['BW_Freq'] = (dfTermoOutros['Banda'] / dfTermoOutros['Freq'])
    
    dfFatorFreqMun = pd.DataFrame()
    resultadoOnusUF = 0
    for codMunOnus in listaCodMunOnus:
        ### fator de proporcionalidade populacional
        
        numFatorpopulacional = dfTermoOnus[dfTermoOnus['codMun'] == codMunOnus]['popMun'].unique()
        FatorPopulacional = numFatorpopulacional/popTotalPrest

        # cálculo do fator de frequência

        NumeradorFreq = np.array(list(dfTermoOnus[dfTermoOnus['codMun'] == codMunOnus]['BW_Freq'])).sum()

        DenominadorFreq = NumeradorFreq + np.array(list(dfTermoOutros[dfTermoOutros['codMun'] == codMunOnus]['BW_Freq'])).sum()
       
        FatorFreq = NumeradorFreq / DenominadorFreq

        onusPorMunicipio = FatorFreq * FatorPopulacional * 0.02 * ROL_UF
        
        resultadoOnusUF = resultadoOnusUF + (onusPorMunicipio)
        
        nomeMun = dfTermoOnus[dfTermoOnus['codMun'] == codMunOnus]['Municipio'].unique()
        
        dfFFAux = pd.DataFrame({'Municipio':nomeMun, 'codMun': codMunOnus,
                                'fatorFreq': FatorFreq, 'fatorPop':FatorPopulacional,
                                'onusMunicipio':onusPorMunicipio})
        dfFatorFreqMun = pd.concat([dfFatorFreqMun, dfFFAux])

    return resultadoOnusUF, dfFatorFreqMun, popTotalPrest


## inicia o dataframe para carregamento dos termos

if 'df_TermosPrg' not in st.session_state:
    df_TermosPrg = pd.DataFrame({
        'AnoBase': [],
        'Entidade': [],
        'NumTermo': [],
        'AnoTermo': [],
        'UF': [],
        'areaPrestacao': [],
        'areaExclusao': [],
        'munExclusao': [],
        'freqInicial': [],
        'freqFinal': [],
        'Freq': [],
        'Banda': [],
        'Tipo': []
    })
    st.session_state.df_TermosPrg = df_TermosPrg


def ad_dfTermoPrg():
    adLinha = pd.DataFrame({
        'AnoBase': [st.session_state.input_anoBase],
        'Entidade': [st.session_state.input_entidade],
        'NumTermo': [st.session_state.input_NumTermo],
        'AnoTermo': [st.session_state.input_AnoTermo],
        'UF': [st.session_state.input_UF],
        'areaPrestacao': [st.session_state.input_areaPrestacao],
        'areaExclusao': [st.session_state.input_areaExcl],
        'munExclusao': [st.session_state.input_munExclusao],
        'freqInicial': [st.session_state.input_freqInicial],
        'freqFinal': [st.session_state.input_freqFinal],
        'Freq': [st.session_state.input_freqFinal - (
                st.session_state.input_freqFinal - st.session_state.input_freqInicial) / 2],
        'Banda': [st.session_state.input_freqFinal - st.session_state.input_freqInicial],
        'Tipo': [st.session_state.input_tipo]
    })
    st.session_state.df_TermosPrg = pd.concat([st.session_state.df_TermosPrg, adLinha])


aba1, aba2, aba3, aba4 = st.tabs(['Cadastro/Carregamento', 'Tabelas', 'Mapas', 'Cálculo do Ônus'])

##''' seção para adicionar linhas pelo usuários'''

with aba1:
    with st.container(border=True):
        dfTermoCol = st.columns(13)
        
        with dfTermoCol[0]:
            
            listaAnoBase = list(dfBasePop['AnoBase'].unique())
            st.selectbox('Ano Base Populacional', options=listaAnoBase, key='input_anoBase')
            
            # cria dataframe com a base populacional do ano selecionado de todo o país
            dfBasePopSel = dfBasePop[dfBasePop['AnoBase'] == st.session_state.input_anoBase]
            listaUF = dfBasePopSel['UF'].unique()  # cria lista das UFs
        
        with dfTermoCol[1]:
            st.selectbox('Operadora', options=listaOP, key='input_entidade')
        
        with dfTermoCol[2]:
            st.text_input('Numero do Termo', key='input_NumTermo', placeholder='Termo')
        
        with dfTermoCol[3]:
            st.selectbox('Ano do Termo', key='input_AnoTermo', options=listaAno)
        
        ### seleciona a UF e gera dataframe das áreas de prestação da UF selecionada
        
        with dfTermoCol[4]:
            
            listaUF.sort()
            UF = st.selectbox('Estado', options=listaUF, key='input_UF')
            
            dfAreaPrestUF_Sel = dfAreaPrest[dfAreaPrest['UF'] == st.session_state.input_UF]
            dfBasePopUF_Sel = dfBasePopSel[dfBasePopSel['UF'] == st.session_state.input_UF]
            dfAreaPopUF = dfAreaPrestUF_Sel.merge(dfBasePopUF_Sel, how='left', on='codMun')
            dfAreaPopUF.drop_duplicates(inplace=True)
            dfAreaPopUF.drop('UF_x', axis=1, inplace=True)
            dfAreaPopUF.rename(columns={'UF_y': 'UF'}, inplace=True)
            # print(dfAreaPopUF)
        ### seleciona a área de prestação
        
        with dfTermoCol[5]:
            
            # cria lista com a expressão "Toda UF" na primeira opção
            listaAreas = list(dfAreaPopUF['AreaPrestacao'].unique())
            
            # seleciona a opção de área de prestação
            st.selectbox('Area de Prestação', options=listaAreas, key='input_areaPrestacao')
            
            # cria o dataframe com a área de prestação relativa a área da UF, que pode ser total ou parcial
            dfAreaPrestacaoSel = dfAreaPopUF[
                dfAreaPopUF['AreaPrestacao'] == st.session_state.input_areaPrestacao]
        
        ########################################
        ### opção de seleção de áreas de exclusão
        ########################################
        
        with dfTermoCol[6]:
            
            ## exclui da lista 'Toda UF' e a área de prestação selecionada
            listaExcl_ini = listaAreas.copy()
            if st.session_state.input_areaPrestacao == 'Toda UF':
                listaExcl_ini.remove('Toda UF')
            else:
                listaExcl_ini.remove('Toda UF')
                listaExcl_ini.remove(st.session_state.input_areaPrestacao)
            
            setAreaPrestacao = set(
                dfAreaPrestacaoSel['codMun'])  # cria conjunto com os códigos de municípios area prest principal
            
            ## elabora lista áreas de exclusão elegíveis e gera o dataframe com as áreas resultantes da exclusão
            
            listaAreasExcl = []
            for areaExcl in listaExcl_ini:
                dfUF_AreasEspec_e_UF_excl = dfAreaPopUF[dfAreaPopUF['AreaPrestacao'] == areaExcl]
                setAreaExcl = set(dfUF_AreasEspec_e_UF_excl[
                                      'codMun'])  # cria conjunto municipios para checar se é subconjunto da AP principal
                
                # compara os subconjuntos por meio dos códigos de município. A expressão equivale a 'menor que'
                if setAreaExcl.issubset(setAreaPrestacao) and setAreaExcl != setAreaPrestacao:
                    listaAreasExcl.append(areaExcl)  # monta a lista de subáreas
            
            areasExcl = st.multiselect('Areas de Exclusão', options=listaAreasExcl, key='input_areaExcl')
            
            if st.session_state.input_areaExcl != []:
                dfAreaExcl = pd.DataFrame()
                for nomeAreaExc in areasExcl:
                    # monta dataframe com as áreas de exclusão selecionadas
                    dfAreaExcl = pd.concat(
                        [dfAreaExcl, dfAreaPopUF[dfAreaPopUF['AreaPrestacao'] == nomeAreaExc]])
                
                lista_CodMUN_Excl = dfAreaExcl['codMun'].unique()  # gera a lista do municipios excluídos
                
                # gera o dataframe com a extração dos municípios excluídos conforme seleção das áreas de exclusão.
                dfAreaPrest_menos_AreasExcl = dfAreaPrestacaoSel.loc[
                    ~dfAreaPrestacaoSel['codMun'].isin(lista_CodMUN_Excl)]
            else:
                dfAreaPrest_menos_AreasExcl = dfAreaPrestacaoSel
        
        ################################################
        ### opção de seleção de municipios para exclusao
        ################################################
        
        with dfTermoCol[7]:
            
            # gera a lista de município com base no resultado entre area de prestação e áreas de exclusão
            
            if st.session_state.input_areaExcl != []:  # ser for sel area de excl, gerar lista municipios prest
                listaMun_excl = dfAreaPrest_menos_AreasExcl['Municipio'].unique()
            else:
                listaMun_excl = dfAreaPrestacaoSel['Municipio'].unique()
            
            mun_excl = st.multiselect('Exclusao de Municipios', options=listaMun_excl, key='input_munExclusao')
            
            if st.session_state.input_munExclusao != []:  #
                dfMunExcl = pd.DataFrame()
                for nomeMunExcl in mun_excl:  # agrupa os municipios excluídos individualmente e monta um dataframe com os mun selecionados.
                    
                    dfMunExcl = pd.concat([dfMunExcl, dfAreaPrest_menos_AreasExcl[
                        dfAreaPrest_menos_AreasExcl['Municipio'] == nomeMunExcl]])
                
                lista_dfMunExcl = dfMunExcl['Municipio'].unique()  # gera a lista de municípios a serem excluídos
                # exclui os municípios da área de prestação
                dfAreaPrestacaoFinal = dfAreaPrest_menos_AreasExcl.loc[
                    ~dfAreaPrest_menos_AreasExcl['Municipio'].isin(lista_dfMunExcl)]
            
            else:
                dfAreaPrestacaoFinal = dfAreaPrest_menos_AreasExcl
            # print(dfAreaPrestacaoFinal)
        ################# fim do bloco de filtros ######################
        
        with dfTermoCol[8]:
            st.number_input('Frequencia Incial', key='input_freqInicial')
        
        with dfTermoCol[9]:
            st.number_input('Frequência Final', key='input_freqFinal')
        
        with dfTermoCol[10]:
            st.number_input('Frequência Central', key='Freq',
                            value=st.session_state.input_freqFinal - (
                                    st.session_state.input_freqFinal - st.session_state.input_freqInicial) / 2,
                            disabled=True)
        
        with dfTermoCol[11]:
            st.number_input('Banda', key='BW',
                            value=st.session_state.input_freqFinal - st.session_state.input_freqInicial, disabled=True)
        
        with dfTermoCol[12]:
            st.selectbox('Tipo', options=['ONUS', 'DEMAIS'], key='input_tipo')
        
        with dfTermoCol[0]:
            st.button('Aplicar', key='buttonTermo')
            
            if st.session_state.buttonTermo:
                ad_dfTermoPrg()
        
        st.session_state.df_TermosPrg.reset_index(drop=True, inplace=True)
        st.data_editor(st.session_state.df_TermosPrg, num_rows='dynamic', key='dfTermoFinal', use_container_width=True,
                       height=300)
        
        ##############################################
        ### rotina para exclusão das linhas deletadas
        ##############################################
        
        if st.session_state.dfTermoFinal["deleted_rows"] != []:
            st.session_state.df_TermosPrg.update(
                st.session_state.df_TermosPrg.drop(st.session_state.dfTermoFinal['deleted_rows'],
                                                   inplace=True), overwrite=True)
        ###############################################
        ### construção do dataframe para o cálculo do ônus
        ###############################################
        
        dfTermos_Atual = pd.DataFrame()
        if not st.session_state.df_TermosPrg.empty:
            
            for i in list(st.session_state.df_TermosPrg.index):
                df_aux = geraDF_Final(
                    st.session_state.df_TermosPrg.loc[i, 'AnoBase'],
                    st.session_state.df_TermosPrg.loc[i, 'Entidade'],
                    st.session_state.df_TermosPrg.loc[i, 'NumTermo'],
                    st.session_state.df_TermosPrg.loc[i, 'AnoTermo'],
                    st.session_state.df_TermosPrg.loc[i, 'UF'],
                    st.session_state.df_TermosPrg.loc[i, 'areaPrestacao'],
                    st.session_state.df_TermosPrg.loc[i, 'areaExclusao'],
                    st.session_state.df_TermosPrg.loc[i, 'munExclusao'],
                    st.session_state.df_TermosPrg.loc[i, 'freqInicial'],
                    st.session_state.df_TermosPrg.loc[i, 'freqFinal'],
                    st.session_state.df_TermosPrg.loc[i, 'Freq'],
                    st.session_state.df_TermosPrg.loc[i, 'Banda'],
                    st.session_state.df_TermosPrg.loc[i, 'Tipo']
                )
                dfTermos_Atual = pd.concat([dfTermos_Atual, df_aux])

with aba2:
    with st.container():
        st.subheader('Tabela de Termos Cadastrados')
        st.dataframe(st.session_state.df_TermosPrg, use_container_width=True)
        st.subheader('Tabela de Municípios')
        st.dataframe(dfTermos_Atual, use_container_width=True)

with aba3:
    try:
        
        st.subheader(':large_green_square: Área de Prestação')
        
        with st.container(height=100):
            col31, col32, col33, col34, col35, col3x, col3y, col3z, col3k, col3l = st.columns(10)
            ############### filtro para apresentar a(s) área(s) de prestação do termo
            with col31:
                # seleciona o termo
                
                termoMapa = st.selectbox('Termo', options=dfTermos_Atual['NumTermo'].unique(), key='inp_termoMapa')
                # monta a matriz com base no termo selecionado
                dftermoMapa = dfTermos_Atual[dfTermos_Atual['NumTermo'] == st.session_state.inp_termoMapa]
            
            with col32:
                # seleciona o ano
                
                anoMapa = st.selectbox('Ano', options=dftermoMapa['AnoTermo'].unique(), key="inp_anoMapa")
                dfAnoMapa = dftermoMapa[dftermoMapa['AnoTermo'] == st.session_state.inp_anoMapa]
            
            with col33:
                # seleciona a UF
                
                UFmapa = st.selectbox('UF', options=dfAnoMapa['UF'].unique(), key='inp_UFmapa')
                dfUFmapa = dfAnoMapa[dfAnoMapa['UF'] == st.session_state.inp_UFmapa]
            
            with col34:
                # seleciona Área de Prestação
                
                AreaPrestMapa = st.selectbox('Área de Prestação', options=dfUFmapa['AreaPrestacao'].unique(),
                                             key='inp_AreaPrestMapa')
                dfAreaPrestMapa = dfUFmapa[dfUFmapa['AreaPrestacao'] == st.session_state.inp_AreaPrestMapa]
                dfAreaPrestMapa_sel = dfAreaPrestMapa[
                    ['codMun', 'AreaPrestacao', 'UF', 'Municipio', 'NumTermo', 'AnoTermo', 'FreqIni',
                     'FreqFin']]
                dfAreaPrestMapa_sel_faixa = dfAreaPrestMapa_sel.copy()
                dfAreaPrestMapa_sel_faixa['FreqIni'] = dfAreaPrestMapa_sel['FreqIni'].apply(lambda x: str(x))
                dfAreaPrestMapa_sel_faixa['FreqFin'] = dfAreaPrestMapa_sel['FreqFin'].apply(lambda x: str(x))
                dfAreaPrestMapa_sel_faixa['Faixa'] = dfAreaPrestMapa_sel_faixa['FreqIni'] + ' - ' + \
                                                     dfAreaPrestMapa_sel_faixa['FreqFin']
            
            with col35:
                # seleciona a faixa de frequência
                
                FreqMapa = st.selectbox('Frequência Inicial', options=dfAreaPrestMapa_sel_faixa['Faixa'].unique(),
                                        key='inp_FreqMapa')
                dfFreqMapa = dfAreaPrestMapa_sel_faixa[
                    dfAreaPrestMapa_sel_faixa['Faixa'] == st.session_state.inp_FreqMapa]
                
                listaCodMunAreaPrest_Mapa = dfFreqMapa['codMun'].unique()
                listaCodMunAreaPrest_Mapa = [str(i) for i in listaCodMunAreaPrest_Mapa]
        
        with st.container(height=600, border=False, ):
            #### Bloco Folium ####
            
            @st.cache_data
            def lerMapa(sessionUF):
                mapa = gpd.read_file(f"SHP_UFs/{sessionUF}.shp")
                return mapa
            
            
            mapa = lerMapa(st.session_state.inp_UFmapa)
            
            geoDF_mapa = gpd.GeoDataFrame(mapa, geometry='geometry', crs='EPSG:3857')
            
            geoDF_AreaPrest_mapa = geoDF_mapa[geoDF_mapa['geocodigo'].isin(listaCodMunAreaPrest_Mapa)]
            
            location = [-15.8, -47.8]
            zoom_start = 4
            
            lonMin, latMin, lonMax, latMax = mapa.total_bounds
            
            mapaFolium = folium.Map(
                location=location,
                no_touch=True,
                tiles='openstreetmap',
                control_scale=True,
                crs='EPSG3857',
                zoom_start=zoom_start,
                key='mapaBase',
                prefer_canvas=False,
                max_bounds=True,
                tooltip='tooltip'
            )
            mapaFolium.fit_bounds([[latMin, lonMin], [latMax, lonMax]])
            
            grupoMapa = folium.FeatureGroup(name='grupoMapa').add_to(mapaFolium)
            
            POLsim_geo = gpd.GeoDataFrame(geoDF_mapa["geometry"]).simplify(tolerance=0.01)
            POLgeo_json = POLsim_geo.to_json()
            POLGeo = folium.GeoJson(data=POLgeo_json, style_function=lambda x: {'fillColor': '#FF0000',
                                                                                "fillOpacity": 0.2,
                                                                                "weight": 0.2,
                                                                                "color": "#B00000"})
            
            ### adiciona a área de prestação
            POLsim_geoTermo = gpd.GeoDataFrame(geoDF_AreaPrest_mapa["geometry"]).simplify(tolerance=0.01)
            POLgeo_jsonTermo = POLsim_geoTermo.to_json()
            POLGeoTermo = folium.GeoJson(data=POLgeo_jsonTermo, style_function=lambda x: {'fillColor': '#4AC423',
                                                                                          "color": "#1C5727",
                                                                                          "fillOpacity": 0.5,
                                                                                          'weight': 0.5})
            
            grupoMapa.add_child(POLGeoTermo)
            grupoMapa.add_child(POLGeo)
            
            mostraMapa = st_folium(mapaFolium,
                                   feature_group_to_add=grupoMapa,
                                   returned_objects=[],
                                   zoom=4,
                                   width=1200,
                                   height=600)
            
    
    except Exception:
        pass

with aba4:
    try:
        with st.container(height=450):
            dfDados = dfTermos_Atual.copy()
            dfDados['popMun'] = dfDados['popMun'].astype(int)
            dfDados['popUF'] = dfDados['popUF'].astype(int)
            dfDados['coefPop'] = dfDados['popMun'] / dfDados['popUF']
            
            st.subheader('Cálculo do ônus')
            st.divider()
            colA, colB, colC, colD, colE, colF = st.columns(6)
            
            with colA: # seleciona o ano da base populacional
                listaAnoBasePop = dfDados['AnoBase'].unique()
                anobase = st.selectbox('Ano da Base Populacional', options=listaAnoBasePop, key='anoBasePop')
                
            with colB:  # seleciona a entidade
                dfListaEntidadeAnoBase = dfDados[dfDados['AnoBase'] == st.session_state.anoBasePop]
                listaEntidades = dfListaEntidadeAnoBase['Entidade'].unique()
                Entidade = st.selectbox('Operadora', options=listaEntidades, key='entidadeOnus')

            with colC:  # seleciona a UF
                
                dflistaEntidadeAnoBaseUF = dfListaEntidadeAnoBase[dfListaEntidadeAnoBase['Entidade'] == st.session_state.entidadeOnus]
                listaEntidadesUF = dflistaEntidadeAnoBaseUF['UF'].unique()
                anoBaseUF = st.selectbox('Estado', options=listaEntidadesUF, key='anoBaseUF')
            
            with colD:  # Seleciona o Termo
                dfListaEntidadeAnoBaseUFTermo = dflistaEntidadeAnoBaseUF[dflistaEntidadeAnoBaseUF['UF'] == st.session_state.anoBaseUF]
                listaTermosEntidadeUF = dfListaEntidadeAnoBaseUFTermo['NumTermo'].unique()
                termo_SEL = st.selectbox('Termo', options=listaTermosEntidadeUF, key='inp_TermoOnus')
                
            with colE:  # Seleciona o ano do Termo
                dfListaEntidadeAnoBaseUFTermoAnoTermo = dfListaEntidadeAnoBaseUFTermo[dfListaEntidadeAnoBaseUFTermo['NumTermo'] == st.session_state.inp_TermoOnus]
                listaEntidadeAnoBaseUFTermoAnoTermo = dfListaEntidadeAnoBaseUFTermoAnoTermo['AnoTermo'].unique()
                anoTermoProrrogado = st.selectbox('Ano do Termo', options=listaEntidadeAnoBaseUFTermoAnoTermo, key='inp_AnoOnus')
            
            with colF:  # Informa a ROL
                ROL = st.number_input("Receita Operacional Líquida (ROL) da UF", value=1000000.00)
            
            with colB:  # Apresenta a identificação do termo que foi calculado o ônus
                st.subheader('')
                st.subheader('')
                st.subheader(
                    f" ÔNUS - Termo {st.session_state.inp_TermoOnus}/{str(st.session_state.inp_AnoOnus).split('.')[0]}")
            
            with colC:  # Executa a rotina de cálculo do ônus por meio da função calculaOnus
                
                onus, dfFatorFreqMun, PopulacaoTotal = calculaOnus(st.session_state.anoBasePop,
                                                   Entidade,
                                                   UF,
                                                   str(st.session_state.inp_TermoOnus),
                                                   st.session_state.inp_AnoOnus,
                                                   ROL,
                                                   dfDados)
                
                st.subheader('')
                st.subheader('')
                st.subheader('R$ {:.2f}'.format(onus))
                st.subheader('')
                # st.subheader(PopulacaoTotal)
                

               
        
        df_tabelaTermosAbaOnus = st.session_state.df_TermosPrg
        df_tabelaTermosAbaOnusAnoBase = df_tabelaTermosAbaOnus[df_tabelaTermosAbaOnus['AnoBase'] == st.session_state.anoBasePop]
        df_tabelaTermosAbaOnusAnoBaseUF = df_tabelaTermosAbaOnusAnoBase[df_tabelaTermosAbaOnusAnoBase['UF'] == st.session_state.anoBaseUF]
        st.dataframe(df_tabelaTermosAbaOnusAnoBaseUF)
        st.dataframe(dfFatorFreqMun)
    except Exception:
        pass


