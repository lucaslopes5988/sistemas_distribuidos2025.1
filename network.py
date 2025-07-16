import socket
import threading
import json
import time
from typing import Dict, Callable, Optional, Tuple
from message import Message, MessageType

class NetworkManager:
    """
    Gerenciador de rede para comunicação entre processos distribuídos.
    Implementa servidor TCP para receber mensagens e cliente TCP para enviar.
    """
    
    def __init__(self, process_id: int, host: str = 'localhost', port: int = None):
        """
        Inicializa o gerenciador de rede.
        
        Args:
            process_id: ID do processo
            host: Endereço do servidor
            port: Porta do servidor (None = auto)
        """
        self.process_id = process_id
        self.host = host
        self.port = port or (8000 + process_id)  # Porta baseada no ID do processo
        
        # Socket servidor
        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        
        # Controle de execução
        self.running = False
        
        # Callback para mensagens recebidas
        self.on_message_received: Optional[Callable[[Message], None]] = None
        
        # Cache de conexões para evitar reconexões desnecessárias
        self.connection_cache: Dict[int, Tuple[str, int]] = {}
        
        # Configurações de timeout
        self.connection_timeout = 5.0
        self.socket_timeout = 10.0
    
    def start_server(self):
        """Inicia o servidor TCP para receber mensagens."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1.0)  # Timeout para accept()
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            print(f"[{self.process_id}] Servidor iniciado em {self.host}:{self.port}")
            
        except Exception as e:
            print(f"[{self.process_id}] Erro ao iniciar servidor: {e}")
            raise
    
    def stop_server(self):
        """Para o servidor TCP."""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
        
        print(f"[{self.process_id}] Servidor parado")
    
    def _server_loop(self):
        """Loop principal do servidor."""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                # Processa cada conexão em uma thread separada
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                # Timeout normal, continua o loop
                continue
            except Exception as e:
                if self.running:
                    print(f"[{self.process_id}] Erro no servidor: {e}")
                break
    
    def _handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """
        Processa uma conexão de cliente.
        
        Args:
            client_socket: Socket do cliente
            address: Endereço do cliente
        """
        try:
            client_socket.settimeout(self.socket_timeout)
            
            # Recebe o tamanho da mensagem (4 bytes)
            size_data = self._recv_all(client_socket, 4)
            if not size_data:
                return
            
            message_size = int.from_bytes(size_data, byteorder='big')
            
            # Recebe a mensagem
            message_data = self._recv_all(client_socket, message_size)
            if not message_data:
                return
            
            message_json = message_data.decode('utf-8')
            message = Message.from_json(message_json)
            
            print(f"[{self.process_id}] Recebeu via rede: {message}")
            
            # Chama o callback se definido
            if self.on_message_received:
                self.on_message_received(message)
            
        except Exception as e:
            print(f"[{self.process_id}] Erro ao processar cliente {address}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _recv_all(self, sock: socket.socket, size: int) -> bytes:
        """
        Recebe exatamente 'size' bytes do socket.
        
        Args:
            sock: Socket
            size: Número de bytes a receber
            
        Returns:
            Dados recebidos ou bytes vazios se erro
        """
        data = b''
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                return b''
            data += chunk
        return data
    
    def send_message(self, message: Message, target_process_id: int) -> bool:
        """
        Envia uma mensagem para outro processo.
        
        Args:
            message: Mensagem a enviar
            target_process_id: ID do processo de destino
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            # Obtém endereço do processo de destino
            target_host, target_port = self._get_process_address(target_process_id)
            
            # Cria conexão
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(self.connection_timeout)
            
            try:
                client_socket.connect((target_host, target_port))
                
                # Serializa a mensagem
                message_json = message.to_json()
                message_data = message_json.encode('utf-8')
                message_size = len(message_data)
                
                # Envia tamanho da mensagem (4 bytes) seguido da mensagem
                size_bytes = message_size.to_bytes(4, byteorder='big')
                client_socket.sendall(size_bytes + message_data)
                
                print(f"[{self.process_id}] Enviou via rede para {target_process_id}: {message}")
                return True
                
            finally:
                client_socket.close()
                
        except Exception as e:
            print(f"[{self.process_id}] Erro ao enviar para {target_process_id}: {e}")
            return False
    
    def _get_process_address(self, process_id: int) -> Tuple[str, int]:
        """
        Obtém o endereço de um processo.
        
        Args:
            process_id: ID do processo
            
        Returns:
            Tupla (host, port)
        """
        if process_id in self.connection_cache:
            return self.connection_cache[process_id]
        
        # Por padrão, usa localhost e porta baseada no ID
        host = 'localhost'
        port = 8000 + process_id
        
        self.connection_cache[process_id] = (host, port)
        return host, port
    
    def register_process(self, process_id: int, host: str, port: int):
        """
        Registra o endereço de um processo.
        
        Args:
            process_id: ID do processo
            host: Host do processo
            port: Porta do processo
        """
        self.connection_cache[process_id] = (host, port)
        print(f"[{self.process_id}] Registrou processo {process_id} em {host}:{port}")
    
    def get_own_address(self) -> Tuple[str, int]:
        """
        Retorna o endereço próprio do processo.
        
        Returns:
            Tupla (host, port)
        """
        return self.host, self.port
    
    def is_running(self) -> bool:
        """Verifica se o servidor está rodando."""
        return self.running and self.server_thread and self.server_thread.is_alive()
    
    def wait_for_connection(self, target_process_id: int, timeout: float = 10.0) -> bool:
        """
        Aguarda até que seja possível conectar com outro processo.
        
        Args:
            target_process_id: ID do processo alvo
            timeout: Timeout em segundos
            
        Returns:
            True se conectou, False se timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                host, port = self._get_process_address(target_process_id)
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.settimeout(1.0)
                
                result = test_socket.connect_ex((host, port))
                test_socket.close()
                
                if result == 0:
                    return True
                    
            except:
                pass
            
            time.sleep(0.5)
        
        return False
    
    def discover_processes(self, process_ids: list, timeout: float = 5.0) -> list:
        """
        Descobre quais processos estão online.
        
        Args:
            process_ids: Lista de IDs de processos para verificar
            timeout: Timeout por processo
            
        Returns:
            Lista de IDs de processos online
        """
        online_processes = []
        
        for process_id in process_ids:
            if process_id == self.process_id:
                online_processes.append(process_id)
                continue
                
            if self.wait_for_connection(process_id, timeout=1.0):
                online_processes.append(process_id)
        
        return online_processes 