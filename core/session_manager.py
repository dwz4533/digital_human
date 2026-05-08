import threading

class SessionManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._current_session_id = 0

    def next_session_id(self):
        with self._lock:
            self._current_session_id += 1
            return self._current_session_id

    def get_session_id(self):
        with self._lock:
            return self._current_session_id