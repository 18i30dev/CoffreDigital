from PIL import Image, ImageDraw

# Cores
cor_fundo = (30, 30, 30, 255)        # cinza escuro
cor_borda = (0, 122, 255, 255)       # azul moderno
cor_cadeado = (240, 240, 240, 255)   # branco gelo

def desenhar_cadeado(desenho, tamanho):
    margem = tamanho * 0.12
    largura = tamanho - margem * 2
    altura = tamanho - margem * 2

    # Corpo do cadeado (retangulo arredondado)
    corpo_top = tamanho * 0.45
    desenho.rounded_rectangle(
        [margem, corpo_top, margem + largura, margem + altura - margem * 0.3],
        radius=tamanho * 0.12,
        fill=cor_cadeado,
        outline=cor_borda,
        width=max(2, int(tamanho * 0.04))
    )

    # Arco superior do cadeado (hasp)
    arco_raio = largura * 0.35
    arco_centro_x = tamanho / 2
    arco_centro_y = corpo_top - margem * 0.2

    desenho.arc(
        [
            arco_centro_x - arco_raio,
            arco_centro_y - arco_raio,
            arco_centro_x + arco_raio,
            arco_centro_y + arco_raio
        ],
        start=180,
        end=360,
        fill=cor_borda,
        width=max(4, int(tamanho * 0.07))
    )

    # Fechadura (circulo pequeno no centro inferior do corpo)
    fechadura_raio = tamanho * 0.06
    fechadura_cx = tamanho / 2
    fechadura_cy = corpo_top + altura * 0.55
    desenho.ellipse(
        [
            fechadura_cx - fechadura_raio,
            fechadura_cy - fechadura_raio,
            fechadura_cx + fechadura_raio,
            fechadura_cy + fechadura_raio
        ],
        fill=cor_borda
    )

# Gerar varios tamanhos para o .ico
tamanhos = [16, 32, 48, 64, 128, 256]
imagens = []

for tam in tamanhos:
    img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(img)
    desenhar_cadeado(desenho, tam)
    imagens.append(img)

# Salvar como ICO com varios tamanhos
imagens[0].save(
    "cadeado.ico",
    format="ICO",
    sizes=[(tam, tam) for tam in tamanhos]
)

print("Icone cadeado.ico gerado com sucesso!")