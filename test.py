import time
import rclpy
from std_msgs.msg import Float64

LTHRUST=500.0
RTHRUST=250.0
rclpy.init()

node = rclpy.create_node("test_drive")
left_pub = node.create_publisher(Float64, "/wamv/thrusters/left/thrust", 10)
right_pub = node.create_publisher(Float64, "/wamv/thrusters/right/thrust", 10)


def send(left, right):
    left_pub.publish(Float64(data=left))
    right_pub.publish(Float64(data=right))


try:
    end = time.time() + 10.0
    while time.time() < end:
        send(LTHRUST, RTHRUST)
        time.sleep(0.1)  # 10 messages per second
finally:
    for _ in range(5):
        send(0.0, 0.0)
        time.sleep(0.05)
    node.destroy_node()
    rclpy.shutdown()