import os
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class TelegramPoster:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.token = os.getenv("TELEGRAM_POST_BOT_TOKEN") 
        self.chat_id = os.getenv("TELEGRAM_POST_CHAT_ID")

        if not self.token or not self.chat_id:
            raise ValueError("Missing Telegram Credentials")

        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    # --- MUST BE INDENTED UNDER CLASS ---
    def post_video(self, file_path, caption):
        url = f"{self.base_url}/sendVideo"
        if not os.path.exists(file_path):
            self.logger.error(f"❌ File not found: {file_path}")
            return False

        with open(file_path, 'rb') as f:
            data = {'chat_id': str(self.chat_id), 'caption': caption}
            try:
                res = self.session.post(url, data=data, files={'video': f}, timeout=60)
                return self._check_response(res)
            except Exception as e:
                self.logger.error(f"   ❌ Telegram Video Error: {e}")
                return False

    def post_image(self, file_path, caption):
        url = f"{self.base_url}/sendPhoto"
        if not os.path.exists(file_path):
            self.logger.error(f"❌ File not found: {file_path}")
            return False

        with open(file_path, 'rb') as f:
            data = {'chat_id': str(self.chat_id), 'caption': caption}
            try:
                res = self.session.post(url, data=data, files={'photo': f}, timeout=60)
                return self._check_response(res)
            except Exception as e:
                self.logger.error(f"   ❌ Telegram Image Error: {e}")
                return False

    def _check_response(self, res):
        if res.status_code != 200:
            self.logger.error(f"Telegram API Error: {res.text}")
            return False
        self.logger.info("   ✅ Telegram Content Posted")
        return True
    def send_message(self, text):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": str(self.chat_id),
            "text": str(text)[:4000]
        }
        try:
            res = self.session.post(url, data=payload, timeout=30)
            if res.status_code != 200:
                self.logger.error(f"Telegram send_message API Error: {res.text}")
                return False
            self.logger.info("   Telegram Summary Sent")
            return True
        except Exception as e:
            self.logger.error(f"Telegram send_message Error: {e}")
            return False

    def post_text(self, text):
        return self.send_message(text)
