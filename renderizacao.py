import numpy as np
import math
from geometria import add_tile, add_aura, add_paralelepipedo

def build_grid():
    SIZE = 1.0
    GRID = 8
    LIGHT = (0.78, 0.86, 0.90)
    DARK = (0.38, 0.52, 0.60)
    PISO_COR = (0.3, 0.3, 0.3)

    data = []
    offset = GRID / 2
    piso_tamanho = GRID * SIZE + 25.0

    # Piso
    data += add_tile(-piso_tamanho / 2, -piso_tamanho / 2, piso_tamanho, PISO_COR, h=0.1, ybase=-0.5, com_textura=True)

    # Tabuleiro
    for row in range(GRID):
        for col in range(GRID):
            color = LIGHT if (row + col) % 2 == 0 else DARK
            data += add_tile(col - offset, row - offset, SIZE, color, h=0.9, ybase=0.0)

    data += add_paralelepipedo(
        4.0,            # x
        -0.4,           # y
        -3,            # z
        3.0,            # largura
        0.7,            # altura
        6.0,            # profundidade
        (0.5, 0.5, 0.5) # cor
    )

    return np.array(data, dtype=np.float32)


def gerar_vertices_auras(tabuleiro):
    """
    Gera SOMENTE as auras (indicadores visuais de movimento/ataque/seleção).
    Isso é leve (poucos triângulos) e pode continuar sendo regenerado em CPU
    a cada frame sem problema de performance.
    Os modelos 3D das peças NÃO passam mais por aqui - eles são desenhados
    direto de VBOs estáticos, posicionados via matriz de modelo na GPU.
    """
    vertices = []

    # Mostrar casas de movimento (se houver peça selecionada)
    if tabuleiro.peca_selecionada is not None and not tabuleiro.peca_selecionada.movido:
        for linha, coluna in tabuleiro.casas_alcancaveis(tabuleiro.peca_selecionada):
            casa_x = coluna - 4
            casa_z = linha - 4
            vertices += add_aura(casa_x + 0.5, casa_z + 0.5, raio=0.25, y=0.91, cor=(0.2, 0.6, 1.0))

    # Aura da peça selecionada
    if tabuleiro.peca_selecionada is not None:
        peca = tabuleiro.peca_selecionada
        x = peca.x_visual + peca.offset_dano_x
        z = peca.z_visual + peca.offset_dano_z
        vertices += add_aura(x + 0.5, z + 0.5, raio=0.55, cor=(1.0, 1.0, 0.0))

    # Mostrar casas disponíveis para ataque
    if tabuleiro.modo_ataque and tabuleiro.peca_selecionada is not None:
        for linha, coluna in tabuleiro.casas_atacaveis(tabuleiro.peca_selecionada):
            x = coluna - 4
            z = linha - 4
            vertices += add_aura(x + 0.5, z + 0.5, raio=0.3, cor=(1.0, 0.0, 0.0))

    if len(vertices) == 0:
        return np.array([], dtype=np.float32)

    return np.array(vertices, dtype=np.float32)