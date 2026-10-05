import os
import json
import time
from typing import List, Dict, Any, Optional

from curl_cffi import requests as curl_requests
from curl_cffi import CurlMime


class ImageToTableClient:
    """
    Client for ImageToTable.ai API using curl_cffi with residential proxy.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("IMAGETOTABLE_API_KEY")
        if not self.api_key:
            raise ValueError("IMAGETOTABLE_API_KEY is not set")

        self.base_url = "https://imagetotable.ai/api/v1"
        self.proxy = os.getenv("RESIDENTIAL_PROXY")

        if not self.proxy:
            print("WARNING: RESIDENTIAL_PROXY not set")
        else:
            print(f"Using residential proxy: {self.proxy[:40]}...")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, url: str, **kwargs):
        if self.proxy:
            kwargs["proxy"] = self.proxy
        kwargs["impersonate"] = "chrome120"
        kwargs["timeout"] = 60
        return curl_requests.post(url, **kwargs)

    def _get(self, url: str, **kwargs):
        if self.proxy:
            kwargs["proxy"] = self.proxy
        kwargs["impersonate"] = "chrome120"
        kwargs["timeout"] = 30
        return curl_requests.get(url, **kwargs)

    def upload_document(self, file_path: str) -> Dict[str, Any]:
        url = f"{self.base_url}/documents"

        with open(file_path, "rb") as f:
            file_content = f.read()

        mp = CurlMime()
        mp.addpart(
            name="file",
            content_type="image/jpeg",
            filename=os.path.basename(file_path),
            data=file_content,
        )

        print(f"Uploading to: {url}")
        response = self._post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            multipart=mp,
        )
        mp.close()

        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text[:500]}")

        response.raise_for_status()
        return response.json()

    def start_processing(self, batch_name: str, fields: List[Dict[str, str]]) -> Dict[str, Any]:
        """Call /process to start extraction for the batch."""
        url = f"{self.base_url}/batches/{batch_name}/process"
        print(f"Starting processing: {url}")

        response = self._post(
            url,
            headers=self.headers,
            json={"fields": fields},
        )
        print(f"Process status: {response.status_code}")
        print(f"Process text: {response.text[:500]}")

        response.raise_for_status()
        return response.json()

    def get_results(self, batch_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}/batches/{batch_name}/results"
        response = self._get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def upload_and_process(self, file_path: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        # 1. Upload
        upload_response = self.upload_document(file_path)
        batch_name = upload_response.get("batch_name")

        if not batch_name:
            raise ValueError(f"No batch_name returned from upload: {upload_response}")

        # 2. Define extraction fields
        if fields is None:
            fields = ["merchant_name", "transaction_date", "total_amount", "tax_amount", "line_items"]

        field_specs = [{"name": f} for f in fields]

        # 3. Trigger processing
        self.start_processing(batch_name, field_specs)

        # 4. Poll for results (with longer timeout)
        for attempt in range(30):  # 30 attempts × 3s = 90s max
            time.sleep(3)
            results = self.get_results(batch_name)
            status = results.get("status")

            print(f"Poll {attempt+1}: status={status}")

            if status == "succeeded":
                print(f"FULL RESULTS: {json.dumps(results, indent=2)[:2000]}")
                return results
            elif status == "failed":
                raise Exception(f"Batch processing failed: {results}")

        raise TimeoutError(f"Batch processing timed out after 90s. Last status: {status}")

