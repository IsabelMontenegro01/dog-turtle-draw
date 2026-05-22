# turtle_draw

Pacote ROS 2 que extrai contornos de imagens utilizando uma pipeline de visão computacional implementada com NumPy e os desenha no **turtlesim**.

---

## Funcionalidades

- Extração de bordas e contornos
- Pipeline de visão computacional implementada manualmente
- Desenho automático no turtlesim
- Parametrização de thresholds e filtros
- Integração com ROS 2

---

## Estrutura do Projeto

```text
turtle_draw/
├── turtle_draw/
│   ├── __init__.py
│   ├── image_processor.py
│   └── turtle_draw_node.py
├── launch/
├── docs/
├── resource/
├── package.xml
├── setup.py
└── setup.cfg
```

---

## Dependências

- ROS 2 Humble ou superior
- Python 3.10+

### Bibliotecas Python

```bash
pip install numpy opencv-python matplotlib
```

> O OpenCV é utilizado apenas para leitura da imagem (`cv2.imread`).

---

## Build

Dentro do workspace ROS 2:

```bash
cd ~/ros2_ws

colcon build --packages-select turtle_draw

source install/setup.bash
```

---

## Execução

### Terminal 1

Inicie o turtlesim:

```bash
ros2 run turtlesim turtlesim_node
```

---

### Terminal 2

Compile e execute o projeto:

```bash
colcon build --packages-select turtle_draw

source install/setup.bash

./install/turtle_draw/bin/turtle_draw_node \
  --ros-args \
  -p image_path:=/caminho/para/imagem.png \
  -p min_contour_len:=80 \
  -p low_ratio:=0.05 \
  -p high_ratio:=0.30
```

---

## Parâmetros

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `image_path` | `image.png` | Caminho da imagem de entrada |
| `low_ratio` | `0.05` | Threshold inferior da histerese |
| `high_ratio` | `0.30` | Threshold superior da histerese |
| `min_contour_len` | `80` | Tamanho mínimo de contorno |
| `pen_r/g/b` | `255/255/255` | Cor RGB da caneta |
| `pen_width` | `2` | Espessura da caneta |

---

## Observações

- Os exemplos do projeto utilizam `dog.png` apenas como imagem de demonstração.
- Recomenda-se informar explicitamente o parâmetro `image_path` durante a execução.

---

## Teste Rápido sem ROS

```python
from turtle_draw.image_processor import process_image

contours, edges = process_image(
    "sua_imagem.png",
    visualize=True
)
```

---

## Documentação

- Relatório técnico resumido: [`docs/relatorio_tecnico.md`](docs/relatorio.md)
- Documentação completa da pipeline: [`docs/documentacao_completa.md`](docs/documentacao_completa.md)

---

## Vídeo Explicativo

[📺 Assista ao vídeo do projeto](https://drive.google.com/file/d/1PdwdPyE50r1I8M1HIDfNiWplReT7OuAn/view?usp=sharing)