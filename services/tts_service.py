import asyncio
import time
import tempfile
import os
import pygame
import edge_tts
import config
from config import logger
import pyttsx3

class TTSService:
    def __init__(self):
        self._pygame_inited = False
        self.engine = self.initialize_engine()
        self.last_sid = None
        self.start_time = None

    def _ensure_pygame(self):
        if not self._pygame_inited:
            pygame.mixer.init()
            self._pygame_inited = True

    def _stop_now(self):
        # 立刻停止当前播放
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except:
            pass

    async def speak(self, text: str, sid: int, get_session_id):
        start_time = time.time()
        output_path = None
        
        if self.last_sid != sid:
            if self.start_time is not None:
                elapsed = time.time() - self.start_time
                logger.info(f"[TTS] 任务 {self.last_sid} 总响应时间：{elapsed:.3f}s")
            self.start_time = time.time()
            self.last_sid = sid

        if sid != get_session_id():
            return "interrupted"

        try:
            logger.info(f"[TTS] start sid={sid}, text={text[:30]}...")

            # 开始合成语音
            start_time = time.time()
            

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                output_path = tmp.name

            communicate = edge_tts.Communicate(text, "zh-CN-YunxiaNeural")
            save_task = asyncio.create_task(communicate.save(output_path))

            while not save_task.done():
                if sid != get_session_id():
                    save_task.cancel()
                    try:
                        await save_task
                    except:
                        pass
                    logger.info(f"[TTS] canceled during synth sid={sid}")
                    return "interrupted"
                await asyncio.sleep(0.05)

            if sid != get_session_id():
                logger.info(f"[TTS] outdated after synth sid={sid}")
                return "interrupted"

            self._ensure_pygame()

            logger.info(f"[TTS] synth time: {time.time() - start_time:.2f}s, play...")

            self._stop_now()

            pygame.mixer.music.load(output_path)
            logger.info("[TTS-Tone] 首字开始播放时间：%lf", time.time() - start_time)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                if sid != get_session_id():
                    logger.info(f"[TTS] interrupted sid={sid}")
                    self._stop_now()
                    return "interrupted"
                await asyncio.sleep(0.05)

            logger.info("[TTS] play completed")
            return "done"

        except asyncio.CancelledError:
            self._stop_now()
            return "interrupted"
        except Exception as e:
            logger.exception(f"[TTS] error sid={sid}: {e}")
            self._stop_now()
            return "error"
        finally:
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
    
    # 状态语音
    # def choose(self, response : bool, state : str):
    #     if response:
    #         pygame.mixer.init()
    #         if state=='hello':
    #             # 加载音频文件 (支持 .wav, .mp3, .ogg 等)
    #             pygame.mixer.music.load(config.AUDIO_HELLO_PATH)
    #         elif state == 'interupt':
    #             # 加载音频文件 (支持 .wav, .mp3, .ogg 等)
    #             pygame.mixer.music.load(config.AUDIO_INTERUPT_PATH)
    #         elif state == 'no_speak':
    #             pygame.mixer.music.load(config.AUDIO_NO_SPEAK_PATH)
    #         elif state == 'brain_short':
    #             pygame.mixer.music.load(config.AUDIO_BRAIN_SHORT_PATH)
    #         elif state == 'thinking':
    #             pygame.mixer.music.load(config.AUDIO_THINKING_PATH)
    #         else:
    #             # 加载音频文件 (支持 .wav, .mp3, .ogg 等)
    #             pygame.mixer.music.load(config.AUDIO_GOODBYE_PATH)
    #         # 播放音频
    #         pygame.mixer.music.play()
    #         # 等待播放完毕
    #         while pygame.mixer.music.get_busy():
    #             pygame.time.Clock().tick(10)
    #     else:
    #         if state == 'hello':
    #             self.speaking('你好, 你有什么问题呢？')
    #         elif state == 'interupt':
    #             self.speaking('已打断')
    #         elif state == 'no_speak':
    #             self.speaking('当前我没有说话')
    #         elif state == 'brain_short':
    #             self.speaking('不好意思，刚刚大脑短路了,请你再问一遍吧')
    #         elif state == 'thinking':
    #             self.speaking('让我转动我的脑子思考一下')
    #         else:
    #             self.speaking('再见，欢迎您下次光临。')

    # 初始化引擎
    def initialize_engine(self):
        logger.info("Initialize engine is starting")
        try:
            engine = pyttsx3.init()
            if not engine:
                logger.warning("Failed to initialize engine")
                return None
                
            logger.info("Initialize engine successfully")
            
            # 设置语速
            engine.setProperty('rate', 200)
            logger.info(f"Set rate: 200")
            
            # 获取可用的语音列表
            voices = engine.getProperty('voices')
            logger.info(f"Available voices: {len(voices)}")
            
            # 中文语音适配
            chinese_voice_found = False
            for voice in voices:
                logger.info(f"Check voice: {voice.id}")
                if 'ZH' in voice.id.upper():
                    engine.setProperty('voice', voice.id)
                    logger.info(f"Set Chinese voice: {voice.id}")
                    chinese_voice_found = True
                    break
                    
            if not chinese_voice_found:
                logger.warning("Warning: Chinese voice not found, using default voice")
                
            return engine
            
        except Exception as e:
            logger.exception(f"Initialize engine error: {e}")
            return None

    # 非联网状态下的语音播报
    def speaking(self, text: str, sid=None, get_session_id=None):
        # 如果会话已经过期，直接不播
        if sid is not None and get_session_id is not None:
            if sid != get_session_id():
                logger.info(f"[TTS-FALLBACK] interrupted before speak sid={sid}")
                return

        # 引擎不存在就重建
        if self.engine is None:
            logger.warning("[TTS-FALLBACK] engine is None, reinitializing...")
            self.engine = self.initialize_engine()
            if self.engine is None:
                logger.error("[TTS-FALLBACK] failed to initialize engine")
                return

        try:
            logger.info(f"[朗读] {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.exception(f"Speak error: {e}")
            try:
                self.engine.stop()
            except Exception:
                pass
            self.engine = None
                
        
