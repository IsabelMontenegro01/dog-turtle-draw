"""
image_processor.py
------------------
Pipeline de visão computacional implementada do zero (apenas NumPy + OpenCV só para leitura).

Etapas:
  1. Carregamento  – OpenCV (único uso permitido)
  2. Pré-processamento – conversão RGB→Grayscale, suavização Gaussiana
  3. Detecção de bordas – operador Sobel + limiarização por histerese (Canny manual)
  4. Extração de contornos – trace de contornos via algoritmo de Moore-Neighbor
  5. Mapeamento – escala do espaço de pixels para o espaço do turtlesim
"""

import cv2          # SOMENTE para imread
import numpy as np
import matplotlib.pyplot as plt


# ─────────────────────────────────────────────
#  1. CARREGAMENTO
# ─────────────────────────────────────────────

def load_image(path: str) -> np.ndarray:
    """Lê a imagem via OpenCV (único uso permitido) e retorna array RGB uint8."""
    bgr = cv2.imread(path)
    if bgr is None:
        raise FileNotFoundError(f"Imagem não encontrada: {path}")
    return bgr[:, :, ::-1].copy()   # BGR → RGB


# ─────────────────────────────────────────────
#  2. PRÉ-PROCESSAMENTO
# ─────────────────────────────────────────────

def rgb_to_gray(img: np.ndarray) -> np.ndarray:
    """
    Converte RGB para escala de cinza usando os pesos ITU-R BT.601:
      Y = 0.299·R + 0.587·G + 0.114·B
    Esses pesos refletem a sensibilidade do olho humano a cada canal.
    """
    weights = np.array([0.299, 0.587, 0.114], dtype=np.float64)
    return (img @ weights).astype(np.float64)


def _gaussian_kernel(size: int, sigma: float) -> np.ndarray:
    """
    Gera um kernel Gaussiano 2-D de forma analítica.
    G(x,y) = exp(-(x²+y²) / (2σ²))
    Normalizado para que a soma seja 1 (evita mudança de brilho).
    """
    half = size // 2
    ax = np.arange(-half, half + 1, dtype=np.float64)
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx**2 + yy**2) / (2.0 * sigma**2))
    return kernel / kernel.sum()


def _convolve2d(img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """
    Convolução 2-D manual com padding 'reflect' para evitar artefatos de borda.
    Percorre cada posição e aplica o produto de Hadamard com o kernel.
    """
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    # Padding reflexivo replica os pixels de borda espelhados
    padded = np.pad(img, ((ph, ph), (pw, pw)), mode='reflect')
    out = np.zeros_like(img, dtype=np.float64)
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):
            region = padded[i:i + kh, j:j + kw]
            out[i, j] = np.sum(region * kernel)
    return out


def gaussian_blur(img: np.ndarray, size: int = 5, sigma: float = 1.4) -> np.ndarray:
    """
    Aplica suavização Gaussiana para reduzir ruído de alta frequência antes
    da detecção de bordas. Sem suavização, ruído seria interpretado como borda.
    """
    kernel = _gaussian_kernel(size, sigma)
    return _convolve2d(img, kernel)


# ─────────────────────────────────────────────
#  3. DETECÇÃO DE BORDAS  (Sobel + Histerese)
# ─────────────────────────────────────────────

# Kernels de Sobel: aproximam a derivada parcial em x e y
_SOBEL_X = np.array([[-1, 0, 1],
                     [-2, 0, 2],
                     [-1, 0, 1]], dtype=np.float64)

_SOBEL_Y = np.array([[-1, -2, -1],
                     [ 0,  0,  0],
                     [ 1,  2,  1]], dtype=np.float64)


def sobel_gradients(img: np.ndarray):
    """
    Calcula gradientes Gx, Gy, magnitude ||G|| e ângulo θ.
    O operador Sobel é preferível ao Prewitt por dar mais peso ao pixel central,
    sendo mais resistente ao ruído.
    """
    Gx = _convolve2d(img, _SOBEL_X)
    Gy = _convolve2d(img, _SOBEL_Y)
    magnitude = np.hypot(Gx, Gy)
    angle = np.arctan2(Gy, Gx)
    return Gx, Gy, magnitude, angle


def _non_maximum_suppression(magnitude: np.ndarray, angle: np.ndarray) -> np.ndarray:
    """
    Supressão de não-máximos: afina as bordas a 1 pixel de largura.
    Para cada pixel, verifica se é máximo local na direção do gradiente;
    se não for, zera o valor (borda "falsa" ou espessa).
    """
    H, W = magnitude.shape
    suppressed = np.zeros((H, W), dtype=np.float64)
    # Quantiza o ângulo em 4 direções: 0°, 45°, 90°, 135°
    angle_deg = np.rad2deg(angle) % 180

    for i in range(1, H - 1):
        for j in range(1, W - 1):
            a = angle_deg[i, j]
            m = magnitude[i, j]
            # Seleciona os dois vizinhos na direção do gradiente
            if (0 <= a < 22.5) or (157.5 <= a <= 180):
                n1, n2 = magnitude[i, j - 1], magnitude[i, j + 1]
            elif 22.5 <= a < 67.5:
                n1, n2 = magnitude[i - 1, j - 1], magnitude[i + 1, j + 1]
            elif 67.5 <= a < 112.5:
                n1, n2 = magnitude[i - 1, j], magnitude[i + 1, j]
            else:
                n1, n2 = magnitude[i - 1, j + 1], magnitude[i + 1, j - 1]

            if m >= n1 and m >= n2:
                suppressed[i, j] = m
    return suppressed


def _hysteresis(suppressed: np.ndarray, low: float, high: float) -> np.ndarray:
    """
    Limiarização por histerese: usa dois limiares para classificar pixels.
    - Acima do limiar alto  → borda forte (definitivamente borda)
    - Entre low e high      → borda fraca (apenas se conectada a uma borda forte)
    - Abaixo do limiar baixo → descartado

    Essa abordagem reduz falsas bordas e mantém a continuidade dos contornos.
    Implementado com flood-fill iterativo (pilha) para evitar recursão profunda.
    """
    strong = suppressed >= high
    weak   = (suppressed >= low) & ~strong
    edges  = strong.copy()

    # Propaga bordas fortes para pixels fracos vizinhos (8-conectividade)
    stack = list(zip(*np.where(strong)))
    while stack:
        i, j = stack.pop()
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                ni, nj = i + di, j + dj
                if (0 <= ni < suppressed.shape[0] and
                        0 <= nj < suppressed.shape[1] and
                        weak[ni, nj] and not edges[ni, nj]):
                    edges[ni, nj] = True
                    stack.append((ni, nj))
    return edges.astype(np.uint8) * 255


def detect_edges(gray: np.ndarray,
                 low_ratio: float = 0.05,
                 high_ratio: float = 0.15) -> np.ndarray:
    """
    Pipeline completa de detecção de bordas estilo Canny:
      1. Sobel → gradientes
      2. Supressão de não-máximos → bordas finas
      3. Histerese com limiares automáticos (percentis da magnitude)

    Os limiares são calculados como percentis da magnitude para se adaptar
    automaticamente a imagens com diferentes contrastes.
    """
    blurred = gaussian_blur(gray)
    _, _, magnitude, angle = sobel_gradients(blurred)

    # Limiares adaptativos baseados em percentis
    high = float(np.percentile(magnitude, 100 * (1 - high_ratio)))
    low  = high * (low_ratio / high_ratio)

    suppressed = _non_maximum_suppression(magnitude, angle)
    edges = _hysteresis(suppressed, low, high)
    return edges


# ─────────────────────────────────────────────
#  4. EXTRAÇÃO DE CONTORNOS  (Moore-Neighbor)
# ─────────────────────────────────────────────

# Vizinhança de Moore: 8 direções em sentido anti-horário
_MOORE = [(-1, 0), (-1, 1), (0, 1), (1, 1),
          (1, 0),  (1, -1), (0, -1), (-1, -1)]


def _trace_contour(edges: np.ndarray, start_i: int, start_j: int,
                   visited: np.ndarray) -> list:
    """
    Traça um único contorno a partir de um pixel de borda usando o algoritmo
    de Moore-Neighbor (também chamado square tracing ou border following).

    O algoritmo percorre a fronteira do objeto mantendo o pixel de borda à
    esquerda da direção de movimento. Ao retornar ao ponto inicial com a mesma
    direção de entrada, o contorno está completo.

    Retorna lista de (col, row) = (x, y) no espaço de imagem.
    """
    contour = []
    i, j = start_i, start_j
    # Direção inicial: vem de cima (índice 0 = vizinho (-1, 0))
    dir_idx = 0

    for _ in range(edges.size):   # limite para evitar loop infinito
        visited[i, j] = True
        contour.append((j, i))    # (x, y) = (col, row)

        # Busca o próximo pixel de borda na vizinhança de Moore
        found = False
        for k in range(8):
            idx = (dir_idx + k) % 8
            ni, nj = i + _MOORE[idx][0], j + _MOORE[idx][1]
            if (0 <= ni < edges.shape[0] and 0 <= nj < edges.shape[1]
                    and edges[ni, nj] > 0):
                # Atualiza a direção de entrada para o próximo passo
                # (entra pelo lado oposto ao que saiu)
                dir_idx = (idx + 5) % 8   # gira 225° = olha para trás + 45°
                i, j = ni, nj
                found = True
                break

        if not found or (i == start_i and j == start_j):
            break   # contorno fechado ou pixel isolado

    return contour


def extract_contours(edges: np.ndarray,
                     min_length: int = 20) -> list:
    """
    Varre toda a imagem de bordas e extrai todos os contornos com pelo menos
    `min_length` pontos. Contornos curtos geralmente são ruído.

    Retorna lista de contornos, cada um sendo lista de (x, y).
    """
    visited = np.zeros(edges.shape, dtype=bool)
    contours = []

    for i in range(1, edges.shape[0] - 1):
        for j in range(1, edges.shape[1] - 1):
            if edges[i, j] > 0 and not visited[i, j]:
                c = _trace_contour(edges, i, j, visited)
                if len(c) >= min_length:
                    contours.append(c)

    return contours


# ─────────────────────────────────────────────
#  5. MAPEAMENTO PARA ESPAÇO TURTLESIM
# ─────────────────────────────────────────────

def map_to_turtlesim(contours: list,
                     img_shape: tuple,
                     margin: float = 0.5,
                     sim_size: float = 11.0) -> list:
    """
    Transforma coordenadas de pixels (origem no canto superior esquerdo, eixo Y
    invertido) para o espaço do turtlesim (origem no canto inferior esquerdo,
    0 ≤ x, y ≤ 11).

    Passos:
      1. Normaliza para [0, 1] mantendo a proporção (fit uniforme)
      2. Aplica margem para que a tartaruga não saia da tela
      3. Inverte o eixo Y (imagem: Y cresce para baixo; turtlesim: Y cresce para cima)
      4. Escala para [margin, sim_size - margin]
    """
    if not contours:
        return []

    H, W = img_shape[:2]
    usable = sim_size - 2 * margin
    scale = usable / max(H, W)   # escala uniforme

    mapped = []
    for contour in contours:
        pts = []
        for (px, py) in contour:
            # Centraliza e escala
            tx = px * scale + margin + (usable - W * scale) / 2
            ty = (H - py) * scale + margin + (usable - H * scale) / 2
            pts.append((tx, ty))
        mapped.append(pts)
    return mapped


# ─────────────────────────────────────────────
#  6. PONTO DE ENTRADA / VISUALIZAÇÃO
# ─────────────────────────────────────────────

def process_image(path: str,
                  low_ratio: float = 0.05,
                  high_ratio: float = 0.15,
                  min_contour_len: int = 20,
                  visualize: bool = False):
    """
    Executa a pipeline completa e retorna os contornos mapeados para o turtlesim.

    Parâmetros:
        path            – caminho para a imagem de entrada
        low_ratio       – fração para limiar baixo da histerese
        high_ratio      – fração para limiar alto da histerese
        min_contour_len – tamanho mínimo de contorno a manter
        visualize       – se True, exibe as etapas via Matplotlib

    Retorna:
        contours_sim    – lista de contornos em coordenadas do turtlesim
        edges           – imagem binária de bordas (para debug)
    """
    rgb    = load_image(path)
    gray   = rgb_to_gray(rgb)
    blurred = gaussian_blur(gray)
    edges  = detect_edges(gray, low_ratio, high_ratio)
    contours = extract_contours(edges, min_contour_len)
    contours_sim = map_to_turtlesim(contours, rgb.shape)

    if visualize:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        axes[0].imshow(rgb);            axes[0].set_title("Original")
        axes[1].imshow(blurred, cmap='gray'); axes[1].set_title("Gaussian Blur")
        axes[2].imshow(edges, cmap='gray');   axes[2].set_title("Bordas (Canny manual)")
        for ax in axes:
            ax.axis('off')
        plt.tight_layout()
        plt.savefig("/tmp/pipeline_debug.png", dpi=150)
        plt.show()
        print(f"[image_processor] {len(contours_sim)} contornos extraídos.")

    return contours_sim, edges