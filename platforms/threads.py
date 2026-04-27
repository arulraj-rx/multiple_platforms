import os
import time
import logging
import requests


class ThreadsPoster:
    def __init__(self, settings=None):
        settings = settings or {}
        self.logger = logging.getLogger(__name__)
        self.user_id = os.getenv("THREADS_USER_ID")
        self.token = os.getenv("THREADS_ACCESS_TOKEN")
        self.base_url = "https://graph.threads.net/v1.0/me"
        self.poll_interval = settings.get("poll_interval", 20)
        self.poll_attempts = settings.get("poll_attempts", 3)
        self.publish_poll_attempts = settings.get("threads_publish_poll_attempts", self.poll_attempts)
        self.processing_poll_attempts = settings.get("threads_processing_poll_attempts", max(self.poll_attempts, 6))

    def post_image(self, image_url, caption):
        return self._create_publish_container(image_url, caption, "IMAGE")

    def post_video(self, video_url, caption):
        return self._create_publish_container(video_url, caption, "VIDEO")

    def post_text(self, text):
        return self._create_text_post(text)

    def _poll_thread(self, thread_id):
        if not thread_id:
            return False

        url = f"https://graph.threads.net/v1.0/{thread_id}"
        params = {
            "fields": "id",
            "access_token": self.token,
        }

        for attempt in range(1, self.publish_poll_attempts + 1):
            res = requests.get(url, params=params, timeout=30)
            if res.status_code == 200 and res.json().get("id"):
                self.logger.info(f"   Threads publish confirmed on poll attempt {attempt}")
                return True

            self.logger.warning(
                f"   Threads poll attempt {attempt}/{self.publish_poll_attempts} pending"
            )
            if attempt < self.publish_poll_attempts:
                time.sleep(self.poll_interval)

        return False

    def _wait_for_container(self, container_id):
        check_url = f"https://graph.threads.net/v1.0/{container_id}"

        for attempt in range(1, self.processing_poll_attempts + 1):
            time.sleep(self.poll_interval)
            check_res = requests.get(check_url, params={
                "fields": "status,error_message",
                "access_token": self.token,
            }, timeout=30)

            if check_res.status_code != 200:
                raise requests.HTTPError(
                    f"Threads Status Check Failed: {check_res.text}",
                    response=check_res,
                )

            data = check_res.json()
            status = data.get("status", "ERROR")
            self.logger.info(f"   Threads processing status: {status} (attempt {attempt})")

            if status == "FINISHED":
                return True
            if status == "ERROR":
                details = data.get("error_message") or "UNKNOWN"
                raise Exception(f"Threads Processing Error: {details}")
            if status == "PUBLISHED":
                return True
            if status not in {"IN_PROGRESS"}:
                self.logger.warning(f"   Threads returned unexpected container status: {status}")

        return False

    def _publish_container(self, container_id):
        pub_url = f"{self.base_url}/threads_publish"
        pub_res = requests.post(pub_url, data={
            "creation_id": container_id,
            "access_token": self.token,
        }, timeout=60)

        if pub_res.status_code != 200:
            raise requests.HTTPError(f"Threads Publish Failed: {pub_res.text}", response=pub_res)

        thread_id = pub_res.json().get("id")
        return self._poll_thread(thread_id)

    def _create_publish_container(self, media_url, caption, media_type):
        url = f"{self.base_url}/threads"
        payload = {
            "access_token": self.token,
            "text": caption,
            "media_type": media_type,
            "image_url" if media_type == "IMAGE" else "video_url": media_url,
        }

        res = requests.post(url, data=payload, timeout=60)
        if res.status_code != 200:
            raise requests.HTTPError(f"Threads Init Failed: {res.text}", response=res)

        container_id = res.json().get("id")
        if not self._wait_for_container(container_id):
            return False

        return self._publish_container(container_id)

    def _create_text_post(self, text):
        url = f"{self.base_url}/threads"
        payload = {
            "access_token": self.token,
            "media_type": "TEXT",
            "text": text,
        }

        res = requests.post(url, data=payload, timeout=60)
        if res.status_code != 200:
            raise requests.HTTPError(f"Threads Text Init Failed: {res.text}", response=res)

        return self._publish_container(res.json().get("id"))
