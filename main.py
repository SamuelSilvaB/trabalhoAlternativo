import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders as gls
import numpy as np
import math
import ctypes
import os
import glm

from tabuleiro import Tabuleiro

# ==============================================================================
# VARIÁVEIS GLOBAIS
# ==============================================================================
resolution = [1000, 700]
viewport = [0, 0, 1000, 700]
tabuleiro = None
shaderId = 0
locations = {}

angle = math.radians(45)
elev = math.radians(35)
target_angle = angle
target_elev = elev

turno = 0
peca_selecionada = None
peca_bloqueada = False 

projMatrix = None
viewMatrix = None

ultimo_tempo = 0.0

def tela_para_casa(mouse_x, mouse_y):
    global projMatrix, viewMatrix, viewport
    altura = viewport[3]
    y_opengl = altura - mouse_y
    ponto_perto = glm.unProject(glm.vec3(mouse_x, y_opengl, 0.0), viewMatrix, projMatrix, glm.vec4(*viewport))
    ponto_longe = glm.unProject(glm.vec3(mouse_x, y_opengl, 1.0), viewMatrix, projMatrix, glm.vec4(*viewport))
    direcao = glm.normalize(ponto_longe - ponto_perto)
    plano_y = 0.9
    if abs(direcao.y) < 0.0001:
        return None
    t = (plano_y - ponto_perto.y) / direcao.y
    if t < 0:
        return None
    impacto = ponto_perto + direcao * t
    coluna = int(math.floor(impacto.x + 4))
    linha = int(math.floor(impacto.z + 4))
    if linha < 0 or linha > 7 or coluna < 0 or coluna > 7:
        return None
    return linha, coluna

def init():
    global tabuleiro, shaderId, locations
    glEnable(GL_MULTISAMPLE)
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.08, 0.10, 0.14, 1.0)
    tabuleiro = Tabuleiro()
    tabuleiro.iniciar_turno(0)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'vertex_shader.glsl')) as file:
        vsSource = file.read()
    with open(os.path.join(here, 'fragment_shader.glsl')) as file:
        fsSource = file.read()

    vsId = gls.compileShader(vsSource, GL_VERTEX_SHADER)
    fsId = gls.compileShader(fsSource, GL_FRAGMENT_SHADER)
    shaderId = gls.compileProgram(vsId, fsId)

    locations['projMatrix'] = glGetUniformLocation(shaderId, 'projMatrix')
    locations['viewMatrix'] = glGetUniformLocation(shaderId, 'viewMatrix')
    locations['modelMatrix'] = glGetUniformLocation(shaderId, 'modelMatrix')
    locations['uMVP'] = glGetUniformLocation(shaderId, 'uMVP')

    # LOCATIONS PARA A LUZ
    locations['lightPos'] = glGetUniformLocation(shaderId, 'lightPos')
    locations['lightDir'] = glGetUniformLocation(shaderId, 'lightDir')
    locations['cutOff'] = glGetUniformLocation(shaderId, 'cutOff')
    locations['outerCutOff'] = glGetUniformLocation(shaderId, 'outerCutOff')
    locations['ambientLight'] = glGetUniformLocation(shaderId, 'ambientLight')

def render():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    global projMatrix, viewMatrix
    glUseProgram(shaderId)

    aspect = resolution[0] / resolution[1]
    projMatrix = glm.ortho(-6 * aspect, 6 * aspect, -6, 6, -0.1, 100.0)

    dist = 12.0
    eye_x = dist * math.cos(elev) * math.sin(angle)
    eye_y = dist * math.sin(elev)
    eye_z = dist * math.cos(elev) * math.cos(angle)
    viewMatrix = glm.lookAt(glm.vec3(eye_x, eye_y, eye_z), glm.vec3(0, 0, 0), glm.vec3(0, 1, 0))

    modelMatrix = glm.mat4(1.0)

    if locations.get('projMatrix') != -1:
        glUniformMatrix4fv(locations['projMatrix'], 1, GL_FALSE, glm.value_ptr(projMatrix))
        glUniformMatrix4fv(locations['viewMatrix'], 1, GL_FALSE, glm.value_ptr(viewMatrix))
        glUniformMatrix4fv(locations['modelMatrix'], 1, GL_FALSE, glm.value_ptr(modelMatrix))

    # ENVIA MATRIZ DIRETAMENTE
    mvp = projMatrix * viewMatrix * modelMatrix
    glUniformMatrix4fv(locations['uMVP'], 1, GL_FALSE, glm.value_ptr(mvp))
    glUniformMatrix4fv(locations['modelMatrix'], 1, GL_FALSE, glm.value_ptr(modelMatrix))

    # LIGAR A LUZ
    glUniform3f(locations['lightPos'], 0.0, 8.0, 0.0)
    glUniform3f(locations['lightDir'], 0.0, -1.0, 0.0)
    glUniform1f(locations['cutOff'], math.cos(math.radians(35.0)))
    glUniform1f(locations['outerCutOff'], math.cos(math.radians(45.0)))
    glUniform3f(locations['ambientLight'], 0.3, 0.3, 0.3)
    glUniform3f(glGetUniformLocation(shaderId, 'lightColor'), 1.0, 1.0, 1.0)

    tabuleiro.render(shaderId, locations, projMatrix, viewMatrix)
    glUseProgram(0)

def update(window):
    global elev, angle, target_angle, target_elev, ultimo_tempo
    angle += (target_angle - angle) * 0.05
    elev += (target_elev - elev) * 0.05
    agora = glfw.get_time()
    dt = agora - ultimo_tempo
    ultimo_tempo = agora
    tabuleiro.atualizar_animacoes(dt)

    if tabuleiro.jogo_terminado:
        if tabuleiro.vencedor == tabuleiro.JOGADOR_AZUL:
            texto = "Time Azul venceu!"
        else:
            texto = "Time Vermelho venceu!"
        glfw.set_window_title(window, f"ToySoldiers - {texto}")

def updateFrameBuffer(window, width, height):
    global resolution, viewport
    resolution = [width, height]
    viewport = [0, 0, width, height]
    glViewport(0, 0, width, height)

def keyboard(window, key, scancode, action, mods):
    global target_angle, target_elev, peca_selecionada
    if action != glfw.PRESS:
        return

    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, True)
        return

    if tabuleiro.jogo_terminado:
        return

    if key == glfw.KEY_RIGHT:
        target_angle -= math.pi
    elif key == glfw.KEY_LEFT:
        target_angle += math.pi
    elif key == glfw.KEY_UP:
        target_elev = math.radians(75)
    elif key == glfw.KEY_DOWN:
        target_elev = math.radians(35)
    elif key == glfw.KEY_SPACE:
        if peca_selecionada is not None:
            tabuleiro.modo_ataque = not tabuleiro.modo_ataque
            tabuleiro.modo_construcao = False
            print("Modo ataque:", tabuleiro.modo_ataque)
    elif key == glfw.KEY_B:
        if peca_selecionada is not None and peca_selecionada.pode_construir_barricada:
            tabuleiro.modo_construcao = not tabuleiro.modo_construcao
            tabuleiro.modo_ataque = False
            print("Modo construção:", tabuleiro.modo_construcao)
    elif key == glfw.KEY_ENTER:
        if peca_selecionada is not None and peca_selecionada.movido and not peca_selecionada.atacou:
            print("Jogador passou o ataque.")
            finalizar_turno()

def finalizar_turno():
    global turno, peca_selecionada, peca_bloqueada
    peca_bloqueada = False
    turno += 1
    tabuleiro.iniciar_turno(turno % 2)
    peca_selecionada = None
    tabuleiro.peca_selecionada = None
    tabuleiro.modo_ataque = False
    tabuleiro.modo_construcao = False
    print(f"--- Turno {turno} - Jogador {turno % 2} ---")

def mouseClick(window, button, action, mods):
    global peca_selecionada, turno, peca_bloqueada
    if button != glfw.MOUSE_BUTTON_LEFT or action != glfw.PRESS:
        return
    if tabuleiro.jogo_terminado:
        return

    x, y = glfw.get_cursor_pos(window)
    casa = tela_para_casa(x, y)
    if casa is None:
        return
    linha, coluna = casa

    if peca_selecionada is not None:
        # Cancela seleção clicando na mesma peça (só se não bloqueada)
        if peca_selecionada.linha == linha and peca_selecionada.coluna == coluna:
            if not peca_bloqueada:
                peca_selecionada = None
                tabuleiro.peca_selecionada = None
                tabuleiro.modo_ataque = False
                tabuleiro.modo_construcao = False
                print("Seleção cancelada")
            return

        # Troca de peça — só permitido antes de mover
        if not peca_bloqueada:
            peca_clicada = tabuleiro.obter_peca(linha, coluna)
            if peca_clicada is not None and peca_clicada.jogador == turno % 2 and not peca_clicada.e_obstaculo:
                peca_selecionada = peca_clicada
                tabuleiro.peca_selecionada = peca_clicada
                tabuleiro.modo_ataque = False
                tabuleiro.modo_construcao = False
                print(f"Trocou seleção para ({linha}, {coluna})")
                return

        # --- CONSTRUÇÃO ---
        if tabuleiro.modo_construcao:
            if tabuleiro.construir_barricada(peca_selecionada, linha, coluna):
                print("Barricada construída!")
                peca_bloqueada = False
                finalizar_turno()
            else:
                print("Não foi possível construir aqui.")
            return

        # --- ATAQUE ---
        if tabuleiro.modo_ataque:
            if tabuleiro.atacar(peca_selecionada, linha, coluna):
                print("Ataque realizado!")
                peca_bloqueada = False
                finalizar_turno()
            else:
                print("Ataque inválido.")
            return

        # --- MOVIMENTO ---
        if tabuleiro.mover_peca(peca_selecionada, linha, coluna):
            print("Movimento realizado!")
            peca_bloqueada = True  # trava: não pode mais trocar de peça
            tabuleiro.modo_ataque = True
            if tabuleiro.tem_alvos_validos(peca_selecionada):
                tabuleiro.modo_ataque = True
                print("Ataque (Enter para passar)!")
            else:
                print("Nenhum inimigo ao alcance. Pressione Enter para passar.")
        else:
            print("Movimento inválido.")
        return

    # Nenhuma peça selecionada
    peca = tabuleiro.obter_peca(linha, coluna)
    if peca is not None and peca.jogador == turno % 2 and not peca.e_obstaculo and not peca.atacou:
        peca_selecionada = peca
        tabuleiro.peca_selecionada = peca
        peca_bloqueada = False
        tabuleiro.modo_ataque = peca.movido
        tabuleiro.modo_construcao = False
        print(f"Peça selecionada em ({linha}, {coluna})")
    else:
        print("Nenhuma peça válida aqui.")

def main():
    glfw.init()
    glfw.window_hint(glfw.SAMPLES, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(resolution[0], resolution[1], 'ToySoldiers - Protótipo', None, None)
    glfw.make_context_current(window)

    init()

    glfw.set_framebuffer_size_callback(window, updateFrameBuffer)
    glfw.set_key_callback(window, keyboard)
    glfw.set_mouse_button_callback(window, mouseClick)
    glfw.set_cursor_pos_callback(window, lambda win, x, y: None)
    glfw.set_scroll_callback(window, lambda win, x, y: None)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        update(window)
        render()
        glfw.swap_buffers(window)

    glfw.terminate()

if __name__ == '__main__':
    main()