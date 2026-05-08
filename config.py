# config.py
import os
import sys
from set_logger import setup_logging


LLM_SYSTEM_PROMPT = """【身份信息】
                        你是黄河非遗问答小助手，你的本体是黄河的一位锦鲤，
                        你的名字是三三，你的任务有三个，
                        1.传播和弘扬黄河流域非遗；
                        2.解答与黄河相关的问题；
                        3.宣传黄河保护；
                        对于非遗知识，你需要以故事的形式进行讲述。
                        注意：绝对不要输出某些表情或者动作符号，比如[微笑]、(笑哭)、*害羞*等，同时过滤掉非正常标点符号"""

def resource_path(relative_path : str) -> str: 
    """获取资源文件的绝对路径"""
    try:
        # 首先尝试获取 PyInstaller 的临时路径
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
            logger.info(f"Using PyInstaller temporary path: {base_path}")
        else:
            # 如果不是打包环境，使用当前目录
            base_path = os.path.dirname(os.path.abspath(__file__))
            # print(f"使用当前目录作为基础路径: {base_path}")
    except Exception as e:
        # 如果出现任何异常，使用当前目录
        base_path = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Use current directory as base path: {base_path}")
        logger.exception(f"Exception: {str(e)}")
    
    full_path = os.path.join(base_path, relative_path)
    if not os.path.exists(full_path):
        logger.warning(f"Warning: File does not exist: {full_path}")
        # 尝试在当前目录下查找
        current_dir_path = os.path.join(os.getcwd(), relative_path)
        if os.path.exists(current_dir_path):
            logger.info(f"File found in current directory: {current_dir_path}")
            return current_dir_path
    return full_path


logger = setup_logging()
# 基础路径
BASE_PATH = os.path.abspath(".")

# 模型相关路径
# VOSK_MODEL_PATH = resource_path("models/vosk-model-cn-0.22")
#     # print(f"VOSK_MODEL_PATH: {VOSK_MODEL_PATH}")
# EMBEDDING_MODEL_PATH = resource_path("models/embedding/BAAI/bge-large-zh-v1___5")

# 本地模型名称
LOCAL_MODEL = "llama3.2"

MODEL = "C:/Users/dwz/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/snapshots/e8f8c211226b894fcb81acc59f3b34ba3efd5f42/"
INDEX_PATH = "db/non_heritage.faiss"
DB_PATH = "db/heritage.db"
L_DB_PATH = 'db/long_term_memory.db'
TABLE_NAME = "heritage"
KEY_PATH = "data/KeyWord.json"
JSONL_PATH = "data/heritage_source.jsonl"

AUDIO_PATH = "./audio/my_audio.wav"

# 讯飞语音识别API配置列表
# 每个配置项包含APPID、APIKey和APISecret
XF_API_CONFIGS = [
    {
        "APPID": "29348254",
        "APIKey": "af5cf07e99f12fe610967aedfdf2d74d",
        "APISecret": "NWE4NzE3ODU5M2Y0OTdmZDBjNjk1YzE5"
    },
    {
        "APPID": "2f730ad3",
        "APIKey": "5d6076cdb8adfd96dc8ae481f07ce682",
        "APISecret": "Yjk1NjQzYjU4ZDczN2U1MjNjMDFlMmNm"
    },
    # 备用API配置1
    {
        "APPID": "3941158",
        "APIKey": "6a8b89a798df21ba598b0c225da49484",
        "APISecret": "M2M5YTFlNmRlYTZhMWRiM2YwZTBmNDRh"
    },
    # 备用API配置2
    {
        "APPID": " 2ddf381b",
        "APIKey": "ac150afaf51742aa2daf2e0b5612ae4b",
        "APISecret": "OTYyMDU4NDA5NGZlN2QyMzFlNGRiOTBi"
    }
]

# logging.config.fileConfig('logger.ini')
# logger = logging.getLogger('appLogger')
