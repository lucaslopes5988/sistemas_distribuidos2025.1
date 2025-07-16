import threading
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import deque

from lamport_clock import LamportClock
from reliable_multicast import ReliableMulticast
from network import NetworkManager
from message import Message, MulticastMessage, MessageType

class DistributedProcess:
    """
    Processo distribuído que implementa Reliable Multicast com Relógio de Lamport.
    Integra todos os componentes do sistema distribuído.
    """
    
    def __init__(self, process_id: int, host: str = 'localhost', port: int = None):
        """
        Inicializa o processo distribuído.
        
        Args:
            process_id: Identificador único do processo
            host: Endereço do host
            port: Porta do processo (None = auto)
        """
        self.process_id = process_id
        self.host = host
        self.port = port or (8000 + process_id)
        
        # Componentes principais
        self.lamport_clock = LamportClock(process_id)
        self.network_manager = NetworkManager(process_id, host, self.port)
        self.reliable_multicast = ReliableMulticast(
            process_id, 
            self.lamport_clock,
            self._send_message_via_network
        )
        
        # Estado do processo
        self.running = False
        self.start_time = None
        
        # Log de eventos para visualização
        self.event_log = deque(maxlen=1000)  # Mantém últimos 1000 eventos
        self.log_lock = threading.Lock()
        
        # Lista de processos conhecidos
        self.known_processes: List[int] = []
        
        # Configurar callbacks
        self.network_manager.on_message_received = self._handle_network_message
        self.reliable_multicast.on_message_delivered = self._on_message_delivered
        self.reliable_multicast.on_message_failed = self._on_message_failed
        
        # Thread para interface de usuário
        self.ui_thread: Optional[threading.Thread] = None
        
        print(f"[{process_id}] Processo distribuído criado")
    
    def start(self, known_processes: List[int] = None):
        """
        Inicia o processo distribuído.
        
        Args:
            known_processes: Lista de IDs de processos conhecidos
        """
        try:
            self.start_time = datetime.now()
            self.known_processes = known_processes or []
            
            # Inicia o servidor de rede
            self.network_manager.start_server()
            
            # Registra processos conhecidos
            for pid in self.known_processes:
                if pid != self.process_id:
                    self.reliable_multicast.add_known_process(pid)
            
            self.running = True
            
            # Log do evento de inicialização
            self._log_event("SYSTEM", f"Processo {self.process_id} iniciado")
            
            # Inicia interface de usuário
            self.ui_thread = threading.Thread(target=self._user_interface, daemon=True)
            self.ui_thread.start()
            
            print(f"[{self.process_id}] Processo iniciado com sucesso")
            print(f"[{self.process_id}] Endereço: {self.host}:{self.port}")
            print(f"[{self.process_id}] Processos conhecidos: {self.known_processes}")
            
        except Exception as e:
            print(f"[{self.process_id}] Erro ao iniciar processo: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Para o processo distribuído."""
        if not self.running:
            return
        
        self.running = False
        
        # Log do evento de parada
        self._log_event("SYSTEM", f"Processo {self.process_id} parando...")
        
        # Para componentes
        self.reliable_multicast.shutdown()
        self.network_manager.stop_server()
        
        print(f"[{self.process_id}] Processo parado")
    
    def send_multicast_message(self, content: str, recipients: List[int] = None) -> str:
        """
        Envia uma mensagem multicast.
        
        Args:
            content: Conteúdo da mensagem
            recipients: Lista de destinatários (None = todos)
            
        Returns:
            ID da mensagem enviada
        """
        if not self.running:
            raise RuntimeError("Processo não está rodando")
        
        # Log do evento
        self._log_event("SEND", f"Enviando: '{content}' para {recipients or 'todos'}")
        
        # Envia via multicast confiável
        message_id = self.reliable_multicast.multicast(content, recipients)
        
        return message_id
    
    def _send_message_via_network(self, message: Message, target_process_id: int):
        """
        Callback para enviar mensagens via rede.
        
        Args:
            message: Mensagem a enviar
            target_process_id: ID do processo de destino
        """
        success = self.network_manager.send_message(message, target_process_id)
        if not success:
            print(f"[{self.process_id}] Falha ao enviar mensagem para {target_process_id}")
    
    def _handle_network_message(self, message: Message):
        """
        Callback para mensagens recebidas da rede.
        
        Args:
            message: Mensagem recebida
        """
        # Repassa para o protocolo de multicast
        self.reliable_multicast.handle_received_message(message)
    
    def _on_message_delivered(self, message: MulticastMessage):
        """
        Callback para mensagens entregues com sucesso.
        
        Args:
            message: Mensagem entregue
        """
        self._log_event(
            "DELIVER", 
            f"De P{message.sender_id} (T:{message.timestamp}): '{message.content}'"
        )
    
    def _on_message_failed(self, message: MulticastMessage):
        """
        Callback para mensagens que falharam na entrega.
        
        Args:
            message: Mensagem que falhou
        """
        self._log_event(
            "FAILED", 
            f"Falha na entrega: '{message.content}' para {message.recipients}"
        )
    
    def _log_event(self, event_type: str, description: str):
        """
        Registra um evento no log.
        
        Args:
            event_type: Tipo do evento (SYSTEM, SEND, RECEIVE, DELIVER, FAILED)
            description: Descrição do evento
        """
        with self.log_lock:
            timestamp = datetime.now()
            lamport_time = self.lamport_clock.get_time()
            
            event = {
                'timestamp': timestamp,
                'lamport_time': lamport_time,
                'process_id': self.process_id,
                'event_type': event_type,
                'description': description
            }
            
            self.event_log.append(event)
    
    def get_event_log(self, last_n: int = None) -> List[Dict[str, Any]]:
        """
        Retorna o log de eventos.
        
        Args:
            last_n: Número de eventos mais recentes (None = todos)
            
        Returns:
            Lista de eventos
        """
        with self.log_lock:
            events = list(self.event_log)
            if last_n:
                return events[-last_n:]
            return events
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do processo.
        
        Returns:
            Dicionário com estatísticas
        """
        uptime = None
        if self.start_time:
            uptime = datetime.now() - self.start_time
        
        multicast_stats = self.reliable_multicast.get_statistics()
        
        return {
            'process_id': self.process_id,
            'running': self.running,
            'uptime': str(uptime) if uptime else None,
            'lamport_time': self.lamport_clock.get_time(),
            'address': f"{self.host}:{self.port}",
            'known_processes': len(self.known_processes),
            'event_count': len(self.event_log),
            'multicast': multicast_stats
        }
    
    def discover_processes(self, process_range: range = None) -> List[int]:
        """
        Descobre processos online.
        
        Args:
            process_range: Range de IDs para verificar (default: 0-9)
            
        Returns:
            Lista de processos online
        """
        if process_range is None:
            process_range = range(10)  # Verifica processos 0-9
        
        process_ids = list(process_range)
        online = self.network_manager.discover_processes(process_ids)
        
        # Adiciona novos processos descobertos
        for pid in online:
            if pid not in self.known_processes and pid != self.process_id:
                self.known_processes.append(pid)
                self.reliable_multicast.add_known_process(pid)
        
        self._log_event("DISCOVERY", f"Processos online: {online}")
        return online
    
    def _user_interface(self):
        """Interface de usuário simples para envio de mensagens."""
        print(f"\n=== Interface do Processo {self.process_id} ===")
        print("Comandos disponíveis:")
        print("  msg <conteúdo>     - Envia mensagem multicast")
        print("  log [n]            - Mostra log de eventos (últimos n)")
        print("  stats              - Mostra estatísticas")
        print("  discover           - Descobre processos online")
        print("  quit               - Para o processo")
        print("=" * 40)
        
        while self.running:
            try:
                command = input(f"P{self.process_id}> ").strip()
                
                if not command:
                    continue
                
                parts = command.split(' ', 1)
                cmd = parts[0].lower()
                
                if cmd == 'quit':
                    self.stop()
                    break
                
                elif cmd == 'msg' and len(parts) > 1:
                    content = parts[1]
                    try:
                        msg_id = self.send_multicast_message(content)
                        print(f"Mensagem enviada: {msg_id[:8]}...")
                    except Exception as e:
                        print(f"Erro ao enviar mensagem: {e}")
                
                elif cmd == 'log':
                    n = None
                    if len(parts) > 1 and parts[1].isdigit():
                        n = int(parts[1])
                    
                    events = self.get_event_log(n)
                    print(f"\n--- Log de Eventos (últimos {len(events)}) ---")
                    for event in events:
                        print(f"[{event['timestamp'].strftime('%H:%M:%S')}] "
                              f"L:{event['lamport_time']:3d} "
                              f"{event['event_type']:8s} {event['description']}")
                    print()
                
                elif cmd == 'stats':
                    stats = self.get_statistics()
                    print(f"\n--- Estatísticas do Processo {self.process_id} ---")
                    for key, value in stats.items():
                        if key == 'multicast':
                            print(f"Multicast:")
                            for k, v in value.items():
                                print(f"  {k}: {v}")
                        else:
                            print(f"{key}: {value}")
                    print()
                
                elif cmd == 'discover':
                    online = self.discover_processes()
                    print(f"Processos online: {online}")
                
                else:
                    print("Comando inválido. Use 'quit' para sair.")
                    
            except KeyboardInterrupt:
                print("\nParando processo...")
                self.stop()
                break
            except EOFError:
                self.stop()
                break
            except Exception as e:
                print(f"Erro: {e}")
    
    def wait_for_shutdown(self):
        """Aguarda o processo ser finalizado."""
        if self.ui_thread and self.ui_thread.is_alive():
            self.ui_thread.join()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop() 