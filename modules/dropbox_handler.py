import logging
import os
import random

import dropbox
from dropbox.exceptions import ApiError


class DropboxHandler:
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
    TEXT_EXTENSIONS = {".txt"}

    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.conf = config
        self.client = None

    # ✅ Dropbox client
    def _get_client(self):
        if self.client is None:
            self.client = dropbox.Dropbox(
                app_key=os.getenv("DROPBOX_APP_KEY"),
                app_secret=os.getenv("DROPBOX_APP_SECRET"),
                oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
                timeout=30,
            )
            self.logger.info("Dropbox client initialized")
        return self.client

    # ✅ Detect file type
    def detect_media_type(self, filename):
        ext = os.path.splitext(filename)[1].lower()

        if ext in self.IMAGE_EXTENSIONS:
            return "image"
        elif ext in self.VIDEO_EXTENSIONS:
            return "video"
        elif ext in self.TEXT_EXTENSIONS:
            return "text"

        return None

    # ✅ MAIN: weighted selection
    def get_file(self):
        path = self.conf.get("folder")
        if not path:
            self.logger.warning("No folder path configured")
            return None

        files = self._list_files(path)

        images = []
        videos = []
        texts = []

        # classify files
        for entry in files:
            media_type = self.detect_media_type(entry.name)

            if media_type == "image":
                images.append(entry)
            elif media_type == "video":
                videos.append(entry)
            elif media_type == "text":
                texts.append(entry)

        if not images and not videos and not texts:
            self.logger.warning("No valid media/text files found")
            return None

        # 🎯 CHANGE WEIGHTS HERE anytime
        types = ["image", "video", "text"]
        weights = [41, 39, 20]

        selected_type = random.choices(types, weights=weights)[0]

        if selected_type == "image" and images:
            selected = random.choice(images)
        elif selected_type == "video" and videos:
            selected = random.choice(videos)
        elif selected_type == "text" and texts:
            selected = random.choice(texts)
        else:
            # fallback if chosen type empty
            selected = random.choice(images or videos or texts)
            selected_type = self.detect_media_type(selected.name)

        self.logger.info(
            f"Selected {selected_type}: {selected.name} | "
            f"Images={len(images)}, Videos={len(videos)}, Texts={len(texts)}"
        )

        return selected

    # ✅ Folder stats
    def get_folder_stats(self):
        inbox_files = self._list_files(self.conf.get("folder", ""))
        failed_files = self._list_files(self.conf.get("failed_folder", ""), recursive=True)

        return {
            "pending": len(inbox_files),
            "failed": len(failed_files),
            "total": len(inbox_files) + len(failed_files),
        }

    # ✅ List files
    def _list_files(self, path, recursive=False):
        if not path:
            return []

        try:
            client = self._get_client()
            results = client.files_list_folder(path, recursive=recursive)

            files = [
                entry for entry in results.entries
                if isinstance(entry, dropbox.files.FileMetadata)
            ]

            while results.has_more:
                results = client.files_list_folder_continue(results.cursor)
                files.extend(
                    entry for entry in results.entries
                    if isinstance(entry, dropbox.files.FileMetadata)
                )

            return files

        except Exception as exc:
            self.logger.error(f"Dropbox list error ({path}): {exc}")
            return []

    # ✅ Download
    def download_file(self, file_metadata):
        try:
            client = self._get_client()
            local_path = os.path.abspath(f"temp_{file_metadata.name}")
            client.files_download_to_file(local_path, file_metadata.path_lower)
            return local_path

        except Exception as exc:
            self.logger.error(f"Download failed: {exc}")
            return None

    # ✅ Temp link
    def get_temp_link(self, file_metadata):
        try:
            client = self._get_client()
            return client.files_get_temporary_link(file_metadata.path_lower).link

        except Exception as exc:
            self.logger.error(f"Temp link failed: {exc}")
            return None

    # ✅ Delete
    def delete_file(self, file_metadata):
        try:
            client = self._get_client()
            client.files_delete_v2(file_metadata.path_lower)
            self.logger.info(f"Deleted {file_metadata.name} from Dropbox")

        except Exception as exc:
            self.logger.error(f"Delete failed: {exc}")

    # ✅ Ensure folder
    def _ensure_folder(self, path):
        client = self._get_client()
        try:
            client.files_create_folder_v2(path)
        except ApiError as exc:
            if exc.error.is_path() and exc.error.get_path().is_conflict():
                return
            raise

    # ✅ Move to failed
    def move_to_failed(self, file_metadata, platform_names=None):
        client = self._get_client()
        failed_root = self.conf.get("failed_folder", "/failed")

        targets = platform_names or ["unclassified"]
        targets = [str(t).strip().lower() for t in targets if str(t).strip()]
        targets = list(dict.fromkeys(targets))

        try:
            self._ensure_folder(failed_root)

            for target in targets:
                failed_path = f"{failed_root}/{target}"
                destination = f"{failed_path}/{file_metadata.name}"

                self._ensure_folder(failed_path)

                client.files_copy_v2(
                    file_metadata.path_lower,
                    destination,
                    autorename=True,
                )

                self.logger.warning(f"Copied failed file to {destination}")

            client.files_delete_v2(file_metadata.path_lower)
            self.logger.warning(f"Removed original file: {file_metadata.name}")

        except Exception as exc:
            self.logger.error(f"Move to failed error: {exc}")
