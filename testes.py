"""Testes da ordenação por inserção, da ordenação por intercalação e da
contagem de comparações.

Rodar:  python testes.py        (só usa a biblioteca padrão)
   ou:  python -m pytest testes.py
"""

import itertools
import math
import random
import unittest
from fractions import Fraction

from medir import (
    comparacoes_esperadas_insercao,
    comparacoes_esperadas_intercalacao,
    gerador,
    lista_aleatoria,
    lista_quase_ordenada,
    log2_fatorial,
    ponto_de_virada,
)
from ordenacao import (
    ElementoContado,
    Contador,
    contar_comparacoes,
    ordenar_por_insercao,
    ordenar_por_intercalacao,
)


class Registro:
    """Compara só pela chave. Serve para testar estabilidade: dois registros
    com a mesma chave devem sair na mesma ordem em que entraram."""

    def __init__(self, chave, origem):
        self.chave = chave
        self.origem = origem

    def __lt__(self, outro):
        return self.chave < outro.chave

    def __repr__(self):
        return f"Registro({self.chave!r}, {self.origem!r})"


class CasosDeOrdenacao:
    """Testes que valem para qualquer algoritmo de ordenação. As subclasses
    abaixo definem ``ordenar``; esta classe sozinha não roda."""

    ordenar = None

    def confere(self, entrada):
        self.assertEqual(self.ordenar(entrada), sorted(entrada))

    # --- casos difíceis pedidos na atividade -----------------------------

    def test_lista_vazia(self):
        self.assertEqual(self.ordenar([]), [])

    def test_um_elemento(self):
        self.assertEqual(self.ordenar([42]), [42])

    def test_todos_iguais(self):
        self.assertEqual(self.ordenar([7] * 50), [7] * 50)

    def test_ja_ordenada(self):
        self.assertEqual(self.ordenar(list(range(100))), list(range(100)))

    def test_invertida(self):
        self.assertEqual(self.ordenar(list(range(100, 0, -1))), list(range(1, 101)))

    # --- outros casos de borda -------------------------------------------

    def test_dois_elementos(self):
        self.assertEqual(self.ordenar([1, 2]), [1, 2])
        self.assertEqual(self.ordenar([2, 1]), [1, 2])

    def test_dois_valores_alternados(self):
        self.confere([1, 0] * 25)

    def test_repetidos(self):
        self.confere([3, 1, 2, 3, 1, 2, 3, 3, 0, 1])

    def test_negativos_e_decimais(self):
        self.confere([-1.5, 3, 0, -10, 2.25, 0, -0.5])

    def test_tamanho_impar_e_par(self):
        for n in (3, 4, 7, 8, 9, 15, 16, 17):
            with self.subTest(n=n):
                self.confere(list(range(n, 0, -1)))

    def test_textos(self):
        self.confere(["pera", "abacaxi", "uva", "Banana", "abacate", ""])

    def test_aceita_tupla_e_range(self):
        self.assertEqual(self.ordenar((3, 1, 2)), [1, 2, 3])
        self.assertEqual(self.ordenar(range(5, 0, -1)), [1, 2, 3, 4, 5])

    def test_nao_altera_a_entrada(self):
        entrada = [5, 3, 9, 1, 7]
        self.ordenar(entrada)
        self.assertEqual(entrada, [5, 3, 9, 1, 7])

    def test_devolve_lista_nova(self):
        for entrada in ([], [1], [2, 1]):
            with self.subTest(entrada=entrada):
                self.assertIsNot(self.ordenar(entrada), entrada)

    def test_estavel(self):
        rng = random.Random(1)
        registros = [Registro(rng.randint(0, 5), i) for i in range(200)]
        saida = self.ordenar(registros)
        esperado = sorted(registros, key=lambda r: r.chave)  # sorted() é estável
        self.assertEqual([(r.chave, r.origem) for r in saida], [(r.chave, r.origem) for r in esperado])

    # --- muitos casos aleatórios -----------------------------------------

    def test_todas_as_permutacoes_ate_7(self):
        for n in range(8):
            for permutacao in itertools.permutations(range(n)):
                self.assertEqual(self.ordenar(list(permutacao)), list(range(n)))

    def test_listas_aleatorias(self):
        rng = random.Random(2026)
        for _ in range(500):
            n = rng.randint(0, 80)
            maximo = rng.choice([1, 5, 1000])  # poucos valores distintos ou muitos
            with self.subTest(n=n, maximo=maximo):
                self.confere([rng.randint(-maximo, maximo) for _ in range(n)])

    def test_tamanhos_da_atividade(self):
        rng = random.Random(7)
        for n in (5, 10, 20, 30, 50, 75, 100, 200, 500, 1000):
            with self.subTest(n=n):
                self.confere(lista_aleatoria(n, rng))


class TestInsercao(CasosDeOrdenacao, unittest.TestCase):
    ordenar = staticmethod(ordenar_por_insercao)


class TestIntercalacao(CasosDeOrdenacao, unittest.TestCase):
    ordenar = staticmethod(ordenar_por_intercalacao)


# ---------------------------------------------------------------------------
# Contagem de comparações
# ---------------------------------------------------------------------------

def inversoes(lista):
    return sum(1 for i in range(len(lista)) for j in range(i + 1, len(lista)) if lista[j] < lista[i])


def melhor_caso_intercalacao(n):
    """Lista já ordenada: cada intercalação compara todos os elementos da
    esquerda e para quando ela acaba."""
    if n <= 1:
        return 0
    return melhor_caso_intercalacao(n // 2) + melhor_caso_intercalacao(n - n // 2) + n // 2


def pior_caso_intercalacao(n):
    """Cada intercalação de n elementos faz no máximo n - 1 comparações."""
    if n <= 1:
        return 0
    return pior_caso_intercalacao(n // 2) + pior_caso_intercalacao(n - n // 2) + n - 1


class TestContagem(unittest.TestCase):

    def test_elemento_contado_so_aceita_menor_que(self):
        contador = Contador()
        a, b = ElementoContado(1, contador), ElementoContado(2, contador)
        self.assertTrue(a < b)
        self.assertTrue(b > a)  # o Python traduz b > a para a < b
        self.assertEqual(contador.total, 2)
        for operacao in (lambda: a <= b, lambda: a >= b, lambda: a == b, lambda: a != b):
            with self.assertRaises(TypeError):
                operacao()

    def test_contar_nao_muda_o_resultado(self):
        rng = random.Random(3)
        lista = [rng.randint(0, 50) for _ in range(300)]
        for ordenar in (ordenar_por_insercao, ordenar_por_intercalacao, sorted):
            with self.subTest(ordenar=ordenar.__name__):
                ordenada, _ = contar_comparacoes(ordenar, lista)
                self.assertEqual(ordenada, sorted(lista))

    def test_vazia_e_um_elemento_nao_comparam(self):
        for ordenar in (ordenar_por_insercao, ordenar_por_intercalacao, sorted):
            for lista in ([], [1]):
                with self.subTest(ordenar=ordenar.__name__, lista=lista):
                    self.assertEqual(contar_comparacoes(ordenar, lista)[1], 0)

    # --- inserção --------------------------------------------------------

    def test_insercao_ordenada_faz_n_menos_1(self):
        for n in (2, 10, 100):
            self.assertEqual(contar_comparacoes(ordenar_por_insercao, range(n))[1], n - 1)

    def test_insercao_todos_iguais_faz_n_menos_1(self):
        self.assertEqual(contar_comparacoes(ordenar_por_insercao, [4] * 30)[1], 29)

    def test_insercao_invertida_faz_n_vezes_n_menos_1_sobre_2(self):
        for n in (2, 10, 100):
            self.assertEqual(contar_comparacoes(ordenar_por_insercao, range(n, 0, -1))[1], n * (n - 1) // 2)

    def test_insercao_conta_exata_em_listas_aleatorias(self):
        # Comparações = inversões + (n - 1) - (quantos elementos, a partir do
        # segundo, são estritamente menores que todos os anteriores).
        rng = random.Random(11)
        for _ in range(200):
            lista = [rng.randint(0, 30) for _ in range(rng.randint(1, 60))]
            novos_minimos = sum(1 for i in range(1, len(lista)) if lista[i] < min(lista[:i]))
            esperado = inversoes(lista) + len(lista) - 1 - novos_minimos
            self.assertEqual(contar_comparacoes(ordenar_por_insercao, lista)[1], esperado)

    # --- intercalação ----------------------------------------------------

    def test_intercalacao_ordenada_e_todos_iguais(self):
        for n in (2, 7, 16, 100, 1000):
            with self.subTest(n=n):
                self.assertEqual(contar_comparacoes(ordenar_por_intercalacao, range(n))[1],
                                 melhor_caso_intercalacao(n))
                self.assertEqual(contar_comparacoes(ordenar_por_intercalacao, [0] * n)[1],
                                 melhor_caso_intercalacao(n))

    def test_intercalacao_potencia_de_2_ordenada_faz_n_log_n_sobre_2(self):
        for k in range(1, 11):
            n = 2 ** k
            self.assertEqual(contar_comparacoes(ordenar_por_intercalacao, range(n))[1], n * k // 2)

    def test_intercalacao_fica_entre_melhor_e_pior_caso(self):
        rng = random.Random(5)
        for n in (5, 10, 20, 30, 50, 75, 100, 200, 500, 1000):
            for _ in range(20):
                c = contar_comparacoes(ordenar_por_intercalacao, lista_aleatoria(n, rng))[1]
                self.assertLessEqual(melhor_caso_intercalacao(n), c)
                self.assertLessEqual(c, pior_caso_intercalacao(n))

    def test_pior_caso_intercalacao_bate_com_formula_fechada(self):
        # W(n) = n⌈log₂n⌉ - 2^⌈log₂n⌉ + 1
        for n in range(1, 2000):
            k = math.ceil(math.log2(n)) if n > 1 else 0
            self.assertEqual(pior_caso_intercalacao(n), n * k - 2 ** k + 1)

    # --- valores esperados usados no relatório ---------------------------

    def test_valor_esperado_bate_com_todas_as_permutacoes(self):
        for n in range(1, 8):
            permutacoes = list(itertools.permutations(range(n)))
            for ordenar, formula in ((ordenar_por_insercao, comparacoes_esperadas_insercao),
                                     (ordenar_por_intercalacao, comparacoes_esperadas_intercalacao)):
                with self.subTest(n=n, ordenar=ordenar.__name__):
                    total = sum(contar_comparacoes(ordenar, p)[1] for p in permutacoes)
                    self.assertEqual(Fraction(total, len(permutacoes)), formula(n))

    # --- sorted() --------------------------------------------------------

    def test_sorted_ordenada_ou_invertida_faz_n_menos_1(self):
        # O Timsort percorre a lista procurando trechos já ordenados (ou
        # estritamente decrescentes, que ele inverte). Se a lista toda é um
        # trecho só, bastam n - 1 comparações.
        for n in (2, 10, 1000):
            self.assertEqual(contar_comparacoes(sorted, range(n))[1], n - 1)
            self.assertEqual(contar_comparacoes(sorted, range(n, 0, -1))[1], n - 1)

    def test_nenhum_metodo_fica_abaixo_de_log2_n_fatorial_em_media(self):
        # Limite inferior de qualquer ordenação por comparação: a média sobre
        # todas as n! permutações não pode ser menor que log₂(n!). Se a
        # contagem deixasse de contar alguma comparação, isso poderia falhar.
        for n in range(2, 8):
            permutacoes = list(itertools.permutations(range(n)))
            for ordenar in (ordenar_por_insercao, ordenar_por_intercalacao, sorted):
                with self.subTest(n=n, ordenar=ordenar.__name__):
                    total = sum(contar_comparacoes(ordenar, p)[1] for p in permutacoes)
                    self.assertGreaterEqual(total / len(permutacoes), log2_fatorial(n))


# ---------------------------------------------------------------------------
# Funções auxiliares do medir.py
# ---------------------------------------------------------------------------

class TestMedir(unittest.TestCase):

    def test_listas_sao_reprodutiveis(self):
        self.assertEqual(lista_aleatoria(50, gerador(1, "x", 50)), lista_aleatoria(50, gerador(1, "x", 50)))
        self.assertNotEqual(lista_aleatoria(50, gerador(1, "x", 50)), lista_aleatoria(50, gerador(2, "x", 50)))

    def test_lista_aleatoria_tem_n_elementos_distintos(self):
        lista = lista_aleatoria(1000, random.Random(0))
        self.assertEqual(len(set(lista)), 1000)

    def test_lista_quase_ordenada(self):
        rng = random.Random(0)
        lista = lista_quase_ordenada(100, 0, rng)
        self.assertEqual(lista, sorted(lista))
        lista = lista_quase_ordenada(1000, 5, rng)
        fora = sum(1 for a, b in zip(lista, sorted(lista)) if a != b)
        self.assertLessEqual(fora, 50)  # no máximo os 5% embaralhados saem do lugar
        self.assertGreater(fora, 25)

    def test_ponto_de_virada(self):
        ns = [5, 10, 20, 30, 50]
        self.assertEqual(ponto_de_virada(ns, [1, 2, 3, 9, 9], [2, 3, 4, 5, 6]), 30)
        # Ganhar em n = 10 e voltar a perder em n = 20 não conta como virada.
        self.assertEqual(ponto_de_virada(ns, [1, 4, 3, 9, 9], [2, 3, 4, 5, 6]), 30)
        self.assertEqual(ponto_de_virada(ns, [9] * 5, [1] * 5), 5)
        self.assertIsNone(ponto_de_virada(ns, [1] * 5, [9] * 5))


if __name__ == "__main__":
    unittest.main(verbosity=2)
