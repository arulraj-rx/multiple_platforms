import os
import time
import logging
import pytumblr
from typing import Tuple, Union


class TumblrPoster:
    def __init__(self, settings=None):
        settings = settings or {}
        self.logger = logging.getLogger(__name__)
        self.blog_name = os.getenv("TUMBLR_BLOG_NAME")
        self.poll_interval = settings.get("poll_interval", 20)
        self.poll_attempts = settings.get("poll_attempts", 3)

        self.client = pytumblr.TumblrRestClient(
            os.getenv("TUMBLR_CONSUMER_KEY"),
            os.getenv("TUMBLR_CONSUMER_SECRET"),
            os.getenv("TUMBLR_OAUTH_TOKEN"),
            os.getenv("TUMBLR_OAUTH_TOKEN_SECRET"),
        )

    def _extract_data(self, caption_data: Union[str, dict]) -> Tuple[str, list]:
        if isinstance(caption_data, dict):
            text = str(caption_data.get("text", "")).strip()
            ai_tags = caption_data.get("tags", [])
            brand_tag = caption_data.get("brand_tag", "")

            if not isinstance(ai_tags, list):
                ai_tags = []

            cleaned_tags = [tag for tag in ai_tags if tag]
            if brand_tag:
                cleaned_tags.append(str(brand_tag).replace("#", "").strip())

            return text or "New Post", cleaned_tags

        return str(caption_data), []

    def _poll_post(self, post_id):
        if not post_id:
            return False

        for attempt in range(1, self.poll_attempts + 1):
            response = self.client.posts(self.blog_name, id=post_id)
            posts = response.get("posts", [])
            if any(str(post.get("id")) == str(post_id) for post in posts):
                self.logger.info(f"   Tumblr publish confirmed on poll attempt {attempt}")
                return True

            self.logger.warning(f"   Tumblr poll attempt {attempt}/{self.poll_attempts} pending")
            if attempt < self.poll_attempts:
                time.sleep(self.poll_interval)

        return False

    def post_image(self, file_path: str, caption_data: Union[str, dict]) -> bool:
        text, tag_str = self._extract_data(caption_data)
        response = self.client.create_photo(
            self.blog_name,
            state="published",
            caption=text,
            tags=tag_str,
            data=[file_path],
        )
        return self._poll_post(response.get("id"))

    def post_video(self, file_path: str, caption_data: Union[str, dict]) -> bool:
        text, tag_str = self._extract_data(caption_data)
        response = self.client.create_video(
            self.blog_name,
            state="published",
            caption=text[:200],
            tags=tag_str,
            data=file_path,
        )
        return self._poll_post(response.get("id"))

    def post_text(self, text: str) -> bool:
        response = self.client.create_text(
            self.blog_name,
            state="published",
            body=text,
        )
        return self._poll_post(response.get("id"))
