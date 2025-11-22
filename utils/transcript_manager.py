from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests


@dataclass
class TranscriptStatus:
    guid: str
    status: str  # none | in_progress | done | error
    assembly_id: Optional[str] = None
    error: Optional[str] = None


class TranscriptManager:
    def __init__(self, base_dir: Path, api_key: Optional[str] = None):
        self.base_dir = Path(base_dir)
        self.transcripts_dir = self.base_dir / "transcripts"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.status_file = self.transcripts_dir / "status.json"
        self._lock = threading.Lock()
        self._api_key = api_key
        self._load()

    def _load(self) -> None:
        with self._lock:
            if self.status_file.exists():
                try:
                    self._statuses: Dict[str, Dict] = json.loads(self.status_file.read_text(encoding="utf-8"))
                except Exception:
                    self._statuses = {}
            else:
                self._statuses = {}

    def _save(self) -> None:
        with self._lock:
            tmp = json.dumps(self._statuses, ensure_ascii=False, indent=2)
            self.status_file.write_text(tmp, encoding="utf-8")

    def set_api_key(self, api_key: Optional[str]) -> None:
        self._api_key = api_key

    def get_status(self, guid: str) -> TranscriptStatus:
        with self._lock:
            data = self._statuses.get(guid)
        if not data:
            return TranscriptStatus(guid=guid, status="none")
        return TranscriptStatus(
            guid=guid,
            status=data.get("status", "none"),
            assembly_id=data.get("assembly_id"),
            error=data.get("error"),
        )

    def set_status(self, guid: str, status: str, assembly_id: Optional[str] = None, error: Optional[str] = None) -> None:
        with self._lock:
            entry = self._statuses.get(guid, {})
            entry.update({"status": status})
            if assembly_id is not None:
                entry["assembly_id"] = assembly_id
            if error is not None:
                entry["error"] = error
            self._statuses[guid] = entry
        self._save()

    def transcript_path(self, guid: str) -> Path:
        return self.transcripts_dir / f"{guid}.txt"

    def has_transcript(self, guid: str) -> bool:
        return self.transcript_path(guid).exists()

    def read_transcript_excerpt(self, guid: str, max_chars: int = 6000) -> Optional[str]:
        p = self.transcript_path(guid)
        if not p.exists():
            return None
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if len(txt) > max_chars:
            return txt[:max_chars] + "\n..."
        return txt

    # ===== AssemblyAI integration =====
    def _headers(self) -> Dict[str, str]:
        if not self._api_key:
            raise RuntimeError("ASSEMBLYAI_API_KEY not configured")
        return {"authorization": self._api_key}

    def _upload_local_file(self, file_path: Path) -> str:
        """Upload a local file to AssemblyAI and return the upload URL."""
        url = "https://api.assemblyai.com/v2/upload"
        headers = self._headers()
        headers["content-type"] = "application/octet-stream"
        with file_path.open("rb") as f:
            # Stream in chunks to avoid memory spikes
            def gen():
                while True:
                    chunk = f.read(5 * 1024 * 1024)
                    if not chunk:
                        break
                    yield chunk
            resp = requests.post(url, headers=headers, data=gen(), timeout=300)
        resp.raise_for_status()
        data = resp.json()
        return data.get("upload_url")

    def _create_transcript(self, audio_url: str) -> str:
        """Create a transcript job and return transcript id."""
        url = "https://api.assemblyai.com/v2/transcript"
        payload = {
            "audio_url": audio_url,
            "auto_chapters": False,
            "speaker_labels": False,
            "punctuate": True,
            "format_text": True,
        }
        resp = requests.post(url, headers={**self._headers(), "content-type": "application/json"}, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["id"]

    def _poll_until_complete(self, transcript_id: str) -> Tuple[str, Optional[str]]:
        url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        headers = self._headers()
        while True:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code >= 400:
                return "error", f"HTTP {resp.status_code}"
            data = resp.json()
            status = data.get("status")
            if status in ("queued", "processing"):
                time.sleep(5)
                continue
            if status == "completed":
                text = data.get("text", "")
                return "completed", text
            if status == "error":
                return "error", data.get("error") or "Transcription failed"
            # Fallback sleep to avoid tight loop
            time.sleep(3)

    def start_transcription_background(self, guid: str, audio_url: str, local_media_dir: Optional[Path] = None) -> bool:
        """Start transcription in background if not already in progress/done."""
        st = self.get_status(guid)
        if st.status in ("in_progress", "done"):
            return False
        self.set_status(guid, "in_progress")

        def _worker():
            try:
                # If local file is available, upload it to get a stable URL
                upload_url = None
                try:
                    if local_media_dir is not None:
                        filename = audio_url.split("/")[-1]
                        local_path = local_media_dir / filename
                        if local_path.exists():
                            upload_url = self._upload_local_file(local_path)
                except Exception:
                    # Fallback to direct audio_url if upload fails
                    upload_url = None

                create_url = upload_url or audio_url
                transcript_id = self._create_transcript(create_url)
                self.set_status(guid, "in_progress", assembly_id=transcript_id)

                status, data = self._poll_until_complete(transcript_id)
                if status == "completed":
                    # Save transcript
                    self.transcript_path(guid).write_text(data or "", encoding="utf-8")
                    self.set_status(guid, "done", assembly_id=transcript_id)
                else:
                    self.set_status(guid, "error", assembly_id=transcript_id, error=data or "unknown error")
            except Exception as e:
                self.set_status(guid, "error", error=str(e))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return True
