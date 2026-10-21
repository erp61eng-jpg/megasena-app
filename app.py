import streamlit as st
import streamlit.components.v1 as components
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
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

TOTAL_NUMS = 60
TAMANHO_JOGO = 6
QTD_LINHAS = 6
QTD_COLUNAS = 10

# Base de contingência caso a Caixa esteja temporariamente inacessível
FALLBACK_MEGASENA = [
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

# ==============================================================================
# 1. CONEXÃO AUTOMÁTICA VIA API OFICIAL DA CAIXA (MEGA-SENA)
# ==============================================================================
@st.cache_data(ttl=7200, show_spinner=False)
def buscar_50_concursos_caixa():
    """Consulta a API oficial da Caixa e busca os últimos 50 sorteios reais da Mega-Sena."""
    url_base = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        resp = requests.get(url_base, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None, "Offline"
        
        dados_ultimo = resp.json()
        ultimo_num = int(dados_ultimo["numero"])
        data_ultimo = dados_ultimo.get("dataApuracao", "")
        
        concursos_dict = {}
        concursos_dict[ultimo_num] = sorted([int(d) for d in dados_ultimo["listaDezenas"]])
        
        alvos = list(range(max(1, ultimo_num - 49), ultimo_num))
        
        def baixar_concurso(num):
            try:
                r = requests.get(f"{url_base}/{num}", headers=headers, timeout=5)
                if r.status_code == 200:
                    dezenas = [int(d) for d in r.json()["listaDezenas"]]
                    return num, sorted(dezenas)
            except Exception:
                pass
            return num, None

        with ThreadPoolExecutor(max_workers=12) as executor:
            futuros = [executor.submit(baixar_concurso, n) for n in alvos]
            for f in as_completed(futuros):
                n_conc, nums = f.result()
                if nums and len(nums) == 6:
                    concursos_dict[n_conc] = nums

        lista_cronologica = [concursos_dict[k] for k in sorted(concursos_dict.keys())]
        if len(lista_cronologica) >= 5:
            info_txt = f"#{ultimo_num} realizado em {data_ultimo}"
            return lista_cronologica, info_txt
    except Exception:
        pass
    return None, "Erro de Conexão"

# ==============================================================================
# 2. MAPEAMENTO MATEMÁTICO DA MATRIZ 6x10 (MEGA-SENA)
# ==============================================================================
@st.cache_data
def get_primos_megasena():
    cands = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
    return [p for p in cands if p <= TOTAL_NUMS]

@st.cache_data
def get_moldura_megasena():
    """Linhas 1 e 6 + Colunas 1 e 10 (Total: 28 dezenas)."""
    mold = set(range(1, 11)) | set(range(51, 61))
    for r in range(6):
        mold.add(r * 10 + 1)
        mold.add(r * 10 + 10)
    return sorted(list(mold))

@st.cache_data
def get_miolo_megasena():
    """Centro interno da matriz 6x10 (Total: 32 dezenas)."""
    mold_set = set(get_moldura_megasena())
    return [n for n in range(1, 61) if n not in mold_set]

@st.cache_data
def get_quadrantes_megasena():
    """4 quadrantes de 15 dezenas (3 linhas x 5 colunas cada)."""
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
    """10 diagonais cilíndricas (+11 mod 10) de 6 dezenas cada."""
    return {
        f"Diag Direita {c+1:02d}": sorted([(r * 10) + ((c + r) % 10) + 1 for r in range(6)])
        for c in range(10)
    }

@st.cache_data
def get_diagonais_esquerda_megasena():
    """10 diagonais cilíndricas (+9 mod 10) de 6 dezenas cada."""
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
        "Centro (Miolo)": get_miolo_megasena()
    }
    for l in range(6):
        grupos[f"Linha {l+1}"] = list(range(l * 10 + 1, (l + 1) * 10 + 1))
    for c in range(10):
        grupos[f"Coluna {c+1}"] = [r * 10 + c + 1 for r in range(6)]
        
    grupos.update(get_diagonais_direita_megasena())
    grupos.update(get_diagonais_esquerda_megasena())
    return grupos

# ==============================================================================
# 3. MOTOR ESTATÍSTICO, CICLO & FUNIL DE ELLIOTT (TOP 30)
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
    top_30_elliott = sorted(dezenas_ordenadas[:30])
    return top_30_elliott, sorted(detalhes_funil, key=lambda x: x["score"], reverse=True)

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
# 4. RENDERIZADORES EM IFRAME (HTML ISOLADO: HEATMAP & VOLANTE)
# ==============================================================================
def renderizar_heatmap_6x10_vibrante(cnt_dezenas, titulo="Mapa de Calor Térmico da Mega-Sena (60 Dezenas)"):
    todos_valores = [cnt_dezenas[n] for n in range(1, 61)]
    val_min = min(todos_valores) if todos_valores else 0
    val_max = max(todos_valores) if todos_valores else 1
    delta = max(1, val_max - val_min)

    def obter_estilo_calor(freq):
        ratio = (freq - val_min) / delta
        if freq == 0 or ratio == 0.0:
            return "#dbeafe", "#0369a1"  # Azul Gelo (Fria)
        elif ratio <= 0.25:
            return "#38bdf8", "#075985"  # Ciano (Baixa)
        elif ratio <= 0.50:
            return "#22c55e", "#ffffff"  # Verde Primavera (Média)
        elif ratio <= 0.70:
            return "#eab308", "#713f12"  # Amarelo Ouro (Aquecida)
        elif ratio <= 0.88:
            return "#f97316", "#ffffff"  # Laranja (Quente)
        else:
            return "#ef4444", "#ffffff"  # Vermelho Rubi (Pico)

    celulas_html = ""
    for r in range(6):
        for c in range(10):
            num = r * 10 + c + 1
            f = cnt_dezenas[num]
            bg, text_color = obter_estilo_calor(f)
            celulas_html += f"""
            <div style="width:50px; height:50px; background:{bg}; color:{text_color}; border-radius:8px; display:flex; flex-direction:column; align-items:center; justify-content:center; font-family:monospace; border:1px solid rgba(0,0,0,0.12); box-shadow:0 1px 3px rgba(0,0,0,0.06);">
                <span style="font-size:16px; font-weight:900; line-height:1.1;">{num:02d}</span>
                <span style="font-size:11px; font-weight:800; opacity:0.95;">{f}x</span>
            </div>
            """

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ margin: 0; padding: 0; background: transparent; font-family: sans-serif; display: flex; justify-content: center; }}
        .heat-wrapper {{
            background: #ffffff;
            border: 2px solid #cbd5e1;
            border-radius: 14px;
            padding: 18px;
            width: fit-content;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        }}
        .heat-grid {{
            display: grid;
            grid-template-columns: repeat(10, 50px);
            gap: 6px;
            justify-content: center;
        }}
      </style>
    </head>
    <body>
      <div class="heat-wrapper">
        <div style="font-size:17px; font-weight:800; color:#15803d; text-align:center; margin-bottom:14px; font-family:sans-serif;">
            {titulo}
        </div>
        <div class="heat-grid">
            {celulas_html}
        </div>
        <div style="display:flex; justify-content:center; flex-wrap:wrap; gap:8px; margin-top:16px; font-size:12px; font-weight:700;">
            <div style="display:flex; align-items:center; gap:4px; background:#f8fafc; padding:4px 9px; border-radius:6px; border:1px solid #e2e8f0;"><span style="width:13px; height:13px; border-radius:3px; background:#dbeafe; border:1px solid #cbd5e1; display:inline-block;"></span> ❄️ Frias ({val_min}x)</div>
            <div style="display:flex; align-items:center; gap:4px; background:#f8fafc; padding:4px 9px; border-radius:6px; border:1px solid #e2e8f0;"><span style="width:13px; height:13px; border-radius:3px; background:#38bdf8; display:inline-block;"></span> 💧 Baixas</div>
            <div style="display:flex; align-items:center; gap:4px; background:#f8fafc; padding:4px 9px; border-radius:6px; border:1px solid #e2e8f0;"><span style="width:13px; height:13px; border-radius:3px; background:#22c55e; display:inline-block;"></span> 🌿 Médias</div>
            <div style="display:flex; align-items:center; gap:4px; background:#f8fafc; padding:4px 9px; border-radius:6px; border:1px solid #e2e8f0;"><span style="width:13px; height:13px; border-radius:3px; background:#eab308; display:inline-block;"></span> ☀️ Aquecidas</div>
            <div style="display:flex; align-items:center; gap:4px; background:#f8fafc; padding:4px 9px; border-radius:6px; border:1px solid #e2e8f0;"><span style="width:13px; height:13px; border-radius:3px; background:#f97316; display:inline-block;"></span> 🔥 Quentes</div>
            <div style="display:flex; align-items:center; gap:4px; background:#f8fafc; padding:4px 9px; border-radius:6px; border:1px solid #e2e8f0;"><span style="width:13px; height:13px; border-radius:3px; background:#ef4444; display:inline-block;"></span> 💥 Top ({val_max}x)</div>
        </div>
      </div>
    </body>
    </html>
    """
    components.html(full_html, height=470, scrolling=False)

def renderizar_card_aposta_colorido(idx, jogo, extra=""):
    dezenas_html = "".join([
        f"<span style='display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; background:linear-gradient(135deg, #16a34a, #15803d); color:#ffffff; font-weight:800; font-size:14px; border-radius:50%; margin:0 3px; box-shadow:0 2px 5px rgba(22,163,74,0.35); font-family:monospace;'>{n:02d}</span>"
        for n in jogo
    ])
    soma_val = sum(jogo)
    extra_txt = f"<span style='color:#15803d; font-weight:700; margin-right:8px;'>{extra}</span>" if extra else ""
    html = f"""
    <div style="background:#ffffff; border:1px solid #bbf7d0; border-left:5px solid #16a34a; border-radius:10px; padding:10px 16px; margin:8px 0; display:flex; justify-content:space-between; align-items:center; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
        <div style="display:flex; align-items:center; gap:12px;">
            <span style="font-weight:800; color:#0f172a; font-size:14px; font-family:sans-serif;">Aposta #{idx:02d}</span>
            <div>{dezenas_html}</div>
        </div>
        <div style="display:flex; align-items:center;">
            {extra_txt}
            <span style="background:#dcfce7; color:#15803d; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:700; font-family:sans-serif;">Soma: {soma_val}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def renderizar_card_conferencia_colorido(idx, jogo, acertos, tag, qtd):
    dezenas_html = ""
    for n in jogo:
        if n in acertos:
            dezenas_html += f"<span style='display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; background:linear-gradient(135deg, #16a34a, #15803d); color:#ffffff; font-weight:800; font-size:14px; border-radius:50%; margin:0 3px; box-shadow:0 2px 6px rgba(22,163,74,0.4); font-family:monospace;'>{n:02d}</span>"
        else:
            dezenas_html += f"<span style='display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; background:#f1f5f9; color:#475569; font-weight:700; font-size:14px; border-radius:50%; margin:0 3px; font-family:monospace; border:1px solid #cbd5e1;'>{n:02d}</span>"
    
    cor_badge = "#64748b"
    bg_badge = "#f1f5f9"
    if qtd == 6: cor_badge, bg_badge = "#b45309", "#fef3c7"
    elif qtd == 5: cor_badge, bg_badge = "#dc2626", "#fee2e2"
    elif qtd == 4: cor_badge, bg_badge = "#16a34a", "#dcfce7"

    html = f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:5px solid {cor_badge}; border-radius:10px; padding:10px 16px; margin:8px 0; display:flex; justify-content:space-between; align-items:center; box-shadow:0 2px 6px rgba(0,0,0,0.04);">
        <div style="display:flex; align-items:center; gap:12px;">
            <span style="font-weight:700; color:#334155; font-size:14px; font-family:sans-serif;">Bilhete #{idx:02d}</span>
            <div>{dezenas_html}</div>
        </div>
        <span style="background:{bg_badge}; color:{cor_badge}; padding:5px 12px; border-radius:14px; font-size:13px; font-weight:800; font-family:sans-serif;">{tag}</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def renderizar_volante_6x10(jogo, titulo=""):
    marcadas = set(jogo)
    celulas_html = ""
    for r in range(6):
        for c in range(10):
            num = r * 10 + c + 1
            if num in marcadas:
                bg = "linear-gradient(135deg, #16a34a, #15803d)"
                color = "#ffffff"
                border = "2px solid #0f5132"
                weight = "800"
            else:
                bg = "#f8fafc"
                color = "#475569"
                border = "1px solid #cbd5e1"
                weight = "600"
            celulas_html += f"""
            <div style="width:38px; height:38px; background:{bg}; color:{color}; border:{border}; font-weight:{weight}; border-radius:8px; display:flex; align-items:center; justify-content:center; font-family:monospace; font-size:13px;">
                {num:02d}
            </div>
            """

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ margin:0; padding:0; background:transparent; display:flex; justify-content:center; font-family:sans-serif; }}
        .volante-box {{
            background: #ffffff;
            border: 2px solid #16a34a;
            border-radius: 14px;
            padding: 16px;
            width: fit-content;
            box-shadow: 0 4px 16px rgba(22,163,74,0.15);
        }}
        .volante-grid {{
            display: grid;
            grid-template-columns: repeat(10, 38px);
            gap: 6px;
            justify-content: center;
        }}
      </style>
    </head>
    <body>
      <div class="volante-box">
        <div style="font-weight:800; font-size:16px; margin-bottom:12px; color:#15803d; text-align:center;">
            {titulo}
        </div>
        <div class="volante-grid">
            {celulas_html}
        </div>
      </div>
    </body>
    </html>
    """
    components.html(full_html, height=360, scrolling=False)

# ==============================================================================
# 5. INICIALIZAÇÃO DE ESTADO COM CONCURSOS REAIS DA CAIXA
# ==============================================================================
if "grupos_base" not in st.session_state:
    st.session_state.grupos_base = construir_todos_grupos()

if "historico_sorteios" not in st.session_state:
    with st.spinner("Conectando à API da Caixa e buscando os últimos 50 concursos reais da Mega-Sena..."):
        dados_oficiais, info_api = buscar_50_concursos_caixa()
        if dados_oficiais and len(dados_oficiais) >= 5:
            st.session_state.historico_sorteios = dados_oficiais
            st.session_state.origem_dados = f"Caixa Oficial ({info_api})"
        else:
            st.session_state.historico_sorteios = [list(j) for j in FALLBACK_MEGASENA]
            st.session_state.origem_dados = "Base Local de Contingência"

if "jogos_aleatorios" not in st.session_state: st.session_state.jogos_aleatorios = []
if "jogos_fechamento" not in st.session_state: st.session_state.jogos_fechamento = []
if "jogos_fechamento_filtrados" not in st.session_state: st.session_state.jogos_fechamento_filtrados = []

def sincronizar_filtros_com_historico(stats_atuais, top30):
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

    st.session_state.filtro_quads_ativo = True
    st.session_state.max_por_quadrante = 3
    st.session_state.min_quadrantes = 3

    for k, v in stats_atuais["stats_grupos"].items():
        eh_padrao = k in ["Pares", "Primos", "Moldura", "Centro (Miolo)"]
        mn, mx = int(v["min"]), int(v["max"])
        st.session_state[f"ativo_{k}"] = eh_padrao
        st.session_state[f"faixa_{k}"] = (mn, mx)

    st.session_state.dezenas_fechamento_input = " ".join([f"{n:02d}" for n in top30])
    st.session_state.jogos_fechamento = []
    st.session_state.jogos_fechamento_filtrados = []

def obter_regras_compiladas():
    regras = []
    for k, dezenas in st.session_state.grupos_base.items():
        if st.session_state.get(f"ativo_{k}", False):
            faixa = st.session_state.get(f"faixa_{k}", (0, 6))
            regras.append((frozenset(dezenas), faixa[0], faixa[1]))
    return regras

# ==============================================================================
# 6. BARRA LATERAL: CONTROLE DINÂMICO
# ==============================================================================
with st.sidebar:
    st.header("Janela Estatística (Mega-Sena)")
    total_disponivel = len(st.session_state.historico_sorteios)
    
    st.info(f"🌐 **Fonte:** {st.session_state.get('origem_dados', 'Caixa Oficial')}")
    
    qtd_analise = st.slider(
        "Quantidade de Concursos:",
        min_value=5,
        max_value=total_disponivel,
        value=min(30, total_disponivel),
        step=1
    )
    st.caption(f"Analisando os últimos {qtd_analise} sorteios.")
    auto_sinc = st.checkbox("Sincronizar Filtros Automaticamente", value=True)

    if st.button("🔄 Atualizar Resultados da Caixa Agora", use_container_width=True):
        st.cache_data.clear()
        dados_oficiais, info_api = buscar_50_concursos_caixa()
        if dados_oficiais:
            st.session_state.historico_sorteios = dados_oficiais
            st.session_state.origem_dados = f"Caixa Oficial ({info_api})"
            st.success("Resultados oficiais atualizados!")
            st.rerun()

    with st.expander("Inserir Concurso Manual"):
        novo_jogo_txt = st.text_input("6 Dezenas (ex: 04 15 28 35 44 58):")
        if st.button("Gravar Concurso"):
            nums = [int(n) for n in re.findall(r'\b\d+\b', novo_jogo_txt) if 1 <= int(n) <= 60]
            if len(nums) == 6:
                st.session_state.historico_sorteios.append(sorted(nums))
                st.success("Concurso da Mega-Sena salvo!")
                st.rerun()
            else:
                st.error("Digite exatamente 6 números entre 1 e 60.")

historico_ativo = st.session_state.historico_sorteios[-qtd_analise:]
stats = calcular_estatisticas_dinamicas(historico_ativo, st.session_state.grupos_base)
top30_elliott, lista_funil_detalhada = calcular_funil_elliott(historico_ativo)
ciclo_atual = calcular_ciclo_dezenas(st.session_state.historico_sorteios)
mapa_quadrantes = get_quadrantes_megasena()
quads_sets = {k: set(v) for k, v in mapa_quadrantes.items()}

# FINGERPRINT
fingerprint_atual = (qtd_analise, len(st.session_state.historico_sorteios), tuple(historico_ativo[-1]) if historico_ativo else ())

if "historico_fingerprint" not in st.session_state:
    st.session_state.historico_fingerprint = fingerprint_atual
    sincronizar_filtros_com_historico(stats, top30_elliott)
elif st.session_state.historico_fingerprint != fingerprint_atual:
    st.session_state.historico_fingerprint = fingerprint_atual
    if auto_sinc:
        sincronizar_filtros_com_historico(stats, top30_elliott)

# ==============================================================================
# 7. COMBINATÓRIA, DESDOBRAMENTO (6 DEZENAS) & VALIDAÇÃO
# ==============================================================================
def validar_jogo(cand, cand_set, regras_compiladas, f_soma, r_soma, f_consec, m_consec,
                 f_rep, r_rep, ult_set, f_coinc, max_c, hist_sets,
                 f_freq, r_q, r_f, s_q, s_f,
                 f_quads, max_q, min_q, q_sets):
    if f_soma and not (r_soma[0] <= sum(cand) <= r_soma[1]): return False
    if f_consec and contar_consecutivos(cand) > m_consec: return False
    for g_set, mn, mx in regras_compiladas:
        qtd = len(cand_set & g_set)
        if qtd < mn or qtd > mx: return False
    if f_rep and ult_set:
        rep = len(cand_set & ult_set)
        if not (r_rep[0] <= rep <= r_rep[1]): return False
    if f_coinc and hist_sets:
        for pass_set in hist_sets:
            if len(cand_set & pass_set) > max_c: return False
    if f_freq:
        if not (r_q[0] <= len(cand_set & s_q) <= r_q[1]): return False
        if not (r_f[0] <= len(cand_set & s_f) <= r_f[1]): return False
        
    if f_quads and q_sets:
        contagens = [len(cand_set & s) for s in q_sets.values()]
        if max(contagens) > max_q: return False
        if sum(1 for c in contagens if c > 0) < min_q: return False
            
    return True

def gerar_fechamento_guloso_megasena(dezenas, garantia):
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
                jogos.append(sorted(cands[:6]))
    return jogos

# ==============================================================================
# 8. INTERFACE PRINCIPAL
# ==============================================================================
st.title("🍀 Mega-Sena: Laboratório & Fechamentos")
st.caption(f"Análise Ativa: Últimos {qtd_analise} Concursos Reais • Matriz 6x10 • Top 30 Elliott • Linhas, Colunas, Moldura & Miolo.")

tab_fechamento, tab_gerador, tab_conferir, tab_filtros, tab_hist, tab_volante = st.tabs([
    "🎯 Fechamentos & Funil",
    "🚀 Gerador de Apostas",
    "🎟️ Conferir Jogos (TXT)",
    "⚙️ Filtros & Estatísticas",
    f"📜 Concursos ({qtd_analise}), Linhas, Colunas & Heatmap",
    "🗺️ Volante Visual 6x10"
])

hist_sets = [set(j) for j in historico_ativo]
ult_set = set(historico_ativo[-1]) if historico_ativo else set()
linhas_chaves = [f"Linha {i}" for i in range(1, 7)]
colunas_chaves = [f"Coluna {i}" for i in range(1, 11)]
diag_dir = [f"Diag Direita {i:02d}" for i in range(1, 11)]
diag_esq = [f"Diag Esquerda {i:02d}" for i in range(1, 11)]

# ==============================================================================
# ABA: FECHAMENTO & FUNIL DE ELLIOTT (TOP 30 MEGA-SENA)
# ==============================================================================
with tab_fechamento:
    st.markdown("### 🔄 Ciclo das Dezenas (Coupon Collector - 60 Dezenas)")
    col_c1, col_c2, col_c3 = st.columns([1, 1, 3])
    col_c1.metric("Ciclo Vigente", f"#{ciclo_atual['numero_ciclo']}")
    col_c2.metric("Sorteios no Ciclo", f"{ciclo_atual['sorteios_no_ciclo']}")
    with col_c3:
        st.write(f"**{ciclo_atual['qtd_faltantes']} Dezenas Faltantes para Fechar o Ciclo da Mega-Sena:**")
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
    st.subheader("2. As 30 Dezenas Ranqueadas pelo Funil de Elliott (Top 30)")
    str_sugestao_30 = " ".join([f"{n:02d}" for n in top30_elliott])
    st.code(f"Top 30 Elliott: {str_sugestao_30}")

    with st.expander("Ver Detalhes do Score do Funil (Top 30)"):
        df_funil = pd.DataFrame(lista_funil_detalhada[:30])
        df_funil.columns = ["Dezena", "Score Funil", "Total Saídas", "Saídas Recentes", "Momentum", "Atraso"]
        st.dataframe(df_funil, use_container_width=True)

    # 3. ESCOLHA DAS DEZENAS & RESULTADOS NA 3ª SEÇÃO
    st.divider()
    st.subheader("3. Escolha das Dezenas & Depuração Direta")
    c_fech1, c_fech2 = st.columns([3, 2])
    with c_fech1:
        entrada_manual = st.text_input(
            "Dezenas Selecionadas:",
            key="dezenas_fechamento_input",
            help="Altere os números livremente respeitando o intervalo de 7 a 30 dezenas."
        )
    with c_fech2:
        gar = st.selectbox(
            "Método de Desdobramento / Garantia (Mega-Sena):",
            [
                "Filtros Definidos (Apenas jogos 100% aprovados nas regras)",
                "Quadra (Garante 4 se 6)",
                "Quina (Garante 5 se 6)",
                "Sena (Garante 6 se 6 - 100% Fechado)",
                "Terno (Garante 3 se 6)"
            ],
            key="metodo_desdobramento_sel"
        )

    dezenas_digitadas = extrair_dezenas_texto(entrada_manual)
    st.write(f"Dezenas selecionadas ({len(dezenas_digitadas)}): `{' - '.join([f'{n:02d}' for n in dezenas_digitadas])}`")

    if len(dezenas_digitadas) < 7:
        st.info("Digite pelo menos 7 dezenas para calcular o desdobramento da Mega-Sena.")
    elif len(dezenas_digitadas) > 30:
        st.error(f"Você informou {len(dezenas_digitadas)} dezenas. O limite máximo é 30.")
    else:
        if st.button("Calcular e Depurar Jogos 🧮", use_container_width=True):
            regras_comp = obter_regras_compiladas()
            
            if "Filtros Definidos" in gar:
                with st.spinner("Analisando combinações e aplicando filtros ativos diretamente..."):
                    jogos_aprovados = []
                    total_testados = 0
                    teto_limite = 5000
                    
                    for comb in combinations(dezenas_digitadas, 6):
                        total_testados += 1
                        cand = sorted(list(comb))
                        if validar_jogo(cand, set(cand), regras_comp,
                                        st.session_state.filtro_soma_ativo, st.session_state.faixa_soma,
                                        st.session_state.filtro_consec_ativo, st.session_state.max_consec,
                                        st.session_state.f_rep_ant_ativo, st.session_state.rep_ant_faixa, ult_set,
                                        st.session_state.f_max_coinc_ativo, st.session_state.max_coinc_30, hist_sets,
                                        st.session_state.f_freq_30_ativo, st.session_state.faixa_quentes, st.session_state.faixa_frias,
                                        stats["quentes"], stats["frias"],
                                        st.session_state.filtro_quads_ativo, st.session_state.max_por_quadrante,
                                        st.session_state.min_quadrantes, quads_sets):
                            jogos_aprovados.append(cand)
                            if len(jogos_aprovados) >= teto_limite:
                                break

                    st.session_state.jogos_fechamento = jogos_aprovados
                    st.session_state.jogos_fechamento_filtrados = jogos_aprovados
                    st.session_state.taxa_cobertura = 100.0
                    st.session_state.total_combinacoes_testadas = total_testados
                    st.session_state.tipo_execucao_sec3 = "filtros_diretos"
            else:
                if len(dezenas_digitadas) > 20 and ("Quadra" in gar or "Quina" in gar):
                    st.warning("⚠️ Com muitas dezenas, o cálculo exato pode demorar alguns segundos.")
                with st.spinner("Processando fechamento matemático da Mega-Sena..."):
                    j_fech, cob = gerar_fechamento_guloso_megasena(dezenas_digitadas, gar)
                    st.session_state.jogos_fechamento = j_fech
                    st.session_state.jogos_fechamento_filtrados = []
                    st.session_state.taxa_cobertura = cob
                    st.session_state.total_combinacoes_testadas = None
                    st.session_state.tipo_execucao_sec3 = "garantia_pura"

    # EXIBIÇÃO DIRETA DOS RESULTADOS DA 3ª SEÇÃO
    if st.session_state.jogos_fechamento:
        qtd_total = len(st.session_state.jogos_fechamento)
        tipo_exec = st.session_state.get("tipo_execucao_sec3", "garantia_pura")
        
        st.markdown("#### 📊 Resultado da 3ª Seção (Mega-Sena):")
        if tipo_exec == "filtros_diretos":
            testados = st.session_state.get('total_combinacoes_testadas', qtd_total)
            st.success(f"🎯 **Depuração Concluída na 3ª Seção:** Das **{testados:,}** combinações testadas, **{qtd_total:,} jogos atenderam 100% dos filtros ativos**.")
        else:
            st.success(f"📦 **Desdobramento Concluído na 3ª Seção:** **{qtd_total:,} apostas geradas** com garantia de **{st.session_state.get('taxa_cobertura', 100):.1f}%**.")

        st.download_button(
            "📥 Baixar Jogos da 3ª Seção (.TXT)",
            data=converter_para_txt(st.session_state.jogos_fechamento),
            file_name="megasena_jogos_sec3.txt",
            mime="text/plain",
            key="btn_down_sec3",
            use_container_width=True
        )

        with st.expander(f"Ver Lista de Apostas da Mega-Sena ({qtd_total} jogos)", expanded=True):
            for i, j in enumerate(st.session_state.jogos_fechamento[:100]):
                renderizar_card_aposta_colorido(i + 1, j)
            if qtd_total > 100:
                st.caption(f"Mostrando as primeiras 100 de {qtd_total} apostas geradas. Baixe o arquivo TXT para ver a relação completa.")

    # 4. RE-DEPURAÇÃO ADICIONAL & UPLOAD EXTERNO
    st.divider()
    st.subheader("4. Re-depuração Adicional & Upload de Jogos")
    origem_depuracao = st.radio(
        "Selecione a fonte para re-depurar:",
        [
            "Apostas da 3ª Seção (Memória Atual)",
            "📁 Fazer Upload de Arquivo .TXT (Jogos Externos da Mega-Sena)"
        ],
        horizontal=True
    )

    base_para_filtrar = []
    nome_origem = ""

    if "Upload" in origem_depuracao:
        arq_upload = st.file_uploader(
            "Carregue o arquivo .TXT com apostas de 6 dezenas para refinar:",
            type=["txt"],
            key="upload_jogos_pre_depurados"
        )
        if arq_upload is not None:
            conteudo_txt = arq_upload.getvalue().decode("utf-8", errors="ignore")
            base_para_filtrar = ler_arquivo_jogos_txt(conteudo_txt)
            if base_para_filtrar:
                st.info(f"📂 **{len(base_para_filtrar):,} apostas da Mega-Sena** carregadas do arquivo.")
                nome_origem = "Arquivo TXT"
            else:
                st.error("Nenhuma aposta válida de 6 dezenas encontrada no arquivo.")
    else:
        if st.session_state.jogos_fechamento:
            base_para_filtrar = st.session_state.jogos_fechamento
            nome_origem = "Apostas da 3ª Seção"
            st.caption(f"Base disponível para re-filtrar: **{len(base_para_filtrar):,} apostas**.")
        else:
            st.info("Nenhuma aposta gerada na 3ª Seção para re-depurar.")

    if base_para_filtrar:
        if st.button("Executar Nova Passada de Filtros 🧹", use_container_width=True):
            regras_comp = obter_regras_compiladas()
            jogos_depurados = []
            
            with st.spinner("Re-filtrando apostas da Mega-Sena..."):
                for c in base_para_filtrar:
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
            
            qtd_ini = len(base_para_filtrar)
            qtd_fim = len(jogos_depurados)
            if qtd_fim > 0:
                reducao = ((qtd_ini - qtd_fim) / qtd_ini) * 100
                st.success(f"🎉 Re-depuração Concluída ({nome_origem})! De **{qtd_ini:,}** restaram **{qtd_fim:,} bilhetes** (Corte adicional de **{reducao:.1f}%**).")
            else:
                st.error("Nenhum jogo passou pelos filtros atuais.")

        if st.session_state.jogos_fechamento_filtrados:
            st.write(f"### 📋 Jogos Re-depurados ({len(st.session_state.jogos_fechamento_filtrados)} bilhetes):")
            st.download_button(
                "📥 Baixar Lista Re-depurada (.TXT)",
                data=converter_para_txt(st.session_state.jogos_fechamento_filtrados),
                file_name="megasena_redepurada_sec4.txt",
                mime="text/plain",
                key="btn_down_sec4",
                use_container_width=True
            )
            for i, j in enumerate(st.session_state.jogos_fechamento_filtrados[:100]):
                renderizar_card_aposta_colorido(i + 1, j)

# ==============================================================================
# ABA: GERADOR DE APOSTAS (6 DEZENAS)
# ==============================================================================
with tab_gerador:
    st.subheader("Gerar Combinações Validadas da Mega-Sena (6 Dezenas)")
    qtd = st.number_input("Quantidade de Jogos:", min_value=1, max_value=200, value=5)
    
    if st.button("Gerar Apostas da Mega-Sena 🚀", use_container_width=True):
        regras_comp = obter_regras_compiladas()
        jogos, unicos, t = [], set(), 0
        pool = list(range(1, 61))
        
        with st.spinner("Filtrando apostas da Mega-Sena segundo as regras..."):
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
            "Baixar Jogos da Mega-Sena em TXT",
            data=converter_para_txt(st.session_state.jogos_aleatorios),
            file_name="apostas_megasena.txt",
            mime="text/plain",
            use_container_width=True
        )
        for i, j in enumerate(st.session_state.jogos_aleatorios):
            renderizar_card_aposta_colorido(i + 1, j)

# ==============================================================================
# ABA: CONFERIR JOGOS (ARQUIVO .TXT - MEGA-SENA)
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
                "Jogos da 3ª Seção (Desdobramento/Filtros Diretos)",
                "Jogos Re-depurados da 4ª Seção",
                "Jogos do Gerador de Apostas"
            ]
        )
        if opcao_sessao == "Jogos da 3ª Seção (Desdobramento/Filtros Diretos)":
            jogos_conferir = st.session_state.jogos_fechamento
        elif opcao_sessao == "Jogos Re-depurados da 4ª Seção":
            jogos_conferir = st.session_state.jogos_fechamento_filtrados
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

            renderizar_card_conferencia_colorido(idx + 1, item["jogo"], item["acertos"], tag, qtd)

# ==============================================================================
# ABA: FILTROS & ESTATÍSTICAS (SISTEMA PADRONIZADO: LINHAS, COLUNAS E DIAGONAIS)
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

    # Quadrantes
    st.divider()
    st.markdown("### 📐 Filtro de Quadrantes 3x5 (Mega-Sena)")
    st.caption("Controla a dispersão nos 4 setores de 15 dezenas da cartela para evitar acúmulos improváveis.")
    cq1, cq2, cq3 = st.columns(3)
    with cq1:
        st.checkbox("Ativar Filtro de Quadrantes", key="filtro_quads_ativo")
    with cq2:
        if st.session_state.filtro_quads_ativo:
            st.slider("Máximo por Quadrante:", 1, 5, key="max_por_quadrante", help="Evita mais que X dezenas em um mesmo quadrante.")
    with cq3:
        if st.session_state.filtro_quads_ativo:
            st.slider("Mínimo de Quadrantes Presentes:", 1, 4, key="min_quadrantes", help="Exige que o jogo ocupe pelo menos X quadrantes distintos.")

    # Moldura, Miolo, Pares, Ímpares e Primos
    st.divider()
    st.write("Padrões da Matriz (Mega-Sena):")
    for padrao in ["Moldura", "Centro (Miolo)", "Pares", "Ímpares", "Primos"]:
        s_g = stats["stats_grupos"][padrao]
        chk, sl = st.columns([2, 3])
        with chk:
            st.checkbox(f"{padrao} (Saídas: {s_g['total_saidas']})", key=f"ativo_{padrao}")
        with sl:
            if st.session_state.get(f"ativo_{padrao}", False):
                st.slider(f"Faixa {padrao}", 0, 6, key=f"faixa_{padrao}", label_visibility="collapsed")

    # 6 Linhas da Matriz (Mesmo Sistema das Diagonais)
    st.divider()
    st.write("6 Linhas (Matriz 6x10):")
    cl_btn1, cl_btn2 = st.columns(2)
    with cl_btn1:
        if st.button("Ativar 6 Linhas", use_container_width=True):
            for k in linhas_chaves: st.session_state[f"ativo_{k}"] = True
            st.rerun()
    with cl_btn2:
        if st.button("Desativar Todas as Linhas", use_container_width=True):
            for k in linhas_chaves: st.session_state[f"ativo_{k}"] = False
            st.rerun()

    with st.expander("6 Linhas da Matriz"):
        for k in linhas_chaves:
            s_d = stats["stats_grupos"][k]
            chk, sl = st.columns([2, 3])
            with chk:
                st.checkbox(f"{k} (Saídas: {s_d['total_saidas']})", key=f"ativo_{k}")
            with sl:
                if st.session_state.get(f"ativo_{k}", False):
                    st.slider(f"Faixa {k}", 0, 6, key=f"faixa_{k}", label_visibility="collapsed")

    # 10 Colunas da Matriz (Mesmo Sistema das Diagonais)
    st.divider()
    st.write("10 Colunas (Matriz 6x10):")
    cc_btn1, cc_btn2 = st.columns(2)
    with cc_btn1:
        if st.button("Ativar 10 Colunas", use_container_width=True):
            for k in colunas_chaves: st.session_state[f"ativo_{k}"] = True
            st.rerun()
    with cc_btn2:
        if st.button("Desativar Todas as Colunas", use_container_width=True):
            for k in colunas_chaves: st.session_state[f"ativo_{k}"] = False
            st.rerun()

    with st.expander("10 Colunas da Matriz"):
        for k in colunas_chaves:
            s_d = stats["stats_grupos"][k]
            chk, sl = st.columns([2, 3])
            with chk:
                st.checkbox(f"{k} (Saídas: {s_d['total_saidas']})", key=f"ativo_{k}")
            with sl:
                if st.session_state.get(f"ativo_{k}", False):
                    st.slider(f"Faixa {k}", 0, 6, key=f"faixa_{k}", label_visibility="collapsed")

    # 20 Diagonais Cilíndricas (Mesmo Sistema)
    st.divider()
    st.write("20 Diagonais Cilíndricas (Matriz 6x10):")
    cd_btn1, cd_btn2 = st.columns(2)
    with cd_btn1:
        if st.button("Ativar 20 Diagonais", use_container_width=True):
            for i in range(1, 11):
                st.session_state[f"ativo_Diag Direita {i:02d}"] = True
                st.session_state[f"ativo_Diag Esquerda {i:02d}"] = True
            st.rerun()
    with cd_btn2:
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
# ABA: HISTÓRICO, LINHAS, COLUNAS, MOLDURA/MIOLO & HEATMAP
# ==============================================================================
with tab_hist:
    st.subheader("🔥 Mapa de Calor Térmico da Mega-Sena (Heatmap 6x10)")
    st.caption(f"Frequência absoluta das 60 dezenas no recorte dos últimos {qtd_analise} sorteios:")
    renderizar_heatmap_6x10_vibrante(stats["cnt_dezenas"], titulo=f"Heatmap das 60 Dezenas — Últimos {qtd_analise} Concursos")

    st.divider()
    st.subheader(f"Últimos {qtd_analise} Concursos Analisados")
    c_h1, c_h2 = st.columns([3, 2])
    with c_h1:
        dados_tabela = [
            {"Concurso": f"#{len(historico_ativo)-idx:02d}", "Dezenas": " - ".join([f"{n:02d}" for n in s]), "Soma": sum(s)}
            for idx, s in enumerate(reversed(historico_ativo))
        ]
        st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True, height=300)
    with c_h2:
        top_10 = [(d, stats["cnt_dezenas"][d]) for d in stats["ordenados_freq"][:10]]
        st.write("**Top 10 Quentes:** " + ", ".join([f"{d:02d} ({qtd}x)" for d, qtd in top_10]))
        bot_10 = sorted(stats["cnt_dezenas"].items(), key=lambda x: x[1])[:10]
        st.write("**Top 10 Frias:** " + ", ".join([f"{d:02d} ({qtd}x)" for d, qtd in bot_10]))

    # Painel Moldura vs. Miolo
    st.divider()
    st.subheader("🖼️ Desempenho: Moldura (28 dezenas) vs. Miolo (32 dezenas)")
    col_mold, col_miolo = st.columns(2)
    s_mold = stats["stats_grupos"]["Moldura"]
    s_miolo = stats["stats_grupos"]["Centro (Miolo)"]
    with col_mold:
        st.metric("Moldura (Perímetro Externo)", f"{s_mold['total_saidas']} saídas", f"Média: {s_mold['media']:.2f}")
        st.caption(f"Variação: Mínimo {s_mold['min']} | Máximo {s_mold['max']} dezenas.")
    with col_miolo:
        st.metric("Miolo (Centro Interno)", f"{s_miolo['total_saidas']} saídas", f"Média: {s_miolo['media']:.2f}")
        st.caption(f"Variação: Mínimo {s_miolo['min']} | Máximo {s_miolo['max']} dezenas.")

    # Tabela 6 Linhas
    st.divider()
    st.subheader("📏 Estatísticas Individuais das 6 Linhas (Mega-Sena)")
    dados_linhas = []
    for k in linhas_chaves:
        info = stats["stats_grupos"][k]
        dados_linhas.append({
            "Linha": k,
            "Total Saídas": info["total_saidas"],
            "Média por Jogo": f"{info['media']:.2f}",
            "Mín": info["min"],
            "Máx": info["max"],
            "Dezenas": " ".join([f"{n:02d}" for n in info["dezenas"]]),
            "Filtro Ativo": "Sim" if st.session_state.get(f"ativo_{k}", False) else "Não"
        })
    df_linhas = pd.DataFrame(dados_linhas).sort_values(by="Total Saídas", ascending=False)
    st.dataframe(df_linhas, use_container_width=True, height=270)

    # Tabela 10 Colunas
    st.divider()
    st.subheader("📐 Estatísticas Individuais das 10 Colunas (Mega-Sena)")
    dados_colunas = []
    for k in colunas_chaves:
        info = stats["stats_grupos"][k]
        dados_colunas.append({
            "Coluna": k,
            "Total Saídas": info["total_saidas"],
            "Média por Jogo": f"{info['media']:.2f}",
            "Mín": info["min"],
            "Máx": info["max"],
            "Dezenas": " ".join([f"{n:02d}" for n in info["dezenas"]]),
            "Filtro Ativo": "Sim" if st.session_state.get(f"ativo_{k}", False) else "Não"
        })
    df_colunas = pd.DataFrame(dados_colunas).sort_values(by="Total Saídas", ascending=False)
    st.dataframe(df_colunas, use_container_width=True, height=360)

    # 4 Quadrantes e 20 Diagonais
    st.divider()
    st.subheader("Mapeamento dos 4 Quadrantes (3x5 - 15 Dezenas Cada)")
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
# ABA: VOLANTE VISUAL (6x10 EM VERDE MEGA-SENA)
# ==============================================================================
with tab_volante:
    st.subheader("Visualizador da Cartela Oficial da Mega-Sena (6x10)")
    opcoes_visualizacao = ["Cartela Vazia"]
    
    lista_fechamento_ativa = st.session_state.jogos_fechamento_filtrados if st.session_state.jogos_fechamento_filtrados else st.session_state.jogos_fechamento
    if lista_fechamento_ativa:
        opcoes_visualizacao.extend([f"Aposta Depurada - #{i+1:02d}" for i in range(len(lista_fechamento_ativa[:100]))])
    if st.session_state.jogos_aleatorios:
        opcoes_visualizacao.extend([f"Gerador - #{i+1:02d}" for i in range(len(st.session_state.jogos_aleatorios))])

    escolha = st.selectbox("Selecione um jogo para ver na cartela:", opcoes_visualizacao)
    jogo_exibir = []
    if "Aposta Depurada" in escolha:
        idx = int(escolha.split("#")[1]) - 1
        jogo_exibir = lista_fechamento_ativa[idx]
    elif "Gerador" in escolha:
        idx = int(escolha.split("#")[1]) - 1
        jogo_exibir = st.session_state.jogos_aleatorios[idx]

    renderizar_volante_6x10(jogo_exibir, titulo=escolha)
