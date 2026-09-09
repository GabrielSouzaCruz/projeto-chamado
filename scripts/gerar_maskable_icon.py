"""
Gera pwa-512x512-maskable.png para a Central de Chamados PMM.
Safe zone maskable: círculo de 80% do diâmetro (409px), conteúdo em 60% (307px).
Fundo: #1A4A92 (primary-color do app).
"""

from PIL import Image, ImageDraw
import os

# Caminhos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_LOGO = os.path.join(BASE_DIR, 'static', 'image', 'machado.png')
OUTPUT_PATH = os.path.join(BASE_DIR, 'static', 'image', 'pwa-512x512-maskable.png')

CANVAS_SIZE = 512
BG_COLOR = (26, 74, 146)       # #1A4A92
LOGO_MAX_SIZE = 307             # 60% de 512 = safe zone para conteúdo

# Criar canvas com fundo sólido
canvas = Image.new('RGBA', (CANVAS_SIZE, CANVAS_SIZE), BG_COLOR + (255,))

# Carregar logo e redimensionar mantendo aspect ratio
logo = Image.open(INPUT_LOGO).convert('RGBA')
logo.thumbnail((LOGO_MAX_SIZE, LOGO_MAX_SIZE), Image.LANCZOS)

# Centralizar logo no canvas
logo_x = (CANVAS_SIZE - logo.width) // 2
logo_y = (CANVAS_SIZE - logo.height) // 2

# Colar logo no canvas (respeitando transparência)
canvas.paste(logo, (logo_x, logo_y), logo)

# Salvar como PNG sem transparência (fundo sólido já está no canvas)
canvas_rgb = canvas.convert('RGB')
canvas_rgb.save(OUTPUT_PATH, 'PNG', optimize=True)

print(f"Ícone maskable gerado: {OUTPUT_PATH}")
print(f"Dimensões: {canvas_rgb.size}")
print(f"Logo posicionado em: ({logo_x}, {logo_y}), tamanho: {logo.size}")
