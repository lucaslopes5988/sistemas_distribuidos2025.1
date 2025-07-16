#!/usr/bin/env python3
"""
Visualizador de eventos para o sistema de Reliable Multicast com Relógio de Lamport.

Permite monitorar em tempo real os eventos e timestamps dos processos distribuídos.
"""

import time
import threading
import socket
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import sys

class EventCollector:
    """Coleta eventos de múltiplos processos distribuídos."""
    
    def __init__(self, monitor_port: int = 9999):
        """
        Inicializa o coletor de eventos.
        
        Args:
            monitor_port: Porta para receber eventos dos processos
        """
        self.monitor_port = monitor_port
        self.events: deque = deque(maxlen=5000)  # Últimos 5000 eventos
        self.process_stats: Dict[int, Dict[str, Any]] = defaultdict(dict)
        self.running = False
        
        # Servidor para receber eventos
        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        
        # Lock para thread-safety
        self.events_lock = threading.Lock()
    
    def start(self):
        """Inicia o coletor de eventos."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.monitor_port))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1.0)
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            print(f"Coletor de eventos iniciado na porta {self.monitor_port}")
            
        except Exception as e:
            print(f"Erro ao iniciar coletor: {e}")
            raise
    
    def stop(self):
        """Para o coletor de eventos."""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
    
    def _server_loop(self):
        """Loop principal do servidor de eventos."""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                # Processa cada conexão em thread separada
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Erro no servidor de eventos: {e}")
                break
    
    def _handle_client(self, client_socket: socket.socket, address):
        """Processa conexão de cliente enviando eventos."""
        try:
            client_socket.settimeout(10.0)
            
            while self.running:
                # Recebe dados
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    event_data = json.loads(data.decode('utf-8'))
                    self._add_event(event_data)
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            pass
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _add_event(self, event_data: Dict[str, Any]):
        """Adiciona um evento à coleção."""
        with self.events_lock:
            # Adiciona timestamp de recebimento
            event_data['received_at'] = datetime.now().isoformat()
            self.events.append(event_data)
            
            # Atualiza estatísticas do processo
            process_id = event_data.get('process_id')
            if process_id is not None:
                stats = self.process_stats[process_id]
                stats['last_seen'] = datetime.now()
                stats['event_count'] = stats.get('event_count', 0) + 1
                stats['last_lamport_time'] = event_data.get('lamport_time', 0)
    
    def get_events(self, process_id: int = None, event_type: str = None, 
                   last_n: int = None) -> List[Dict[str, Any]]:
        """
        Retorna eventos filtrados.
        
        Args:
            process_id: Filtro por ID do processo
            event_type: Filtro por tipo de evento
            last_n: Últimos N eventos
            
        Returns:
            Lista de eventos
        """
        with self.events_lock:
            events = list(self.events)
        
        # Aplica filtros
        if process_id is not None:
            events = [e for e in events if e.get('process_id') == process_id]
        
        if event_type is not None:
            events = [e for e in events if e.get('event_type') == event_type]
        
        # Ordena por timestamp
        events.sort(key=lambda x: x.get('lamport_time', 0))
        
        if last_n:
            events = events[-last_n:]
        
        return events
    
    def get_process_stats(self) -> Dict[int, Dict[str, Any]]:
        """Retorna estatísticas dos processos."""
        return dict(self.process_stats)

class EventVisualizer:
    """Visualizador de eventos em tempo real."""
    
    def __init__(self, collector: EventCollector):
        """
        Inicializa o visualizador.
        
        Args:
            collector: Coletor de eventos
        """
        self.collector = collector
        self.running = False
        self.display_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Inicia a visualização."""
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
    
    def stop(self):
        """Para a visualização."""
        self.running = False
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=1.0)
    
    def _display_loop(self):
        """Loop principal de visualização."""
        last_event_count = 0
        
        while self.running:
            try:
                # Limpa a tela (funciona no Windows e Unix)
                print('\033[2J\033[H', end='')
                
                # Cabeçalho
                print("=" * 80)
                print("VISUALIZADOR DE EVENTOS - RELIABLE MULTICAST COM LAMPORT CLOCK")
                print("=" * 80)
                print(f"Timestamp: {datetime.now().strftime('%H:%M:%S')}")
                print()
                
                # Estatísticas dos processos
                stats = self.collector.get_process_stats()
                if stats:
                    print("PROCESSOS ATIVOS:")
                    print("-" * 40)
                    for pid, pstats in sorted(stats.items()):
                        last_seen = pstats.get('last_seen', datetime.now())
                        time_diff = (datetime.now() - last_seen).total_seconds()
                        status = "🟢 ONLINE" if time_diff < 10 else "🔴 OFFLINE"
                        
                        print(f"Processo {pid:2d}: {status} | "
                              f"Eventos: {pstats.get('event_count', 0):3d} | "
                              f"Lamport: {pstats.get('last_lamport_time', 0):3d}")
                    print()
                
                # Eventos recentes
                recent_events = self.collector.get_events(last_n=15)
                if recent_events:
                    print("EVENTOS RECENTES (ordenados por Lamport Clock):")
                    print("-" * 80)
                    print(f"{'Time':>4} {'Proc':>4} {'Type':>8} {'Description':<50}")
                    print("-" * 80)
                    
                    for event in recent_events:
                        lamport_time = event.get('lamport_time', 0)
                        process_id = event.get('process_id', '?')
                        event_type = event.get('event_type', 'UNK')[:8]
                        description = event.get('description', '')[:50]
                        
                        print(f"{lamport_time:4d} {process_id:4} {event_type:>8} {description}")
                else:
                    print("Aguardando eventos...")
                
                print()
                print("Pressione Ctrl+C para sair")
                
                # Atualiza a cada 2 segundos
                time.sleep(2.0)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Erro na visualização: {e}")
                time.sleep(1.0)

def create_event_logger():
    """
    Cria um logger de eventos que pode ser usado pelos processos.
    
    Returns:
        Função de logging que envia eventos para o coletor
    """
    def log_event(process_id: int, lamport_time: int, event_type: str, description: str):
        """Envia evento para o coletor."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(('localhost', 9999))
            
            event_data = {
                'process_id': process_id,
                'lamport_time': lamport_time,
                'event_type': event_type,
                'description': description,
                'timestamp': datetime.now().isoformat()
            }
            
            data = json.dumps(event_data).encode('utf-8')
            sock.sendall(data)
            sock.close()
            
        except Exception:
            # Falha silenciosa se o coletor não estiver disponível
            pass
    
    return log_event

def main():
    """Função principal do visualizador."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Visualizador de eventos do sistema distribuído")
    parser.add_argument('--port', type=int, default=9999, help='Porta do monitor (default: 9999)')
    
    args = parser.parse_args()
    
    try:
        # Inicia o coletor
        collector = EventCollector(args.port)
        collector.start()
        
        # Inicia o visualizador
        visualizer = EventVisualizer(collector)
        visualizer.start()
        
        print("Visualizador iniciado. Aguardando eventos dos processos...")
        
        # Aguarda interrupção
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nParando visualizador...")
        
        # Para componentes
        visualizer.stop()
        collector.stop()
        
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 