import os
import sys
import json
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import builtins

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.history_manager import HistoryAndTimeManager

class TestHistoryAndTimeManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        # 假设路径中包含子目录 history
        self.timestamp_path = os.path.join(self.temp_dir.name, "history", "history_timestamp.json")
        # 确保父目录存在
        os.makedirs(os.path.dirname(self.timestamp_path), exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_timestamp_file_not_exist(self):
        manager = HistoryAndTimeManager(timestamp_file=self.timestamp_path)
        self.assertAlmostEqual(manager.last_update_unix, time.time(), delta=0.5)
        self.assertAlmostEqual(manager.next_update_expected, time.time(), delta=0.5)

    def test_load_timestamp_file_exists(self):
        expected_unix = 1700000000.0
        expected_next = 1700000000.0 + 10 * 24 * 3600
        data = {
            "last_update_unix": expected_unix,
            "next_update_expected": expected_next,
            "last_update_iso": datetime.fromtimestamp(expected_unix).isoformat()
        }
        with open(self.timestamp_path, 'w') as f:
            json.dump(data, f)

        manager = HistoryAndTimeManager(timestamp_file=self.timestamp_path)
        self.assertEqual(manager.last_update_unix, expected_unix)
        self.assertEqual(manager.next_update_expected, expected_next)

    def test_ensure_timestamp_save_normal(self):
        manager = HistoryAndTimeManager(timestamp_file=self.timestamp_path)
        save_func = manager.ensure_timestamp_save()
        save_func("manual_test")

        self.assertTrue(os.path.exists(self.timestamp_path))
        with open(self.timestamp_path, 'r') as f:
            data = json.load(f)

        self.assertIn("last_update_iso", data)
        self.assertIn("last_update_unix", data)
        self.assertIn("next_update_expected", data)

        now_unix = time.time()
        self.assertAlmostEqual(data["last_update_unix"], now_unix, delta=1.0)
        expected_next = now_unix + 10 * 24 * 3600
        self.assertAlmostEqual(data["next_update_expected"], expected_next, delta=1.0)

    def test_ensure_timestamp_save_fallback_simple_file(self):
        """降级到 .simple 文件：模拟 json.dump 失败"""
        manager = HistoryAndTimeManager(timestamp_file=self.timestamp_path)
        save_func = manager.ensure_timestamp_save()

        # 模拟 json.dump 抛出异常，但其他文件操作正常
        with patch('json.dump', side_effect=IOError("模拟写入失败")):
            save_func("test_fallback")

        # 验证降级文件 .simple 被创建
        simple_path = f"{self.timestamp_path}.simple"
        self.assertTrue(os.path.exists(simple_path))
        with open(simple_path, 'r') as f:
            content = f.read().strip()
            float(content)  # 应该是时间戳数字

    def test_ensure_timestamp_save_fallback_os_system(self):
        """降级到 os.system：模拟 json.dump 和 .simple 写入都失败"""
        manager = HistoryAndTimeManager(timestamp_file=self.timestamp_path)
        save_func = manager.ensure_timestamp_save()

        # 模拟第一层 json.dump 失败，且第二层 open('.simple', 'w') 也失败
        # 通过同时 mock open 在写模式时抛异常，但注意不能影响读取
        original_open = builtins.open
        def failing_write_open(*args, **kwargs):
            mode = kwargs.get('mode', args[1] if len(args) > 1 else 'r')
            if 'w' in mode:
                raise IOError("模拟写入失败")
            return original_open(*args, **kwargs)

        with patch('builtins.open', failing_write_open):
            # 还需要确保 os.system 不被实际执行，但我们要验证它被调用了
            with patch('os.system') as mock_system:
                save_func("test_fallback_os")
                mock_system.assert_called_once()
                call_args = mock_system.call_args[0][0]
                self.assertIn("guaranteed_timestamp.txt", call_args)

    def test_ensure_timestamp_save_fallback_stderr(self):
        """最终降级到 stderr：所有写入方式都失败"""
        manager = HistoryAndTimeManager(timestamp_file=self.timestamp_path)
        save_func = manager.ensure_timestamp_save()

        # 模拟所有文件写入失败，且 os.system 也失败
        original_open = builtins.open
        def failing_write_open(*args, **kwargs):
            mode = kwargs.get('mode', args[1] if len(args) > 1 else 'r')
            if 'w' in mode:
                raise IOError("模拟写入失败")
            return original_open(*args, **kwargs)

        with patch('builtins.open', failing_write_open):
            with patch('os.system', side_effect=Exception("os.system 失败")):
                with patch('sys.stderr.write') as mock_stderr_write:
                    save_func("test_fallback_stderr")
                    mock_stderr_write.assert_called_once()
                    written_text = mock_stderr_write.call_args[0][0]
                    self.assertTrue(written_text.startswith("GUARANTEED_TIMESTAMP:"))
                    timestamp_str = written_text.split(":")[1].strip()
                    float(timestamp_str)

    def test_atexit_registration(self):
        with patch("atexit.register") as mock_register:
            manager = HistoryAndTimeManager(timestamp_file=self.timestamp_path)
            manager.ensure_timestamp_save()
            mock_register.assert_called_once()
            registered_func = mock_register.call_args[0][0]
            self.assertTrue(callable(registered_func))

    def test_signal_handlers(self):
        with patch("signal.signal") as mock_signal:
            manager = HistoryAndTimeManager(timestamp_file=self.timestamp_path)
            manager.ensure_timestamp_save()
            # 至少 SIGINT 和 SIGTERM
            self.assertGreaterEqual(mock_signal.call_count, 2)
            if mock_signal.call_count > 0:
                handlers = [call[0][1] for call in mock_signal.call_args_list]
                first_handler = handlers[0]
                for h in handlers:
                    self.assertIs(h, first_handler)

if __name__ == "__main__":
    unittest.main()