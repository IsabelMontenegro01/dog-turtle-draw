# Documentação Técnica - Turtle Draw

## 📖 Índice

1. [Visão Geral](#1-visão-geral)
2. [Conceitos Fundamentais](#2-conceitos-fundamentais)
3. [Arquitetura da Pipeline](#3-arquitetura-da-pipeline)
4. [Detalhes de Implementação](#4-detalhes-de-implementação)
5. [Troubleshooting Avançado](#5-troubleshooting-avançado)

---

## 1. Visão Geral

**Turtle Draw** é um projeto que implementa uma pipeline completa de visão computacional do zero, usando apenas NumPy para processamento matemático. O objetivo é demonstrar como transformar uma imagem arbitrária em um conjunto de contornos que podem ser desenhados pelo turtlesim via ROS 2.

### Resultado Final

![Turtle desenhando contornos](img/turtle_result.png)
*Adicionar screenshot do turtle desenhando o resultado*

---

## 2. Conceitos Fundamentais

### 2.1. Espaço de Cores RGB vs Grayscale

**RGB → Grayscale** não é apenas média simples. Usamos pesos perceptuais (ITU-R BT.601):

```
Grayscale = 0.299*R + 0.587*G + 0.114*B
```

Por quê? O olho humano é mais sensível ao verde, menos ao azul. Isso preserva percepção de luminância.

**Implementação:**
```python
def rgb_to_gray(img: np.ndarray) -> np.ndarray:
    weights = np.array([0.299, 0.587, 0.114], dtype=np.float64)
    return (img @ weights).astype(np.float64)  # Produto matriz-vetor vetorizado
```

---

### 2.2. Blur Gaussiano

**Propósito**: Suavizar ruído e reduzir sensibilidade a variações locais.

**Kernel Gaussiano 15×15, σ=3.5:**
```
G(x,y) = (1 / 2πσ²) * exp(-(x² + y²) / 2σ²)
```

**Por que 15×15 e não menor?**
- 5×5 deixa muitos artefatos
- 15×15 suaviza bem sem eliminar bordas importantes
- σ=3.5 controla "força" do blur (maior = mais suave)

**Implementação:**
```python
def _gaussian_kernel(size: int, sigma: float) -> np.ndarray:
    half = size // 2
    ax = np.arange(-half, half + 1, dtype=np.float64)
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx**2 + yy**2) / (2.0 * sigma**2))
    return kernel / kernel.sum()  # Normalizar para preservar brilho

def _convolve2d(img, kernel):  # Convolução manual com padding reflexivo
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = np.pad(img, ((ph, ph), (pw, pw)), mode='reflect')
    out = np.zeros_like(img, dtype=np.float64)
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):
            region = padded[i:i + kh, j:j + kw]
            out[i, j] = np.sum(region * kernel)
    return out
```

---

### 2.3. Detecção de Bordas: Sobel + Histerese

#### 2.3.1. Sobel - O que é?

Sobel calcula **gradientes** (taxa de mudança de intensidade) usando kernels 3×3:

```
Gx = [-1  0  1]    Gy = [-1 -2 -1]
     [-2  0  2]         [ 0  0  0]
     [-1  0  1]         [ 1  2  1]

Magnitude = √(Gx² + Gy²)
Ângulo = atan2(Gy, Gx)
```

**Intuição**: Onde a imagem muda rápido de cor (alto gradiente), há uma borda.

#### 2.3.2. Non-Maximum Suppression

Depois de calcular magnitude, as bordas são **grossas** (vários pixels). NMS as **afina para 1 pixel**:

```python
def _non_maximum_suppression(magnitude, angle):
    # Para cada pixel, comparar com vizinhos na direção do gradiente
    # Manter só o máximo local (máximo não-suprimido)
    # Resultado: bordas finas de ~1 pixel
```

#### 2.3.3. Histerese (Canny-style)

Problema: limiar fixo deixa ruído ou perde bordas fracas.

**Solução**: Usar dois limiares (low e high):

```
Strong edges: magnitude ≥ high_threshold
Weak edges:   low_threshold ≤ magnitude < high_threshold

Conectar bordas fracas que tocam bordas fortes
```

**Implementação:**
```python
def _hysteresis(suppressed, low, high):
    strong = suppressed >= high
    weak = (suppressed >= low) & ~strong
    edges = strong.copy()
    
    # BFS/DFS: marcar bordas fracas conectadas a bordas fortes
    stack = list(zip(*np.where(strong)))
    while stack:
        i, j = stack.pop()
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                ni, nj = i + di, j + dj
                if (0 <= ni < ...) and weak[ni, nj] and not edges[ni, nj]:
                    edges[ni, nj] = True
                    stack.append((ni, nj))
    return edges
```

---

### 2.4. Extração de Contornos: Moore-Neighbor Tracing

**Problema**: Temos uma imagem binária de bordas. Como extrair o **caminho** conectado?

**Moore-Neighbor Algorithm** (Contour Tracing):

1. Começar em um pixel de borda não visitado
2. Seguir vizinhos (8 direções) em ordem circular
3. Marcar como visitado
4. Parar quando voltar ao início

```python
_MOORE = [(-1, 0), (-1, 1), (0, 1), (1, 1),
          (1, 0),  (1, -1), (0, -1), (-1, -1)]
```

**Resultado**: Lista de coordenadas (x, y) do contorno em ordem.

---

### 2.5. Filtro de Ruído: Compactness

**Problema**: Bordas "espalhadas" (ruído, textura de fundo) vs objetos localizados (cachorro, rosto).

**Solução**: Razão de compactness da bounding box:

```python
def _contour_compactness(contour, img_shape):
    bbox_area = (max_x - min_x) * (max_y - min_y)
    return bbox_area / (H * W)
```

- Ruído espalhado: ratio ≈ 1.0 (cobre muita área)
- Objeto localizado: ratio << 1.0 (concentrado)

**Filtro**: Descartar contornos com `ratio > max_bbox_ratio` (padrão: 0.85).

---

### 2.6. Mapeamento para Turtlesim

**Problema**: Coordenadas da imagem (pixels) ≠ coordenadas do turtlesim.

**Turtlesim**: 
- Tamanho: 11×11 unidades
- Origem: (0, 0) no canto inferior esquerdo
- Y aumenta para cima

**Transformação**:
```python
# Escalar imagem para caber em 11×11 (com margem)
scale = (11 - 2*margin) / max(H, W)

# Inverter Y (imagem tem Y para baixo, turtlesim para cima)
tx = px * scale + margin + ...
ty = (H - py) * scale + margin + ...
```

---

## 3. Arquitetura da Pipeline

### 3.1. Fluxo Completo

```
┌─ process_image() ────────────────────────────┐
│                                               │
│  1. load_image(path)                         │
│     └─ BGR → RGB + float64                   │
│                                               │
│  2. rgb_to_gray(img)                         │
│     └─ Pesos ITU-R BT.601                    │
│                                               │
│  3. gaussian_blur(gray)                      │
│     └─ Kernel 15×15, σ=3.5                   │
│                                               │
│  4. detect_edges(blurred)                    │
│     ├─ sobel_gradients()                     │
│     ├─ _non_maximum_suppression()            │
│     └─ _hysteresis()                         │
│                                               │
│  5. extract_contours(edges)                  │
│     ├─ _trace_contour() (Moore-Neighbor)    │
│     ├─ Filtro por min_length                │
│     └─ Filtro por compactness               │
│                                               │
│  6. map_to_turtlesim(contours)               │
│     └─ Escalar + normalizar coordenadas      │
│                                               │
└─ return: contours_sim, edges ────────────────┘
```

### 3.2. Parâmetros Ajustáveis

| Parâmetro | Padrão | Efeito |
|-----------|--------|--------|
| `low_ratio` | 0.05 | Controla limiar baixo de histerese (menor = mais bordas fracas detectadas) |
| `high_ratio` | 0.30 | Controla limiar alto (maior = menos falsos positivos) |
| `min_contour_len` | 80 | Mínimo pixels contíguo (filtra ruído pontual) |
| `max_bbox_ratio` | 0.85 | Máxima fração da imagem (filtra ruído espalhado) |

---

## 4. Detalhes de Implementação

### 4.1. Operação de Convolução Manual

Por que implementar convolução manualmente em vez de usar `scipy.signal.convolve2d`?

1. **Aprendizado**: Entender o algoritmo
2. **Controle**: Escolher padding (reflexivo) apropriado
3. **Sem dependências extras**: Apenas NumPy

**Trade-off**: Implementação manual é ~100x mais lenta, mas suficiente para imagens pequenas (< 1000×1000).

### 4.2. Por que Moore-Neighbor e não OpenCV?

OpenCV teria contours prontas em uma linha:
```python
contours, _ = cv2.findContours(edges, ...)
```

Mas aqui implementamos do zero para:
- Ensinar algoritmo de rastreamento
- Adicionar filtros customizados (min_length, compactness)
- Entender geometria e conectividade

---

## 5. Troubleshooting Avançado

### 5.1. Sintoma: Muitos contornos indesejados (ruído)

**Diagnosticar:**
```python
from turtle_draw.image_processor import process_image
contours, edges = process_image("imagem.png", visualize=True)
# Ver em /tmp/pipeline_debug.png se há muitas bordas ou bordas finas/falsas
```

**Causas possíveis:**
1. Imagem muito com textura/ruído → aumentar `high_ratio` (0.35 ou 0.40)
2. Contornos pequenos → aumentar `min_contour_len` (100, 150, 200)
3. Contornos espalhados → reduzir `max_bbox_ratio` (0.70, 0.60)

### 5.2. Sintoma: Nenhum contorno ou muito poucos

**Causas:**
1. Limiar muito rigoroso → reduzir `high_ratio` (0.20, 0.15)
2. Blur demais → código em `process_image()` está com size/sigma grandes demais
3. Imagem muito escura ou clara → aumentar contraste antes de processar

### 5.3. Sintoma: Bordas espessas / múltiplas linhas paralelas

**Causa**: Blur insuficiente (deixa detalhes de textura).

**Fix**: Em `image_processor.py`, ajustar:
```python
blurred = gaussian_blur(gray, size=17, sigma=4.0)  # Aumentar
```

---

## 🎥 Vídeo Explicativo

[📺 Assista ao vídeo completo do projeto](LINK_DO_VIDEO_AQUI)
