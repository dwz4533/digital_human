import threading
import queue
from datetime import time
import pyaudio
import json
import time
# from say import response1
# 添加讯飞语音识别所需的库
import websocket
import base64
import datetime
import hashlib
import hmac
from datetime import datetime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from time import mktime
import threading
from config import logger
import config
import asyncio

recognized_q = asyncio.Queue()

# 讯飞语音识别参数类
class Ws_Param(object):
    # 初始化
    def __init__(self, APPID : str, APIKey : str, APISecret : str):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.iat_params = {
            "domain": "slm", "language": "mul_cn", "accent": "mandarin","result":
                {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "json"
                }
        }

    def create_url_v2(self):
        """使用V2接口URL"""
        # V2接口的URL
        url = 'wss://iat-api.xfyun.cn/v2/iat'
        
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        # V2接口的签名格式
        signature_origin = "host: " + "iat-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        
        # 进行hmac-sha256加密
        signature_sha = hmac.new(
            self.APISecret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
        
        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "iat-api.xfyun.cn"
        }
        
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        return url
    
    def create_url(self):
        """保持向后兼容，但默认使用V2"""
        return self.create_url_v2()

# 音频录制类
class AudioRecorder:
    def __init__(self):
        self.CHUNK = 1280  # 每次读取的音频块大小
        self.FORMAT = pyaudio.paInt16  # 音频格式
        self.CHANNELS = 1  # 单声道
        self.RATE = 16000  # 采样率
        self.p = pyaudio.PyAudio()
        self.stream = None

    def start_recording(self):
        self.stream = self.p.open(format=self.FORMAT,
                                channels=self.CHANNELS,
                                rate=self.RATE,
                                input=True,
                                frames_per_buffer=self.CHUNK)
        logger.info("Start recording...")

    def read_audio(self):
        if self.stream:
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            return data
        return None

    def stop_recording(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        logger.info("Recording ended")

logger.info("Now is connected!")
# 全局变量，用于存储识别结果

recognition_complete = False

# API管理器类，用于管理多个API配置并自动切换
class ApiManager:
    def __init__(self, api_configs : list[dict]):
        self.api_configs = api_configs
        self.current_index = 0
        self.ws_param = None
        self.initialize_current_api()
    
    def initialize_current_api(self):
        """初始化当前API配置"""
        if not self.api_configs:  # 如果没有可用的API配置
            logger.error("No available API configurations!")
            return None
            
        config = self.api_configs[self.current_index]
        self.ws_param = Ws_Param(
            APPID=config["APPID"],
            APIKey=config["APIKey"],
            APISecret=config["APISecret"]
        )
        logger.info(f"Using API configuration {self.current_index + 1}/{len(self.api_configs)}")
    
    def remove_current_api(self):
        """删除当前API配置"""
        if self.api_configs:
            removed_config = self.api_configs.pop(self.current_index)
            logger.warning(f"Removed invalid API configuration: {removed_config['APPID']}")
            
            # 如果删除后没有API配置了
            if not self.api_configs:
                logger.error("No more API configurations available!")
                return None
                
            # 调整current_index，确保不越界
            if self.current_index >= len(self.api_configs):
                self.current_index = 0
                
            # 重新初始化当前API
            self.initialize_current_api()
            return self.ws_param
        return None
    
    def switch_to_next_api(self):
        """切换到下一个API配置"""
        if not self.api_configs:  # 如果没有可用的API配置
            logger.error("No available API configurations!")
            return None
            
        self.current_index = (self.current_index + 1) % len(self.api_configs)
        self.initialize_current_api()
        return self.ws_param
    
    def get_current_api(self):
        """获取当前API配置"""
        return self.ws_param

# 修改on_message函数，完全使用V2格式
def on_message(ws: websocket.WebSocketApp, message: str):
    global recognition_complete
    try:
        message_data = json.loads(message)
        print(f"DEBUG - 收到完整消息: {json.dumps(message_data, ensure_ascii=False)}")
        
        # V2格式：直接读取code字段
        code = message_data.get("code", 0)
        status = message_data.get("data", {}).get("status", 0)
        
        logger.info(f"收到消息，code={code}, status={status}")
        
        if code != 0:
            error_msg = message_data.get("message", "未知错误")
            logger.error(f"API错误 {code}: {error_msg}")
            
            if code == 10163:
                logger.error("参数验证错误！请确保：")
                logger.error("1. 使用V2数据格式（common/business/data）")
                logger.error("2. 不要包含V1字段（header/parameter/payload）")
                logger.error("3. 必须有data字段")
            
            ws.close()
            return
        
        # 处理识别结果（V2格式）
        data = message_data.get("data", {})
        result = data.get("result", {})
        
        if result and "ws" in result:
            text_ws = result["ws"]
            recognition_text = ""
            for ws_item in text_ws:
                for cw_item in ws_item["cw"]:
                    recognition_text += cw_item["w"]
            
            if recognition_text.strip():
                recognized_q.put(recognition_text.strip())
                logger.info(f"识别结果已放入队列: {recognition_text.strip()}")
        
        # 检查是否结束
        if status == 2:
            recognition_complete = True
            logger.info("识别完成")
            ws.close()
            
    except Exception as e:
        logger.exception(f"处理消息异常: {e}")
        
        
# 修改on_error函数
def on_error(ws: websocket.WebSocketApp, error: Exception):
    logger.error(f"### WebSocket错误: {error}")
    # 标记API错误
    ws.api_error = True
    # 发送错误标记
    # recognized_q.put("__ERROR__")

# 修改on_close函数
def on_close(ws: websocket.WebSocketApp, close_status_code: int, close_msg: str):
    logger.info("### Connection closed ###")
    logger.info(f"Close status code: {close_status_code}")
    logger.info(f"Close message: {close_msg}")
    # 如果还没发送结束标记，发送一个
    # recognized_q.put("__END__")


# 修改 on_open 函数中的数据格式
def on_open(ws: websocket.WebSocketApp):
    global websocket_connected
    logger.info("### Connection established ###")
    websocket_connected = True
    
    # 等待连接稳定
    time.sleep(0.5)
    
    def run(*args):
        global recognition_complete
        recognition_complete = False
        
        recorder = AudioRecorder()
        recorder.start_recording()
        
        logger.info("开始录制音频...")
        
        try:
            # ====== 发送开始帧（V2格式） ======
            start_frame = {
                "common": {
                    "app_id": ws.ws_param.APPID
                },
                "business": {
                    "domain": "iat",           # 必须
                    "language": "zh_cn",       # 必须
                    "accent": "mandarin",      # 必须
                    # 可选参数
                    "dwa": "wpgs",             # 动态修正
                    "pd": "ued",               # 产品
                    "nunum": 0,
                    "speex_size": 0,
                    "nbest": 5,
                    "wbest": 3
                },
                "data": {
                    "status": 0,               # 0=开始
                    "format": "audio/L16;rate=16000",  # 必须
                    "encoding": "raw",         # 必须
                    "audio": ""                # 开始帧为空
                }
            }
            
            logger.info("发送开始帧...")
            logger.debug(f"开始帧内容: {json.dumps(start_frame, ensure_ascii=False)}")
            ws.send(json.dumps(start_frame))
            logger.info("开始帧已发送")
            
            # 短暂等待
            time.sleep(0.1)
            
            # ====== 发送音频数据帧 ======
            frame_count = 0
            max_seconds = 10  # 最多录制10秒
            start_time = time.time()
            
            while time.time() - start_time < max_seconds:
                if not ws.sock or not ws.sock.connected:
                    logger.info("连接已断开")
                    break
                
                if recognition_complete:
                    logger.info("识别已完成，停止录音")
                    break
                
                # 读取音频
                audio_data = recorder.read_audio()
                if not audio_data:
                    logger.warning("读取音频数据失败")
                    break
                
                # 检查音频数据有效性
                if len(audio_data) < 100:
                    logger.warning(f"音频数据过短: {len(audio_data)} bytes")
                    continue
                
                # 编码为base64
                audio_base64 = str(base64.b64encode(audio_data), 'utf-8')
                
                # 中间帧（V2格式）
                data_frame = {
                    "common": {
                        "app_id": ws.ws_param.APPID
                    },
                    "business": {
                        "domain": "iat",
                        "language": "zh_cn",
                        "accent": "mandarin"
                    },
                    "data": {
                        "status": 1,               # 1=中间帧
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": audio_base64      # 音频数据
                    }
                }
                
                try:
                    ws.send(json.dumps(data_frame))
                    frame_count += 1
                    
                    if frame_count == 1:
                        logger.info("发送第一帧音频数据")
                    elif frame_count % 50 == 0:
                        logger.debug(f"已发送{frame_count}帧音频数据")
                        
                except Exception as e:
                    logger.error(f"发送音频帧失败: {e}")
                    break
                
                # 控制发送速率
                time.sleep(0.04)  # 约25帧/秒
            
            # ====== 发送结束帧 ======
            logger.info(f"音频发送完成，共发送{frame_count}帧，发送结束帧")
            
            end_frame = {
                "common": {
                    "app_id": ws.ws_param.APPID
                },
                "business": {
                    "domain": "iat",
                    "language": "zh_cn",
                    "accent": "mandarin"
                },
                "data": {
                    "status": 2,               # 2=结束
                    "format": "audio/L16;rate=16000",
                    "encoding": "raw",
                    "audio": ""                # 结束帧为空
                }
            }
            
            try:
                ws.send(json.dumps(end_frame))
                logger.info("结束帧已发送")
                
                # 等待服务器返回最终结果
                logger.info("等待最终识别结果...")
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"发送结束帧失败: {e}")
            
            recognition_complete = True
            
        except Exception as e:
            logger.exception(f"录音线程错误: {e}")
        finally:
            recorder.stop_recording()
            logger.info("录音结束")
            # 确保发送结束标记
            # recognized_q.put("__END__")
    
    # 启动录音线程
    run_thread = threading.Thread(target=run, args=(), daemon=True)
    run_thread.start()

api_manager = ApiManager(config.XF_API_CONFIGS)

def check_ws_connection(mainwindow):
    global websocket_connected
    if websocket_connected:
        mainwindow.set_overlay_text("正在聆听···")
    else:
        mainwindow.set_overlay_text("等我打开耳朵")