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

## Dependências

- **ROS 2** (Humble ou superior)
- **Python 3.10+**

### Dependências Python

```bash
pip install numpy opencv-python matplotlib
```

> **Nota**: O OpenCV é usado **apenas** para leitura da imagem (`cv2.imread`).  
> Todo o processamento de visão computacional é implementado com NumPy puro.

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
| `low_ratio`      | 0.05      | Fração do limiar baixo (histerese de Canny)       |
| `high_ratio`     | 0.30      | Fração do limiar alto (histerese de Canny)        |
| `min_contour_len`| 80        | Tamanho mínimo de contorno em pixels (filtra ruído)|
| `pen_r/g/b`      | 255/255/255| Cor RGB da caneta                                |
| `pen_width`      | 2         | Espessura da caneta em pixels                     |

#### Ajuste Rápido de Problemas

- **Muito ruído / falsos contornos**: aumente `high_ratio` (ex: 0.35)
- **Poucos contornos**: reduza `high_ratio` (ex: 0.20) e aumente `low_ratio` (ex: 0.08)
- **Teste rápido sem ROS**:
  ```python
  from turtle_draw.image_processor import process_image
  contours, edges = process_image("sua_imagem.png", visualize=True)
  ```

Para troubleshooting avançado, consulte a [documentação técnica](docs/documentacao.md#troubleshooting-avançado).

## Documentação

Para mais detalhes sobre a lógica de código, conceitos de visão computacional e arquitetura da pipeline, consulte a [documentação completa](docs/documentacao.md).

### 🎥 Vídeo Explicativo

[📺 Assista ao vídeo do projeto](https://drive.google.com/file/d/1PdwdPyE50r1I8M1HIDfNiWplReT7OuAn/view?usp=sharing)