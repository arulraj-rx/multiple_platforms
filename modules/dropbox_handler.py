import logging
import os
import random
import dropbox
from dropbox.exceptions import ApiError


class DropboxHandler:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.conf = config
        self.client = None  # Lazy initialization

    # =====================================================
    # LAZY CLIENT CONNECT
    # =====================================================

    def _get_client(self):
        """
        Initialize Dropbox client only when first needed.
        Prevents startup delay.
        """
        if self.client is None:
            try:
                self.client = dropbox.Dropbox(
                    app_key=os.getenv("DROPBOX_APP_KEY"),
                    app_secret=os.getenv("DROPBOX_APP_SECRET"),
                    oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
                    timeout=30,
                )
                self.logger.info("Dropbox client initialized (lazy)")
            except Exception as e:
                self.logger.error(f"Dropbox initialization failed: {e}")
                raise

        return self.client

    # =====================================================
    # FILE SELECTION
    # =====================================================

    def get_file(self):
        """
        Returns random file metadata from the configured Dropbox inbox folder.
        """
        path = self.conf.get("folder")
        if not path:
            return None

        files = self._list_files(path)
        return random.choice(files) if files else None

    # =====================================================
    # FOLDER STATS (WITH PAGINATION SUPPORT)
    # =====================================================

    def get_folder_stats(self):
        inbox_files = self._list_files(self.conf.get("folder", ""))
        failed_files = self._list_files(self.conf.get("failed_folder", ""))
        return {
            "pending": len(inbox_files),
            "failed": len(failed_files),
            "total": len(inbox_files) + len(failed_files),
        }

    # =====================================================
    # LIST FILES (Handles >2000 files safely)
    # =====================================================

    def _list_files(self, path):
        try:
            client = self._get_client()
            results = client.files_list_folder(path)
            files = [
                entry
                for entry in results.entries
                if isinstance(entry, dropbox.files.FileMetadata)
            ]

            # Handle pagination
            while results.has_more:
                results = client.files_list_folder_continue(results.cursor)
                files.extend(
                    entry
                    for entry in results.entries
                    if isinstance(entry, dropbox.files.FileMetadata)
                )

            return files

        except Exception as e:
            self.logger.error(f"Dropbox list error ({path}): {e}")
            return []

    # =====================================================
    # DOWNLOAD
    # =====================================================

    def download_file(self, file_metadata):
        try:
            client = self._get_client()

            local_path = f"temp_{file_metadata.name}"
            client.files_download_to_file(local_path, file_metadata.path_lower)

            return local_path

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None

    # =====================================================
    # TEMP LINK (FOR IG / THREADS)
    # =====================================================

    def get_temp_link(self, file_metadata):
        try:
            client = self._get_client()
            link = client.files_get_temporary_link(
                file_metadata.path_lower
            ).link
            return link
        except Exception as e:
            self.logger.error(f"Temp link failed: {e}")
            return None

    # =====================================================
    # DELETE FILE
    # =====================================================

    def delete_file(self, file_metadata):
        try:
            client = self._get_client()
            client.files_delete_v2(file_metadata.path_lower)
            self.logger.info(f"Deleted {file_metadata.name} from Dropbox")
        except Exception as e:
            self.logger.error(f"Delete failed: {e}")

    # =====================================================
    # MOVE TO FAILED
    # =====================================================

    def move_to_failed(self, file_metadata):
        """
        Moves a file to the configured Dropbox failed folder.
        """
        client = self._get_client()
        failed_path = self.conf.get("failed_folder", "/failed")
        destination = f"{failed_path}/{file_metadata.name}"

        try:
            try:
                client.files_create_folder_v2(failed_path)
            except ApiError as e:
                if e.error.is_path() and e.error.get_path().is_conflict():
                    pass
                else:
                    raise

            client.files_move_v2(
                file_metadata.path_lower,
                destination,
                autorename=True,
            )

            self.logger.warning(
                f"Moved failed file to {destination}"
            )

        except Exception as e:
            self.logger.error(f"Move to failed error: {e}")
