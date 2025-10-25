import io
import os
import time
import pytest
import hashlib
from unittest.mock import MagicMock, patch, mock_open
from kapipy.job_result import JobResult, DownloadResult, JobStatus


@pytest.fixture
def mock_session():
    """Mocked SessionManager with get() and headers."""
    session = MagicMock()
    session.headers = {"Authorization": "Bearer test"}
    return session


@pytest.fixture
def sample_payload():
    """Minimal initial payload for JobResult."""
    return {
        "url": "https://example.com/job/123",
        "id": 123,
        "name": "test_job",
        "state": "complete",
        "progress": 100.0,
        "download_url": "https://example.com/download.zip",
    }


# -----------------------------------------------------------------------------
# DownloadResult Tests
# -----------------------------------------------------------------------------

def test_downloadresult_repr_and_str():
    dr = DownloadResult(
        folder="/tmp",
        filename="data.zip",
        file_path="/tmp/data.zip",
        file_size_bytes=1234,
        download_url="https://example.com/dl.zip",
        final_url="https://cdn.example.com/dl.zip",
        job_id=42,
        completed_at=1000000.0,
        checksum="abc123",
    )

    assert "DownloadResult" in repr(dr)
    assert "data.zip" in repr(dr)
    assert "job id: 42" in str(dr)
    assert "/tmp/data.zip" in str(dr)


# -----------------------------------------------------------------------------
# JobStatus Tests
# -----------------------------------------------------------------------------

def test_jobstatus_repr():
    js = JobStatus(state="processing", progress=42.5)
    assert repr(js) == "JobStatus(state='processing', progress=42.5)"


# -----------------------------------------------------------------------------
# JobResult Initialization and Properties
# -----------------------------------------------------------------------------

def test_jobresult_properties(sample_payload, mock_session):
    job = JobResult(sample_payload, mock_session)

    job_string = str(job)
    job_repr = repr(job)
    job_dict = job.to_dict()

    assert job.id == 123
    assert job.name == "test_job"
    assert job.download_url == "https://example.com/download.zip"
    assert isinstance(job.status, JobStatus)
    assert "JobResult" in job_string
    assert "complete" in job_repr
    assert job_dict["id"] == 123


# -----------------------------------------------------------------------------
# JobResult.output()
# -----------------------------------------------------------------------------

def test_output_completes_immediately(sample_payload, mock_session):
    job = JobResult(sample_payload, mock_session)
    result = job.output()
    assert result["state"] == "complete"


def test_output_times_out(sample_payload, mock_session):
    sample_payload["state"] = "processing"
    job = JobResult(sample_payload, mock_session, poll_interval=0.01, timeout=0.02)

    # Simulate no state change
    mock_session.get.return_value = {"state": "processing"}

    with pytest.raises(TimeoutError):
        job.output()


def test_output_fails(sample_payload, mock_session):
    sample_payload["state"] = "error"
    job = JobResult(sample_payload, mock_session)

    with pytest.raises(RuntimeError):
        job.output()


# -----------------------------------------------------------------------------
# JobResult.download()
# -----------------------------------------------------------------------------

@patch("os.makedirs")
@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=1234)
@patch("builtins.open", new_callable=mock_open, read_data=b"filecontent")
@patch("httpx.Client")
def test_download_success(mock_httpx, mock_openfile, mock_getsize, mock_exists, mock_makedirs, sample_payload, mock_session, tmp_path):
    job = JobResult(sample_payload, mock_session)
    job._last_response["state"] = "complete"

    # mock HTTPX behavior
    mock_client = mock_httpx.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.url = "https://cdn.example.com/file.zip"
    mock_response.iter_bytes.return_value = [b"filecontent"]
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response
    mock_client.stream.return_value.__enter__.return_value = mock_response

    result = job.download(folder=str(tmp_path))

    assert isinstance(result, DownloadResult)
    assert result.filename.endswith(".zip")
    assert result.file_size_bytes == 1234
    assert result.final_url == "https://cdn.example.com/file.zip"
    assert job.downloaded
    assert os.path.basename(result.file_path).endswith(".zip")
    assert result.checksum == hashlib.sha256(b"filecontent").hexdigest()


def test_download_raises_no_download_url(sample_payload, mock_session):
    sample_payload.pop("download_url", None)
    job = JobResult(sample_payload, mock_session)
    job._last_response["state"] = "complete"

    with pytest.raises(ValueError):
        job.download(folder="/tmp")
