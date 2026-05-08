import logging
import socket, json

class UnitySender:
    def __init__(self):
        self.HOST="0.0.0.0"
        self.PORT=5005

    def connect_to_unity(self):
        print("Connecting to Unity...")
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.HOST, self.PORT))
        self.server.listen(1)
        logging.info("✅ Listening on %s %s", self.HOST, self.PORT)

        conn, addr = self.server.accept()
        logging.info("✅ Unity connected: %s", addr)
        
        return conn
    
    def send_line(self, conn, msg: dict):
        conn.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))
        logging.info("向Unity客户端发送消息:", msg)

