import os
import logging
import requests

class TelegramLogHandler(logging.Handler):
    """Sends logs to Telegram Admin Chat"""
    def __init__(self):
        super().__init__()
        self.token = os.getenv("TELEGRAM_LOG_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_LOG_CHAT_ID")
        
    def emit(self, record):
        log_entry = self.format(record)
        # Only send Important Info or Errors (don't spam debugs)
        if record.levelno >= logging.INFO:
            self.send_message(log_entry)

    def send_message(self, text):
        if not self.token or not self.chat_id:
            return
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            # Simple synchronous request
            requests.post(url, data={
                "chat_id": self.chat_id, 
                "text": text[:4000] # Telegram limit
            })
        except:
            pass # Never crash the app just because logging failed

def setup_logging():
    logger = logging.getLogger("SocialAuto")
    logger.setLevel(logging.INFO)
    
    # 1. Console Handler (Prints to screen)
    c_handler = logging.StreamHandler()
    c_format = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
    c_handler.setFormatter(c_format)
    logger.addHandler(c_handler)
    
    # 2. Telegram Log Handler (Sends to your DM)
    # Check if user enabled it in env
    if os.getenv("TELEGRAM_LOG_BOT_TOKEN"):
        t_handler = TelegramLogHandler()
        t_format = logging.Formatter('🤖 [%(levelname)s] %(message)s')
        t_handler.setFormatter(t_format)
        logger.addHandler(t_handler)
        
    return logger