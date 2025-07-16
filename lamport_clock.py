import threading
from typing import Dict, Any

class LamportClock:
    """
    Implementação do Relógio de Lamport para ordenação lógica de eventos
    em sistemas distribuídos assíncronos.
    """
    
    def __init__(self, process_id: int):
        """
        Inicializa o relógio de Lamport.
        
        Args:
            process_id: Identificador único do processo
        """
        self.process_id = process_id
        self._clock = 0
        self._lock = threading.Lock()
    
    def tick(self) -> int:
        """
        Incrementa o relógio para um evento local.
        
        Returns:
            Valor atual do relógio após incremento
        """
        with self._lock:
            self._clock += 1
            return self._clock
    
    def update(self, received_timestamp: int) -> int:
        """
        Atualiza o relógio ao receber uma mensagem.
        Regra: clock = max(local_clock, received_timestamp) + 1
        
        Args:
            received_timestamp: Timestamp da mensagem recebida
            
        Returns:
            Valor atual do relógio após atualização
        """
        with self._lock:
            self._clock = max(self._clock, received_timestamp) + 1
            return self._clock
    
    def get_time(self) -> int:
        """
        Retorna o valor atual do relógio.
        
        Returns:
            Valor atual do relógio
        """
        with self._lock:
            return self._clock
    
    def __str__(self) -> str:
        """Representação string do relógio."""
        return f"LamportClock(process_id={self.process_id}, time={self._clock})"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o estado do relógio para dicionário.
        
        Returns:
            Dicionário com estado do relógio
        """
        with self._lock:
            return {
                'process_id': self.process_id,
                'timestamp': self._clock
            } 