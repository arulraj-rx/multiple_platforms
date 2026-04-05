import os
import logging
import pytumblr
from typing import Tuple, List, Union


class TumblrPoster:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.blog_name = os.getenv("TUMBLR_BLOG_NAME")

        self.client = pytumblr.TumblrRestClient(
            os.getenv("TUMBLR_CONSUMER_KEY"),
            os.getenv("TUMBLR_CONSUMER_SECRET"),
            os.getenv("TUMBLR_OAUTH_TOKEN"),
            os.getenv("TUMBLR_OAUTH_TOKEN_SECRET"),
        )

    # 🔥 Central Clean Logic
    

    def _extract_data(self, caption_data: Union[str, dict]) -> Tuple[str, list]:
        if isinstance(caption_data, dict):
            text = str(caption_data.get("text", "")).strip()
            ai_tags = caption_data.get("tags", [])
            brand_tag = caption_data.get("brand_tag", "")

            # Ensure list
            if not isinstance(ai_tags, list):
                ai_tags = []

            # Remove # and clean
            cleaned_tags = []
            for tag in ai_tags:
                
                if tag:
                    cleaned_tags.append(tag)

            # Add brand tag
            if brand_tag:
                cleaned_tags.append(str(brand_tag).replace("#", "").strip())

            return text or "New Post", cleaned_tags

        return str(caption_data), []

    def post_image(self, file_path: str, caption_data: Union[str, dict]) -> bool:
        text, tag_str = self._extract_data(caption_data)

        try:
            response = self.client.create_photo(
                self.blog_name,
                state="published",
                caption=text,
                tags=tag_str,
                data=[file_path],
            )
            return "id" in response
        except Exception as e:
            self.logger.error(f"Tumblr Photo Error: {e}")
            return False

    def post_video(self, file_path: str, caption_data: Union[str, dict]) -> bool:
        text, tag_str = self._extract_data(caption_data)

        try:
            response = self.client.create_video(
                self.blog_name,
                state="published",
                caption=text[:200],  # metadata safe
                tags=tag_str,
                data=file_path,  # correct for video
            )
            return "id" in response
        except Exception as e:
            self.logger.error(f"Tumblr Video Error: {e}")
            return False

    def post_text(self, text: str) -> bool:
        try:
            response = self.client.create_text(
                self.blog_name,
                state="published",
                body=text,
            )
            return "id" in response
        except Exception as e:
            self.logger.error(f"Tumblr Text Error: {e}")
            return False
