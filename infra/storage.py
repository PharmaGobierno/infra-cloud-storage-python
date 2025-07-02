import os
from datetime import timedelta
from typing import Optional

from google.api_core.exceptions import GoogleAPIError
from google.cloud import storage
from google.oauth2 import service_account


class Storage:
    """
    Google Cloud Storage wrapper class.
    """

    __version__ = "1.0"

    _ENV_DEFAULT_BUCKET_NAME = "DEFAULT_BUCKET_NAME"
    _ENV_GOOGLE_CLOUD_PROJECT = "GOOGLE_CLOUD_PROJECT"
    _SIGNED_URL_EXPIRATION_MINUTES = 60

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        service_account_path: Optional[str] = None,
        project_id: Optional[str] = None,
        verbose: bool = False,
    ):
        self.verbose = verbose

        self.bucket_name = bucket_name or os.getenv(self._ENV_DEFAULT_BUCKET_NAME)
        if not self.bucket_name:
            raise ValueError("Bucket name not specified")

        self._project_id = project_id or os.getenv(self._ENV_GOOGLE_CLOUD_PROJECT)

        self._client: Optional[storage.Client] = None
        self._bucket: Optional[storage.Bucket] = None

        self._client = self._create_storage_client(service_account_path)

    def _create_storage_client(
        self, service_account_path: Optional[str]
    ) -> storage.Client:
        kwargs = {}

        if service_account_path:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            kwargs["credentials"] = credentials

            if not self._project_id:
                self._project_id = credentials.project_id

        if self._project_id:
            kwargs["project"] = self._project_id

        if self.verbose:
            print(f"[Storage] Initializing GCS client with: {kwargs}")

        return storage.Client(**kwargs)

    def _get_bucket(self) -> Optional[storage.Bucket]:
        if self._bucket is None:
            if self.verbose:
                print(f"[Storage] Fetching bucket instance: {self.bucket_name}")
            self._bucket = self._client.bucket(self.bucket_name)
        return self._bucket

    def download_as_text(self, filename: Optional[str] = None) -> Optional[str]:
        if not filename:
            raise ValueError("Filename not specified")

        try:
            bucket = self._get_bucket()
            blob = bucket.get_blob(filename)
            if blob is None:
                raise FileNotFoundError("File not found in bucket")
            return blob.download_as_text()

        except GoogleAPIError as e:
            if self.verbose:
                print(f"[Storage] Failed to download '{filename}': {e.message}")
            return None
        except Exception as e:
            if self.verbose:
                print(f"[Storage] Unexpected error in download '{filename}': {e}")
            return None

    def exists(self, filename: Optional[str] = None) -> Optional[bool]:
        if not filename:
            raise ValueError("Filename not specified")

        try:
            bucket = self._get_bucket()
            blob = bucket.get_blob(filename)
            return blob is not None
        except GoogleAPIError as e:
            if self.verbose:
                print(
                    f"[Storage] Error checking existence of '{filename}': {e.message}"
                )
            return None
        except Exception as e:
            if self.verbose:
                print(f"[Storage] Unexpected error in exists('{filename}'): {e}")
            return None

    def upload_text(
        self,
        filename: Optional[str] = None,
        text: Optional[str] = None,
        generate_public_url: bool = False,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        if not filename:
            raise ValueError("Filename not specified")
        if text is None:
            raise ValueError("Text content not provided")

        try:
            bucket = self._get_bucket()
            blob = bucket.blob(filename)
            kwargs = {"content_type": content_type} if content_type else {}
            blob.upload_from_string(text, **kwargs)

            if generate_public_url:
                blob.make_public()

            return blob.public_url

        except GoogleAPIError as e:
            if self.verbose:
                print(f"[Storage] Failed to upload text to '{filename}': {e.message}")
            return None
        except Exception as e:
            if self.verbose:
                print(f"[Storage] Unexpected error uploading text to '{filename}': {e}")
            return None

    def upload_data(
        self,
        filename: Optional[str] = None,
        data: Optional[bytes] = None,
        generate_public_url: bool = False,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        if not filename:
            raise ValueError("Filename not specified")
        if data is None:
            raise ValueError("Binary data not provided")

        try:
            bucket = self._get_bucket()
            blob = bucket.blob(filename)
            kwargs = {"content_type": content_type} if content_type else {}
            blob.upload_from_string(data, **kwargs)

            if generate_public_url:
                blob.make_public()

            return blob.public_url

        except GoogleAPIError as e:
            if self.verbose:
                print(
                    f"[Storage] Failed to upload binary data to '{filename}': {e.message}"
                )
            return None
        except Exception as e:
            if self.verbose:
                print(
                    f"[Storage] Unexpected error uploading binary data to '{filename}': {e}"
                )
            return None

    def list_files(self, filepath: Optional[str] = None) -> Optional[list[str]]:
        if filepath is None:
            raise ValueError("Filepath not specified")

        try:
            bucket = self._get_bucket()
            all_blobs = list(self._client.list_blobs(bucket, prefix=filepath))
            return [blob.name for blob in all_blobs]

        except GoogleAPIError as e:
            if self.verbose:
                print(f"[Storage] Failed to list files at '{filepath}': {e.message}")
            return None
        except Exception as e:
            if self.verbose:
                print(f"[Storage] Unexpected error listing files at '{filepath}': {e}")
            return None

    def generate_url_signed(
        self,
        filename: Optional[str] = None,
        expiration_time: int = None,
    ) -> Optional[str]:
        if not filename:
            raise ValueError("Filename not specified")
        if expiration_time is None:
            expiration_time = self._SIGNED_URL_EXPIRATION_MINUTES

        try:
            bucket = self._get_bucket()
            blob = bucket.get_blob(filename)
            if blob is None:
                raise FileNotFoundError("File does not exist in bucket")

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_time),
                method="GET",
            )
            if self.verbose:
                print(
                    f"[Storage] Signed URL generated for '{filename}' ({expiration_time} min)"
                )
            return url

        except GoogleAPIError as e:
            if self.verbose:
                print(
                    f"[Storage] Failed to generate signed URL for '{filename}': {e.message}"
                )
            return None
        except Exception as e:
            if self.verbose:
                print(
                    f"[Storage] Unexpected error generating signed URL for '{filename}': {e}"
                )
            return None
