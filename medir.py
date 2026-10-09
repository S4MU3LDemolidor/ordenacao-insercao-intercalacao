"""Mede tempo e número de comparações da inserção, da intercalação e do
``sorted()``, salva os números brutos em CSV e gera os gráficos.

Uso:
    python medir.py                  # medição completa (~30 s)
    python medir.py --rapido         # versão curta, só para conferir que roda
    python medir.py --repeticoes 50  # mais repetições por medição

Tudo o que é gerado (dados*.csv e graficos/*.png) é sobrescrito a cada
execução. As listas são sorteadas a partir de uma semente fixa, então as
comparações da inserção e da intercalação saem idênticas em qualquer máquina.
Os tempos mudam, e as comparações do sorted() podem mudar com a versão do
Python (o Timsort do CPython foi alterado algumas vezes).
"""

import argparse
import csv
import math
import platform
import random
import statistics
import sys
import time
import timeit
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from ordenacao import ALGORITMOS, contar_comparacoes

PASTA = Path(__file__).resolve().parent
PASTA_GRAFICOS = PASTA / "graficos"

# Tamanhos pedidos na atividade.
TAMANHOS = [5, 10, 20, 30, 50, 75, 100, 200, 500, 1000]
# Varredura de n em n para achar o ponto de virada com precisão de 1 elemento.
TAMANHOS_VIRADA = list(range(2, 121))
# Experimento com listas quase ordenadas: n fixo, % de elementos fora do lugar.
N_QUASE_ORDENADA = 1000
PORCENTAGENS_FORA_DO_LUGAR = [0, 0.5, 1, 2, 3, 4, 5, 7.5, 10, 15, 20]

REPETICOES = 30          # a atividade pede no mínimo 10
TEMPO_MINIMO = 0.002     # segundos cronometrados, no mínimo, por repetição
SEMENTE = 2026

NOMES = {"insercao": "Inserção", "intercalacao": "Intercalação", "sorted": "sorted()"}


# ---------------------------------------------------------------------------
# Geração das listas
# ---------------------------------------------------------------------------

def gerador(semente, *chave):
    """Gerador aleatório reprodutível. A semente em texto passa por SHA-512
    dentro do ``random``, então o resultado é o mesmo em qualquer máquina."""
    return random.Random(":".join(str(p) for p in (semente, *chave)))


def lista_aleatoria(n, rng):
    """n inteiros distintos sorteados entre 0 e 999 999."""
    return rng.sample(range(1_000_000), n)


def lista_quase_ordenada(n, porcentagem, rng):
    """Lista ordenada em que ``porcentagem``% das posições, sorteadas, têm seus
    valores embaralhados entre si."""
    lista = sorted(lista_aleatoria(n, rng))
    posicoes = rng.sample(range(n), round(n * porcentagem / 100))
    valores = [lista[p] for p in posicoes]
    rng.shuffle(valores)
    for p, v in zip(posicoes, valores):
        lista[p] = v
    return lista


# ---------------------------------------------------------------------------
# Medição
# ---------------------------------------------------------------------------

def cronometrar(ordenar, lista, tempo_minimo=TEMPO_MINIMO):
    """Devolve (segundos por execução, número de execuções).

    Uma única ordenação de 5 elementos leva cerca de 1 µs, perto da resolução
    do relógio. Por isso a mesma lista é ordenada várias vezes seguidas até
    somar pelo menos ``tempo_minimo`` segundos, e o total é dividido pelo
    número de execuções. Como as funções devolvem uma lista nova, a entrada
    continua desordenada em todas as execuções. O ``timeit`` desliga o coletor
    de lixo durante a cronometragem.
    """
    timer = timeit.Timer("ordenar(lista)", globals={"ordenar": ordenar, "lista": lista})
    execucoes = 1
    while True:
        total = timer.timeit(execucoes)
        if total >= tempo_minimo:
            return total / execucoes, execucoes
        # Estima quantas execuções faltam para passar do mínimo (com folga).
        execucoes = max(2 * execucoes, math.ceil(1.2 * execucoes * tempo_minimo / max(total, 1e-9)))


def medir(casos, gerar_lista, algoritmos, repeticoes, semente, tempo_minimo, experimento):
    """Mede todos os ``casos`` (dicionários de parâmetros que vão para o CSV).

    Em cada repetição sorteia uma lista nova e mede todos os algoritmos sobre
    essa mesma lista, em ordem sorteada (para que nenhum algoritmo rode sempre
    primeiro). Devolve uma linha por (caso, repetição, algoritmo).
    """
    linhas = []
    for caso in casos:
        inicio = time.perf_counter()
        for repeticao in range(1, repeticoes + 1):
            rng = gerador(semente, experimento, *caso.values(), repeticao)
            lista = gerar_lista(caso, rng)
            esperado = sorted(lista)
            ordem = list(algoritmos)
            rng.shuffle(ordem)
            for nome in ordem:
                ordenar = ALGORITMOS[nome]
                segundos, execucoes = cronometrar(ordenar, lista, tempo_minimo)
                ordenada, comparacoes = contar_comparacoes(ordenar, lista)
                if ordenada != esperado:
                    raise AssertionError(f"{nome} ordenou errado: {caso}, repetição {repeticao}")
                linhas.append({
                    **caso,
                    "algoritmo": nome,
                    "repeticao": repeticao,
                    "tempo_us": segundos * 1e6,
                    "execucoes": execucoes,
                    "comparacoes": comparacoes,
                })
        parametros = ", ".join(f"{chave} = {valor}" for chave, valor in caso.items())
        print(f"      {parametros:<32} {time.perf_counter() - inicio:5.2f} s", flush=True)
    return linhas


def salvar_csv(linhas, caminho):
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({**linha, "tempo_us": f"{linha['tempo_us']:.4f}"})


def resumir(linhas, parametro="n"):
    """Agrupa por (algoritmo, parâmetro) e calcula média e desvio padrão do
    tempo e das comparações."""
    grupos = {}
    for linha in linhas:
        grupos.setdefault((linha["algoritmo"], linha[parametro]), []).append(linha)
    resumo = {}
    for chave, grupo in grupos.items():
        tempos = [g["tempo_us"] for g in grupo]
        comparacoes = [g["comparacoes"] for g in grupo]
        resumo[chave] = {
            "repeticoes": len(grupo),
            "tempo_medio": statistics.mean(tempos),
            "tempo_desvio": statistics.stdev(tempos) if len(tempos) > 1 else 0.0,
            "comparacoes_media": statistics.mean(comparacoes),
            "comparacoes_desvio": statistics.stdev(comparacoes) if len(comparacoes) > 1 else 0.0,
        }
    return resumo


def ponto_de_virada(valores, custo_a, custo_b):
    """Menor valor a partir do qual ``b`` custa menos que ``a`` em todos os
    valores seguintes (ou None se isso nunca acontece). Exigir "todos os
    seguintes" evita que uma oscilação de ruído perto do empate seja tomada
    como a virada."""
    virada = None
    for valor, a, b in zip(reversed(valores), reversed(custo_a), reversed(custo_b)):
        if b < a:
            virada = valor
        else:
            break
    return virada


# ---------------------------------------------------------------------------
# Teoria: valores esperados e limites
# ---------------------------------------------------------------------------

def comparacoes_esperadas_insercao(n):
    """Média exata de comparações da inserção sobre todas as permutações de n
    elementos distintos.

    Cada inversão custa uma comparação que desloca um elemento; cada elemento
    a partir do segundo faz ainda uma comparação que para o laço, exceto
    quando é o menor até ali (o laço para por j < 0, sem comparar). São
    n(n-1)/4 inversões em média e o elemento i é o menor até ali com
    probabilidade 1/i, o que dá n(n-1)/4 + (n-1) - (H_n - 1).
    """
    harmonico = sum(Fraction(1, k) for k in range(1, n + 1))
    return Fraction(n * (n - 1), 4) + n - harmonico


@lru_cache(maxsize=None)
def comparacoes_esperadas_intercalacao(n):
    """Média exata de comparações desta intercalação sobre todas as
    permutações de n elementos distintos.

    Intercalar p e q elementos custa p + q menos o que sobra no lado que não
    acabou; em média sobram p/(q+1) + q/(p+1).
    """
    if n <= 1:
        return Fraction(0)
    p, q = n // 2, n - n // 2
    intercalar = p + q - Fraction(p, q + 1) - Fraction(q, p + 1)
    return comparacoes_esperadas_intercalacao(p) + comparacoes_esperadas_intercalacao(q) + intercalar


def log2_fatorial(n):
    """log2(n!): limite inferior de comparações de qualquer ordenação por
    comparação (no pior caso e também em média)."""
    return math.lgamma(n + 1) / math.log(2)


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

CORES = {"insercao": "#2a78d6", "intercalacao": "#eb6834", "sorted": "#1baf7a"}
MARCADORES = {"insercao": "o", "intercalacao": "s", "sorted": "^"}
COR_TEMPO, COR_COMPARACOES = "#4a3aa7", "#008300"
TINTA, TINTA_SECUNDARIA, TINTA_MUDA = "#0b0b0b", "#52514e", "#898781"
GRADE, EIXO, FUNDO = "#e1e0d9", "#c3c2b7", "#fcfcfb"


def importar_pyplot():
    try:
        import matplotlib
    except ImportError:
        sys.exit(
            "Erro: o matplotlib não está instalado (ele é usado para gerar os gráficos).\n"
            "Instale com:  python -m pip install -r requirements.txt"
        )
    matplotlib.use("Agg")  # gera arquivos sem precisar de janela/interface gráfica
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": FUNDO,
        "axes.facecolor": FUNDO,
        "savefig.facecolor": FUNDO,
        "axes.edgecolor": EIXO,
        "axes.labelcolor": TINTA_SECUNDARIA,
        "axes.titlecolor": TINTA,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRADE,
        "grid.linewidth": 0.8,
        "xtick.color": TINTA_MUDA,
        "ytick.color": TINTA_MUDA,
        "xtick.labelcolor": TINTA_SECUNDARIA,
        "ytick.labelcolor": TINTA_SECUNDARIA,
        "legend.frameon": False,
        "legend.labelcolor": TINTA,
        "lines.linewidth": 2,
        "lines.markersize": 5.5,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "font.size": 10,
    })
    return plt


def _serie(resumo, algoritmo, valores, campo):
    return [resumo[(algoritmo, v)][campo] for v in valores]


def _formato_decimal():
    """Números dos eixos com vírgula decimal (0,1 em vez de 0.1)."""
    from matplotlib.ticker import FuncFormatter

    return FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))


def _linha(ax, x, y, algoritmo, desvio=None):
    ax.plot(x, y, color=CORES[algoritmo], marker=MARCADORES[algoritmo],
            markeredgecolor=FUNDO, markeredgewidth=1.2, label=NOMES[algoritmo])
    if desvio is not None:
        baixo = [max(m - d, 1e-12) for m, d in zip(y, desvio)]
        alto = [m + d for m, d in zip(y, desvio)]
        ax.fill_between(x, baixo, alto, color=CORES[algoritmo], alpha=0.12, linewidth=0)


def _marcar_virada(ax, x, texto, cor=TINTA_MUDA, y=1.0, lado="direita", coordenada_y="axes fraction"):
    ax.axvline(x, color=cor, linewidth=1, linestyle=(0, (4, 3)))
    deslocamento = 6 if lado == "direita" else -6
    ax.annotate(texto, xy=(x, y), xycoords=("data", coordenada_y), xytext=(deslocamento, -4),
                textcoords="offset points", va="top", ha="left" if lado == "direita" else "right",
                color=TINTA_SECUNDARIA, fontsize=9)


def _escala_log(ax, marcas_y=None):
    from matplotlib.ticker import FixedLocator

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_locator(FixedLocator([5, 10, 20, 50, 100, 200, 500, 1000]))
    if marcas_y:
        ax.yaxis.set_major_locator(FixedLocator(marcas_y))
    ax.xaxis.set_major_formatter(_formato_decimal())
    ax.yaxis.set_major_formatter(_formato_decimal())
    ax.minorticks_off()


def _titulo(figura, texto):
    figura.suptitle(texto, x=0.01, ha="left", fontsize=13, fontweight="bold", color=TINTA)


def grafico_tempos(plt, resumo, virada, caminho):
    figura, (geral, zoom) = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    pequenos = [n for n in TAMANHOS if n <= 100]
    for algoritmo in ALGORITMOS:
        media = _serie(resumo, algoritmo, TAMANHOS, "tempo_medio")
        desvio = _serie(resumo, algoritmo, TAMANHOS, "tempo_desvio")
        _linha(geral, TAMANHOS, media, algoritmo, desvio)
        _linha(zoom, pequenos, media[:len(pequenos)], algoritmo, desvio[:len(pequenos)])
    _escala_log(geral)
    geral.set_title("Todos os tamanhos (escala log-log)")
    zoom.set_title("Zoom em n ≤ 100 (escala linear)")
    zoom.set_xticks(pequenos)
    zoom.set_ylim(bottom=0)
    if virada and virada <= 100:
        _marcar_virada(zoom, virada, f"intercalação mais rápida\na partir de n = {virada}",
                       y=0.3, lado="esquerda" if virada > 60 else "direita")
    for ax in (geral, zoom):
        ax.set_xlabel("n (tamanho da lista)")
        ax.set_ylabel("tempo médio por ordenação (µs)")
        ax.legend(loc="upper left")
    _titulo(figura, "Tempo de ordenação de listas aleatórias (média e faixa de ±1 desvio padrão)")
    figura.savefig(caminho, dpi=150)
    plt.close(figura)


def grafico_comparacoes(plt, resumo, virada, caminho):
    figura, (geral, limite) = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    razoes = {}
    for algoritmo in ALGORITMOS:
        media = _serie(resumo, algoritmo, TAMANHOS, "comparacoes_media")
        razoes[algoritmo] = [m / log2_fatorial(n) for m, n in zip(media, TAMANHOS)]
        _linha(geral, TAMANHOS, media, algoritmo)
        _linha(limite, TAMANHOS, razoes[algoritmo], algoritmo)

    continuo = [5 * 1.02 ** k for k in range(400) if 5 * 1.02 ** k <= 1000]
    referencias = [
        ("n²/4", lambda n: n * n / 4, (0, (5, 3))),
        ("n·log₂n", lambda n: n * math.log2(n), (0, (1, 2))),
        ("log₂(n!)  (limite inferior)", log2_fatorial, (0, (6, 2, 1, 2))),
    ]
    for rotulo, funcao, estilo in referencias:
        geral.plot(continuo, [funcao(n) for n in continuo], color=TINTA_MUDA, linewidth=1.1,
                   linestyle=estilo, label=rotulo)
    _escala_log(geral)
    geral.set_title("Comparações (escala log-log)")
    geral.set_ylabel("comparações (média das repetições)")
    geral.legend(loc="upper left", fontsize=9)

    # Painel da direita: cada curva dividida por log₂(n!). Dividir todas pelo
    # mesmo número não muda quem compara menos, mas amplia a região perto do
    # limite, onde intercalação e sorted() ficam sobrepostas no painel da esquerda.
    limite.plot(continuo, [n * math.log2(n) / log2_fatorial(n) for n in continuo], color=TINTA_MUDA,
                linewidth=1.1, linestyle=(0, (1, 2)), label="n·log₂n")
    limite.axhline(1, color=TINTA_SECUNDARIA, linewidth=1)
    limite.annotate("1 = log₂(n!), o mínimo possível", xy=(1000, 1), xytext=(0, -5), textcoords="offset points",
                    ha="right", va="top", color=TINTA_SECUNDARIA, fontsize=9)
    ultima = razoes["insercao"][-1]
    limite.annotate(f"a inserção sai do gráfico:\nchega a {_numero(ultima)}× em n = {TAMANHOS[-1]}",
                    xy=(22, 1.8), xytext=(8, 0), textcoords="offset points", ha="left", va="top",
                    color=TINTA_SECUNDARIA, fontsize=9)
    _escala_log(limite)
    limite.set_yscale("linear")
    limite.set_ylim(0.9, 1.8)
    limite.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}×".replace(".", ",")))
    if virada:
        _marcar_virada(limite, virada, f"virada: n = {virada}", y=0.985, coordenada_y="data")
    limite.set_title("Zoom perto do limite: comparações ÷ log₂(n!)")
    limite.set_ylabel("comparações ÷ log₂(n!)")
    limite.legend(loc="upper right", fontsize=9)
    for ax in (geral, limite):
        ax.set_xlabel("n (tamanho da lista)")
    _titulo(figura, "Número de comparações em listas aleatórias")
    figura.savefig(caminho, dpi=150)
    plt.close(figura)


def grafico_virada(plt, resumo, ns, virada_tempo, virada_comparacoes, caminho):
    from matplotlib.ticker import FixedLocator, FuncFormatter

    razao_tempo = [resumo[("insercao", n)]["tempo_medio"] / resumo[("intercalacao", n)]["tempo_medio"]
                   for n in ns]
    razao_comp = [resumo[("insercao", n)]["comparacoes_media"] / resumo[("intercalacao", n)]["comparacoes_media"]
                  for n in ns]
    teoria = [float(comparacoes_esperadas_insercao(n) / comparacoes_esperadas_intercalacao(n)) for n in ns]

    figura, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    ax.axhline(1, color=TINTA_SECUNDARIA, linewidth=1)
    ax.plot(ns, teoria, color=TINTA_MUDA, linewidth=1.1, linestyle=(0, (5, 3)),
            label="comparações (valor esperado, teoria)")
    ax.plot(ns, razao_comp, color=COR_COMPARACOES, label="comparações (medido)")
    ax.plot(ns, razao_tempo, color=COR_TEMPO, label="tempo (medido)")
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(FixedLocator([0.25, 0.5, 1, 2, 4, 8]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}×".replace(".", ",")))
    ax.minorticks_off()
    ax.set_xlim(0, ns[-1] + 2)
    ax.set_ylim(0.15, 7)
    if virada_comparacoes:
        _marcar_virada(ax, virada_comparacoes, f"virada em comparações:\nn = {virada_comparacoes}",
                       cor=COR_COMPARACOES, y=0.8, coordenada_y="data")
    if virada_tempo:
        _marcar_virada(ax, virada_tempo, f"virada em tempo:\nn = {virada_tempo}",
                       cor=COR_TEMPO, y=2.4, coordenada_y="data")
    ax.annotate("↑ intercalação melhor", xy=(48, 1), xytext=(0, 4), textcoords="offset points",
                va="bottom", color=TINTA_SECUNDARIA, fontsize=9)
    ax.annotate("↓ inserção melhor", xy=(48, 1), xytext=(0, -4), textcoords="offset points",
                va="top", color=TINTA_SECUNDARIA, fontsize=9)
    ax.set_xlabel("n (tamanho da lista)")
    ax.set_ylabel("custo da inserção ÷ custo da intercalação")
    ax.set_title("Ponto de virada: inserção ÷ intercalação para cada n de 2 a 120 (listas aleatórias)")
    ax.legend(loc="upper left")
    figura.savefig(caminho, dpi=150)
    plt.close(figura)


def grafico_quase_ordenada(plt, resumo, pcts, virada, caminho):
    from matplotlib.ticker import FuncFormatter

    figura, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    for algoritmo in ALGORITMOS:
        media = [resumo[(algoritmo, p)]["tempo_medio"] / 1000 for p in pcts]
        desvio = [resumo[(algoritmo, p)]["tempo_desvio"] / 1000 for p in pcts]
        _linha(ax, pcts, media, algoritmo, desvio)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(_formato_decimal())
    ax.minorticks_off()
    if virada is not None:
        _marcar_virada(ax, virada, f"intercalação mais rápida a partir\nde {virada:g}% fora do lugar".replace(".", ","),
                       y=0.97)
    ax.set_xticks([p for p in pcts if p == 0 or p >= 1])  # 0,5% ficaria grudado no 0% e no 1%
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%".replace(".", ",")))
    ax.set_xlabel("elementos fora do lugar (posições sorteadas e embaralhadas entre si)")
    ax.set_ylabel("tempo médio por ordenação (ms, escala log)")
    ax.set_title(f"Listas quase ordenadas, n = {N_QUASE_ORDENADA} (média e faixa de ±1 desvio padrão)")
    ax.legend(loc="lower right")
    figura.savefig(caminho, dpi=150)
    plt.close(figura)


# ---------------------------------------------------------------------------
# Saída no terminal
# ---------------------------------------------------------------------------

def _numero(valor, casas=1):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_tabelas(resumo):
    print("\nTempo médio por ordenação (µs) ± desvio padrão")
    print("| n | Inserção | Intercalação | sorted() |")
    print("|---:|---:|---:|---:|")
    for n in TAMANHOS:
        celulas = [f"{_numero(resumo[(a, n)]['tempo_medio'], 2)} ± {_numero(resumo[(a, n)]['tempo_desvio'], 2)}"
                   for a in ALGORITMOS]
        print(f"| {n} | " + " | ".join(celulas) + " |")

    print("\nComparações (média das repetições)")
    print("| n | Inserção | Intercalação | sorted() | log₂(n!) | n·log₂n |")
    print("|---:|---:|---:|---:|---:|---:|")
    for n in TAMANHOS:
        celulas = [_numero(resumo[(a, n)]["comparacoes_media"]) for a in ALGORITMOS]
        celulas += [_numero(log2_fatorial(n)), _numero(n * math.log2(n))]
        print(f"| {n} | " + " | ".join(celulas) + " |")

    print("\nTempo médio por comparação (ns) = tempo médio ÷ comparações médias")
    print("| n | Inserção | Intercalação | sorted() |")
    print("|---:|---:|---:|---:|")
    for n in TAMANHOS:
        celulas = [_numero(1000 * resumo[(a, n)]["tempo_medio"] / resumo[(a, n)]["comparacoes_media"])
                   for a in ALGORITMOS]
        print(f"| {n} | " + " | ".join(celulas) + " |")


# ---------------------------------------------------------------------------

def main():
    # No Windows, com a saída redirecionada, caracteres como "₂" podem não
    # existir na codificação do terminal; troca por "?" em vez de dar erro.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repeticoes", type=int, default=REPETICOES,
                        help=f"repetições por tamanho (padrão {REPETICOES}, mínimo 10)")
    parser.add_argument("--semente", type=int, default=SEMENTE, help=f"semente aleatória (padrão {SEMENTE})")
    parser.add_argument("--rapido", action="store_true",
                        help="10 repetições e varreduras reduzidas, só para conferir que tudo roda")
    args = parser.parse_args()
    if args.repeticoes < 10:
        parser.error("use pelo menos 10 repetições")

    plt = importar_pyplot()  # falha logo, antes de medir, se faltar o matplotlib
    repeticoes, tempo_minimo = args.repeticoes, TEMPO_MINIMO
    tamanhos_virada, porcentagens = TAMANHOS_VIRADA, PORCENTAGENS_FORA_DO_LUGAR
    if args.rapido:
        repeticoes, tempo_minimo = 10, 0.0005
        tamanhos_virada, porcentagens = TAMANHOS_VIRADA[::6], PORCENTAGENS_FORA_DO_LUGAR[::2]

    print(f"Python {platform.python_version()} ({platform.python_implementation()}) em "
          f"{platform.system()} {platform.machine()}")
    print(f"semente {args.semente}, {repeticoes} repetições por tamanho\n")
    inicio = time.perf_counter()

    print("[1/3] Listas aleatórias nos tamanhos pedidos")
    principal = medir([{"n": n} for n in TAMANHOS], lambda c, rng: lista_aleatoria(c["n"], rng),
                      ALGORITMOS, repeticoes, args.semente, tempo_minimo, "principal")
    salvar_csv(principal, PASTA / "dados.csv")

    print("[2/3] Varredura fina para achar o ponto de virada")
    virada = medir([{"n": n} for n in tamanhos_virada], lambda c, rng: lista_aleatoria(c["n"], rng),
                   ["insercao", "intercalacao"], repeticoes, args.semente, tempo_minimo, "virada")
    salvar_csv(virada, PASTA / "dados_virada.csv")

    print("[3/3] Listas quase ordenadas")
    quase = medir([{"n": N_QUASE_ORDENADA, "fora_do_lugar_pct": p} for p in porcentagens],
                  lambda c, rng: lista_quase_ordenada(c["n"], c["fora_do_lugar_pct"], rng),
                  ALGORITMOS, repeticoes, args.semente, tempo_minimo, "quase_ordenada")
    salvar_csv(quase, PASTA / "dados_quase_ordenada.csv")

    r_principal = resumir(principal)
    r_virada = resumir(virada)
    r_quase = resumir(quase, "fora_do_lugar_pct")

    def virada_em(resumo, valores, campo):
        return ponto_de_virada(valores, _serie(resumo, "insercao", valores, campo),
                               _serie(resumo, "intercalacao", valores, campo))

    tempo_principal = virada_em(r_principal, TAMANHOS, "tempo_medio")
    comp_principal = virada_em(r_principal, TAMANHOS, "comparacoes_media")
    tempo_fino = virada_em(r_virada, tamanhos_virada, "tempo_medio")
    comp_fino = virada_em(r_virada, tamanhos_virada, "comparacoes_media")
    comp_teoria = ponto_de_virada(TAMANHOS_VIRADA, [comparacoes_esperadas_insercao(n) for n in TAMANHOS_VIRADA],
                                  [comparacoes_esperadas_intercalacao(n) for n in TAMANHOS_VIRADA])
    pct_quase = virada_em(r_quase, porcentagens, "tempo_medio")

    PASTA_GRAFICOS.mkdir(exist_ok=True)
    grafico_tempos(plt, r_principal, tempo_principal, PASTA_GRAFICOS / "tempos.png")
    grafico_comparacoes(plt, r_principal, comp_principal, PASTA_GRAFICOS / "comparacoes.png")
    grafico_virada(plt, r_virada, tamanhos_virada, tempo_fino, comp_fino, PASTA_GRAFICOS / "virada.png")
    grafico_quase_ordenada(plt, r_quase, porcentagens, pct_quase, PASTA_GRAFICOS / "quase_ordenada.png")

    imprimir_tabelas(r_principal)
    print("\nPonto de virada (intercalação passa a ganhar e não perde mais)")
    print(f"  tempo,       tamanhos pedidos: n = {tempo_principal}")
    print(f"  tempo,       varredura n a n:  n = {tempo_fino}")
    print(f"  comparações, tamanhos pedidos: n = {comp_principal}")
    print(f"  comparações, varredura n a n:  n = {comp_fino}")
    print(f"  comparações, valor esperado:   n = {comp_teoria}")
    print(f"  quase ordenada (n = {N_QUASE_ORDENADA}): a partir de {pct_quase}% fora do lugar")
    print(f"\nArquivos gerados: dados.csv, dados_virada.csv, dados_quase_ordenada.csv, graficos/*.png "
          f"({time.perf_counter() - inicio:.0f} s)")


if __name__ == "__main__":
    main()
