PYTHON_PROJECT/
├── main.py
├── config.py
├── logger.ini
├── set_logger.py
│
├── core/
│   ├── app_controller.py
│   ├── queue_manager.py
│   ├── session_manager.py
│   ├── state_manager.py
│   └── history_manager.py
│
├── services/
│   ├── llm_service.py
│   ├── asr_service.py
│   ├── tts_service.py
│   ├── unity_service.py
│   ├── rag_service.py
│   ├── memory_service.py
│   └── safety_service.py
│
├── workers/
│   ├── asr_worker.py
│   ├── llm_worker.py
│   ├── ui_worker.py
│   ├── tts_worker.py
│   └── dispatcher.py
│
├── utils/
│   ├── text_utils.py
│   ├── file_utils.py
│   ├── time_utils.py
│   └── log_utils.py
│
├── data/
│   ├── audio/
│   ├── logs/
│   ├── history/
│   └── cache/
│
└── tests/
    ├── test_voice.py
    ├── test_whisper.py
    ├── test_tts.py
    └── test_pipeline.py