import threading
import time
from collections import defaultdict, deque
from typing import Dict, List, Set, Callable, Optional
from dataclasses import dataclass
from message import Message, MulticastMessage, AckMessage, MessageType, MessageFactory
from lamport_clock import LamportClock

@dataclass
class PendingMessage:
    """Estrutura para mensagens pendentes de acknowledgment."""
    message: MulticastMessage
    sent_time: float
    ack_received: Set[int]
    retry_count: int = 0

class ReliableMulticast:
    """
    Implementação do protocolo de Multicast Confiável.
    Garante a entrega ordenada e confiável de mensagens entre processos distribuídos.
    """
    
    def __init__(self, process_id: int, lamport_clock: LamportClock, 
                 send_callback: Callable[[Message, int], None]):
        """
        Inicializa o protocolo de multicast confiável.
        
        Args:
            process_id: ID do processo local
            lamport_clock: Relógio de Lamport do processo
            send_callback: Função para enviar mensagens via rede
        """
        self.process_id = process_id
        self.lamport_clock = lamport_clock
        self.send_callback = send_callback
        
        # Controle de mensagens pendentes e acknowledgments
        self.pending_messages: Dict[str, PendingMessage] = {}
        self.received_messages: Dict[str, MulticastMessage] = {}
        self.delivered_messages: Set[str] = set()
        
        # Fila de mensagens ordenadas por timestamp
        self.message_queue = deque()
        
        # Controle de sequência por processo
        self.sequence_numbers: Dict[int, int] = defaultdict(int)
        self.expected_sequence: Dict[int, int] = defaultdict(int)
        
        # Lista de processos conhecidos
        self.known_processes: Set[int] = {process_id}
        
        # Configurações de timeout e retry
        self.ack_timeout = 5.0  # 5 segundos
        self.max_retries = 3
        
        # Locks para thread-safety
        self.pending_lock = threading.Lock()
        self.queue_lock = threading.Lock()
        
        # Thread para verificar timeouts
        self.timeout_thread = threading.Thread(target=self._timeout_checker, daemon=True)
        self.running = True
        self.timeout_thread.start()
        
        # Callbacks para eventos
        self.on_message_delivered: Optional[Callable[[MulticastMessage], None]] = None
        self.on_message_failed: Optional[Callable[[MulticastMessage], None]] = None
    
    def add_known_process(self, process_id: int):
        """Adiciona um processo à lista de processos conhecidos."""
        self.known_processes.add(process_id)
    
    def multicast(self, content: str, recipients: List[int] = None) -> str:
        """
        Envia uma mensagem multicast confiável.
        
        Args:
            content: Conteúdo da mensagem
            recipients: Lista de destinatários (None = todos os processos conhecidos)
            
        Returns:
            ID da mensagem enviada
        """
        if recipients is None:
            recipients = list(self.known_processes - {self.process_id})
        
        # Incrementa o relógio e número de sequência
        timestamp = self.lamport_clock.tick()
        sequence_num = self.sequence_numbers[self.process_id]
        self.sequence_numbers[self.process_id] += 1
        
        # Cria a mensagem
        message = MessageFactory.create_multicast(
            sender_id=self.process_id,
            timestamp=timestamp,
            content=content,
            recipients=recipients,
            sequence_number=sequence_num
        )
        
        # Adiciona à lista de mensagens pendentes
        with self.pending_lock:
            self.pending_messages[message.message_id] = PendingMessage(
                message=message,
                sent_time=time.time(),
                ack_received=set()
            )
        
        # Envia para todos os destinatários
        for recipient_id in recipients:
            self.send_callback(message, recipient_id)
        
        print(f"[{self.process_id}] Enviou multicast: {message}")
        return message.message_id
    
    def handle_received_message(self, message: Message):
        """
        Processa uma mensagem recebida.
        
        Args:
            message: Mensagem recebida
        """
        # Atualiza o relógio de Lamport
        self.lamport_clock.update(message.timestamp)
        
        if message.message_type == MessageType.MULTICAST:
            self._handle_multicast_message(message)
        elif message.message_type == MessageType.ACK:
            self._handle_ack_message(message)
    
    def _handle_multicast_message(self, message: MulticastMessage):
        """Processa uma mensagem de multicast recebida."""
        print(f"[{self.process_id}] Recebeu multicast: {message}")
        
        # Evita processar mensagens duplicadas
        if message.message_id in self.received_messages:
            print(f"[{self.process_id}] Mensagem duplicada ignorada: {message.message_id[:8]}")
            return
        
        # Adiciona o remetente aos processos conhecidos
        self.add_known_process(message.sender_id)
        
        # Armazena a mensagem
        self.received_messages[message.message_id] = message
        
        # Envia acknowledgment
        ack_timestamp = self.lamport_clock.tick()
        ack_message = MessageFactory.create_ack(
            sender_id=self.process_id,
            timestamp=ack_timestamp,
            original_message_id=message.message_id
        )
        self.send_callback(ack_message, message.sender_id)
        
        # Adiciona à fila ordenada
        self._add_to_ordered_queue(message)
        
        # Tenta entregar mensagens em ordem
        self._try_deliver_messages()
    
    def _handle_ack_message(self, ack_message: AckMessage):
        """Processa uma mensagem de acknowledgment."""
        original_msg_id = ack_message.original_message_id
        
        with self.pending_lock:
            if original_msg_id in self.pending_messages:
                pending = self.pending_messages[original_msg_id]
                pending.ack_received.add(ack_message.sender_id)
                
                print(f"[{self.process_id}] ACK recebido de {ack_message.sender_id} "
                      f"para mensagem {original_msg_id[:8]}... "
                      f"({len(pending.ack_received)}/{len(pending.message.recipients)})")
                
                # Verifica se todos os ACKs foram recebidos
                if len(pending.ack_received) >= len(pending.message.recipients):
                    print(f"[{self.process_id}] Todos os ACKs recebidos para {original_msg_id[:8]}...")
                    del self.pending_messages[original_msg_id]
    
    def _add_to_ordered_queue(self, message: MulticastMessage):
        """Adiciona mensagem à fila ordenada por timestamp."""
        with self.queue_lock:
            # Insere ordenado por timestamp (Lamport)
            inserted = False
            for i, queued_msg in enumerate(self.message_queue):
                if message.timestamp < queued_msg.timestamp:
                    self.message_queue.insert(i, message)
                    inserted = True
                    break
                elif (message.timestamp == queued_msg.timestamp and 
                      message.sender_id < queued_msg.sender_id):
                    # Desempate por ID do processo
                    self.message_queue.insert(i, message)
                    inserted = True
                    break
            
            if not inserted:
                self.message_queue.append(message)
    
    def _try_deliver_messages(self):
        """Tenta entregar mensagens em ordem."""
        with self.queue_lock:
            while self.message_queue:
                message = self.message_queue[0]
                
                # Verifica se pode entregar (ordem por timestamp)
                can_deliver = True
                for other_msg in list(self.message_queue)[1:]:
                    if (other_msg.timestamp < message.timestamp or 
                        (other_msg.timestamp == message.timestamp and 
                         other_msg.sender_id < message.sender_id)):
                        can_deliver = False
                        break
                
                if can_deliver and message.message_id not in self.delivered_messages:
                    # Entrega a mensagem
                    self.message_queue.popleft()
                    self.delivered_messages.add(message.message_id)
                    
                    print(f"[{self.process_id}] ✓ ENTREGOU mensagem: "
                          f"sender={message.sender_id}, timestamp={message.timestamp}, "
                          f"content='{message.content}'")
                    
                    if self.on_message_delivered:
                        self.on_message_delivered(message)
                else:
                    break
    
    def _timeout_checker(self):
        """Thread que verifica timeouts e realiza retransmissões."""
        while self.running:
            time.sleep(1.0)  # Verifica a cada segundo
            
            with self.pending_lock:
                current_time = time.time()
                messages_to_retry = []
                messages_to_fail = []
                
                for msg_id, pending in list(self.pending_messages.items()):
                    if current_time - pending.sent_time > self.ack_timeout:
                        if pending.retry_count < self.max_retries:
                            messages_to_retry.append(pending)
                        else:
                            messages_to_fail.append(pending)
                            del self.pending_messages[msg_id]
                
                # Realiza retransmissões
                for pending in messages_to_retry:
                    pending.retry_count += 1
                    pending.sent_time = current_time
                    
                    # Reenvia para destinatários que não enviaram ACK
                    missing_acks = set(pending.message.recipients) - pending.ack_received
                    for recipient_id in missing_acks:
                        self.send_callback(pending.message, recipient_id)
                    
                    print(f"[{self.process_id}] Retransmitindo mensagem {pending.message.message_id[:8]}... "
                          f"(tentativa {pending.retry_count}/{self.max_retries}) "
                          f"para {len(missing_acks)} destinatários")
                
                # Notifica falhas
                for pending in messages_to_fail:
                    print(f"[{self.process_id}] ✗ FALHA na entrega de {pending.message.message_id[:8]}... "
                          f"após {self.max_retries} tentativas")
                    
                    if self.on_message_failed:
                        self.on_message_failed(pending.message)
    
    def get_statistics(self) -> Dict:
        """Retorna estatísticas do protocolo."""
        with self.pending_lock:
            pending_count = len(self.pending_messages)
        
        with self.queue_lock:
            queue_size = len(self.message_queue)
        
        return {
            'pending_messages': pending_count,
            'queue_size': queue_size,
            'delivered_messages': len(self.delivered_messages),
            'known_processes': len(self.known_processes)
        }
    
    def shutdown(self):
        """Finaliza o protocolo."""
        self.running = False
        if self.timeout_thread.is_alive():
            self.timeout_thread.join(timeout=2.0) 