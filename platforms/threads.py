import os
import requests
import time
import logging

class ThreadsPoster:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user_id = os.getenv("THREADS_USER_ID")
        self.token = os.getenv("THREADS_ACCESS_TOKEN")
        self.base_url = f"https://graph.threads.net/v1.0/{self.user_id}"

    def post_image(self, image_url, caption):
        return self._create_publish_container(image_url, caption, "IMAGE")

    def post_video(self, video_url, caption):
        return self._create_publish_container(video_url, caption, "VIDEO")

    def post_text(self, text):
        return self._create_text_post(text)

    def _create_publish_container(self, media_url, caption, media_type):
        # 1. Start Upload
        url = f"{self.base_url}/threads"
        payload = {
            "access_token": self.token,
            "text": caption,
            "media_type": media_type,
            "image_url" if media_type == "IMAGE" else "video_url": media_url
        }
        
        res = requests.post(url, data=payload, timeout=60)
        if res.status_code != 200:
            raise Exception(f"Threads Init Failed: {res.text}")
            
        container_id = res.json()['id']

        # 2. MANDATORY POLLING LOOP
        # Larger videos need more time to transcode.
        self.logger.info(f"   ⏳ Threads: Waiting for {media_type} to process...")
        
        status = "IN_PROGRESS"
        attempts = 0
        while status != "FINISHED" and attempts < 60:
            time.sleep(5)
            attempts += 1
            
            # Check Status
            check_url = f"https://graph.threads.net/v1.0/{container_id}"
            check_res = requests.get(check_url, params={
                "fields": "status,error_message",
                "access_token": self.token
            })
            
            data = check_res.json()
            status = data.get("status", "ERROR")
            self.logger.info(f"      - Processing Status: {status} (Attempt {attempts})")
            
            if status == "ERROR":
                raise Exception(f"Threads Processing Error: {data.get('error_message')}")

        if status != "FINISHED":
            raise Exception("Threads upload timed out after 5 minutes.")

        # 3. Final Publish
        pub_url = f"{self.base_url}/threads_publish"
        pub_res = requests.post(pub_url, data={
            "creation_id": container_id,
            "access_token": self.token
        })
        
        if pub_res.status_code == 200:
            self.logger.info("   ✅ Threads Published Successfully!")
            return True
        else:
            raise Exception(f"Threads Publish Failed: {pub_res.text}")

    def _create_text_post(self, text):
        url = f"{self.base_url}/threads"
        payload = {
            "access_token": self.token,
            "media_type": "TEXT",
            "text": text
        }

        res = requests.post(url, data=payload, timeout=60)
        if res.status_code != 200:
            raise Exception(f"Threads Text Init Failed: {res.text}")

        container_id = res.json()["id"]
        pub_url = f"{self.base_url}/threads_publish"
        pub_res = requests.post(pub_url, data={
            "creation_id": container_id,
            "access_token": self.token
        })

        if pub_res.status_code == 200:
            self.logger.info("   Threads text published successfully")
            return True

        raise Exception(f"Threads Text Publish Failed: {pub_res.text}")
