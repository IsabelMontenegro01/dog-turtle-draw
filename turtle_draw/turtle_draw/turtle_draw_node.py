import rclpy
from rclpy.node import Node
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
        self.contours, _ = process_image(image_path, low_ratio=low_ratio, high_ratio=high_ratio, min_contour_len=min_contour_len, visualize=False)
        self.get_logger().info(f"{len(self.contours)} contornos extraidos.")

        # monta fila plana: (x, y, is_first)
        self._points = []
        for contour in self.contours:
            for i, (x, y) in enumerate(contour):
                self._points.append((x, y, i == 0))
        self.get_logger().info(f"{len(self._points)} pontos no total.")

        self._idx     = 0
        self._future  = None
        self._stage   = 'pen_off'  # pen_off | teleport | pen_on | draw
        self._cur_x   = 0.0
        self._cur_y   = 0.0

        self.timer = self.create_timer(0.01, self._control_loop)

    def _control_loop(self):
        # se tem future pendente, espera terminar
        if self._future is not None:
            if self._future.done():
                self._future = None
            return

        if self._idx >= len(self._points):
            self.get_logger().info("Desenho concluido!")
            self.timer.cancel()
            return

        x, y, is_first = self._points[self._idx]

        if is_first:
            # sequencia: pen_off -> teleport -> pen_on
            if self._stage == 'pen_off':
                req = SetPen.Request()
                req.r = self.pen_r; req.g = self.pen_g; req.b = self.pen_b
                req.width = self.pen_width; req.off = 1
                self._future = self.pen_client.call_async(req)
                self._stage = 'teleport'

            elif self._stage == 'teleport':
                req = TeleportAbsolute.Request()
                req.x = float(x); req.y = float(y); req.theta = 0.0
                self._future = self.teleport_client.call_async(req)
                self._stage = 'pen_on'

            elif self._stage == 'pen_on':
                req = SetPen.Request()
                req.r = self.pen_r; req.g = self.pen_g; req.b = self.pen_b
                req.width = self.pen_width; req.off = 0
                self._future = self.pen_client.call_async(req)
                self._stage = 'draw'

            elif self._stage == 'draw':
                self._idx += 1
                self._stage = 'pen_off'

        else:
            # so teleporta com caneta abaixada
            req = TeleportAbsolute.Request()
            req.x = float(x); req.y = float(y); req.theta = 0.0
            self._future = self.teleport_client.call_async(req)
            self._idx += 1
            self._stage = 'pen_off'


def main(args=None):
    rclpy.init(args=args)
    node = TurtleDrawNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()