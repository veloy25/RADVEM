import json
import logging
import queue
import threading
import urllib.error
import urllib.request


logger = logging.getLogger(__name__)


class DetectionApi:
    def __init__(self, url, timeout_seconds=5):
        if not url or "SEU_SERVIDOR" in url:
            raise ValueError("Configure uma URL real para a API.")
        if timeout_seconds <= 0:
            raise ValueError("O timeout da API deve ser maior que zero.")

        self.url = url
        self.timeout_seconds = timeout_seconds
        self.events = queue.Queue()
        self.closed = False
        self.worker = threading.Thread(
            target=self._send_events,
            name="detection-api",
            daemon=False,
        )
        self.worker.start()

    def submit(self, detection):
        if self.closed:
            raise RuntimeError("O cliente da API já foi encerrado.")
        if not isinstance(detection, dict):
            raise TypeError("A detecção deve ser fornecida como um dicionário.")
        self.events.put(dict(detection))

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.events.put(None)
        self.worker.join()

    def _send_events(self):
        while True:
            detection = self.events.get()
            if detection is None:
                return
            try:
                self._post_detection(detection)
            except (
                TypeError,
                ValueError,
                urllib.error.URLError,
                TimeoutError,
                OSError,
            ):
                logger.exception(
                    "Falha ao enviar detecção %s para a API",
                    detection.get("detection_id"),
                )

    def _post_detection(self, detection):
        payload = json.dumps(detection).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=self.timeout_seconds,
        ) as response:
            if not 200 <= response.status < 300:
                raise urllib.error.URLError(
                    f"A API respondeu com HTTP {response.status}."
                )
