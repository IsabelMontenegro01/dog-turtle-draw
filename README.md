# turtle_draw

Pacote ROS 2 que extrai contornos de uma imagem com uma pipeline de visão computacional implementada do zero e os desenha no **turtlesim**.

## Estrutura

```
turtle_draw/
├── turtle_draw/
│   ├── __init__.py
│   ├── image_processor.py   # pipeline de visão computacional
│   └── turtle_draw_node.py  # nó ROS 2
├── launch/
│   └── turtle_draw.launch.py
├── resource/turtle_draw
├── package.xml
├── setup.py
└── setup.cfg
```

## Dependências Python

```bash
pip install numpy opencv-python matplotlib
```

> O OpenCV é usado **apenas** para leitura da imagem (`cv2.imread`).  
> Todo o processamento usa somente NumPy.

## Build

```bash
# Dentro do seu workspace ROS 2 (ex: ~/ros2_ws)
cd ~/ros2_ws/src
# copie ou clone o pacote aqui, depois:
cd ~/ros2_ws
colcon build --packages-select turtle_draw
source install/setup.bash
```

## Execução

### Opção 1 – Launch file (recomendado, sobe turtlesim + nó juntos)

```bash
ros2 launch turtle_draw turtle_draw.launch.py image_path:=/caminho/para/sua_imagem.png
```

### Opção 2 – Manual (dois terminais)

**Terminal 1:**
```bash
ros2 run turtlesim turtlesim_node
```

**Terminal 2:**
```bash
ros2 run turtle_draw turtle_draw_node \
  --ros-args -p image_path:=/caminho/para/sua_imagem.png
```

### Parâmetros disponíveis

| Parâmetro        | Padrão    | Descrição                                         |
|------------------|-----------|---------------------------------------------------|
| `image_path`     | image.png | Caminho para a imagem de entrada                  |
| `low_ratio`      | 0.05      | Fração do limiar baixo (histerese)                |
| `high_ratio`     | 0.15      | Fração do limiar alto (histerese)                 |
| `min_contour_len`| 20        | Tamanho mínimo de contorno (filtra ruído)         |
| `pen_r/g/b`      | 255/255/255| Cor RGB da caneta                               |
| `pen_width`      | 1         | Espessura da caneta                               |

### Dicas de ajuste

- **Imagem muito simples / poucos contornos**: reduza `min_contour_len` (ex: `10`)
- **Ruído excessivo / muitos traços falsos**: aumente `high_ratio` (ex: `0.25`)
- **Bordas fracas não detectadas**: reduza `high_ratio` (ex: `0.10`) e `low_ratio` (ex: `0.03`)

## Visualizar a pipeline sem ROS

```python
from turtle_draw.image_processor import process_image

contours, edges = process_image(
    "sua_imagem.png",
    visualize=True   # salva debug em /tmp/pipeline_debug.png
)
print(f"{len(contours)} contornos prontos para o turtlesim")
```

## Pipeline de Visão Computacional

```
Imagem RGB
    │
    ▼  rgb_to_gray()         — pesos ITU-R BT.601
Grayscale float64
    │
    ▼  gaussian_blur()       — kernel Gaussiano 5×5, σ=1.4
Imagem suavizada
    │
    ▼  sobel_gradients()     — kernels Sobel 3×3 em X e Y
Magnitude + Ângulo
    │
    ▼  _non_maximum_suppression()   — afina bordas a 1 pixel
Bordas finas
    │
    ▼  _hysteresis()         — limiares adaptativos por percentil
Bordas binárias
    │
    ▼  extract_contours()    — Moore-Neighbor tracing
Lista de contornos (pixels)
    │
    ▼  map_to_turtlesim()    — normalização + inversão Y + escala
Lista de contornos (coord. turtlesim)
```