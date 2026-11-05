"""ApiToggle - coordenador de envio de detecções para a API.

Permite ligar/desligar o envio para a API em tempo de execução, criando e
liberando o cliente ``DetectionApi`` conforme necessário. Módulo puro em
Python (sem dependência de Tkinter) para ser testável diretamente.

O ``DetectionApi`` é importado no nível do módulo para que ``api_toggle.DetectionApi``
seja um alvo válido de ``unittest.mock.patch`` nos testes.
"""

from api import DetectionApi


class ApiToggle:
    """Coordena o ciclo de vida do cliente da API de detecções.

    Quando habilitado, mantém um ``DetectionApi`` ativo que envia detecções
    em uma thread em segundo plano. Quando desabilitado, nenhum cliente
    existe e ``submit`` é um no-op, permitindo o processamento local das
    detecções sem envio remoto.
    """

    def __init__(self, url, timeout_seconds, enabled):
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.client = None
        if enabled:
            self.client = DetectionApi(url, timeout_seconds=timeout_seconds)

    def enable(self):
        """Cria um novo cliente da API se nenhum estiver ativo."""
        if self.client is None:
            self.client = DetectionApi(
                self.url, timeout_seconds=self.timeout_seconds
            )

    def disable(self):
        """Fecha o cliente ativo e libera a thread e a fila de eventos."""
        if self.client is not None:
            self.client.close()
            self.client = None

    def submit(self, detection):
        """Envia a detecção ao cliente ativo; no-op quando desabilitado."""
        if self.client is not None:
            self.client.submit(detection)

    def is_enabled(self):
        """Retorna ``True`` quando há um cliente ativo da API."""
        return self.client is not None

    def close(self):
        """Encerramento idempotente: fecha o cliente ativo se houver.

        Seguro para ser chamado tanto no encerramento da interface quanto no
        bloco ``finally`` de ``main.py``, inclusive várias vezes.
        """
        self.disable()
