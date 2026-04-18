import os
from typing import Iterable, Optional

from minio import Minio
from minio.error import S3Error

from src.core.config import Settings


def _local_path_for_object(dest_dir: str, object_key: str) -> str:
    safe = object_key.strip("/").replace("/", "__")
    return os.path.join(dest_dir, safe)


def _parse_minio_endpoint(endpoint: str) -> tuple[str, int]:
    ep = endpoint.strip().replace("http://", "").replace("https://", "")
    if ":" in ep:
        host, port_s = ep.rsplit(":", 1)
        return host, int(port_s)
    return ep, 9000


class MinioClient:
    def __init__(self, settings: Settings) -> None:
        host, port = _parse_minio_endpoint(settings.minio_endpoint)
        self._bucket = settings.minio_bucket
        self._client = Minio(
            f"{host}:{port}",
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def download_files(self, paths: Iterable[str], dest_dir: str) -> dict[str, str]:
        os.makedirs(dest_dir, exist_ok=True)
        mapping: dict[str, str] = {}
        for object_key in paths:
            local_path = _local_path_for_object(dest_dir, object_key)
            self._client.fget_object(self._bucket, object_key, local_path)
            mapping[object_key] = local_path
        return mapping

    def download_file_if_exists(self, object_key: str, dest_dir: str) -> Optional[str]:
        os.makedirs(dest_dir, exist_ok=True)
        try:
            self._client.stat_object(self._bucket, object_key)
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return None
            raise
        local_path = _local_path_for_object(dest_dir, object_key)
        self._client.fget_object(self._bucket, object_key, local_path)
        return local_path

    def upload_file(self, local_path: str, s3_key: str) -> None:
        self._client.fput_object(self._bucket, s3_key, local_path)
