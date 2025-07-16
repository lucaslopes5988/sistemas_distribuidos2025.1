#!/usr/bin/env python3
"""
Script de teste automatizado para o sistema de Reliable Multicast com Relógio de Lamport.

Executa testes básicos e demonstrações do funcionamento do sistema.
"""

import time
import threading
import subprocess
import sys
from datetime import datetime

def test_single_process():
    """Testa criação de um processo único."""
    print("\n=== Teste 1: Processo Único ===")
    
    from process import DistributedProcess
    
    try:
        with DistributedProcess(process_id=0) as process:
            process.start()
            
            print("✓ Processo criado e iniciado com sucesso")
            
            # Testa envio de mensagem (sem destinatários)
            try:
                msg_id = process.send_multicast_message("Mensagem de teste")
                print(f"✓ Mensagem enviada: {msg_id[:8]}...")
            except Exception as e:
                print(f"✗ Erro ao enviar mensagem: {e}")
            
            # Verifica estatísticas
            stats = process.get_statistics()
            print(f"✓ Estatísticas obtidas: {stats['process_id']}")
            
            time.sleep(1.0)
            
    except Exception as e:
        print(f"✗ Erro no teste: {e}")
        return False
    
    print("✓ Teste de processo único concluído")
    return True

def test_lamport_clock():
    """Testa funcionalidade do relógio de Lamport."""
    print("\n=== Teste 2: Relógio de Lamport ===")
    
    from lamport_clock import LamportClock
    
    try:
        clock1 = LamportClock(1)
        clock2 = LamportClock(2)
        
        # Teste de incremento
        t1 = clock1.tick()
        t2 = clock1.tick()
        assert t2 > t1, "Relógio deve incrementar"
        print(f"✓ Incremento: {t1} -> {t2}")
        
        # Teste de sincronização
        clock2_time = clock2.tick()  # clock2 = 1
        clock1_time = clock1.update(clock2_time)  # clock1 = max(2, 1) + 1 = 3
        
        print(f"✓ Sincronização: clock1={clock1_time}, clock2={clock2_time}")
        assert clock1_time > max(t2, clock2_time), "Sincronização deve funcionar"
        
    except Exception as e:
        print(f"✗ Erro no teste do relógio: {e}")
        return False
    
    print("✓ Teste do relógio de Lamport concluído")
    return True

def test_message_serialization():
    """Testa serialização de mensagens."""
    print("\n=== Teste 3: Serialização de Mensagens ===")
    
    from message import MessageFactory, MessageType
    
    try:
        # Cria mensagem multicast
        msg = MessageFactory.create_multicast(
            sender_id=1,
            timestamp=5,
            content="Teste de serialização",
            recipients=[2, 3],
            sequence_number=1
        )
        
        # Serializa e deserializa
        json_str = msg.to_json()
        msg_restored = msg.from_json(json_str)
        
        # Verifica integridade
        assert msg.sender_id == msg_restored.sender_id
        assert msg.timestamp == msg_restored.timestamp
        assert msg.content == msg_restored.content
        assert msg.message_type == msg_restored.message_type
        
        print(f"✓ Serialização funcionando: {msg.message_id[:8]}...")
        
        # Testa ACK
        ack = MessageFactory.create_ack(
            sender_id=2,
            timestamp=6,
            original_message_id=msg.message_id
        )
        
        ack_json = ack.to_json()
        ack_restored = ack.from_json(ack_json)
        
        assert ack.original_message_id == ack_restored.original_message_id
        print(f"✓ ACK serialização funcionando")
        
    except Exception as e:
        print(f"✗ Erro no teste de serialização: {e}")
        return False
    
    print("✓ Teste de serialização concluído")
    return True

def test_network_basic():
    """Testa funcionalidade básica de rede."""
    print("\n=== Teste 4: Rede Básica ===")
    
    from network import NetworkManager
    from message import MessageFactory
    
    try:
        # Cria dois gerenciadores de rede
        net1 = NetworkManager(1, port=8001)
        net2 = NetworkManager(2, port=8002)
        
        messages_received = []
        
        def on_message(msg):
            messages_received.append(msg)
        
        net2.on_message_received = on_message
        
        # Inicia servidores
        net1.start_server()
        net2.start_server()
        
        time.sleep(0.5)  # Aguarda inicialização
        
        # Registra processos
        net1.register_process(2, 'localhost', 8002)
        net2.register_process(1, 'localhost', 8001)
        
        # Envia mensagem
        msg = MessageFactory.create_multicast(
            sender_id=1,
            timestamp=1,
            content="Teste de rede",
            recipients=[2]
        )
        
        success = net1.send_message(msg, 2)
        assert success, "Envio deve ser bem-sucedido"
        
        time.sleep(1.0)  # Aguarda recebimento
        
        assert len(messages_received) > 0, "Mensagem deve ser recebida"
        received_msg = messages_received[0]
        assert received_msg.content == "Teste de rede"
        
        print(f"✓ Mensagem enviada e recebida: '{received_msg.content}'")
        
        # Para servidores
        net1.stop_server()
        net2.stop_server()
        
    except Exception as e:
        print(f"✗ Erro no teste de rede: {e}")
        return False
    
    print("✓ Teste de rede básica concluído")
    return True

def run_demo_simulation():
    """Executa uma simulação de demonstração."""
    print("\n=== Simulação de Demonstração ===")
    
    from process import DistributedProcess
    import random
    
    processes = []
    
    try:
        # Cria 3 processos
        for i in range(3):
            process = DistributedProcess(i, port=8010 + i)
            processes.append(process)
        
        # Inicia todos os processos
        for i, process in enumerate(processes):
            other_processes = [j for j in range(3) if j != i]
            process.start(known_processes=other_processes)
            time.sleep(0.3)
        
        print("✓ Todos os processos iniciados")
        
        # Simula envio de mensagens
        messages = [
            "Primeira mensagem do sistema",
            "Segunda mensagem concorrente",
            "Terceira mensagem para teste",
            "Mensagem final de demonstração"
        ]
        
        for i, msg in enumerate(messages):
            sender = random.choice(processes)
            sender.send_multicast_message(f"[{i+1}] {msg}")
            time.sleep(1.0)
        
        print("✓ Mensagens enviadas")
        
        # Aguarda processamento
        time.sleep(3.0)
        
        # Mostra logs de cada processo
        for i, process in enumerate(processes):
            events = process.get_event_log(last_n=10)
            print(f"\n--- Log do Processo {i} ---")
            for event in events[-5:]:  # Últimos 5 eventos
                print(f"L:{event['lamport_time']:3d} {event['event_type']:8s} {event['description']}")
        
        # Para todos os processos
        for process in processes:
            process.stop()
        
        print("\n✓ Simulação de demonstração concluída")
        return True
        
    except Exception as e:
        print(f"✗ Erro na simulação: {e}")
        
        # Limpa processos em caso de erro
        for process in processes:
            try:
                process.stop()
            except:
                pass
        
        return False

def main():
    """Executa todos os testes."""
    print("SISTEMA DE TESTES - RELIABLE MULTICAST COM LAMPORT CLOCK")
    print("=" * 60)
    print(f"Início dos testes: {datetime.now().strftime('%H:%M:%S')}")
    
    tests = [
        ("Relógio de Lamport", test_lamport_clock),
        ("Serialização de Mensagens", test_message_serialization),
        ("Rede Básica", test_network_basic),
        ("Processo Único", test_single_process),
        ("Simulação Completa", run_demo_simulation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- Executando: {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name}: PASSOU")
            else:
                print(f"✗ {test_name}: FALHOU")
        except Exception as e:
            print(f"✗ {test_name}: ERRO - {e}")
    
    print(f"\n" + "=" * 60)
    print(f"RESULTADO FINAL: {passed}/{total} testes passaram")
    print(f"Fim dos testes: {datetime.now().strftime('%H:%M:%S')}")
    
    if passed == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 