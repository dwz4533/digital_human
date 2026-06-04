import socket
import time


def send_to_fish(message, ip="127.0.0.1", port=5005, max_retry=5):
    """发送消息给金鱼程序，支持重试"""
    for attempt in range(max_retry):
        try:
            print(f"尝试连接 ({attempt + 1}/{max_retry})...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)  # 3秒超时
            s.connect((ip, port))
            s.send(message.encode("utf-8"))
            s.close()
            print(f"✅ 已发送: {message}")
            return True
        except ConnectionRefusedError:
            print("❌ 连接被拒绝，请确保Unity程序已启动")
            time.sleep(2)  # 等待2秒后重试
        except Exception as e:
            print(f"❌ 错误: {e}")
            break
    return False


if __name__ == "__main__":
    # 你可以在这里修改要发送的话
    messages = [
        "黄河鲤鱼是中华民族的象征之一",
        "锦鲤在中国文化中代表好运",
        "鱼儿水中游"
    ]

    for msg in messages:
        if send_to_fish(msg):
            time.sleep(10)  # 等待5秒让鱼说完
        else:
            print("发送失败，跳过此条消息")
            time.sleep(2)