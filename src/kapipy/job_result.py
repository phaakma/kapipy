# job_result.py

import logging
import os
import time
import asyncio
import httpx
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """
    Contains metadata about a completed file download from a Koordinates export job.

    Returned by JobResult.download and JobResult.download_async, this class provides
    detailed information about the downloaded file and its context.

    Attributes:
        folder (str): Directory where the file was saved.
        filename (str): Name of the downloaded file (without path).
        file_path (str): Full path to the downloaded file.
        file_size_bytes (int): Size of the downloaded file in bytes.
        download_url (str): Original download URL provided by the job.
        final_url (str): Final resolved URL after redirects (e.g., S3 location).
        job_id (int): Unique identifier of the export job.
        completed_at (float): Timestamp (seconds since epoch) when the download completed.
        checksum (str | None): SHA256 checksum of the downloaded file, or None if unavailable.
    """

    folder: str
    filename: str
    file_path: str
    file_size_bytes: int
    download_url: str
    final_url: str
    job_id: int
    completed_at: float
    checksum: str | None = None

    def __str__(self):
        """
        Return a user friendly string of the DownloadResult
        """

        return f"DownloadResult: job id: {self.job_id}, file path: {self.file_path}"

@dataclass
class JobStatus:
    """
    Contains data about the last known job status.

    Attributes:
        state (str): The current state of the job.
        progress (float): The progress of the job as a percentage.
    """

    state: str
    progress: float

class JobResult:
    """
    Represents the result of an asynchronous export or processing job.

    Provides methods to poll for job completion, retrieve job status, and download results.
    The download and download_async methods return a DownloadResult object containing
    detailed metadata about the downloaded file. Download metadata is also stored as
    attributes on the JobResult instance after a successful download.

    Attributes:
        _initial_payload (dict): The initial job payload from the API.
        _job_url (str): The URL to poll for job status.
        _id (int): The unique identifier of the job.
        _poll_interval (int): Polling interval in seconds.
        _timeout (int): Maximum time to wait for job completion in seconds.
        _last_response (dict): The most recent job status response.
        _gis (GISK): The GISK instance associated with this job.

        # Populated after download:
        download_folder (str): The directory where the file was saved.
        download_filename (str): The name of the downloaded file.
        download_file_path (str): The full path to the downloaded file.
        download_file_size_bytes (int): The size of the downloaded file in bytes.
        download_completed_at (float): The timestamp when the download completed.
        download_resolved_url (str): The final resolved URL after redirects.
        download_checksum (str | None): The SHA256 checksum of the downloaded file.
    """

    def __init__(
        self,
        payload: dict,
        session: "SessionManager",
        poll_interval: int = None,
        timeout: int = None,
    ) -> None:
        """
        Initializes the JobResult instance.

        Parameters:
            payload (dict): The job payload, typically from an API response.
            gis (GISK): The GISK instance associated with this job.
            poll_interval (int, optional): Interval in seconds to poll the job status. Default is 10.
            timeout (int, optional): Maximum time in seconds to wait for the job to complete. Default is 600.
        """

        self._initial_payload = payload
        self._job_url = payload["url"]
        self._id = payload["id"]
        self.downloaded = False
        self._poll_interval = poll_interval if poll_interval is not None else 10
        self._timeout = timeout if timeout is not None else 600
        self._last_response = payload
        self._session = session


    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        """Returns the name of the job."""
        return self._last_response.get("name", "unknown_name")

    @property
    def download_url(self) -> str | None:
        return self._last_response.get("download_url")

    @property
    def status(self) -> JobStatus:
        """
        Refreshes and returns the current job status.

        Returns:
            JobStatus: The state and progress of the job.
        """

        self._refresh_sync()
        return JobStatus(
            state = self._last_response.get("state"),
            progress = self._last_response.get("progress", None),
        )

    @property
    def state(self) -> str:
        """
        Returns the current state of the job.

        Returns:
            str: The job state. Possible values include 'complete', 'processing', 'cancelled', 'error', 'gone'.
        """

        return self._last_response.get("state")


    @property
    def progress(self) -> float | None:
        """
        Returns the progress of the job as a percentage.

        Returns:
            float | None: The progress value, or None if not available.
        """

        return self._last_response.get("progress", None)

    @property
    def created_at(self) -> str | None:
        """
        Returns the creation time of the job.

        Returns:
            str | None: The creation timestamp, or None if not available.
        """

        return self._last_response.get("created_at", None)

    def to_dict(self) -> dict:
        """
        Returns the most recent job status response as a dictionary.

        Returns:
            dict: The most recent job status response.
        """
        return self._last_response

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the JobResult.

        Returns:
            str: User-friendly string representation.
        """

        progress = self.progress
        progress_str = f"{progress:.2f}" if progress is not None else "None"
        return (
            f"JobResult(id={self.id}, name='{self.name}', "
            f"state='{self._last_response.get('state')}', "
            f"progress={progress_str})"
        )

    def _refresh_sync(self) -> None:
        """
        Refreshes the job status using synchronous HTTP via the GISK instance.

        Returns:
            None
        """
        self._last_response = self._session.get(self._job_url)


    def output(self) -> dict:
        """
        Blocks until the job completes, then returns the final job response.

        Returns:
            dict: The final job response after completion.

        Raises:
            TimeoutError: If the job does not complete within the timeout.
            RuntimeError: If the job fails or is cancelled.
        """

        start = time.time()

        while True:            
            state = self._last_response.get("state")
            if state != "processing":
                break

            if (time.time() - start) > self._timeout:
                raise TimeoutError(
                    f"Export job {self._id} did not complete within timeout."
                )

            time.sleep(self._poll_interval)
            self._refresh_sync()

        if self._last_response.get("state") != "complete":
            raise RuntimeError(
                f"Export job {self._id} failed with state: {self._last_response.get('state')}"
            )

        return self._last_response


    def download(self, folder: str, file_name: str | None = None) -> DownloadResult:
        """
        Waits for the job to finish, then downloads the file synchronously.

        Parameters:
            folder (str): The folder where the file will be saved.
            file_name (str, optional): The name of the file to save. If None, uses the job name.

        Returns:
            DownloadResult: Object containing details about the downloaded file.

        Raises:
            ValueError: If the download URL is not available.
        """

        self.output()  # ensure job is complete
        if not self.download_url:
            raise ValueError(
                "Download URL not available. Job may not have completed successfully."
            )

        file_name = f"{file_name}.zip" if file_name else f"{self.name}.zip"
        file_path = os.path.join(folder, file_name)
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        headers = self._session.headers

        with httpx.Client(follow_redirects=True) as client:
            resp = client.get(self.download_url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            final_url = str(resp.url)

            with client.stream("GET", final_url) as r, open(file_path, "wb") as f:
                r.raise_for_status()
                for chunk in r.iter_bytes():
                    f.write(chunk)

        file_size_bytes = os.path.getsize(file_path)
        checksum = None
        try:
            with open(file_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
        except Exception:
            pass
        completed_at = time.time()

        # Set as attributes on the JobResult instance
        self.download_folder = folder
        self.download_filename = file_name
        self.download_file_path = file_path
        self.download_file_size_bytes = file_size_bytes
        self.download_completed_at = completed_at
        self.download_resolved_url = final_url
        self.download_checksum = checksum
        self.downloaded = True

        return DownloadResult(
            folder=folder,
            filename=file_name,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            download_url=self.download_url,
            final_url=final_url,
            job_id=self._id,
            completed_at=completed_at,
            checksum=checksum,
        )
