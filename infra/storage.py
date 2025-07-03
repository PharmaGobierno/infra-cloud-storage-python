import os
from datetime import timedelta
from typing import Optional

from google.cloud import storage
from google.oauth2 import service_account


class Storage:
    """
    Google Cloud Storage wrapper class compatible with Cloud Run.
    """

    __version__ = "1.1"

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

        self._client: storage.Client = self._create_storage_client(service_account_path)
        self._bucket: Optional[storage.Bucket] = None

    def _create_storage_client(
        self, service_account_path: Optional[str]
    ) -> storage.Client:
        if service_account_path:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            if not self._project_id:
                self._project_id = credentials.project_id
            if self.verbose:
                print("[Storage] Using service account credentials from file")
            return storage.Client(credentials=credentials, project=self._project_id)

        if self.verbose:
            print("[Storage] Using default credentials (Cloud Run, etc.)")
        return storage.Client(project=self._project_id)

    def _get_bucket(self) -> storage.Bucket:
        if self._bucket is None:
            if self.verbose:
                print(f"[Storage] Fetching bucket instance: {self.bucket_name}")
            self._bucket = self._client.bucket(self.bucket_name)
        return self._bucket

    def download_as_text(self, filename: str) -> str:
        bucket = self._get_bucket()
        blob = bucket.get_blob(filename)
        if blob is None:
            raise FileNotFoundError(f"File '{filename}' not found in bucket")
        return blob.download_as_text()

    def exists(self, filename: str) -> bool:
        bucket = self._get_bucket()
        return bucket.get_blob(filename) is not None

    def upload_text(
        self,
        filename: str,
        text: str,
        generate_public_url: bool = False,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        bucket = self._get_bucket()
        blob = bucket.blob(filename)
        blob.upload_from_string(text, content_type=content_type)

        if generate_public_url:
            blob.make_public()
            return blob.public_url
        return None

    def upload_data(
        self,
        filename: str,
        data: bytes,
        generate_public_url: bool = False,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        bucket = self._get_bucket()
        blob = bucket.blob(filename)
        blob.upload_from_string(data, content_type=content_type)

        if generate_public_url:
            blob.make_public()
            return blob.public_url
        return None

    def list_files(self, filepath: str) -> list[str]:
        bucket = self._get_bucket()
        all_blobs = list(self._client.list_blobs(bucket, prefix=filepath))
        return [blob.name for blob in all_blobs]

    def generate_url_signed(
        self,
        filename: str,
        expiration_time: int = None,
    ) -> str:
        expiration_time = expiration_time or self._SIGNED_URL_EXPIRATION_MINUTES

        bucket = self._get_bucket()
        blob = bucket.get_blob(filename)
        if blob is None:
            raise FileNotFoundError(f"File '{filename}' does not exist in bucket")

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_time),
            method="GET",
        )
        if self.verbose:
            print(f"[Storage] Signed URL for '{filename}' valid {expiration_time} min")
        return url
