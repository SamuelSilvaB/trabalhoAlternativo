import glfw
from OpenGL.GL import *
import numpy as np
import ctypes
import math
import glm

from pecas import *
from utils import lerp, carregar_textura
from renderizacao import build_grid, gerar_vertices_auras
from geometria import carregar_modelo_base, preparar_modelo_renderizavel, preparar_barricada_renderizavel

class Tabuleiro:
    def __init__(self):
        vertices = build_grid()
        self.qtdVertices = len(vertices) // 8

        self.casas = [[None for _ in range(8)] for _ in range(8)]
        self.pecas = []

        # Jogador 1
        self.adicionar_peca(Tanque(0, 6, 6))
        self.adicionar_peca(Atirador(0, 3, 7))
        self.adicionar_peca(Batedor(0, 1, 5))

        # jogador 2
        self.adicionar_peca(Tanque(1, 0, 0))
        self.adicionar_peca(Atirador(1, 3, 2))
        self.adicionar_peca(Batedor(1, 7, 0))

        self.peca_selecionada = None
        self.modo_ataque = False
        self.modo_construcao = False

        # ------------------------------------------------------------------
        # Condição de vitória: time vermelho (jogador 0) defende a base,
        # que fica na coluna 7 (lado direito do tabuleiro). O time azul
        # (jogador 1) vence se alguma peça sua alcançar a coluna 7.
        # Qualquer time vence também se o time adversário perder todas as peças.
        # ------------------------------------------------------------------
        self.JOGADOR_VERMELHO = 0
        self.JOGADOR_AZUL = 1
        self.COLUNA_OBJETIVO = 7

        self.jogo_terminado = False
        self.vencedor = None

        self.textura_piso = carregar_textura("woodfloor2.jpg")

        print("Carregando os modelos 3D...")
        # self.modelos = {
        #     "Tanque": carregar_modelo_base("modelos/Soldier_tank/Soldier_tank_otimizado.obj", escala=0.15),
        #     "Atirador": carregar_modelo_base("modelos/Soldier_atirador/Soldier_atirador_otimizado.obj", escala=0.15),
        #     "Batedor": carregar_modelo_base("modelos/Soldier_batedor/Soldier_batedor_otimizado.obj", escala=0.15),
        # }

        self.modelos = {
            0: {   # jogador vermelho
                "Tanque": carregar_modelo_base(
                    "modelos/Soldier_tank/Soldier_tank_otimizado.obj",
                    escala=0.15
                ),
                "Atirador": carregar_modelo_base(
                    "modelos/Soldier_atirador/Soldier_atirador_otimizado.obj",
                    escala=0.15
                ),
                "Batedor": carregar_modelo_base(
                    "modelos/Soldier_batedor/Soldier_batedor_otimizado.obj",
                    escala=0.15
                ),
            },

            1: {   # jogador azul
                "Tanque": carregar_modelo_base(
                    "modelos/Robot/robo_otimizado.obj",
                    escala=0.05
                ),
                "Atirador": carregar_modelo_base(
                    "modelos/Robot/robo_otimizado.obj",
                    escala=0.05
                ),
                "Batedor": carregar_modelo_base(
                    "modelos/Robot/robo_otimizado.obj",
                    escala=0.05
                ),
            }
        }

        # Configurar VAO/VBO para o grid (estático)
        self.vaoId = glGenVertexArrays(1)
        glBindVertexArray(self.vaoId)

        self.vboId = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vboId)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        stride = 8 * 4
        glEnableVertexAttribArray(0) # Posiçao 0
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1) # Cor 1
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(2) # Textura UV 2
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))

        glBindVertexArray(0)

        # ------------------------------------------------------------------
        # VBOs ESTÁTICOS DOS MODELOS (uma vez só, na origem, sem transformação)
        # Uma combinação (tipo, cor) = um buffer próprio. A posição/rotação
        # de cada peça no tabuleiro é aplicada depois, na GPU, via modelMatrix.
        # ------------------------------------------------------------------
        self.vaos_modelos = {}
        for peca in self.pecas:
            self._garantir_vao_estatico(peca)

        # ------------------------------------------------------------------
        # VAO/VBO PERSISTENTE PARA AS AURAS (reaproveitado todo frame,
        # em vez de criar/destruir glGenVertexArrays/glGenBuffers em loop)
        # ------------------------------------------------------------------
        self.vao_auras = glGenVertexArrays(1)
        self.vbo_auras = glGenBuffers(1)
        glBindVertexArray(self.vao_auras)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_auras)
        # aloca um buffer inicial vazio; o tamanho real é definido a cada frame
        glBufferData(GL_ARRAY_BUFFER, 0, None, GL_DYNAMIC_DRAW)

        stride_aura = 6 * 4
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride_aura, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride_aura, ctypes.c_void_p(12))
        glBindVertexArray(0)

    def adicionar_peca(self, peca):
        self.pecas.append(peca)
        self.casas[peca.linha][peca.coluna] = peca

    def obter_peca(self, linha, coluna):
        for peca in self.pecas:
            if peca.linha == linha and peca.coluna == coluna:
                return peca
        return None

    def mover_peca(self, peca, linha, coluna):
        if peca.movido:
            print("Esta peça já se moveu neste turno!")
            return False
        if linha < 0 or linha > 7 or coluna < 0 or coluna > 7:
            return False
        if self.obter_peca(linha, coluna) is not None:
            return False

        distancia = abs(linha - peca.linha) + abs(coluna - peca.coluna)
        if distancia > peca.movimento:
            print(f"Movimento muito longo ({distancia}) máximo = {peca.movimento}")
            return False

        peca.x_inicial = peca.x_visual
        peca.z_inicial = peca.z_visual
        peca.x_destino = coluna - 4
        peca.z_destino = linha - 4
        peca.tempo_animacao = 0.0
        peca.animando = True
        peca.linha = linha
        peca.coluna = coluna
        peca.movido = True

        self.verificar_fim_de_jogo()
        return True

    def casas_atacaveis(self, peca):
        casas = []
        alcance = peca.alcance_do_ataque
        for linha in range(8):
            for coluna in range(8):
                distancia = abs(linha - peca.linha) + abs(coluna - peca.coluna)
                if 0 < distancia <= alcance:
                    casas.append((linha, coluna))
        return casas

    def atualizar_animacoes(self, dt):

        pecas_para_remover = []

        for peca in self.pecas:

            # -------------------
            # Movimento
            # -------------------
            if peca.animando:

                peca.tempo_animacao += dt

                t = peca.tempo_animacao / peca.duracao_animacao
                t = min(t, 1.0)

                t = t * t * (3 - 2 * t)

                if t >= 1.0:
                    t = 1.0
                    peca.animando = False

                peca.x_visual = lerp(
                    peca.x_inicial,
                    peca.x_destino,
                    t
                )

                peca.z_visual = lerp(
                    peca.z_inicial,
                    peca.z_destino,
                    t
                )

                if peca.animando:
                    peca.y_visual = (
                        math.sin(t * math.pi)
                        * 0.5
                    )
                else:
                    peca.y_visual = 0.0

            # -------------------
            # Dano
            # -------------------
            if peca.recebendo_dano:

                peca.tempo_dano += dt

                if peca.tempo_dano >= peca.duracao_dano:

                    peca.recebendo_dano = False

                    peca.offset_dano_x = 0.0
                    peca.offset_dano_z = 0.0

                    if peca.morta:
                        pecas_para_remover.append(peca)

                else:

                    intensidade = 0.08

                    if int(peca.tempo_dano * 50) % 2 == 0:
                        peca.offset_dano_x = intensidade
                    else:
                        peca.offset_dano_x = -intensidade

                    peca.offset_dano_z = 0.0

        # -------------------
        # Remove peças mortas
        # -------------------
        for peca in pecas_para_remover:

            if peca in self.pecas:

                self.casas[
                    peca.linha
                ][
                    peca.coluna
                ] = None

                self.pecas.remove(peca)

                print(f"{peca.tipo} removida do jogo")

        if pecas_para_remover:
            self.verificar_fim_de_jogo()

    def atacar(self, atacante, linha, coluna):

        alvo = self.obter_peca(
            linha,
            coluna
        )

        if atacante.atacou:
            print(
                "Esta peça já atacou neste turno!"
            )
            return False

        if alvo is None:
            return False

        if alvo.morta:
            return False

        if alvo.jogador == atacante.jogador:
            return False

        distancia = (
            abs(linha - atacante.linha)
            +
            abs(coluna - atacante.coluna)
        )

        if distancia == 0:
            return False

        if distancia > atacante.alcance_do_ataque:
            return False

        alvo.vida -= atacante.dano

        print(
            f"{alvo.tipo} recebeu "
            f"{atacante.dano} de dano"
        )

        print(
            f"Vida restante: "
            f"{alvo.vida}"
        )

        alvo.recebendo_dano = True
        alvo.tempo_dano = 0.0

        if alvo.vida <= 0:

            alvo.morta = True

            print(
                f"{alvo.tipo} será destruído"
            )

        print(
            f"{atacante.tipo} atacou "
            f"{alvo.tipo}"
        )

        atacante.atacou = True

        return True

    def remover_peca(self, peca):
        self.pecas.remove(peca)
        self.casas[peca.linha][peca.coluna] = None

    def construir_barricada(self, construtor, linha, coluna):
        """Tenta construir uma barricada na casa indicada, usando a ação do turno do construtor."""
        if not construtor.pode_construir_barricada:
            print(f"{construtor.tipo} não sabe construir barricadas!")
            return False

        if construtor.atacou:
            print("Esta peça já realizou sua ação neste turno!")
            return False

        if linha < 0 or linha > 7 or coluna < 0 or coluna > 7:
            return False

        if self.obter_peca(linha, coluna) is not None:
            print("Já existe algo nessa casa.")
            return False

        distancia = abs(linha - construtor.linha) + abs(coluna - construtor.coluna)
        if distancia == 0 or distancia > construtor.alcance_de_construcao:
            print(f"Muito longe para construir (máximo = {construtor.alcance_de_construcao}).")
            return False

        barricada = Barricada(construtor.jogador, linha, coluna)
        self._garantir_vao_estatico(barricada)
        self.adicionar_peca(barricada)

        construtor.atacou = True
        print(f"{construtor.tipo} construiu uma barricada em ({linha}, {coluna})!")
        return True

    def _garantir_vao_estatico(self, peca):
        """
        Garante que existe um VBO/VAO estático já carregado na GPU para o
        tipo+cor desta peça. Para peças criadas no __init__ (soldados) isso
        já foi feito antes; para peças criadas durante o jogo (barricadas),
        criamos aqui, uma única vez por combinação (tipo, cor).
        """
        chave = (peca.jogador, peca.tipo)
        if chave in self.vaos_modelos:
            return

        if peca.tipo == "Barricada":
            dados = preparar_barricada_renderizavel(0.8, peca.cor)
        else:
            dados = preparar_modelo_renderizavel(
                self.modelos[peca.jogador][peca.tipo],
                peca.cor
            )

        qtd_vertices = len(dados) // 8

        vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, dados.nbytes, dados, GL_STATIC_DRAW)

        stride = 8 * 4
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))

        glBindVertexArray(0)

        self.vaos_modelos[chave] = (vao, vbo, qtd_vertices)

    def casas_alcancaveis(self, peca):
        casas = []
        for linha in range(8):
            for coluna in range(8):
                distancia = abs(linha - peca.linha) + abs(coluna - peca.coluna)
                if distancia <= peca.movimento and self.obter_peca(linha, coluna) is None:
                    casas.append((linha, coluna))
        return casas

    def iniciar_turno(self, jogador):
        for peca in self.pecas:
            if peca.jogador == jogador:
                peca.movido = False
                peca.atacou = False
        print(f"Turno do jogador {jogador} começou!")

    def tem_alvos_validos(self, peca):
        """Retorna True se a peça tem pelo menos um inimigo ao alcance de ataque."""
        for linha in range(8):
            for coluna in range(8):
                alvo = self.obter_peca(linha, coluna)
                if alvo and alvo.jogador != peca.jogador:
                    distancia = abs(linha - peca.linha) + abs(coluna - peca.coluna)
                    if distancia <= peca.alcance_do_ataque:
                        return True
        return False

    def turno_acabou(self, jogador):
        """Retorna True se todas as peças do jogador já moveram E atacaram."""
        for peca in self.pecas:
            if peca.jogador == jogador and (not peca.movido or not peca.atacou):
                return False
        return True

    def verificar_fim_de_jogo(self):
        """
        Verifica as duas condições de vitória:
        1) Uma peça do time azul alcançou a coluna objetivo (a base) -> azul vence.
        2) Um dos times perdeu todas as peças -> o outro time vence.
        Não faz nada se o jogo já tiver terminado.
        """
        if self.jogo_terminado:
            return

        # Condição 1: peça azul chegou na coluna da base
        for peca in self.pecas:
            if peca.jogador == self.JOGADOR_AZUL and peca.coluna == self.COLUNA_OBJETIVO:
                self.jogo_terminado = True
                self.vencedor = self.JOGADOR_AZUL
                print("=== FIM DE JOGO: time AZUL alcançou a base e venceu! ===")
                return

        # Condição 2: time sem peças (obstáculos/barricadas não contam)
        tem_vermelho = any(
            p.jogador == self.JOGADOR_VERMELHO and not p.e_obstaculo
            for p in self.pecas
        )
        tem_azul = any(
            p.jogador == self.JOGADOR_AZUL and not p.e_obstaculo
            for p in self.pecas
        )

        if not tem_vermelho:
            self.jogo_terminado = True
            self.vencedor = self.JOGADOR_AZUL
            print("=== FIM DE JOGO: time VERMELHO perdeu todas as peças. AZUL venceu! ===")
        elif not tem_azul:
            self.jogo_terminado = True
            self.vencedor = self.JOGADOR_VERMELHO
            print("=== FIM DE JOGO: time AZUL perdeu todas as peças. VERMELHO venceu! ===")

    def render(self, shaderId, locations, projMatrix, viewMatrix):
        # --------------------------------------------------------------
        # Grid (estático) - desenhado com modelMatrix = identidade,
        # que é exatamente o que já está configurado em main.render()
        # antes de chamar tabuleiro.render().
        # --------------------------------------------------------------
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.textura_piso)

        glBindVertexArray(self.vaoId)
        glDrawArrays(GL_TRIANGLES, 0, self.qtdVertices)
        glBindVertexArray(0)

        glBindTexture(GL_TEXTURE_2D, 0)

        # --------------------------------------------------------------
        # Peças: SEM gerar vértices em CPU. Cada peça usa um VBO estático
        # (na origem) e só recebe uma matriz de modelo (translação+rotação)
        # calculada na CPU (custo irrisório: uma matriz 4x4 por peça) e
        # aplicada pela GPU no vertex shader.
        # --------------------------------------------------------------
        for peca in self.pecas:
            x = peca.x_visual + peca.offset_dano_x
            z = peca.z_visual + peca.offset_dano_z
            angulo = math.radians(90) if peca.jogador == 0 else math.radians(-90)

            modelMatrix = glm.translate(glm.mat4(1.0), glm.vec3(x + 0.5, 0.9 + peca.y_visual, z + 0.5))
            modelMatrix = glm.rotate(modelMatrix, -angulo, glm.vec3(0, 1, 0))
            mvp = projMatrix * viewMatrix * modelMatrix

            glUniformMatrix4fv(locations['uMVP'], 1, GL_FALSE, glm.value_ptr(mvp))
            glUniformMatrix4fv(locations['modelMatrix'], 1, GL_FALSE, glm.value_ptr(modelMatrix))

            chave = (peca.jogador, peca.tipo)
            vao, vbo, qtd_vertices = self.vaos_modelos[chave]
            glBindVertexArray(vao)
            glDrawArrays(GL_TRIANGLES, 0, qtd_vertices)

        glBindVertexArray(0)

        # --------------------------------------------------------------
        # Restaura a matriz de modelo para identidade antes de desenhar
        # as auras, já que os vértices delas vêm em coordenadas absolutas
        # do mundo (calculados em add_aura).
        # --------------------------------------------------------------
        modelIdentity = glm.mat4(1.0)
        mvpIdentity = projMatrix * viewMatrix * modelIdentity
        glUniformMatrix4fv(locations['uMVP'], 1, GL_FALSE, glm.value_ptr(mvpIdentity))
        glUniformMatrix4fv(locations['modelMatrix'], 1, GL_FALSE, glm.value_ptr(modelIdentity))

        # --------------------------------------------------------------
        # Auras (dinâmico, mas reaproveitando sempre o mesmo VAO/VBO -
        # nada de glGenVertexArrays/glGenBuffers/glDeleteBuffers em loop)
        # --------------------------------------------------------------
        vertices = gerar_vertices_auras(self)
        glBindVertexArray(self.vao_auras)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_auras)
        if len(vertices) > 0:
            glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
            glDrawArrays(GL_TRIANGLES, 0, len(vertices) // 6)
        glBindVertexArray(0)