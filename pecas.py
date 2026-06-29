class Peca:

    def __init__(self, jogador, linha, coluna):

        self.jogador = jogador

        self.linha = linha
        self.coluna = coluna

        # Movimento
        self.movimento = 2

        # Posição visual
        self.x_visual = coluna - 4
        self.z_visual = linha - 4

        # Animação de movimento
        self.animando = False

        self.x_inicial = self.x_visual
        self.z_inicial = self.z_visual

        self.x_destino = self.x_visual
        self.z_destino = self.z_visual

        self.y_visual = 0.0

        self.tempo_animacao = 0.0
        self.duracao_animacao = 0.25

        # Combate
        self.vida = 3
        self.dano = 1
        self.alcance_do_ataque = 1

        self.direcao = (0, -1)

        # Controle de turno
        self.movido = False
        self.atacou = False

        # Estado de morte
        self.morta = False

        # Feedback de dano
        self.recebendo_dano = False
        self.tempo_dano = 0.0
        self.duracao_dano = 0.15

        self.offset_dano_x = 0.0
        self.offset_dano_z = 0.0

        # Construção de barricadas (só algumas peças do time 0 podem)
        self.pode_construir_barricada = False
        self.alcance_de_construcao = 0

        # Marca se esta "peça" é, na verdade, um obstáculo (ex: barricada).
        # Obstáculos bloqueiam movimento mas não contam para a condição
        # de vitória por eliminação de peças.
        self.e_obstaculo = False

        # Cor por jogador
        if jogador == 0:
            self.cor = (0.33, 0.42, 0.18)
        else:
            self.cor = (0.2, 0.4, 1.0)

class Tanque(Peca):

    def __init__(self, jogador, linha, coluna):

        super().__init__(jogador, linha, coluna)
        self.tipo = "Tanque"
        self.vida = 5
        self.dano = 1
        self.movimento = 1
        self.alcance_do_ataque = 1

class Atirador(Peca):

    def __init__(self, jogador, linha, coluna):

        super().__init__(jogador, linha, coluna)
        self.tipo = "Atirador"
        self.vida = 2
        self.dano = 3
        self.movimento = 3
        self.alcance_do_ataque = 3

class Batedor(Peca):

    def __init__(self, jogador, linha, coluna):

        super().__init__(jogador, linha, coluna)
        self.tipo = "Batedor"
        self.vida = 4
        self.dano = 2
        self.movimento = 2
        self.alcance_do_ataque = 1

        # Só o Batedor do time vermelho (defensor) pode construir barricadas
        if jogador == 0:
            self.pode_construir_barricada = True
            self.alcance_de_construcao = 1

class Barricada(Peca):
    """
    Obstáculo construído pelo Batedor do time vermelho.
    Não se move, não ataca, só ocupa uma casa (bloqueando movimento) e
    pode ser destruída por ataques normais, como qualquer outra peça.
    """

    def __init__(self, jogador, linha, coluna):
        super().__init__(jogador, linha, coluna)
        self.tipo = "Barricada"
        self.vida = 3
        self.dano = 0
        self.movimento = 0
        self.alcance_do_ataque = 0
        self.e_obstaculo = True

        self.cor = (0.45, 0.32, 0.18)