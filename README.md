# Ordenação por inserção × ordenação por intercalação

[![testes](https://github.com/S4MU3LDemolidor/ordenacao-insercao-intercalacao/actions/workflows/testes.yml/badge.svg)](https://github.com/S4MU3LDemolidor/ordenacao-insercao-intercalacao/actions/workflows/testes.yml)

Implementação da ordenação por inserção e da ordenação por intercalação (merge
sort) em Python, com medição de tempo e de número de comparações para listas
aleatórias de 5 a 1000 elementos, comparação com o `sorted()` e contagem das
comparações do próprio `sorted()`.

**A análise completa está no [RELATORIO.md](RELATORIO.md).** Principais
resultados:

- Em **tempo**, a intercalação passa a ser mais rápida a partir de **n = 100**
  entre os tamanhos pedidos (≈ 95 medindo n de 1 em 1).
- Em **comparações**, ela já ganha a partir de **n = 4**. A diferença vem do
  custo de cada comparação: na intercalação ela custa ~4,6 vezes mais que na
  inserção (recursão, cópias de listas, `append`).
- O `sorted()` faz quase as mesmas comparações que a intercalação, mas é ~23
  vezes mais rápido porque roda em C. Por isso ele não serve para decidir entre
  os dois algoritmos.
- Em listas quase ordenadas a inserção ganha mesmo com n = 1000: com a lista
  já ordenada, foi 15 vezes mais rápida.

![Tempos](graficos/tempos.png)

## Arquivos

| arquivo | o que é |
|---|---|
| [`ordenacao.py`](ordenacao.py) | os dois métodos de ordenação e a contagem de comparações |
| [`testes.py`](testes.py) | testes que provam que os dois ordenam certo e que a contagem de comparações está certa |
| [`medir.py`](medir.py) | roda todas as medições e gera os CSVs e os gráficos |
| [`dados.csv`](dados.csv) | números brutos das medições pedidas (uma linha por repetição) |
| [`RELATORIO.md`](RELATORIO.md) | a análise |
| [`graficos/`](graficos) | `tempos.png` e `comparacoes.png` (pedidos), mais `virada.png` e `quase_ordenada.png` |
| [`dados_virada.csv`](dados_virada.csv) | extra: tempos e comparações para cada n de 2 a 120, para achar o ponto de virada |
| [`dados_quase_ordenada.csv`](dados_quase_ordenada.csv) | extra: listas de 1000 elementos com 0% a 20% dos elementos fora do lugar |
| [`requirements.txt`](requirements.txt) | dependência (só o matplotlib, para os gráficos) |

## Como rodar

É preciso ter o **Python 3.9 ou mais novo**. Os testes e os algoritmos usam só a
biblioteca padrão; o `medir.py` precisa do `matplotlib` para desenhar os
gráficos.

```bash
git clone https://github.com/S4MU3LDemolidor/ordenacao-insercao-intercalacao.git
cd ordenacao-insercao-intercalacao
python3 -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

No Windows, use `python` no lugar de `python3` no comando que cria o ambiente.
Com o ambiente ativado, `python` funciona em qualquer sistema.

### Testes

```bash
python testes.py
```

São 54 testes e levam menos de 1 segundo. Cobrem os casos difíceis pedidos
(**lista vazia, um elemento, todos iguais, já ordenada, invertida**) e também:
dois elementos, tamanhos pares e ímpares, repetidos, negativos e decimais,
textos, tuplas e `range` como entrada, todas as permutações de até 7 elementos,
500 listas aleatórias, estabilidade, não alterar a lista de entrada e devolver
uma lista nova. Também conferem a contagem de comparações contra fórmulas exatas
(por exemplo, a inserção faz n − 1 comparações numa lista ordenada e n(n−1)/2
numa invertida).

Também funciona com `python -m pytest testes.py`, se o pytest estiver
instalado.

### Medições

```bash
python medir.py
```

Leva cerca de 30 segundos e **refaz do zero** `dados.csv`, `dados_virada.csv`,
`dados_quase_ordenada.csv` e os quatro gráficos em `graficos/`. No fim, imprime
as tabelas de tempo, comparações e custo por comparação, e os pontos de virada
calculados para a sua máquina.

Opções:

| comando | o que faz |
|---|---|
| `python medir.py --repeticoes 50` | mais repetições por tamanho (padrão 30, mínimo 10) |
| `python medir.py --semente 7` | sorteia outras listas (padrão 2026) |
| `python medir.py --rapido` | versão de ~3 segundos, só para ver que tudo roda (**sobrescreve os CSVs e gráficos** com dados menos precisos) |

**O que muda na sua máquina:** as listas vêm de uma semente fixa, então a
coluna `comparacoes` da inserção e da intercalação sai **idêntica** à deste
repositório. Os tempos mudam com o computador e com a versão do Python, e o
ponto de virada em tempo muda junto (no Python 3.9 ele ficou entre 62 e 75; no
3.14, perto de 95). As comparações do `sorted()` podem variar um pouco entre
versões do Python, porque o Timsort do CPython já foi alterado algumas vezes.

## Como as medições são feitas

- Cada tamanho é medido **30 vezes**, cada vez com uma lista aleatória nova, e
  o valor usado é a **média**. Os três métodos ordenam a mesma lista em cada
  repetição.
- Para listas pequenas, uma única ordenação leva menos de 1 µs. Por isso cada
  repetição ordena a mesma lista várias vezes seguidas, até somar pelo menos
  2 ms, e divide o total pelo número de execuções (coluna `execucoes`).
- As comparações são contadas embrulhando cada elemento num objeto cujo `<`
  incrementa um contador (`ElementoContado`, em `ordenacao.py`). Os algoritmos
  não têm contador nenhum dentro deles, então o tempo é medido sem esse custo
  extra, e o `sorted()` é contado exatamente do mesmo jeito.

Colunas de `dados.csv`:

| coluna | significado |
|---|---|
| `n` | tamanho da lista |
| `algoritmo` | `insercao`, `intercalacao` ou `sorted` |
| `repeticao` | 1 a 30 |
| `tempo_us` | tempo médio de uma ordenação nessa repetição, em microssegundos |
| `execucoes` | quantas vezes a lista foi ordenada para medir esse tempo |
| `comparacoes` | número de comparações entre elementos para ordenar essa lista |

O GitHub Actions roda os testes e o `medir.py --rapido` em Linux, Windows e
macOS, com Python 3.10 e 3.14, a cada push (selo no topo desta página).
