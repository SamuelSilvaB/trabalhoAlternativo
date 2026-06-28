from OpenGL.GL import *
from PIL import Image

def lerp(a, b, t):
    return a + (b - a) * t

def carregar_textura(caminho_imagem):
    try:
        # Abre a imagem, inverte (OpenGL lê de baixo pra cima) e garante o formato RGBA
        img = Image.open(caminho_imagem).transpose(Image.FLIP_TOP_BOTTOM).convert('RGBA')
        img_data = img.tobytes()

        textura_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, textura_id)

        # Isso previne que a imagem fique distorcida ou preta se a largura for ímpar
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        # GL_CLAMP_TO_EDGE garante que texturas de qualquer tamanho funcionem nas placas de vídeo
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        
        glBindTexture(GL_TEXTURE_2D, 0)
        return textura_id
    except Exception as e:
        print(f"Erro ao carregar textura: {e}")
        return 0