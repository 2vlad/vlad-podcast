from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

# Setup logger for transcription
logger = logging.getLogger("transcript_manager")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


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
        logger.info(f"TranscriptManager initialized - base_dir: {self.base_dir}")
        logger.info(f"API key configured: {bool(api_key)}")
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
        logger.debug(f"API key updated: {bool(api_key)}")

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
            logger.error("ASSEMBLYAI_API_KEY not configured!")
            raise RuntimeError("ASSEMBLYAI_API_KEY not configured")
        return {"authorization": self._api_key}

    def _upload_local_file(self, file_path: Path) -> str:
        """Upload a local file to AssemblyAI and return the upload URL."""
        logger.info(f"Uploading local file to AssemblyAI: {file_path}")
        url = "https://api.assemblyai.com/v2/upload"
        headers = self._headers()
        headers["content-type"] = "application/octet-stream"
        
        file_size = file_path.stat().st_size
        logger.info(f"File size: {file_size / (1024*1024):.2f} MB")
        
        with file_path.open("rb") as f:
            # Stream in chunks to avoid memory spikes
            def gen():
                while True:
                    chunk = f.read(5 * 1024 * 1024)
                    if not chunk:
                        break
                    yield chunk
            resp = requests.post(url, headers=headers, data=gen(), timeout=300)
        
        logger.debug(f"Upload response status: {resp.status_code}")
        if resp.status_code >= 400:
            logger.error(f"Upload failed: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
        data = resp.json()
        upload_url = data.get("upload_url")
        logger.info(f"File uploaded successfully, URL: {upload_url[:50]}...")
        return upload_url

    def _create_transcript(self, audio_url: str) -> str:
        """Create a transcript job and return transcript id."""
        logger.info(f"Creating transcript for URL: {audio_url[:80]}...")
        url = "https://api.assemblyai.com/v2/transcript"
        payload = {
            "audio_url": audio_url,
            "auto_chapters": False,
            "speaker_labels": False,
            "punctuate": True,
            "format_text": True,
        }
        resp = requests.post(url, headers={**self._headers(), "content-type": "application/json"}, json=payload, timeout=60)
        logger.debug(f"Create transcript response: {resp.status_code}")
        if resp.status_code >= 400:
            logger.error(f"Create transcript failed: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
        transcript_id = resp.json()["id"]
        logger.info(f"Transcript job created: {transcript_id}")
        return transcript_id

    def _poll_until_complete(self, transcript_id: str) -> Tuple[str, Optional[str]]:
        url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        headers = self._headers()
        poll_count = 0
        while True:
            poll_count += 1
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code >= 400:
                logger.error(f"Poll failed: HTTP {resp.status_code} - {resp.text}")
                return "error", f"HTTP {resp.status_code}"
            data = resp.json()
            status = data.get("status")
            logger.debug(f"Poll #{poll_count} - Status: {status}")
            if status in ("queued", "processing"):
                time.sleep(5)
                continue
            if status == "completed":
                text = data.get("text", "")
                logger.info(f"Transcription completed! Text length: {len(text)} chars")
                return "completed", text
            if status == "error":
                error_msg = data.get("error") or "Transcription failed"
                logger.error(f"Transcription error: {error_msg}")
                return "error", error_msg
            # Fallback sleep to avoid tight loop
            logger.warning(f"Unknown status: {status}")
            time.sleep(3)

    def start_transcription_background(self, guid: str, audio_url: str, local_media_dir: Optional[Path] = None) -> bool:
        """Start transcription in background if not already in progress/done."""
        logger.info(f"=== Starting transcription for GUID: {guid} ===")
        logger.info(f"Audio URL: {audio_url}")
        logger.info(f"Local media dir: {local_media_dir}")
        
        st = self.get_status(guid)
        logger.debug(f"Current status: {st.status}")
        if st.status in ("in_progress", "done"):
            logger.info(f"Skipping - already {st.status}")
            return False
        self.set_status(guid, "in_progress")
        logger.info("Status set to in_progress, starting background worker...")

        def _worker():
            try:
                logger.info(f"[Worker] Started for GUID: {guid}")
                
                # If local file is available, upload it to get a stable URL
                upload_url = None
                try:
                    if local_media_dir is not None:
                        filename = audio_url.split("/")[-1]
                        local_path = local_media_dir / filename
                        logger.info(f"[Worker] Checking local file: {local_path}")
                        if local_path.exists():
                            logger.info(f"[Worker] Local file found, uploading...")
                            upload_url = self._upload_local_file(local_path)
                        else:
                            logger.warning(f"[Worker] Local file not found: {local_path}")
                except Exception as upload_err:
                    # Fallback to direct audio_url if upload fails
                    logger.error(f"[Worker] Upload failed: {upload_err}", exc_info=True)
                    upload_url = None

                create_url = upload_url or audio_url
                logger.info(f"[Worker] Creating transcript with URL: {create_url[:80]}...")
                transcript_id = self._create_transcript(create_url)
                self.set_status(guid, "in_progress", assembly_id=transcript_id)

                logger.info(f"[Worker] Polling for completion...")
                status, data = self._poll_until_complete(transcript_id)
                if status == "completed":
                    # Save transcript
                    transcript_path = self.transcript_path(guid)
                    transcript_path.write_text(data or "", encoding="utf-8")
                    logger.info(f"[Worker] Transcript saved to: {transcript_path}")
                    self.set_status(guid, "done", assembly_id=transcript_id)
                    logger.info(f"[Worker] ✅ Transcription completed for GUID: {guid}")
                else:
                    error_msg = data or "unknown error"
                    logger.error(f"[Worker] ❌ Transcription failed: {error_msg}")
                    self.set_status(guid, "error", assembly_id=transcript_id, error=error_msg)
            except Exception as e:
                logger.error(f"[Worker] ❌ Exception in worker: {e}", exc_info=True)
                self.set_status(guid, "error", error=str(e))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        logger.info("Background thread started")
        return True
