import os
import requests
import logging
import time

class FacebookPoster:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.page_id = os.getenv("FB_PAGE_ID")
        self.token = os.getenv("META_TOKEN")
        self.base_url = f"https://graph.facebook.com/v18.0/{self.page_id}"

    def post_video(self, file_path, caption):
        url = f"{self.base_url}/videos"
        data = {
            "access_token": self.token,
            "description": caption
        }
        
        if not os.path.exists(file_path):
             self.logger.error(f"❌ File not found: {file_path}")
             return False

        # 1. Log File Size
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        self.logger.info(f"   📂 File Size: {size_mb:.2f} MB")
        
        self.logger.info("   ⏳ FB: Uploading Video... (Timeout: 120s)")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'source': f}
                # Added timeout to prevent freezing
                res = requests.post(url, data=data, files=files, timeout=120)
            
            self.logger.info(f"   📩 Response Code: {res.status_code}")

            if res.status_code != 200:
                raise requests.HTTPError(f"FB Upload Failed: {res.text}", response=res)
            
            self.logger.info(f"   ✅ FB Video Published ID: {res.json().get('id')}")
            return True
            
        except requests.exceptions.Timeout:
            self.logger.error("   ❌ FB Timeout: Video too large for current speed.")
            return False
        except Exception as e:
            self.logger.error(f"   ❌ FB Error: {e}")
            raise e

    def post_image(self, file_path, caption):
        url = f"{self.base_url}/photos"
        data = {
            "access_token": self.token,
            "message": caption
        }
        
        if not os.path.exists(file_path):
             self.logger.error(f"❌ File not found: {file_path}")
             return False

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        self.logger.info(f"   📂 File Size: {size_mb:.2f} MB")
        
        self.logger.info("   ⏳ FB: Uploading Image... (Timeout: 60s)")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'source': f}
                res = requests.post(url, data=data, files=files, timeout=60)
                
            self.logger.info(f"   📩 Response Code: {res.status_code}")
            
            if res.status_code != 200:
                raise requests.HTTPError(f"FB Photo Failed: {res.text}", response=res)
                
            self.logger.info(f"   ✅ FB Photo Published ID: {res.json().get('post_id')}")
            return True
        except Exception as e:
            self.logger.error(f"   ❌ FB Error: {e}")
            raise e

    def post_text(self, text):
        url = f"{self.base_url}/feed"
        data = {
            "access_token": self.token,
            "message": text
        }

        try:
            res = requests.post(url, data=data, timeout=60)
            self.logger.info(f"   Response Code: {res.status_code}")

            if res.status_code != 200:
                raise requests.HTTPError(f"FB Text Post Failed: {res.text}", response=res)

            self.logger.info(f"   FB Text Published ID: {res.json().get('id')}")
            return True
        except Exception as e:
            self.logger.error(f"   FB Text Error: {e}")
            raise e
