"""Ordenação por inserção e ordenação por intercalação (merge sort).

As duas funções seguem a mesma interface do ``sorted()`` do Python: recebem
qualquer sequência, devolvem uma lista nova ordenada e não alteram a entrada.

As duas comparam elementos usando apenas o operador ``<``. Isso tem dois
motivos:

* basta que os elementos implementem ``__lt__`` (o mesmo que o ``sorted()``
  exige);
* permite contar as comparações sem mexer no código dos algoritmos: basta
  ordenar elementos embrulhados em ``ElementoContado`` (ver
  ``contar_comparacoes`` no fim deste arquivo). Assim o tempo é medido no
  código "limpo", sem o custo de um contador, e as comparações dos três
  métodos (inserção, intercalação e ``sorted()``) são contadas com a mesma
  régua.
"""


def ordenar_por_insercao(lista):
    """Ordena por inserção. Tempo O(n²) no pior caso e no caso médio, O(n) se
    a lista já estiver ordenada. Estável."""
    a = list(lista)
    for i in range(1, len(a)):
        chave = a[i]
        j = i - 1
        # Desloca para a direita os elementos maiores que a chave.
        # Usar "<" (e não "<=") faz o laço parar em elementos iguais,
        # o que mantém a ordem original dos empates (estabilidade).
        while j >= 0 and chave < a[j]:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = chave
    return a


def ordenar_por_intercalacao(lista):
    """Ordena por intercalação (merge sort, versão recursiva de cima para
    baixo). Tempo O(n log n) em qualquer caso, memória extra O(n). Estável."""
    return _intercalacao(list(lista))


def _intercalacao(a):
    if len(a) <= 1:
        return a
    meio = len(a) // 2
    # Os fatiamentos a[:meio] e a[meio:] já criam listas novas.
    esquerda = _intercalacao(a[:meio])
    direita = _intercalacao(a[meio:])
    return _intercalar(esquerda, direita)


def _intercalar(esquerda, direita):
    """Junta duas listas ordenadas em uma lista ordenada."""
    resultado = []
    i = j = 0
    while i < len(esquerda) and j < len(direita):
        # Só pega da direita se ela for estritamente menor: em caso de empate
        # o elemento da esquerda (que veio antes) sai primeiro -> estável.
        if direita[j] < esquerda[i]:
            resultado.append(direita[j])
            j += 1
        else:
            resultado.append(esquerda[i])
            i += 1
    # Quando um lado acaba, o resto do outro já está ordenado e não precisa
    # de mais comparações.
    resultado.extend(esquerda[i:])
    resultado.extend(direita[j:])
    return resultado


# ---------------------------------------------------------------------------
# Contagem de comparações
# ---------------------------------------------------------------------------

class Contador:
    """Guarda quantas comparações foram feitas."""

    __slots__ = ("total",)

    def __init__(self):
        self.total = 0


class ElementoContado:
    """Embrulha um valor e conta cada chamada de ``<``.

    Só ``<`` é permitido. ``>`` também funciona e também é contado, porque o
    Python o traduz para o ``__lt__`` do outro operando. Já ``<=``, ``>=``,
    ``==`` e ``!=`` levantam ``TypeError``: se algum algoritmo usasse um desses
    operadores, a contagem ficaria incompleta sem ninguém perceber, então é
    melhor quebrar de forma visível.
    """

    __slots__ = ("valor", "contador")

    def __init__(self, valor, contador):
        self.valor = valor
        self.contador = contador

    def __lt__(self, outro):
        self.contador.total += 1
        return self.valor < outro.valor

    def _proibido(self, outro):
        raise TypeError("ElementoContado só permite comparar com '<'")

    __le__ = __ge__ = __eq__ = __ne__ = _proibido
    __hash__ = None

    def __repr__(self):
        return f"ElementoContado({self.valor!r})"


def contar_comparacoes(ordenar, lista):
    """Ordena ``lista`` com ``ordenar`` e devolve ``(ordenada, comparacoes)``.

    ``ordenar`` pode ser qualquer função que receba uma lista e devolva uma
    lista nova ordenada: ``ordenar_por_insercao``, ``ordenar_por_intercalacao``
    ou o próprio ``sorted``.
    """
    contador = Contador()
    embrulhados = [ElementoContado(v, contador) for v in lista]
    resultado = ordenar(embrulhados)
    return [e.valor for e in resultado], contador.total


ALGORITMOS = {
    "insercao": ordenar_por_insercao,
    "intercalacao": ordenar_por_intercalacao,
    "sorted": sorted,
}
