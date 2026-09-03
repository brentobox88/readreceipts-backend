import os
import requests
import json
from typing import List, Dict, Any, Optional

class ImageToTableClient:
    """
    Client for ImageToTable.ai API
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://imagetotable.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def upload_document(self, file_path: str) -> Dict[str, Any]:
        """
        Upload a document to ImageToTable.ai
        """
        url = f"{self.base_url}/documents"
        
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'image/jpeg')}
            response = requests.post(url, headers={"Authorization": f"Bearer {self.api_key}"}, files=files)
        
        response.raise_for_status()
        return response.json()

    def upload_document_from_bytes(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload a document from bytes (e.g., from a frontend upload)
        """
        url = f"{self.base_url}/documents"
        files = {'file': (filename, file_content, 'image/jpeg')}
        response = requests.post(url, headers={"Authorization": f"Bearer {self.api_key}"}, files=files)
        response.raise_for_status()
        return response.json()

    def process_batch(self, batch_name: str) -> Dict[str, Any]:
        """
        Process a batch of documents
        """
        url = f"{self.base_url}/batches/{batch_name}/process"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_results(self, batch_name: str) -> Dict[str, Any]:
        """
        Get the results of a processed batch
        """
        url = f"{self.base_url}/batches/{batch_name}/results"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def upload_and_process(self, file_path: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Upload a document, process it, and return the results
        """
        # Upload the document
        upload_response = self.upload_document(file_path)
        batch_name = upload_response.get("batch_name")
        
        if not batch_name:
            raise ValueError("No batch_name returned from upload")
        
        # Process the batch
        process_response = self.process_batch(batch_name)
        
        # Wait for processing to complete (simple polling)
        import time
        for _ in range(10):  # Try up to 10 times
            results = self.get_results(batch_name)
            status = results.get("status")
            
            if status == "succeeded":
                return results
            elif status == "failed":
                raise Exception(f"Batch processing failed: {results}")
            
            time.sleep(2)
        
        raise TimeoutError("Batch processing timed out")
