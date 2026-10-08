        # Submit the job via /run (async, returns immediately)
        print(f"Submitting to Runpod endpoint: {self.endpoint_id} via /run")
        submit = requests.post(
            f"{self.base_url}/run",
            headers=self._headers(),
            json=body,
            timeout=60,
        )

        if not submit.ok:
            # Log the full error body for debugging
            print(f"Runpod submit failed: {submit.status_code} {submit.text[:500]}")
        submit.raise_for_status()