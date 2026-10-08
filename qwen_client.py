import os
import base64
import json
import time
from typing import Any, Dict, Optional

import requests


class QwenClient:
    """
    Client for the Qwen2.5-VL-7B Runpod endpoint.

    Uses /run (async) + polling instead of /runsync to avoid 409 Conflict
    errors when the endpoint is busy or queuing multiple jobs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        timeout_seconds: int = 600,
    ):
        self.api_key = api_key or os.getenv("RUNPOD_API_KEY")
        self.endpoint_id = endpoint_id or os.getenv("QWEN_ENDPOINT_ID")
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("RUNPOD_API_KEY is not set")
        if not self.endpoint_id:
            raise ValueError("QWEN_ENDPOINT_ID is not set")

        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def process_image_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Send image bytes to the Runpod endpoint via /run and poll for result.
        """
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        body = {"input": {"image_base64": image_b64}}

        # Submit the job via /run (async, returns immediately)
        print(f"Submitting to Runpod endpoint: {self.endpoint_id} via /run")
        submit = requests.post(
            f"{self.base_url}/run",
            headers=self._headers(),
            json=body,
            timeout=60,
        )
        submit.raise_for_status()
        response = submit.json()

        job_id = response.get("id")
        if not job_id:
            raise RuntimeError(f"Runpod did not return a job id: {response}")

        print(f"Runpod job {job_id} submitted")

        # Poll for completion
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            time.sleep(3)
            poll = requests.get(
                f"{self.base_url}/status/{job_id}",
                headers=self._headers(),
                timeout=30,
            )
            poll.raise_for_status()
            result = poll.json()
            status = result.get("status")
            print(f"Poll {job_id}: status={status}")

            if status == "COMPLETED":
                output = result.get("output", {})
                if output.get("error"):
                    raise RuntimeError(f"Qwen extraction failed: {output}")
                return output
            if status in ("FAILED", "CANCELLED"):
                raise RuntimeError(f"Runpod job {job_id} failed: {result.get('output')}")

        raise TimeoutError(f"Runpod job {job_id} timed out after {self.timeout_seconds}s")

    def process_image_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            return self.process_image_bytes(f.read())