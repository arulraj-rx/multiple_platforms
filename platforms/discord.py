import os
import requests
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class DiscordPoster:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        self.token = os.getenv("DISCORD_BOT_TOKEN")
        self.channel_id = os.getenv("DISCORD_CHANNEL_ID")
        
        if not self.token or not self.channel_id:
            raise ValueError("Missing Discord Credentials")

        self.base_url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"

        # Robust Session
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        
        self.session.headers.update({
            "Authorization": f"Bot {self.token}",
            "User-Agent": "DiscordBot (SocialAuto, 1.0)"
        })

    def post_image(self, file_path, caption):
        if not os.path.exists(file_path):
            self.logger.error(f"❌ File not found: {file_path}")
            return False

        # 1. Check File Size and Warn User
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        self.logger.info(f"   📂 File Size: {file_size_mb:.2f} MB")
        
        if file_size_mb > 8:
            self.logger.warning("   ⚠️ WARNING: File > 8MB. Upload might fail without Nitro.")

        safe_caption = caption[:2000]
        payload = {"content": safe_caption}
        
        try:
            with open(file_path, 'rb') as f:
                files = {
                    "file": (os.path.basename(file_path), f, "application/octet-stream")
                }
                
                # 2. PRINT DEBUG MSG BEFORE UPLOAD
                self.logger.info("   ⏳ Connecting to Discord... (This may take 30-60s)")
                
                # 3. PERFORM UPLOAD
                response = self.session.post(self.base_url, data=payload, files=files, timeout=60)

                # 4. PRINT DEBUG MSG AFTER UPLOAD
                self.logger.info(f"   📩 Response Code: {response.status_code}")

                if response.status_code == 429:
                    self.logger.warning("   ⚠️ Rate Limited! Waiting safely...")
                    time.sleep(int(response.json().get('retry_after', 5)) + 1)
                    response = self.session.post(self.base_url, data=payload, files=files, timeout=60)

                if response.status_code in [200, 201]:
                    self.logger.info("   ✅ Discord Upload Complete!")
                    return True
                elif response.status_code == 404:
                    raise Exception("Invalid Channel ID (404)")
                elif response.status_code == 401:
                    raise Exception("Invalid Bot Token (401)")
                elif response.status_code == 413:
                    raise Exception("File Too Large (413)")
                else:
                    raise Exception(f"Discord API Error: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            self.logger.error("   ❌ Timeout: Your internet is too slow for this file size.")
            raise Exception("Connection Timed Out")
        except Exception as e:
            self.logger.error(f"   ❌ Connection Error: {e}")
            raise e

    def post_video(self, file_path, caption):
        # Discord treats video files exactly like images (attachments)
        self.logger.info("   ⏳ Discord: Uploading Video...")
        return self.post_image(file_path, caption)

    def post_text(self, text):
        payload = {"content": str(text)[:2000]}

        try:
            response = self.session.post(self.base_url, json=payload, timeout=30)
            self.logger.info(f"   Response Code: {response.status_code}")

            if response.status_code in [200, 201]:
                self.logger.info("   Discord text post complete")
                return True
            if response.status_code == 404:
                raise Exception("Invalid Channel ID (404)")
            if response.status_code == 401:
                raise Exception("Invalid Bot Token (401)")

            raise Exception(f"Discord API Error: {response.status_code} - {response.text}")
        except Exception as e:
            self.logger.error(f"   Discord text error: {e}")
            raise e
