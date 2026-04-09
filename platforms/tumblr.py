import os
import time
import logging
import re
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

    def _normalize_tags(self, raw_tags) -> str:
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        elif not isinstance(raw_tags, list):
            raw_tags = []

        cleaned_tags = []
        seen = set()

        for raw_tag in raw_tags:
            text = str(raw_tag).strip()
            if not text:
                continue

            parts = re.split(r"[\s,]+", text)
            for part in parts:
                normalized = part.strip().lstrip("#").strip(".,!?:;()[]{}\"'")
                if not normalized:
                    continue
                if len(normalized) <= 1:
                    continue
                if normalized.lower() in seen:
                    continue
                seen.add(normalized.lower())
                cleaned_tags.append(normalized)

        tag_string = ",".join(cleaned_tags)
        self.logger.info(f"   Tumblr tags prepared: {tag_string or 'none'}")
        return tag_string

    def _extract_inline_tags(self, text: str) -> Tuple[str, str]:
        matches = re.findall(r"#([A-Za-z0-9_]+)", text)
        cleaned_text = re.sub(r"\s*#([A-Za-z0-9_]+)", "", text).strip()
        return cleaned_text or text.strip(), self._normalize_tags(matches)

    def _extract_data(self, caption_data: Union[str, dict]) -> Tuple[str, str]:
        if isinstance(caption_data, dict):
            text = str(caption_data.get("text", "")).strip()
            ai_tags = caption_data.get("tags", [])
            brand_tag = caption_data.get("brand_tag", "")

            inline_text, inline_tags = self._extract_inline_tags(text)
            merged_tags = ai_tags if isinstance(ai_tags, list) else [ai_tags]
            if inline_tags:
                merged_tags.extend(inline_tags.split(","))
            if brand_tag:
                merged_tags.append(brand_tag)

            return inline_text or "New Post", self._normalize_tags(merged_tags)

        text = str(caption_data).strip()
        clean_text, tag_string = self._extract_inline_tags(text)
        return clean_text, tag_string

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
        body_text, tag_str = self._extract_data(text)
        response = self.client.create_text(
            self.blog_name,
            state="published",
            body=body_text,
            tags=tag_str,
        )
        return self._poll_post(response.get("id"))
