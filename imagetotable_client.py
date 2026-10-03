import os
import json
import time
from typing import List, Dict, Any, Optional

from curl_cffi import requests as curl_requests


class ImageToTableClient:
    """
    Client for ImageToTable.ai API using curl_cffi to bypass Cloudflare's
    TLS fingerprinting (impersonates Chrome 120).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("IMAGETOTABLE_API_KEY")
        if not self.api_key:
            raise ValueError("IMAGETOTABLE_API_KEY is not set")
        self.base_url = "https://imagetotable.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def upload_document(self, file_path: str) -> Dict[str, Any]:
        """
        Upload a document to ImageToTable.ai
        """
        url = f"{self.base_url}/documents"

        with open(file_path, "rb") as f:
            file_content = f.read()

        files = {
            "file": (os.path.basename(file_path), file_content, "image/jpeg")
        }
        print(f"Uploading to: {url}")
        print(f"Using API Key: {self.api_key[:10]}...")

        response = curl_requests.post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            files=files,
            impersonate="chrome120",
            timeout=60,
        )
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text[:500]}")

        response.raise_for_status()
        return response.json()

    def upload_document_from_bytes(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload a document from bytes (e.g., from a frontend upload)
        """
        url = f"{self.base_url}/documents"
        files = {"file": (filename, file_content, "image/jpeg")}
        print(f"Uploading to: {url}")
        print(f"Using API Key: {self.api_key[:10]}...")

        response = curl_requests.post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            files=files,
            impersonate="chrome120",
            timeout=60,
        )
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text[:500]}")

        response.raise_for_status()
        return response.json()

    def get_results(self, batch_name: str) -> Dict[str, Any]:
        """
        Get the results of a processed batch
        """
        url = f"{self.base_url}/batches/{batch_name}/results"
        response = curl_requests.get(
            url,
            headers=self.headers,
            impersonate="chrome120",
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def upload_and_process(self, file_path: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Upload a document, process it, and return the results
        """
        upload_response = self.upload_document(file_path)
        batch_name = upload_response.get("batch_name")

        if not batch_name:
            raise ValueError(f"No batch_name returned from upload: {upload_response}")

        for _ in range(15):
            results = self.get_results(batch_name)
            status = results.get("status")

            if status == "succeeded":
                return results
            elif status == "failed":
                raise Exception(f"Batch processing failed: {results}")

            time.sleep(2)

        raise TimeoutError("Batch processing timed out")
