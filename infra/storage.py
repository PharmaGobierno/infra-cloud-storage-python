from datetime import timedelta
from os import getenv
from typing import Optional

import google.auth
from google.auth import impersonated_credentials
from google.cloud import storage

SIGNED_URL_EXPIRATION_MINUTES = 120
ENV_SA_SIGNER = "IMPERSONATED_SIGNER_SA_EMAIL"


class BlobNotFoudException(Exception):
    pass


class Storage:
    """
    Google Cloud Storage wrapper class compatible with Cloud Run.
    """

    __version__ = "1.2.0"

    def __init__(
        self,
        impersonated_signer_sa_email: Optional[str] = None,
        verbose: bool = False,
    ):
        self.verbose = verbose

        self.impersonated_signer_sa_email = (
            impersonated_signer_sa_email or self._get_default_env(ENV_SA_SIGNER)
        )
        self._client: storage.Client = self.__create_storage_client()

    def __create_storage_client(self) -> storage.Client:
        source_credentials, _ = google.auth.default()  # service credentials
        if self.impersonated_signer_sa_email is None:
            # return Client with service credential authorization
            return storage.Client(credentials=source_credentials)
        target_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        impersonated_creds = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=self.impersonated_signer_sa_email,
            target_scopes=target_scopes,
            lifetime=3600,
        )
        # return Client with impersonated creds authorization
        return storage.Client(credentials=impersonated_creds)

    def _get_default_env(self, name: str) -> str:
        """
        Look for values in enviroment file.
        :param name: The name to look in env
        :type name: str
        :return: Value given the name
        :rtype: str
        """
        value: Optional[str] = getenv(name)
        if value is None:
            raise ValueError(f"The default value for {name} was not found in ENV FILE")
        return value

    def get_bucket(self, bucket_name: str) -> storage.Bucket:
        return self._client.bucket(bucket_name)

    def generate_signed_url(
        self,
        filename: str,
        *,
        bucket: storage.Bucket,
        expiration_minutes: Optional[int] = None,
    ) -> Optional[str]:
        if expiration_minutes is None:
            expiration_minutes = SIGNED_URL_EXPIRATION_MINUTES
        blob = bucket.get_blob(filename)
        if blob is None:
            raise BlobNotFoudException(f"File '{filename}' does not exist in bucket")
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )
        return url
