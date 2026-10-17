import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(
    page_title="Painel de Frequência de Dezenas",
    page_icon="🎯",
    layout="wide"
)

# Estilização visual para os cards e badges de dezenas
st.markdown("""
<style>
    .badge {
        display: inline-block;
        padding: 6px 12px;
        margin: 4px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 15px;
        text-align: center;
        color: #ffffff;
    }
    .badge-red { background-color: #d9383a; }
    .badge-orange { background-color: #e67e22; }
    .badge-yellow { background-color: #f1c40f; color: #2c3e50 !important; }
    .badge-blue { background-color: #2980b9; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Análise e Termômetro de Frequência de Dezenas")
st.write("Faça o upload da sua base de concursos para calcular a frequência e classificar as dezenas por cores.")

# ==========================================
# 1. COMPONENTE DE UPLOAD DE ARQUIVOS
# ==========================================
uploaded_file = st.sidebar.file_uploader(
    "Carregar arquivo de jogos / resultados",
    type=["csv", "xlsx", "xls", "txt"],
    help="Envie um arquivo separado por vírgula, ponto e vírgula, espaço ou colunas de Excel."
)

def extrair_dezenas(arquivo) -> list:
    """Lê diferentes extensões de arquivos e extrai listas de dezenas por linha."""
    jogos = []
    nome = arquivo.name.lower()
    
    if nome.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(arquivo)
        for _, row in df.iterrows():
            numeros = re.findall(r'\b\d{1,2}\b', " ".join(row.astype(str)))
            if numeros:
                jogos.append([int(n) for n in numeros])
    else:
        conteudo = arquivo.getvalue().decode("utf-8", errors="ignore")
        for linha in conteudo.splitlines():
            numeros = re.findall(r'\b\d{1,2}\b', linha)
            if numeros:
                jogos.append([int(n) for n in numeros])
                
    return jogos

if uploaded_file is not None:
    todos_jogos = extrair_dezenas(uploaded_file)
    total_concursos = len(todos_jogos)
    
    if total_concursos == 0:
        st.error("Nenhuma dezena válida foi identificada no arquivo.")
        st.stop()
        
    st.sidebar.success(f"Arquivo lido com sucesso: **{total_concursos}** concursos carregados.")
    
    # ==========================================
    # 2. FILTROS DINÂMICOS
    # ==========================================
    st.sidebar.subheader("Filtros de Análise")
    
    # Filtro de recorte de concursos
    quantidade_jogos = st.sidebar.slider(
        "Considerar últimos N concursos:",
        min_value=1,
        max_value=total_concursos,
        value=min(total_concursos, 100),
        step=1
    )
    
    jogos_selecionados = todos_jogos[-quantidade_jogos:]
    
    # Contagem de ocorrências
    todas_dezenas = [num for jogo in jogos_selecionados for num in jogo]
    frequencias = pd.Series(todas_dezenas).value_counts().sort_index()
    
    df_freq = pd.DataFrame({
        "Dezena": [f"{n:02d}" for n in frequencias.index],
        "Numero": frequencias.index,
        "Ocorrencias": frequencias.values
    })
    
    # Cálculo das faixas estatísticas (Quartis)
    q75 = df_freq["Ocorrencias"].quantile(0.75)
    q50 = df_freq["Ocorrencias"].quantile(0.50)
    q25 = df_freq["Ocorrencias"].quantile(0.25)
    
    def classificar_temperatura(qtd):
        if qtd >= q75:
            return "🔴 Super Quente", "badge-red"
        elif qtd >= q50:
            return "🟠 Alta", "badge-orange"
        elif qtd >= q25:
            return "🟡 Média", "badge-yellow"
        else:
            return "🔵 Fria", "badge-blue"
            
    df_freq[["Classificacao", "Classe_CSS"]] = df_freq["Ocorrencias"].apply(
        lambda x: pd.Series(classificar_temperatura(x))
    )
    
    # Filtro por classificação térmica
    opcoes_classes = ["Todas", "🔴 Super Quente", "🟠 Alta", "🟡 Média", "🔵 Fria"]
    filtro_classe = st.sidebar.selectbox("Filtrar por Categoria Térmica:", opcoes_classes)
    
    df_exibicao = df_freq.copy()
    if filtro_classe != "Todas":
        df_exibicao = df_exibicao[df_exibicao["Classificacao"] == filtro_classe]
        
    df_exibicao = df_exibicao.sort_values(by="Ocorrencias", ascending=False).reset_index(drop=True)

    # ==========================================
    # 3. PAINEL DE VISUALIZAÇÃO E COLORIZAÇÃO
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Concursos Analisados", quantidade_jogos)
    col2.metric("Dezenas Distintas Sorteadas", len(df_freq))
    col3.metric("Maior Volume de Saídas", f"{df_freq['Ocorrencias'].max()} vezes")
    col4.metric("Menor Volume de Saídas", f"{df_freq['Ocorrencias'].min()} vezes")
    
    st.write("---")
    
    # Visão em Grade / Cartela Colorida
    st.subheader("Mapa Visual das Dezenas")
    html_badges = ""
    for _, row in df_exibicao.iterrows():
        html_badges += f'<span class="badge {row["Classe_CSS"]}">{row["Dezena"]} ({row["Ocorrencias"]}x)</span>'
    st.markdown(html_badges, unsafe_allow_html=True)
    
    st.write("---")
    
    # Tabela detalhada com Formatação Condicional
    st.subheader("Tabela de Frequência Detalhada")
    
    def estilo_linhas(row):
        cores = {
            "🔴 Super Quente": "background-color: #fce4e4; color: #a92022; font-weight: bold;",
            "🟠 Alta": "background-color: #fdf2e9; color: #d35400; font-weight: bold;",
            "🟡 Média": "background-color: #fefde8; color: #7d6608; font-weight: bold;",
            "🔵 Fria": "background-color: #eaf2f8; color: #1b4f72; font-weight: bold;"
        }
        cor = cores.get(row["Classificacao"], "")
        return [cor] * len(row)

    colunas_tabela = ["Dezena", "Ocorrencias", "Classificacao"]
    st.dataframe(
        df_exibicao[colunas_tabela].style.apply(estilo_linhas, axis=1),
        use_container_width=True,
        height=400
    )

    # Download dos resultados processados
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_freq[["Dezena", "Ocorrencias", "Classificacao"]].to_excel(writer, index=False, sheet_name="Frequencia")
    
    st.download_button(
        label="📥 Baixar Análise em Excel (.xlsx)",
        data=buffer.getvalue(),
        file_name="frequencia_dezenas_colorida.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Aguardando upload de arquivo. Formatos suportados: `.csv`, `.xlsx`, `.txt`.")
    st.markdown("""
    **Exemplo de formato aceito no arquivo de texto ou planilha:**
    ```text
    04, 10, 18, 25, 33, 52
    02, 11, 25, 34, 41, 60
    10, 18, 22, 36, 44, 51
    ```
    """)
