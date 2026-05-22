"""
launch/turtle_draw.launch.py
-----------------------------
Inicia o turtlesim_node e o turtle_draw_node em sequência.

Uso:
  ros2 launch turtle_draw turtle_draw.launch.py image_path:=/caminho/para/imagem.png

Parâmetros opcionais (todos com valores padrão):
  image_path      – caminho da imagem de entrada
  low_ratio       – limiar baixo relativo da histerese  (padrão 0.05)
  high_ratio      – limiar alto relativo da histerese   (padrão 0.15)
  min_contour_len – tamanho mínimo de contorno em pixels (padrão 20)
  pen_r/g/b       – cor RGB da caneta                   (padrão 255/255/255)
  pen_width       – espessura da caneta em pixels        (padrão 1)
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # ── declaração de argumentos ────────────────────────────────────────────
    args = [
        DeclareLaunchArgument('image_path',      default_value='image.png',
                              description='Caminho para a imagem de entrada'),
        DeclareLaunchArgument('low_ratio',       default_value='0.05'),
        DeclareLaunchArgument('high_ratio',      default_value='0.30'),
        DeclareLaunchArgument('min_contour_len', default_value='80'),
        DeclareLaunchArgument('pen_r',           default_value='255'),
        DeclareLaunchArgument('pen_g',           default_value='255'),
        DeclareLaunchArgument('pen_b',           default_value='255'),
        DeclareLaunchArgument('pen_width',       default_value='2'),
    ]

    # ── nó do simulador ─────────────────────────────────────────────────────
    turtlesim_node = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim',
        output='screen',
    )

    # ── nó de desenho ───────────────────────────────────────────────────────
    draw_node = Node(
        package='turtle_draw',
        executable='turtle_draw_node',
        name='turtle_draw_node',
        output='screen',
        parameters=[{
            'image_path':      LaunchConfiguration('image_path'),
            'low_ratio':       LaunchConfiguration('low_ratio'),
            'high_ratio':      LaunchConfiguration('high_ratio'),
            'min_contour_len': LaunchConfiguration('min_contour_len'),
            'pen_r':           LaunchConfiguration('pen_r'),
            'pen_g':           LaunchConfiguration('pen_g'),
            'pen_b':           LaunchConfiguration('pen_b'),
            'pen_width':       LaunchConfiguration('pen_width'),
        }],
    )

    return LaunchDescription(args + [turtlesim_node, draw_node])