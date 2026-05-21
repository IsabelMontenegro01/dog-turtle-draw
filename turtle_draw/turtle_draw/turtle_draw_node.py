import threading
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from turtlesim.srv import TeleportAbsolute, SetPen
from turtle_draw.image_processor import process_image


class TurtleDrawNode(Node):

    def __init__(self):
        super().__init__('turtle_draw_node')
        self.declare_parameter('image_path',      'image.png')
        self.declare_parameter('low_ratio',       0.05)
        self.declare_parameter('high_ratio',      0.3)
        self.declare_parameter('min_contour_len', 80)
        self.declare_parameter('pen_r',           255)
        self.declare_parameter('pen_g',           255)
        self.declare_parameter('pen_b',           255)
        self.declare_parameter('pen_width',       2)

        self.pen_r     = self.get_parameter('pen_r').value
        self.pen_g     = self.get_parameter('pen_g').value
        self.pen_b     = self.get_parameter('pen_b').value
        self.pen_width = self.get_parameter('pen_width').value

        self.teleport_client = self.create_client(TeleportAbsolute, '/turtle1/teleport_absolute')
        self.pen_client      = self.create_client(SetPen, '/turtle1/set_pen')

        self.get_logger().info("Aguardando servicos do turtlesim...")
        self.teleport_client.wait_for_service(timeout_sec=10.0)
        self.pen_client.wait_for_service(timeout_sec=10.0)
        self.get_logger().info("Servicos disponiveis.")

        image_path      = self.get_parameter('image_path').value
        low_ratio       = self.get_parameter('low_ratio').value
        high_ratio      = self.get_parameter('high_ratio').value
        min_contour_len = self.get_parameter('min_contour_len').value

        self.get_logger().info(f"Processando imagem: {image_path}")
        self.contours, _ = process_image(
            image_path,
            low_ratio=low_ratio,
            high_ratio=high_ratio,
            min_contour_len=min_contour_len,
            visualize=False
        )
        self.get_logger().info(f"{len(self.contours)} contornos extraidos.")

    def _wait_future(self, future):
        """Aguarda um future sem criar executor novo — usa um Event thread-safe."""
        event = threading.Event()
        future.add_done_callback(lambda _: event.set())
        event.wait()  # bloqueia só a thread de desenho, não o executor

    def call_set_pen(self, off):
        req = SetPen.Request()
        req.r = self.pen_r; req.g = self.pen_g; req.b = self.pen_b
        req.width = self.pen_width; req.off = int(off)
        future = self.pen_client.call_async(req)
        self._wait_future(future)

    def call_teleport(self, x, y):
        req = TeleportAbsolute.Request()
        req.x = float(x); req.y = float(y); req.theta = 0.0
        future = self.teleport_client.call_async(req)
        self._wait_future(future)

    def draw(self):
        self.get_logger().info("Iniciando desenho...")
        for i, contour in enumerate(self.contours):
            self.get_logger().info(f"Contorno {i+1}/{len(self.contours)} ({len(contour)} pts)")
            self.call_set_pen(off=True)
            x0, y0 = contour[0]
            self.call_teleport(x0, y0)
            self.call_set_pen(off=False)
            for x, y in contour[1:]:
                self.call_teleport(x, y)
        self.call_set_pen(off=True)
        self.get_logger().info("Desenho concluido!")


def main(args=None):
    rclpy.init(args=args)
    node = TurtleDrawNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    draw_thread = threading.Thread(target=node.draw, daemon=True)
    draw_thread.start()

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()