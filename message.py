import json
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

class MessageType(Enum):
    """Tipos de mensagens no sistema distribuído."""
    MULTICAST = "multicast"
    ACK = "acknowledgment"
    HEARTBEAT = "heartbeat"
    JOIN = "join"
    LEAVE = "leave"

@dataclass
class Message:
    """
    Estrutura base para mensagens no sistema distribuído.
    """
    message_id: str
    sender_id: int
    message_type: MessageType
    timestamp: int
    content: str
    recipients: List[int] = None
    
    def __post_init__(self):
        """Inicialização pós-criação do objeto."""
        if self.recipients is None:
            self.recipients = []
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
    
    def to_json(self) -> str:
        """
        Serializa a mensagem para JSON.
        
        Returns:
            String JSON da mensagem
        """
        data = asdict(self)
        data['message_type'] = self.message_type.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """
        Deserializa mensagem a partir de JSON.
        
        Args:
            json_str: String JSON da mensagem
            
        Returns:
            Objeto Message
        """
        data = json.loads(json_str)
        message_type = MessageType(data['message_type'])
        
        # Cria instância baseada no tipo de mensagem
        if message_type == MessageType.MULTICAST:
            return MulticastMessage(
                message_id=data['message_id'],
                sender_id=data['sender_id'],
                message_type=message_type,
                timestamp=data['timestamp'],
                content=data['content'],
                recipients=data.get('recipients', []),
                sequence_number=data.get('sequence_number', 0),
                requires_ack=data.get('requires_ack', True)
            )
        elif message_type == MessageType.ACK:
            return AckMessage(
                message_id=data['message_id'],
                sender_id=data['sender_id'],
                message_type=message_type,
                timestamp=data['timestamp'],
                content=data['content'],
                recipients=data.get('recipients', []),
                original_message_id=data.get('original_message_id', '')
            )
        else:
            # Mensagem base para outros tipos
            return cls(
                message_id=data['message_id'],
                sender_id=data['sender_id'],
                message_type=message_type,
                timestamp=data['timestamp'],
                content=data['content'],
                recipients=data.get('recipients', [])
            )
    
    def __str__(self) -> str:
        """Representação string da mensagem."""
        return (f"Message(id={self.message_id[:8]}..., "
                f"sender={self.sender_id}, "
                f"type={self.message_type.value}, "
                f"timestamp={self.timestamp}, "
                f"content='{self.content[:50]}{'...' if len(self.content) > 50 else ''}')")

@dataclass
class AckMessage(Message):
    """Mensagem de acknowledgment para multicast confiável."""
    original_message_id: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.message_type = MessageType.ACK

@dataclass
class MulticastMessage(Message):
    """Mensagem de multicast para o sistema distribuído."""
    sequence_number: int = 0
    requires_ack: bool = True
    
    def __post_init__(self):
        super().__post_init__()
        self.message_type = MessageType.MULTICAST

class MessageFactory:
    """Factory para criação de mensagens."""
    
    @staticmethod
    def create_multicast(sender_id: int, timestamp: int, content: str, 
                        recipients: List[int], sequence_number: int = 0) -> MulticastMessage:
        """
        Cria uma mensagem de multicast.
        
        Args:
            sender_id: ID do remetente
            timestamp: Timestamp do relógio de Lamport
            content: Conteúdo da mensagem
            recipients: Lista de destinatários
            sequence_number: Número de sequência
            
        Returns:
            Mensagem de multicast
        """
        return MulticastMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            message_type=MessageType.MULTICAST,
            timestamp=timestamp,
            content=content,
            recipients=recipients,
            sequence_number=sequence_number
        )
    
    @staticmethod
    def create_ack(sender_id: int, timestamp: int, original_message_id: str) -> AckMessage:
        """
        Cria uma mensagem de acknowledgment.
        
        Args:
            sender_id: ID do remetente do ACK
            timestamp: Timestamp do relógio de Lamport
            original_message_id: ID da mensagem original sendo confirmada
            
        Returns:
            Mensagem de acknowledgment
        """
        return AckMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            message_type=MessageType.ACK,
            timestamp=timestamp,
            content="ACK",
            original_message_id=original_message_id
        ) 