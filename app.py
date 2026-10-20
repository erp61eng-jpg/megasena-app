import streamlit as st
import random
import re
from itertools import combinations
from collections import defaultdict, Counter
import pandas as pd

st.set_page_config(
    page_title="Mega-Sena - Laboratório & Fechamentos",
    page_icon="🍀",
    layout="wide"
)

# ==============================================================================
# 1. BASE HISTÓRICA DOS ÚLTIMOS 50 CONCURSOS DA MEGA-SENA
# ==============================================================================
HISTORICO_50_MEGASENA = [
    [4, 12, 18, 30, 35, 54], [1, 9, 15, 23, 44, 52], [7, 14, 27, 39, 48, 59],
    [10, 11, 25, 33, 42, 58], [3, 16, 28, 37, 45, 60], [5, 20, 22, 34, 49, 56],
    [8, 17, 31, 40, 50, 57], [2, 13, 24, 38, 43, 55], [6, 19, 29, 36, 47, 53],
    [12, 21, 32, 41, 46, 51], [4, 15, 26, 35, 48, 58], [7, 18, 23, 39, 44, 59],
    [1, 10, 27, 34, 42, 54], [9, 14, 30, 37, 50, 60], [3, 16, 25, 38, 49, 57],
    [5, 11, 28, 33, 45, 53], [8, 20, 31, 43, 52, 56], [2, 17, 24, 36, 47, 55],
    [6, 13, 29, 40, 46, 51], [12, 19, 32, 41, 50, 58], [4, 22, 27, 35, 44, 60],
    [7, 15, 26, 39, 48, 54], [1, 18, 30, 37, 42, 59], [9, 14, 23, 34, 49, 57],
    [3, 10, 28, 38, 45, 55], [5, 16, 31, 33, 50, 56], [8, 11, 25, 43, 47, 53],
    [2, 20, 29, 36, 46, 52], [6, 17, 32, 40, 51, 58], [12, 13, 24, 41, 48, 60],
    [4, 19, 27, 35, 44, 54], [7, 22, 30, 39, 49, 59], [1, 15, 26, 37, 42, 57],
    [9, 18, 28, 34, 45, 56], [3, 14, 31, 38, 50, 55], [5, 10, 23, 33, 46, 53],
    [8, 16, 29, 43, 47, 58], [2, 11, 32, 36, 51, 60], [6, 20, 25, 40, 48, 54],
    [12, 17, 27, 41, 49, 59], [4, 13, 30, 35, 44, 57], [7, 19, 26, 39, 42, 56],
    [1, 22, 28, 37, 45, 55], [9, 15, 31, 34, 50, 58], [3, 18, 24, 38, 46, 60],
    [5, 14, 29, 33, 47, 54], [8, 10, 32, 43, 48, 59], [2, 16, 27, 36, 51, 57],
    [6, 11, 25, 40, 49, 55], [12, 20, 28, 41, 46, 58]
]

TOTAL_NUMS = 60
TAMANHO_JOGO = 6
QTD_LINHAS = 6

# ==============================================================================
# 2. MAPEAMENTO MATEMÁTICO DA MATRIZ 6x10 (MEGA-SENA)
# ==============================================================================
@st.cache_data
def get_primos_megasena():
    cands = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
    return [p for p in cands if p <= TOTAL_NUMS]

@st.cache_data
def get_moldura_megasena():
    mold = set(range(1, 11)) | set(range(51, 61))
    for r in range(6):
        mold.add(r * 10 + 1)
        mold.add(r * 10 + 10)
    return sorted(list(mold))

@st.cache_data
def get_quadrantes_megasena():
    """Divisão da matriz 6x10 em 4 quadrantes de 15 dezenas (3x5 cada)."""
    q1, q2, q3, q4 = [], [], [], []
    for r in range(6):
        for c in range(10):
            num = r * 10 + c + 1
            if r < 3 and c < 5: q1.append(num)
            elif r < 3 and c >= 5: q2.append(num)
            elif r >= 3 and c < 5: q3.append(num)
            else: q4.append(num)
    return {
        "Q1 (Noroeste)": sorted(q1),
        "Q2 (Nordeste)": sorted(q2),
        "Q3 (Sudoeste)": sorted(q3),
        "Q4 (Sudeste)": sorted(q4)
    }

@st.cache_data
def get_diagonais_direita_megasena():
    return {
        f"Diag Direita {c+1:02d}": sorted([(r * 10) + ((c + r) % 10) + 1 for r in range(6)])
        for c in range(10)
    }

@st.cache_data
def get_diagonais_esquerda_megasena():
    return {
        f"Diag Esquerda {c+1:02d}": sorted([(r * 10) + ((c - r) % 10) + 1 for r in range(6)])
        for c in range(10)
    }

def construir_todos_grupos():
    grupos = {
        "Pares": [n for n in range(1, 61) if n % 2 == 0],
        "Ímpares": [n for n in range(1, 61) if n % 2 != 0],
        "Primos": get_primos_megasena(),
        "Moldura": get_moldura_megasena(),
        "Centro (Miolo)": [n for n in range(1, 61) if n not in get_moldura_megasena()]
    }
    for l in range(6):
        grupos[f"Linha {l+1}"] = list(range(l * 10 + 1, (l + 1) * 10 + 1))
    for c in range(10):
        grupos[f"Coluna {c+1}"] = [r * 10 + c + 1 for r in range(6)]
        
    grupos.update(get_diagonais_direita_megasena())
    grupos.update(get_diagonais_esquerda_megasena())
    return grupos

# ==============================================================================
# 3. MOTOR ESTATÍSTICO, CICLO DAS DEZENAS & FUNIL DE ELLIOTT
# ==============================================================================
def contar_consecutivos(jogo):
    maior = seq = 1
    for i in range(len(jogo) - 1):
        if jogo[i+1] == jogo[i] + 1:
            seq += 1
            if seq > maior: maior = seq
        else:
            seq = 1
    return maior

def calcular_ciclo_dezenas(historico_completo):
    """Calcula o ciclo atual com base no Coupon Collector's Problem."""
    dezenas_sorteadas = set()
    sorteios_no_ciclo = 0
    numero_ciclo = 1

    for sorteio in historico_completo:
        sorteios_no_ciclo += 1
        dezenas_sorteadas.update(sorteio)
        if len(dezenas_sorteadas) == 60:
            numero_ciclo += 1
            sorteios_no_ciclo = 0
            dezenas_sorteadas = set()

    faltantes = sorted(list(set(range(1, 61)) - dezenas_sorteadas))
    return {
        "numero_ciclo": numero_ciclo,
        "sorteios_no_ciclo": sorteios_no_ciclo,
        "qtd_sorteadas": len(dezenas_sorteadas),
        "qtd_faltantes": len(faltantes),
        "faltantes": faltantes
    }

def calcular_funil_elliott(historico_fatia):
    total_jogos = len(historico_fatia)
    metade = max(1, total_jogos // 2)
    jogos_antigos = historico_fatia[:metade]
    jogos_recentes = historico_fatia[metade:]
    
    cnt_antigos = Counter()
    for s in jogos_antigos: cnt_antigos.update(s)
    
    cnt_recentes = Counter()
    for s in jogos_recentes: cnt_recentes.update(s)
    
    cnt_total = Counter()
    for s in historico_fatia: cnt_total.update(s)
    
    scores = {}
    detalhes_funil = []

    for num in range(1, 61):
        f_rec = cnt_recentes[num]
        f_ant = cnt_antigos[num]
        f_tot = cnt_total[num]
        
        atraso = 0
        for s in reversed(historico_fatia):
            if num in s:
                break
            atraso += 1

        momentum = f_rec - f_ant
        pts_momentum = momentum * 2.5

        pts_fibonacci = 0.0
        if atraso in [1, 2]:
            pts_fibonacci = 4.0
        elif atraso in [3, 4, 5]:
            pts_fibonacci = 3.0
        elif atraso in [6, 7, 8]:
            pts_fibonacci = 1.5
        elif atraso > 15:
            pts_fibonacci = -3.0

        pts_exaustao = 0.0
        if f_rec >= 4 and len(jogos_recentes) <= 10:
            pts_exaustao = -3.5

        score_final = (f_tot * 1.5) + pts_momentum + pts_fibonacci + pts_exaustao
        scores[num] = score_final

        detalhes_funil.append({
            "num": num,
            "score": score_final,
            "f_tot": f_tot,
            "f_rec": f_rec,
            "momentum": momentum,
            "atraso": atraso
        })

    dezenas_ordenadas = sorted(scores.keys(), key=lambda d: scores[d], reverse=True)
    top_20_elliott = sorted(dezenas_ordenadas[:20])
    
    return top_20_elliott, sorted(detalhes_funil, key=lambda x: x["score"], reverse=True)

def calcular_estatisticas_dinamicas(historico_fatia, grupos_base):
    cnt_dezenas = Counter()
    for s in historico_fatia: cnt_dezenas.update(s)
    ordenados_freq = sorted(range(1, 61), key=lambda d: (cnt_dezenas[d], -d), reverse=True)
    quentes = set(ordenados_freq[:20])
    medias = set(ordenados_freq[20:40])
    frias = set(ordenados_freq[40:])

    somas = [sum(s) for s in historico_fatia]
    min_soma = min(somas) if somas else 21
    max_soma = max(somas) if somas else 345
    media_soma = sum(somas) / len(somas) if somas else 183.0

    consecs = [contar_consecutivos(s) for s in historico_fatia]
    max_consec = max(consecs) if consecs else 1

    reps = []
    for i in range(1, len(historico_fatia)):
        reps.append(len(set(historico_fatia[i]) & set(historico_fatia[i-1])))
    min_rep = min(reps) if reps else 0
    max_rep = max(reps) if reps else 1

    stats_grupos = {}
    for nome, dezenas in grupos_base.items():
        dez_set = set(dezenas)
        ocorrencias = [len(set(s) & dez_set) for s in historico_fatia]
        stats_grupos[nome] = {
            "min": min(ocorrencias) if ocorrencias else 0,
            "max": max(ocorrencias) if ocorrencias else 6,
            "media": sum(ocorrencias) / len(ocorrencias) if ocorrencias else 0.0,
            "total_saidas": sum(ocorrencias),
            "dezenas": dezenas
        }

    return {
        "cnt_dezenas": cnt_dezenas,
        "ordenados_freq": ordenados_freq,
        "quentes": quentes,
        "medias": medias,
        "frias": frias,
        "min_soma": min_soma,
        "max_soma": max_soma,
        "media_soma": media_soma,
        "max_consec": max_consec,
        "min_rep": min_rep,
        "max_rep": max_rep,
        "stats_grupos": stats_grupos
    }

# ==============================================================================
# 4. FUNÇÕES DE SINCRONIZAÇÃO E CONTROLE DE ESTADO
# ==============================================================================
if "grupos_base" not in st.session_state:
    st.session_state.grupos_base = construir_todos_grupos()

if "historico_sorteios" not in st.session_state:
    st.session_state.historico_sorteios = [list(j) for j in HISTORICO_50_MEGASENA]

if "jogos_aleatorios" not in st.session_state: st.session_state.jogos_aleatorios = []
if "jogos_fechamento" not in st.session_state: st.session_state.jogos_fechamento = []
if "jogos_fechamento_filtrados" not in st.session_state: st.session_state.jogos_fechamento_filtrados = []

def sincronizar_filtros_com_historico(stats_atuais, top20):
    st.session_state.filtro_soma_ativo = True
    st.session_state.faixa_soma = (int(stats_atuais["min_soma"]), int(stats_atuais["max_soma"]))
    st.session_state.filtro_consec_ativo = True
    st.session_state.max_consec = int(stats_atuais["max_consec"])
    st.session_state.f_rep_ant_ativo = True
    st.session_state.rep_ant_faixa = (int(stats_atuais["min_rep"]), int(stats_atuais["max_rep"]))
    st.session_state.f_max_coinc_ativo = True
    st.session_state.max_coinc_30 = 3
    st.session_state.f_freq_30_ativo = True
    st.session_state.faixa_quentes = (1, 4)
    st.session_state.faixa_frias = (0, 2)

    # Filtro de Quadrantes 2x2
    st.session_state.filtro_quads_ativo = True
    st.session_state.max_por_quadrante = 3
    st.session_state.min_quadrantes = 3

    for k, v in stats_atuais["stats_grupos"].items():
        eh_padrao = k in ["Pares", "Primos", "Moldura"]
        mn, mx = int(v["min"]), int(v["max"])
        st.session_state[f"ativo_{k}"] = eh_padrao
        st.session_state[f"faixa_{k}"] = (mn, mx)

    st.session_state.dezenas_fechamento_input = " ".join([f"{n:02d}" for n in top20])
    st.session_state.jogos_fechamento_filtrados = []

def obter_regras_compiladas():
    regras = []
    for k, dezenas in st.session_state.grupos_base.items():
        if st.session_state.get(f"ativo_{k}", False):
            faixa = st.session_state.get(f"faixa_{k}", (0, 6))
            regras.append((frozenset(dezenas), faixa[0], faixa[1]))
    return regras

# ==============================================================================
# 5. BARRA LATERAL: CONTROLE DINÂMICO
# ==============================================================================
with st.sidebar:
    st.header("Janela Estatística")
    total_disponivel = len(st.session_state.historico_sorteios)
    
    qtd_analise = st.slider(
        "Quantidade de Concursos:",
        min_value=5,
        max_value=total_disponivel,
        value=min(30, total_disponivel),
        step=1
    )
    st.caption(f"Analisando os últimos {qtd_analise} sorteios.")
    auto_sinc = st.checkbox("Sincronizar Filtros Automaticamente", value=True)

    with st.expander("Inserir Concurso Manual"):
        novo_jogo_txt = st.text_input("6 Dezenas (ex: 04 15 28 35 44 58):")
        if st.button("Gravar Concurso"):
            nums = [int(n) for n in re.findall(r'\b\d+\b', novo_jogo_txt) if 1 <= int(n) <= 60]
            if len(nums) == 6:
                st.session_state.historico_sorteios.append(sorted(nums))
                st.success("Concurso salvo!")
                st.rerun()
            else:
                st.error("Digite exatamente 6 números entre 1 e 60.")

historico_ativo = st.session_state.historico_sorteios[-qtd_analise:]
stats = calcular_estatisticas_dinamicas(historico_ativo, st.session_state.grupos_base)
top20_elliott, lista_funil_detalhada = calcular_funil_elliott(historico_ativo)
ciclo_atual = calcular_ciclo_dezenas(st.session_state.historico_sorteios)
mapa_quadrantes = get_quadrantes_megasena()
quads_sets = {k: set(v) for k, v in mapa_quadrantes.items()}

# FINGERPRINT: Detecta troca de concursos ou novos sorteios inseridos
fingerprint_atual = (qtd_analise, len(st.session_state.historico_sorteios), tuple(historico_ativo[-1]) if historico_ativo else ())

if "historico_fingerprint" not in st.session_state:
    st.session_state.historico_fingerprint = fingerprint_atual
    sincronizar_filtros_com_historico(stats, top20_elliott)
elif st.session_state.historico_fingerprint != fingerprint_atual:
    st.session_state.historico_fingerprint = fingerprint_atual
    if auto_sinc:
        sincronizar_filtros_com_historico(stats, top20_elliott)

with st.sidebar:
    if st.button("🔄 Recalibrar Filtros Agora", use_container_width=True):
        sincronizar_filtros_com_historico(stats, top20_elliott)
        st.success("Filtros sincronizados!")
        st.rerun()

# ==============================================================================
# 6. COMBINATÓRIA E VALIDAÇÃO DE FILTROS
# ==============================================================================
def validar_jogo(cand, cand_set, regras_compiladas, f_soma, r_soma, f_consec, m_consec,
                 f_rep, r_rep, ult_set, f_coinc, max_c, hist_sets,
                 f_freq, r_q, r_f, s_q, s_f,
                 f_quads, max_q, min_q, q_sets):
    if f_soma and not (r_soma[0] <= sum(cand) <= r_soma[1]):
        return False
    if f_consec and contar_consecutivos(cand) > m_consec:
        return False
    for g_set, mn, mx in regras_compiladas:
        qtd = len(cand_set & g_set)
        if qtd < mn or qtd > mx:
            return False
    if f_rep and ult_set:
        rep = len(cand_set & ult_set)
        if not (r_rep[0] <= rep <= r_rep[1]):
            return False
    if f_coinc and hist_sets:
        for pass_set in hist_sets:
            if len(cand_set & pass_set) > max_c:
                return False
    if f_freq:
        if not (r_q[0] <= len(cand_set & s_q) <= r_q[1]): return False
        if not (r_f[0] <= len(cand_set & s_f) <= r_f[1]): return False
        
    # Filtro de Quadrantes 2x2
    if f_quads and q_sets:
        contagens = [len(cand_set & s) for s in q_sets.values()]
        if max(contagens) > max_q:
            return False
        if sum(1 for c in contagens if c > 0) < min_q:
            return False
            
    return True

def gerar_fechamento_guloso(dezenas, garantia):
    nums = sorted(dezenas)
    if "Sena" in garantia:
        escolhidos = [sorted(list(c)) for c in combinations(nums, 6)]
        return escolhidos, 100.0

    k_alvo = 5 if "Quina" in garantia else (4 if "Quadra" in garantia else 3)
    alvos_totais = set(combinations(nums, k_alvo))
    total_alvos = len(alvos_totais)
    candidatos = list(combinations(nums, 6))
    if not candidatos: return [], 0.0

    cand_alvos = {c: set(combinations(c, k_alvo)) for c in candidatos}
    alvo_para_cands = defaultdict(list)
    for c, sub in cand_alvos.items():
        for a in sub: alvo_para_cands[a].append(c)

    ganhos = {c: len(sub) for c, sub in cand_alvos.items()}
    alvos_restantes = set(alvos_totais)
    escolhidos = []

    while alvos_restantes:
        melhor = max(ganhos, key=ganhos.get)
        if ganhos[melhor] == 0: break
        escolhidos.append(sorted(list(melhor)))
        novos = cand_alvos[melhor] & alvos_restantes
        alvos_restantes -= novos
        for a in novos:
            for c in alvo_para_cands[a]: ganhos[c] -= 1
        ganhos[melhor] = -1

    taxa = ((total_alvos - len(alvos_restantes)) / total_alvos) * 100 if total_alvos else 100.0
    return escolhidos, taxa

def converter_para_txt(jogos):
    return "\n".join([" ".join([f"{n:02d}" for n in j]) for j in jogos])

def extrair_dezenas_texto(texto):
    numeros = re.findall(r'\b\d+\b', str(texto))
    validos = [int(n) for n in numeros if 1 <= int(n) <= 60]
    return sorted(list(set(validos)))

def ler_arquivo_jogos_txt(conteudo_texto):
    jogos = []
    for linha in conteudo_texto.splitlines():
        linha_limpa = linha.strip()
        if not linha_limpa: continue
        nums = [int(n) for n in re.findall(r'\b\d+\b', linha_limpa) if 1 <= int(n) <= 60]
        if len(nums) == 6:
            jogos.append(sorted(nums))
        elif len(nums) > 6:
            cands = [n for n in nums if n <= 60]
            if len(cands) >= 6:
                if len(cands) == 7 and cands[0] < 50:
                    jogos.append(sorted(cands[1:7]))
                else:
                    jogos.append(sorted(cands[:6]))
    return jogos

def renderizar_volante_6x10(jogo, titulo=""):
    marcadas = set(jogo)
    grid_html = f"""
    <style>
        .volante-box {{ background:#ffffff; border:2px solid #1b5e20; border-radius:10px; padding:14px; width:fit-content; margin:8px auto; }}
        .volante-grid {{ display:grid; grid-template-columns:repeat(10, 36px); gap:5px; }}
        .v-cell {{ width:36px; height:36px; border:1px solid #dcdcdc; border-radius:6px; display:flex; align-items:center; justify-content:center; font-family:monospace; font-size:12px; color:#555; background:#fafafa; font-weight:500; }}
        .v-marcada {{ background:linear-gradient(135deg, #2e7d32, #1b5e20) !important; color:#ffffff !important; border:2px solid #0b4317 !important; font-weight:bold; }}
    </style>
    <div class="volante-box">
    """
    if titulo:
        grid_html += f"<p style='font-weight:700; font-size:15px; margin-bottom:10px; color:#1b5e20; text-align:center;'>{titulo}</p>"
    grid_html += '<div class="volante-grid">'
    for r in range(6):
        for c in range(10):
            num = r * 10 + c + 1
            cls = "v-cell v-marcada" if num in marcadas else "v-cell"
            grid_html += f'<div class="{cls}">{num:02d}</div>'
    grid_html += "</div></div>"
    st.markdown(grid_html, unsafe_allow_html=True)

# ==============================================================================
# 7. INTERFACE PRINCIPAL
# ==============================================================================
st.title("🍀 Mega-Sena: Laboratório & Fechamentos")
st.caption(f"Análise Ativa: Últimos {qtd_analise} Concursos • Matriz 6x10 • Ciclo & Quadrantes • Funil de Elliott.")

tab_fechamento, tab_gerador, tab_conferir, tab_filtros, tab_hist, tab_volante = st.tabs([
    "🎯 Fechamentos & Funil",
    "🚀 Gerador de Apostas",
    "🎟️ Conferir Jogos (TXT)",
    "⚙️ Filtros & Estatísticas",
    f"📜 Concursos ({qtd_analise}) & Quadrantes",
    "🗺️ Volante Visual 6x10"
])

hist_sets = [set(j) for j in historico_ativo]
ult_set = set(historico_ativo[-1]) if historico_ativo else set()
diag_dir = [f"Diag Direita {i:02d}" for i in range(1, 11)]
diag_esq = [f"Diag Esquerda {i:02d}" for i in range(1, 11)]

# ==============================================================================
# ABA: FECHAMENTO & FUNIL DE ELLIOTT
# ==============================================================================
with tab_fechamento:
    # Card do Ciclo das Dezenas
    st.markdown("### 🔄 Ciclo das Dezenas (Coupon Collector)")
    col_c1, col_c2, col_c3 = st.columns([1, 1, 3])
    col_c1.metric("Ciclo Vigente", f"#{ciclo_atual['numero_ciclo']}")
    col_c2.metric("Sorteios no Ciclo", f"{ciclo_atual['sorteios_no_ciclo']}")
    with col_c3:
        st.write(f"**{ciclo_atual['qtd_faltantes']} Dezenas Faltantes para Fechar o Ciclo:**")
        if ciclo_atual["faltantes"]:
            st.code(" ".join([f"{n:02d}" for n in ciclo_atual["faltantes"]]))
        else:
            st.success("O ciclo acabou de fechar! Todas as 60 dezenas foram sorteadas.")

    st.divider()
    st.subheader(f"1. Frequência das 60 Dezenas (Últimos {qtd_analise} Concursos)")
    linhas_texto = []
    for r in range(6):
        linha_nums = []
        for c in range(10):
            num = r * 10 + c + 1
            qtd_saiu = stats["cnt_dezenas"][num]
            linha_nums.append(f"{num:02d}: {qtd_saiu}x")
        linhas_texto.append(" | ".join(linha_nums))
    st.text("\n".join(linhas_texto))

    st.divider()
    st.subheader("2. As 20 Dezenas Ranqueadas pelo Funil de Elliott")
    str_sugestao_20 = " ".join([f"{n:02d}" for n in top20_elliott])
    st.code(f"Top 20 Elliott: {str_sugestao_20}")

    with st.expander("Ver Detalhes do Score do Funil"):
        df_funil = pd.DataFrame(lista_funil_detalhada[:20])
        df_funil.columns = ["Dezena", "Score Funil", "Total Saídas", "Saídas Recentes", "Momentum", "Atraso"]
        st.dataframe(df_funil, use_container_width=True)

    st.divider()
    st.subheader("3. Escolha das Dezenas do Fechamento (Editável)")
    c_fech1, c_fech2 = st.columns([3, 1])
    with c_fech1:
        entrada_manual = st.text_input(
            "Dezenas Selecionadas:",
            key="dezenas_fechamento_input",
            help="Altere os números livremente respeitando o intervalo de 7 a 20 dezenas."
        )
    with c_fech2:
        gar = st.selectbox(
            "Garantia Matemática:",
            [
                "Quadra (Garante 4 se 6)",
                "Quina (Garante 5 se 6)",
                "Sena (Garante 6 se 6 - 100% Fechado)",
                "Terno (Garante 3 se 6)"
            ]
        )

    dezenas_digitadas = extrair_dezenas_texto(entrada_manual)
    st.write(f"Dezenas selecionadas ({len(dezenas_digitadas)}): `{' - '.join([f'{n:02d}' for n in dezenas_digitadas])}`")

    if len(dezenas_digitadas) < 7:
        st.info("Digite pelo menos 7 dezenas para calcular o fechamento.")
    elif len(dezenas_digitadas) > 20:
        st.error(f"Você informou {len(dezenas_digitadas)} dezenas. O limite máximo é 20.")
    else:
        if st.button("Calcular Desdobramento Fechado 🧮", use_container_width=True):
            with st.spinner("Processando combinações da Mega-Sena..."):
                j_fech, cob = gerar_fechamento_guloso(dezenas_digitadas, gar)
                st.session_state.jogos_fechamento = j_fech
                st.session_state.taxa_cobertura = cob
                st.session_state.jogos_fechamento_filtrados = []

    if st.session_state.jogos_fechamento:
        qtd_bruta = len(st.session_state.jogos_fechamento)
        st.success(f"Fechamento Bruto: **{qtd_bruta} jogos gerados** (Garantia: {st.session_state.get('taxa_cobertura', 100):.1f}%)")

        st.divider()
        st.subheader("4. Depuração e Redução por Filtros Ativos")
        if st.button("Depurar e Reduzir Jogos com Filtros Ativos 🧹", use_container_width=True):
            regras_comp = obter_regras_compiladas()
            jogos_depurados = []
            
            with st.spinner("Filtrando apostas da Mega-Sena..."):
                for c in st.session_state.jogos_fechamento:
                    if validar_jogo(c, set(c), regras_comp,
                                    st.session_state.filtro_soma_ativo, st.session_state.faixa_soma,
                                    st.session_state.filtro_consec_ativo, st.session_state.max_consec,
                                    st.session_state.f_rep_ant_ativo, st.session_state.rep_ant_faixa, ult_set,
                                    st.session_state.f_max_coinc_ativo, st.session_state.max_coinc_30, hist_sets,
                                    st.session_state.f_freq_30_ativo, st.session_state.faixa_quentes, st.session_state.faixa_frias,
                                    stats["quentes"], stats["frias"],
                                    st.session_state.filtro_quads_ativo, st.session_state.max_por_quadrante,
                                    st.session_state.min_quadrantes, quads_sets):
                        jogos_depurados.append(c)

            st.session_state.jogos_fechamento_filtrados = jogos_depurados
            
            if jogos_depurados:
                qtd_dep = len(jogos_depurados)
                reducao = ((qtd_bruta - qtd_dep) / qtd_bruta) * 100
                st.success(f"🎉 Depuração Concluída! De **{qtd_bruta}** apostas brutas, restaram **{qtd_dep} jogos aprovados** (Redução de **{reducao:.1f}%** no custo).")
            else:
                st.error("Nenhum jogo do fechamento passou em todos os filtros. Alivie algumas regras na aba de Filtros.")

        if st.session_state.jogos_fechamento_filtrados:
            st.write(f"### 📋 Apostas Depuradas Prontas ({len(st.session_state.jogos_fechamento_filtrados)} jogos):")
            st.download_button(
                "📥 Baixar Jogos Depurados em TXT",
                data=converter_para_txt(st.session_state.jogos_fechamento_filtrados),
                file_name="megasena_fechamento_depurado.txt",
                mime="text/plain",
                use_container_width=True
            )
            for i, j in enumerate(st.session_state.jogos_fechamento_filtrados):
                st.code(f"Aposta #{i+1:02d}: {'  '.join([f'{n:02d}' for n in j])} | Soma: {sum(j)}")

        with st.expander(f"Ver lista completa do Fechamento Bruto ({qtd_bruta} apostas)"):
            st.download_button(
                "📥 Baixar Fechamento Bruto (.TXT)",
                data=converter_para_txt(st.session_state.jogos_fechamento),
                file_name="megasena_fechamento_bruto.txt",
                mime="text/plain"
            )
            for i, j in enumerate(st.session_state.jogos_fechamento):
                st.code(f"Aposta #{i+1:02d}: {'  '.join([f'{n:02d}' for n in j])}")

# ==============================================================================
# ABA: GERADOR DE APOSTAS
# ==============================================================================
with tab_gerador:
    st.subheader("Gerar Combinações Validadas (6 Dezenas)")
    qtd = st.number_input("Quantidade de Jogos:", min_value=1, max_value=200, value=5)
    
    if st.button("Gerar Apostas da Mega-Sena 🚀", use_container_width=True):
        regras_comp = obter_regras_compiladas()
        jogos, unicos, t = [], set(), 0
        pool = list(range(1, 61))
        
        with st.spinner("Filtrando apostas segundo as regras..."):
            while len(jogos) < qtd and t < 250_000:
                c = sorted(random.sample(pool, 6))
                ctup = tuple(c)
                if ctup not in unicos:
                    if validar_jogo(c, set(c), regras_comp,
                                    st.session_state.filtro_soma_ativo, st.session_state.faixa_soma,
                                    st.session_state.filtro_consec_ativo, st.session_state.max_consec,
                                    st.session_state.f_rep_ant_ativo, st.session_state.rep_ant_faixa, ult_set,
                                    st.session_state.f_max_coinc_ativo, st.session_state.max_coinc_30, hist_sets,
                                    st.session_state.f_freq_30_ativo, st.session_state.faixa_quentes, st.session_state.faixa_frias,
                                    stats["quentes"], stats["frias"],
                                    st.session_state.filtro_quads_ativo, st.session_state.max_por_quadrante,
                                    st.session_state.min_quadrantes, quads_sets):
                        jogos.append(c)
                        unicos.add(ctup)
                t += 1
                
        st.session_state.jogos_aleatorios = jogos
        if not jogos:
            st.error("Nenhum jogo passou pelos critérios configurados. Alivie alguns filtros na aba de Filtros.")

    if st.session_state.jogos_aleatorios:
        st.success(f"{len(st.session_state.jogos_aleatorios)} jogos gerados:")
        st.download_button(
            "Baixar Jogos em TXT",
            data=converter_para_txt(st.session_state.jogos_aleatorios),
            file_name="apostas_megasena.txt",
            mime="text/plain",
            use_container_width=True
        )
        for i, j in enumerate(st.session_state.jogos_aleatorios):
            st.code(f"Jogo #{i+1:02d}: {'  '.join([f'{n:02d}' for n in j])} | Soma: {sum(j)}")

# ==============================================================================
# ABA: CONFERIR JOGOS (ARQUIVO .TXT)
# ==============================================================================
with tab_conferir:
    st.subheader("Conferência Oficial da Mega-Sena (.TXT)")
    col_res1, col_res2 = st.columns([2, 1])
    with col_res1:
        res_digitado = st.text_input("Digite as 6 dezenas sorteadas:", placeholder="Ex: 04 15 28 35 44 58")
    with col_res2:
        dezenas_extraidas = extrair_dezenas_texto(res_digitado)
        if len(dezenas_extraidas) == 6:
            st.success(f"Resultado: `{' - '.join([f'{n:02d}' for n in dezenas_extraidas])}`")
        elif res_digitado.strip():
            st.warning(f"{len(dezenas_extraidas)} dezenas digitadas (precisa de 6).")

    st.divider()
    arquivo_enviado = st.file_uploader("Buscar arquivo de apostas (.TXT):", type=["txt"])
    jogos_conferir = []

    if arquivo_enviado is not None:
        try:
            conteudo = arquivo_enviado.getvalue().decode("utf-8")
        except UnicodeDecodeError:
            conteudo = arquivo_enviado.getvalue().decode("latin-1")
        
        jogos_conferir = ler_arquivo_jogos_txt(conteudo)
        if jogos_conferir:
            st.write(f"**{len(jogos_conferir)} apostas carregadas do arquivo.**")
        else:
            st.error("Nenhuma aposta válida de 6 dezenas encontrada no arquivo.")
    else:
        st.caption("Ou confira apostas geradas na memória desta sessão:")
        opcao_sessao = st.selectbox(
            "Usar da memória:",
            [
                "Nenhum",
                "Jogos do Fechamento Depurado (Filtrados)",
                "Jogos do Fechamento Bruto",
                "Jogos do Gerador de Apostas"
            ]
        )
        if opcao_sessao == "Jogos do Fechamento Depurado (Filtrados)":
            jogos_conferir = st.session_state.jogos_fechamento_filtrados
        elif opcao_sessao == "Jogos do Fechamento Bruto":
            jogos_conferir = st.session_state.jogos_fechamento
        elif opcao_sessao == "Jogos do Gerador de Apostas":
            jogos_conferir = st.session_state.jogos_aleatorios

    if len(dezenas_extraidas) == 6 and jogos_conferir:
        st.divider()
        so_premiados = st.checkbox("Mostrar apenas apostas premiadas (Quadra, Quina, Sena)", value=False)
        set_sorteio = set(dezenas_extraidas)
        contadores = {6: 0, 5: 0, 4: 0, 3: 0, 2: 0, 1: 0, 0: 0}
        resultados_processados = []

        for j in jogos_conferir:
            acertos = sorted(list(set(j) & set_sorteio))
            qtd = len(acertos)
            contadores[qtd] += 1
            resultados_processados.append({
                "jogo": j,
                "acertos": acertos,
                "qtd_acertos": qtd
            })

        resultados_processados.sort(key=lambda x: x["qtd_acertos"], reverse=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🏆 SENA (6)", contadores[6])
        m2.metric("🎯 QUINA (5)", contadores[5])
        m3.metric("🥈 QUADRA (4)", contadores[4])
        m4.metric("❌ SEM PRÊMIO", contadores[0] + contadores[1] + contadores[2] + contadores[3])

        st.divider()
        for idx, item in enumerate(resultados_processados):
            qtd = item["qtd_acertos"]
            if so_premiados and qtd < 4:
                continue

            tag = f"{qtd} acertos"
            if qtd == 6: tag = "🏆 SENA! PARABÉNS!"
            elif qtd == 5: tag = "🎯 QUINA!"
            elif qtd == 4: tag = "🥈 QUADRA!"

            jogo_str = " ".join([f"[{n:02d}]" if n in item["acertos"] else f"{n:02d}" for n in item["jogo"]])
            st.write(f"Bilhete #{idx+1:02d}: {jogo_str} — **{tag}**")

# ==============================================================================
# ABA: FILTROS & ESTATÍSTICAS
# ==============================================================================
with tab_filtros:
    st.subheader(f"Filtros Calibrados nos Últimos {qtd_analise} Concursos (Mega-Sena)")
    
    c1, c2 = st.columns(2)
    with c1:
        st.checkbox("Filtrar Soma", key="filtro_soma_ativo")
        st.caption(f"Min: {stats['min_soma']} | Max: {stats['max_soma']} | Média: {stats['media_soma']:.1f}")
        if st.session_state.filtro_soma_ativo:
            st.slider("Faixa de Soma:", 21, 345, key="faixa_soma")
    with c2:
        st.checkbox("Limitar Consecutivos", key="filtro_consec_ativo")
        st.caption(f"Maior consecutivo no período: {stats['max_consec']}")
        if st.session_state.filtro_consec_ativo:
            st.slider("Máximo consecutivo:", 1, 6, key="max_consec")

    st.divider()
    ch1, ch2, ch3 = st.columns(3)
    with ch1:
        st.checkbox("Repetição Anterior", key="f_rep_ant_ativo")
        if st.session_state.f_rep_ant_ativo:
            st.slider("Repetidas:", 0, 6, key="rep_ant_faixa")
    with ch2:
        st.checkbox("Teto Coincidência Histórica", key="f_max_coinc_ativo")
        if st.session_state.f_max_coinc_ativo:
            st.slider("Máx acertos em sorteios passados:", 1, 6, key="max_coinc_30")
    with ch3:
        st.checkbox("Equilíbrio Quentes/Frias", key="f_freq_30_ativo")
        if st.session_state.f_freq_30_ativo:
            st.slider("Top Quentes:", 0, 6, key="faixa_quentes")
            st.slider("Mais Atrasadas:", 0, 6, key="faixa_frias")

    # Bloco do Filtro de Quadrantes 2x2
    st.divider()
    st.markdown("### 📐 Filtro de Quadrantes 2x2 (Distribuição Multinomial)")
    st.caption("Controla o espalhamento nas 4 áreas de 15 dezenas da cartela. Evita concentração excessiva num mesmo setor.")
    cq1, cq2, cq3 = st.columns(3)
    with cq1:
        st.checkbox("Ativar Filtro de Quadrantes", key="filtro_quads_ativo")
    with cq2:
        if st.session_state.filtro_quads_ativo:
            st.slider("Máximo por Quadrante:", 1, 5, key="max_por_quadrante", help="Evita mais que X dezenas em um só quadrante.")
    with cq3:
        if st.session_state.filtro_quads_ativo:
            st.slider("Mínimo de Quadrantes Presentes:", 1, 4, key="min_quadrantes", help="Garante que as 6 dezenas ocupem pelo menos X quadrantes distintos.")

    st.divider()
    st.write("Padrões da Matriz (Mega-Sena):")
    for padrao in ["Pares", "Primos", "Moldura", "Centro (Miolo)"]:
        s_g = stats["stats_grupos"][padrao]
        chk, sl = st.columns([2, 3])
        with chk:
            st.checkbox(f"{padrao} (Min: {s_g['min']} | Max: {s_g['max']})", key=f"ativo_{padrao}")
        with sl:
            if st.session_state.get(f"ativo_{padrao}", False):
                st.slider(f"Faixa {padrao}", 0, 6, key=f"faixa_{padrao}")

    st.divider()
    st.write("20 Diagonais Cilíndricas (Matriz 6x10):")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("Ativar 20 Diagonais", use_container_width=True):
            for i in range(1, 11):
                st.session_state[f"ativo_Diag Direita {i:02d}"] = True
                st.session_state[f"ativo_Diag Esquerda {i:02d}"] = True
            st.rerun()
    with c_btn2:
        if st.button("Desativar Todas as Diagonais", use_container_width=True):
            for i in range(1, 11):
                st.session_state[f"ativo_Diag Direita {i:02d}"] = False
                st.session_state[f"ativo_Diag Esquerda {i:02d}"] = False
            st.rerun()

    with st.expander("10 Diagonais Direitas"):
        for k in diag_dir:
            s_d = stats["stats_grupos"][k]
            chk, sl = st.columns([2, 3])
            with chk:
                st.checkbox(f"{k} (Saídas: {s_d['total_saidas']})", key=f"ativo_{k}")
            with sl:
                if st.session_state.get(f"ativo_{k}", False):
                    st.slider(f"Faixa {k}", 0, 6, key=f"faixa_{k}", label_visibility="collapsed")

    with st.expander("10 Diagonais Esquerdas"):
        for k in diag_esq:
            s_d = stats["stats_grupos"][k]
            chk, sl = st.columns([2, 3])
            with chk:
                st.checkbox(f"{k} (Saídas: {s_d['total_saidas']})", key=f"ativo_{k}")
            with sl:
                if st.session_state.get(f"ativo_{k}", False):
                    st.slider(f"Faixa {k}", 0, 6, key=f"faixa_{k}", label_visibility="collapsed")

# ==============================================================================
# ABA: HISTÓRICO, QUADRANTES & TABELA DE DIAGONAIS
# ==============================================================================
with tab_hist:
    st.subheader(f"Últimos {qtd_analise} Concursos Analisados")
    c_h1, c_h2 = st.columns([3, 2])
    with c_h1:
        dados_tabela = [
            {"Concurso": f"#{len(historico_ativo)-idx:02d}", "Dezenas": " - ".join([f"{n:02d}" for n in s]), "Soma": sum(s)}
            for idx, s in enumerate(reversed(historico_ativo))
        ]
        st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True, height=350)
    with c_h2:
        top_10 = [(d, stats["cnt_dezenas"][d]) for d in stats["ordenados_freq"][:10]]
        st.write("**Top 10 Quentes:** " + ", ".join([f"{d:02d} ({qtd}x)" for d, qtd in top_10]))
        bot_10 = sorted(stats["cnt_dezenas"].items(), key=lambda x: x[1])[:10]
        st.write("**Top 10 Frias:** " + ", ".join([f"{d:02d} ({qtd}x)" for d, qtd in bot_10]))

    st.divider()
    st.subheader("Mapeamento dos 4 Quadrantes (3x5)")
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    for idx_q, (nome_q, dezenas_q) in enumerate(mapa_quadrantes.items()):
        total_saidas_quad = sum(stats["cnt_dezenas"][d] for d in dezenas_q)
        alvo_col = [col_q1, col_q2, col_q3, col_q4][idx_q]
        with alvo_col:
            alvo_col.metric(nome_q, f"{total_saidas_quad} saídas")
            alvo_col.caption(" ".join([f"{n:02d}" for n in dezenas_q]))

    st.divider()
    st.subheader("Desempenho das 20 Diagonais (6x10)")
    dados_diags = []
    for k in (diag_dir + diag_esq):
        info = stats["stats_grupos"][k]
        dados_diags.append({
            "Diagonal": k,
            "Total Saídas": info["total_saidas"],
            "Média": f"{info['media']:.2f}",
            "Min": info["min"],
            "Max": info["max"],
            "Dezenas": " ".join([f"{n:02d}" for n in info["dezenas"]]),
            "Ativo": "Sim" if st.session_state.get(f"ativo_{k}", False) else "Não"
        })
    df_diags = pd.DataFrame(dados_diags).sort_values(by="Total Saídas", ascending=False)
    st.dataframe(df_diags, use_container_width=True, height=400)

# ==============================================================================
# ABA: VOLANTE VISUAL (6x10)
# ==============================================================================
with tab_volante:
    st.subheader("Visualizador da Cartela Oficial da Mega-Sena (6x10)")
    opcoes_visualizacao = ["Cartela Vazia"]
    
    if st.session_state.jogos_fechamento_filtrados:
        opcoes_visualizacao.extend([f"Fechamento Depurado - #{i+1:02d}" for i in range(len(st.session_state.jogos_fechamento_filtrados))])
    if st.session_state.jogos_fechamento:
        opcoes_visualizacao.extend([f"Fechamento Bruto - #{i+1:02d}" for i in range(len(st.session_state.jogos_fechamento))])
    if st.session_state.jogos_aleatorios:
        opcoes_visualizacao.extend([f"Gerador - #{i+1:02d}" for i in range(len(st.session_state.jogos_aleatorios))])

    escolha = st.selectbox("Selecione um jogo para ver na cartela:", opcoes_visualizacao)
    jogo_exibir = []
    if "Depurado" in escolha:
        idx = int(escolha.split("#")[1]) - 1
        jogo_exibir = st.session_state.jogos_fechamento_filtrados[idx]
    elif "Fechamento Bruto" in escolha:
        idx = int(escolha.split("#")[1]) - 1
        jogo_exibir = st.session_state.jogos_fechamento[idx]
    elif "Gerador" in escolha:
        idx = int(escolha.split("#")[1]) - 1
        jogo_exibir = st.session_state.jogos_aleatorios[idx]

    renderizar_volante_6x10(jogo_exibir, titulo=escolha)
