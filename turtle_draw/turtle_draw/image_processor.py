"""
image_processor.py
------------------
Pipeline de visão computacional implementada do zero (apenas NumPy + OpenCV só para leitura).
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt


# ─────────────────────────────────────────────
#  1. CARREGAMENTO
# ─────────────────────────────────────────────

def load_image(path: str) -> np.ndarray:
    bgr = cv2.imread(path)
    if bgr is None:
        raise FileNotFoundError(f"Imagem não encontrada: {path}")
    return bgr[:, :, ::-1].copy()


# ─────────────────────────────────────────────
#  2. PRÉ-PROCESSAMENTO
# ─────────────────────────────────────────────

def rgb_to_gray(img: np.ndarray) -> np.ndarray:
    weights = np.array([0.299, 0.587, 0.114], dtype=np.float64)
    return (img @ weights).astype(np.float64)


def _gaussian_kernel(size: int, sigma: float) -> np.ndarray:
    half = size // 2
    ax = np.arange(-half, half + 1, dtype=np.float64)
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx**2 + yy**2) / (2.0 * sigma**2))
    return kernel / kernel.sum()


def _convolve2d(img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = np.pad(img, ((ph, ph), (pw, pw)), mode='reflect')
    out = np.zeros_like(img, dtype=np.float64)
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):
            region = padded[i:i + kh, j:j + kw]
            out[i, j] = np.sum(region * kernel)
    return out


def gaussian_blur(img: np.ndarray, size: int = 9, sigma: float = 2.5) -> np.ndarray:
    kernel = _gaussian_kernel(size, sigma)
    return _convolve2d(img, kernel)


# ─────────────────────────────────────────────
#  3. DETECÇÃO DE BORDAS  (Sobel + Histerese)
# ─────────────────────────────────────────────

_SOBEL_X = np.array([[-1, 0, 1],
                     [-2, 0, 2],
                     [-1, 0, 1]], dtype=np.float64)

_SOBEL_Y = np.array([[-1, -2, -1],
                     [ 0,  0,  0],
                     [ 1,  2,  1]], dtype=np.float64)


def sobel_gradients(img: np.ndarray):
    Gx = _convolve2d(img, _SOBEL_X)
    Gy = _convolve2d(img, _SOBEL_Y)
    magnitude = np.hypot(Gx, Gy)
    angle = np.arctan2(Gy, Gx)
    return Gx, Gy, magnitude, angle


def _non_maximum_suppression(magnitude: np.ndarray, angle: np.ndarray) -> np.ndarray:
    H, W = magnitude.shape
    suppressed = np.zeros((H, W), dtype=np.float64)
    angle_deg = np.rad2deg(angle) % 180

    for i in range(1, H - 1):
        for j in range(1, W - 1):
            a = angle_deg[i, j]
            m = magnitude[i, j]
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
    strong = suppressed >= high
    weak   = (suppressed >= low) & ~strong
    edges  = strong.copy()

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
                 high_ratio: float = 0.30) -> np.ndarray:
    """
    CORRIGIDO: recebe imagem já suavizada, NÃO aplica gaussian_blur novamente.
    O double-blur anterior distorcia os gradientes e detectava bordas fantasmas.
    """
    # ← REMOVIDO: blurred = gaussian_blur(gray) que causava double-blur
    _, _, magnitude, angle = sobel_gradients(gray)

    high = float(np.percentile(magnitude, 100 * (1 - high_ratio)))
    low  = high * (low_ratio / high_ratio)

    suppressed = _non_maximum_suppression(magnitude, angle)
    edges = _hysteresis(suppressed, low, high)
    return edges


# ─────────────────────────────────────────────
#  4. EXTRAÇÃO DE CONTORNOS  (Moore-Neighbor)
# ─────────────────────────────────────────────

_MOORE = [(-1, 0), (-1, 1), (0, 1), (1, 1),
          (1, 0),  (1, -1), (0, -1), (-1, -1)]


def _trace_contour(edges: np.ndarray, start_i: int, start_j: int,
                   visited: np.ndarray) -> list:
    contour = []
    i, j = start_i, start_j
    dir_idx = 0

    for _ in range(edges.size):
        visited[i, j] = True
        contour.append((j, i))

        found = False
        for k in range(8):
            idx = (dir_idx + k) % 8
            ni, nj = i + _MOORE[idx][0], j + _MOORE[idx][1]
            if (0 <= ni < edges.shape[0] and 0 <= nj < edges.shape[1]
                    and edges[ni, nj] > 0):
                dir_idx = (idx + 5) % 8
                i, j = ni, nj
                found = True
                break

        if not found or (i == start_i and j == start_j):
            break

    return contour


def _contour_compactness(contour: list, img_shape: tuple) -> float:
    """
    Razão entre área do bounding box do contorno e área total da imagem.
    Contornos de ruído espalhado pelo fundo têm razão próxima de 1.0.
    O contorno do cachorro (objeto localizado) tem razão bem menor.
    """
    H, W = img_shape
    xs = [p[0] for p in contour]
    ys = [p[1] for p in contour]
    bbox_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
    return bbox_area / (H * W)


def extract_contours(edges: np.ndarray,
                     min_length: int = 20,
                     max_bbox_ratio: float = 0.85) -> list:
    """
    Extrai contornos e filtra ruído de fundo por dois critérios:
      - min_length: descarta contornos muito curtos (pontos isolados)
      - max_bbox_ratio: descarta contornos cujo bounding box cobre uma fração
        grande da imagem — esses são tipicamente ruído/textura de fundo espalhado,
        não objetos localizados como o cachorro.
    """
    visited = np.zeros(edges.shape, dtype=bool)
    contours = []

    for i in range(1, edges.shape[0] - 1):
        for j in range(1, edges.shape[1] - 1):
            if edges[i, j] > 0 and not visited[i, j]:
                c = _trace_contour(edges, i, j, visited)
                if len(c) < min_length:
                    continue
                # Filtra contornos espalhados (ruído de fundo)
                ratio = _contour_compactness(c, edges.shape)
                if ratio < max_bbox_ratio:
                    contours.append(c)

    return contours


# ─────────────────────────────────────────────
#  5. MAPEAMENTO PARA ESPAÇO TURTLESIM
# ─────────────────────────────────────────────

def map_to_turtlesim(contours: list,
                     img_shape: tuple,
                     margin: float = 0.5,
                     sim_size: float = 11.0) -> list:
    if not contours:
        return []

    H, W = img_shape[:2]
    usable = sim_size - 2 * margin
    scale = usable / max(H, W)

    mapped = []
    for contour in contours:
        pts = []
        for (px, py) in contour:
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
                  high_ratio: float = 0.3,
                  min_contour_len: int = 80,
                  visualize: bool = False):
    rgb     = load_image(path)
    gray    = rgb_to_gray(rgb)
    blurred = gaussian_blur(gray, size=15, sigma=3.5)  # era size=9, sigma=2.5
    edges   = detect_edges(blurred, low_ratio, high_ratio)
    contours = extract_contours(edges, min_contour_len)
    contours_sim = map_to_turtlesim(contours, rgb.shape)

    if visualize:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        axes[0].imshow(rgb);                  axes[0].set_title("Original")
        axes[1].imshow(blurred, cmap='gray'); axes[1].set_title("Blur")
        axes[2].imshow(edges, cmap='gray');   axes[2].set_title("Bordas")
        for ax in axes:
            ax.axis('off')
        plt.tight_layout()
        plt.savefig("/tmp/pipeline_debug.png", dpi=150)
        plt.show()
        print(f"[image_processor] {len(contours_sim)} contornos extraídos.")

    return contours_sim, edges