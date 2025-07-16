#!/usr/bin/env python3
"""
Script principal para execução do sistema de Reliable Multicast com Relógio de Lamport.

Permite executar processos distribuídos individuais ou múltiplos processos
para demonstração do sistema.

Uso:
    python main.py <process_id> [--host HOST] [--port PORT] [--processes PROC_LIST]
    python main.py --demo [--num-processes N]
    python main.py --help
"""

import argparse
import sys
import time
import threading
import signal
from typing import List
from process import DistributedProcess

class MultiProcessDemo:
    """Demonstração com múltiplos processos em threads separadas."""
    
    def __init__(self, num_processes: int = 3):
        """
        Inicializa a demonstração.
        
        Args:
            num_processes: Número de processos a criar
        """
        self.num_processes = num_processes
        self.processes: List[DistributedProcess] = []
        self.running = False
    
    def start(self):
        """Inicia todos os processos."""
        print(f"Iniciando demonstração com {self.num_processes} processos...")
        
        # Lista de todos os IDs de processos
        all_process_ids = list(range(self.num_processes))
        
        # Cria e inicia os processos
        for i in range(self.num_processes):
            try:
                process = DistributedProcess(
                    process_id=i,
                    host='localhost',
                    port=8000 + i
                )
                
                # Inicia o processo com conhecimento dos outros
                other_processes = [pid for pid in all_process_ids if pid != i]
                process.start(known_processes=other_processes)
                
                self.processes.append(process)
                print(f"Processo {i} iniciado na porta {8000 + i}")
                
                # Pequena pausa entre inicializações
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Erro ao iniciar processo {i}: {e}")
                self.stop()
                return False
        
        self.running = True
        print(f"\nTodos os {len(self.processes)} processos estão rodando!")
        print("\nPara interagir com os processos:")
        print("- Cada processo tem sua própria interface de comando")
        print("- Use 'msg <conteúdo>' para enviar mensagens multicast")
        print("- Use 'log' para ver eventos e timestamps")
        print("- Use 'stats' para ver estatísticas")
        print("- Use 'discover' para descobrir processos online")
        print("- Use 'quit' para parar um processo")
        print("- Pressione Ctrl+C para parar todos os processos\n")
        
        return True
    
    def wait_for_completion(self):
        """Aguarda a finalização de todos os processos."""
        try:
            while self.running and any(p.running for p in self.processes):
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário. Parando todos os processos...")
            self.stop()
    
    def stop(self):
        """Para todos os processos."""
        if not self.running:
            return
        
        self.running = False
        
        print("Parando todos os processos...")
        for i, process in enumerate(self.processes):
            try:
                process.stop()
                print(f"Processo {i} parado.")
            except Exception as e:
                print(f"Erro ao parar processo {i}: {e}")
        
        self.processes.clear()
        print("Demonstração finalizada.")

def signal_handler(signum, frame):
    """Handler para sinais do sistema."""
    print("\nRecebido sinal de interrupção. Finalizando...")
    sys.exit(0)

def run_single_process(process_id: int, host: str, port: int, known_processes: List[int]):
    """
    Executa um único processo distribuído.
    
    Args:
        process_id: ID do processo
        host: Host do processo
        port: Porta do processo
        known_processes: Lista de processos conhecidos
    """
    print(f"Iniciando processo {process_id} em {host}:{port}")
    print(f"Processos conhecidos: {known_processes}")
    
    try:
        with DistributedProcess(process_id, host, port) as process:
            process.start(known_processes)
            
            # Aguarda descoberta inicial
            if known_processes:
                print("Aguardando descoberta de processos...")
                time.sleep(2.0)
                online = process.discover_processes(range(max(known_processes) + 1))
                print(f"Processos descobertos: {online}")
            
            # Aguarda finalização
            process.wait_for_shutdown()
            
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuário.")
    except Exception as e:
        print(f"Erro no processo: {e}")

def parse_process_list(process_str: str) -> List[int]:
    """
    Parseia uma string de lista de processos.
    
    Args:
        process_str: String como "1,2,3" ou "1-3"
        
    Returns:
        Lista de IDs de processos
    """
    processes = []
    
    for part in process_str.split(','):
        part = part.strip()
        if '-' in part:
            # Range como "1-3"
            start, end = map(int, part.split('-'))
            processes.extend(range(start, end + 1))
        else:
            # ID único
            processes.append(int(part))
    
    return processes

def main():
    """Função principal."""
    # Registra handler para sinais
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="Sistema de Reliable Multicast com Relógio de Lamport",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Executa processo único com ID 0
  python main.py 0
  
  # Executa processo 1 conhecendo processos 0 e 2
  python main.py 1 --processes 0,2
  
  # Executa processo em host/porta específicos
  python main.py 2 --host 192.168.1.100 --port 9000
  
  # Demonstração com 4 processos
  python main.py --demo --num-processes 4
        """
    )
    
    # Grupo mutuamente exclusivo para modo de operação
    mode_group = parser.add_mutually_exclusive_group(required=True)
    
    mode_group.add_argument(
        'process_id',
        type=int,
        nargs='?',
        help='ID do processo (0-9)'
    )
    
    mode_group.add_argument(
        '--demo',
        action='store_true',
        help='Executa demonstração com múltiplos processos'
    )
    
    # Argumentos para processo único
    parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='Host do processo (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='Porta do processo (default: 8000 + process_id)'
    )
    
    parser.add_argument(
        '--processes',
        type=str,
        help='Lista de processos conhecidos (ex: "1,2,3" ou "1-3")'
    )
    
    # Argumentos para demonstração
    parser.add_argument(
        '--num-processes',
        type=int,
        default=3,
        help='Número de processos na demonstração (default: 3)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.demo:
            # Modo demonstração
            demo = MultiProcessDemo(args.num_processes)
            if demo.start():
                demo.wait_for_completion()
        else:
            # Modo processo único
            if args.process_id is None:
                parser.error("process_id é obrigatório quando não usando --demo")
            
            process_id = args.process_id
            host = args.host
            port = args.port or (8000 + process_id)
            
            known_processes = []
            if args.processes:
                known_processes = parse_process_list(args.processes)
            
            run_single_process(process_id, host, port, known_processes)
    
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 