import io
from minio import Minio
from minio.error import S3Error
from core.config import Settings


def _parse_endpoint(endpoint: str) -> tuple[str, int]:
    ep = endpoint.strip().replace("http://", "").replace("https://", "")
    if ":" in ep:
        host, port_s = ep.rsplit(":", 1)
        return host, int(port_s)
    return ep, 9000


class OrderMinioClient:
    def __init__(self, settings: Settings) -> None:
        host, port = _parse_endpoint(settings.minio_endpoint)
        self._bucket = settings.minio_bucket
        self._client = Minio(
            f"{host}:{port}",
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def check_bucket_access(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            raise RuntimeError(f"Bucket {self._bucket} is not available")

    def upload_stl(self, file_id: str, filename: str, data: bytes) -> str:
        object_key = f"stl/orders/{file_id}/{filename}"
        self._client.put_object(
            self._bucket,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type="application/octet-stream",
        )
        return object_key

    def stat_object(self, object_key: str):
        return self._client.stat_object(self._bucket, object_key)

    def get_object(self, object_key: str):
        return self._client.get_object(self._bucket, object_key)
