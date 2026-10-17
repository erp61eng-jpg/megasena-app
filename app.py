import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(
    page_title="Filtrador de Jogos por Temperatura de Dezenas",
    page_icon="🎯",
    layout="wide"
)

# Estilização CSS para as dezenas coloridas (Pills/Badges)
st.markdown("""
<style>
    .dezena-box {
        display: inline-block;
        width: 38px;
        height: 38px;
        line-height: 38px;
        text-align: center;
        border-radius: 50%;
        margin: 2px 4px;
        font-weight: 700;
        font-size: 15px;
        color: #ffffff !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.25);
    }
    .quente { background-color: #d63031; } /* Vermelho */
    .media  { background-color: #e67e22; } /* Laranja / Amarelo escuro */
    .fria   { background-color: #0984e3; } /* Azul */
    
    .jogo-card {
        background-color: #1e272e;
        border: 1px solid #2f3640;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .info-tag {
        font-size: 13px;
        color: #dcdde1;
        margin-left: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Filtrador de Combinações com Dezenas Coloridas")

def extrair_jogos_do_texto(conteudo_texto: str) -> list[list[int]]:
    """Extrai uma lista de jogos (cada jogo é uma lista de inteiros ordenados)."""
    jogos = []
    for linha in conteudo_texto.splitlines():
        dezenas = re.findall(r'\b\d{1,2}\b', linha)
        if len(dezenas) >= 5:  # Considera linhas com pelo menos 5 dezenas válidas
            jogos.append(sorted([int(d) for d in dezenas]))
    return jogos

# =====================================================================
# 1. BARRA LATERAL: UPLOADS DE ARQUIVOS
# =====================================================================
st.sidebar.header("📁 1. Entrada de Arquivos")

# Upload Principal: Arquivo que receberá os filtros
upload_jogos = st.sidebar.file_uploader(
    "Carregar arquivo de jogos para FILTRAR (.txt ou .csv):",
    type=["txt", "csv"],
    help="Envie o arquivo contendo os jogos gerados (um jogo por linha)."
)

# Upload Opcional: Histórico de resultados para base de cálculo
upload_historico = st.sidebar.file_uploader(
    "Carregar histórico/sorteios para frequência (Opcional):",
    type=["txt", "csv"],
    help="Se não enviar histórico, a frequência será calculada sobre o próprio arquivo de jogos."
)

if upload_jogos is not None:
    conteudo_jogos = upload_jogos.getvalue().decode("utf-8", errors="ignore")
    jogos_brutos = extrair_jogos_do_texto(conteudo_jogos)
    
    if not jogos_brutos:
        st.error("Nenhuma combinação válida com 5 ou mais dezenas foi encontrada no arquivo.")
        st.stop()
        
    st.sidebar.success(f"Carregados **{len(jogos_brutos)}** jogos para filtragem.")

    # =====================================================================
    # 2. CÁLCULO E CLASSIFICAÇÃO DE TEMPERATURA (CORES)
    # =====================================================================
    if upload_historico is not None:
        conteudo_hist = upload_historico.getvalue().decode("utf-8", errors="ignore")
        base_frequencia = extrair_jogos_do_texto(conteudo_hist)
        st.sidebar.info(f"Frequência baseada no histórico ({len(base_frequencia)} sorteios).")
    else:
        base_frequencia = jogos_brutos
        st.sidebar.info("Frequência baseada no próprio arquivo de jogos.")

    todas_dezenas = [d for jogo in base_frequencia for d in jogo]
    serie_freq = pd.Series(todas_dezenas).value_counts()
    
    # Determinação das faixas de corte por percentis
    corte_quente = serie_freq.quantile(0.66)
    corte_medio = serie_freq.quantile(0.33)
    
    dezenas_quentes = set(serie_freq[serie_freq >= corte_quente].index)
    dezenas_frias   = set(serie_freq[serie_freq < corte_medio].index)
    dezenas_medias  = set(serie_freq[(serie_freq >= corte_medio) & (serie_freq < corte_quente)].index)

    # =====================================================================
    # 3. FILTROS PARAMÉTRICOS DO ARQUIVO
    # =====================================================================
    st.sidebar.header("⚙️ 2. Parâmetros de Filtro")
    
    max_por_jogo = max(len(j) for j in jogos_brutos)
    
    filtro_quentes = st.sidebar.slider(
        "Quantidade de Dezenas 🔴 QUENTES por jogo:",
        min_value=0, max_value=max_por_jogo, value=(1, max_por_jogo)
    )
    filtro_medias = st.sidebar.slider(
        "Quantidade de Dezenas 🟠 MÉDIAS por jogo:",
        min_value=0, max_value=max_por_jogo, value=(0, max_por_jogo)
    )
    filtro_frias = st.sidebar.slider(
        "Quantidade de Dezenas 🔵 FRIAS por jogo:",
        min_value=0, max_value=max_por_jogo, value=(0, max_por_jogo)
    )
    
    filtro_pares_ativo = st.sidebar.checkbox("Ativar filtro de Pares")
    if filtro_pares_ativo:
        filtro_pares = st.sidebar.slider(
            "Quantidade de Dezenas PARES por jogo:",
            min_value=0, max_value=max_por_jogo, value=(2, 4)
        )

    # =====================================================================
    # 4. EXECUÇÃO DO FILTRO NO ARQUIVO
    # =====================================================================
    jogos_filtrados = []
    
    for jogo in jogos_brutos:
        qtd_q = sum(1 for d in jogo if d in dezenas_quentes)
        qtd_m = sum(1 for d in jogo if d in dezenas_medias)
        qtd_f = sum(1 for d in jogo if d in dezenas_frias)
        qtd_pares = sum(1 for d in jogo if d % 2 == 0)
        
        # Teste de conformidade com os filtros
        valido = (
            filtro_quentes[0] <= qtd_q <= filtro_quentes[1] and
            filtro_medias[0]  <= qtd_m <= filtro_medias[1] and
            filtro_frias[0]   <= qtd_f <= filtro_frias[1]
        )
        if filtro_pares_ativo and valido:
            valido = filtro_pares[0] <= qtd_pares <= filtro_pares[1]
            
        if valido:
            jogos_filtrados.append({
                "dezenas": jogo,
                "quentes": qtd_q,
                "medias": qtd_m,
                "frias": qtd_f,
                "pares": qtd_pares
            })

    # =====================================================================
    # 5. PAINEL DE RESULTADOS E COLORIZAÇÃO VISUAL
    # =====================================================================
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Jogos no Arquivo", len(jogos_brutos))
    col2.metric("Jogos Aprovados", len(jogos_filtrados))
    taxa_retencao = (len(jogos_filtrados) / len(jogos_brutos)) * 100 if jogos_brutos else 0
    col3.metric("Taxa de Aprovação", f"{taxa_retencao:.1f}%")
    col4.metric("Jogos Eliminados", len(jogos_brutos) - len(jogos_filtrados))
    
    st.write("---")
    
    # Resumo das Dezenas Classificadas com Cores
    st.subheader("Classificação Térmica das Dezenas")
    
    def renderizar_pills(conjunto_dezenas, classe_css):
        html = ""
        for d in sorted(conjunto_dezenas):
            html += f'<span class="dezena-box {classe_css}">{d:02d}</span>'
        return html

    st.markdown(f"**🔴 Quentes ({len(dezenas_quentes)} dezenas):**", unsafe_allow_html=True)
    st.markdown(renderizar_pills(dezenas_quentes, "quente"), unsafe_allow_html=True)
    
    st.markdown(f"**🟠 Médias ({len(dezenas_medias)} dezenas):**", unsafe_allow_html=True)
    st.markdown(renderizar_pills(dezenas_medias, "media"), unsafe_allow_html=True)
    
    st.markdown(f"**🔵 Frias ({len(dezenas_frias)} dezenas):**", unsafe_allow_html=True)
    st.markdown(renderizar_pills(dezenas_frias, "fria"), unsafe_allow_html=True)

    st.write("---")

    # Exibição dos Jogos Aprovados com as Dezenas Coloridas
    st.subheader(f"Jogos Aprovados no Filtro ({len(jogos_filtrados)} jogos)")
    
    limite_visualizacao = 100  # Limite para renderização suave no navegador
    for idx, item in enumerate(jogos_filtrados[:limite_visualizacao]):
        html_jogo = '<div class="jogo-card"><div>'
        html_jogo += f'<strong style="color:#a4b0be; margin-right: 12px;">#{idx+1:03d}</strong>'
        
        # Colorir cada dezena de acordo com o grupo
        for d in item["dezenas"]:
            if d in dezenas_quentes:
                css = "quente"
            elif d in dezenas_medias:
                css = "media"
            else:
                css = "fria"
            html_jogo += f'<span class="dezena-box {css}">{d:02d}</span>'
            
        html_jogo += '</div>'
        html_jogo += f'<div class="info-tag">🔴 {item["quentes"]} | 🟠 {item["medias"]} | 🔵 {item["frias"]} | P: {item["pares"]}</div>'
        html_jogo += '</div>'
        
        st.markdown(html_jogo, unsafe_allow_html=True)

    if len(jogos_filtrados) > limite_visualizacao:
        st.info(f"Exibindo os primeiros {limite_visualizacao} jogos na tela. O download abaixo contém todos os {len(jogos_filtrados)} jogos aprovados.")

    # Botão de Download do Arquivo Filtrado
    linhas_saida = [" ".join(f"{d:02d}" for d in item["dezenas"]) for item in jogos_filtrados]
    texto_exportacao = "\n".join(linhas_saida)
    
    st.download_button(
        label="📥 Baixar Arquivo Filtrado (.txt)",
        data=texto_exportacao,
        file_name="jogos_filtrados.txt",
        mime="text/plain"
    )

else:
    st.info("Utilize a barra lateral à esquerda para carregar o seu arquivo de combinações (`.txt` ou `.csv`).")
