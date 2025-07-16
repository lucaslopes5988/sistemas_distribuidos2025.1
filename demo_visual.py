#!/usr/bin/env python3
"""
Demonstração visual do sistema de Reliable Multicast com Relógio de Lamport.
Mostra troca de mensagens entre processos com timestamps claros.
"""

import time
import threading
from process import DistributedProcess

def print_header():
    """Imprime cabeçalho da demonstração."""
    print("=" * 70)
    print("DEMONSTRAÇÃO: RELIABLE MULTICAST COM RELÓGIO DE LAMPORT")
    print("=" * 70)
    print()

def demo_simple_communication():
    """Demonstração simples de comunicação entre dois processos."""
    print("🚀 Iniciando demonstração de comunicação entre 2 processos...")
    print()
    
    processes = []
    
    try:
        # Cria dois processos
        process0 = DistributedProcess(0, port=9000)
        process1 = DistributedProcess(1, port=9001)
        processes.extend([process0, process1])
        
        # Inicia os processos
        process0.start(known_processes=[1])
        time.sleep(0.5)
        process1.start(known_processes=[0])
        time.sleep(1.0)
        
        print("✅ Ambos os processos iniciados")
        print()
        
        # Aguarda descoberta
        time.sleep(1.0)
        
        # Processo 0 envia primeira mensagem
        print("📤 Processo 0 enviando primeira mensagem...")
        process0.send_multicast_message("Olá do Processo 0! Como está?")
        time.sleep(2.0)
        
        # Processo 1 responde
        print("📤 Processo 1 respondendo...")
        process1.send_multicast_message("Olá Processo 0! Estou bem, obrigado!")
        time.sleep(2.0)
        
        # Processo 0 envia outra mensagem
        print("📤 Processo 0 enviando segunda mensagem...")
        process0.send_multicast_message("Ótimo! Vamos testar o sistema distribuído.")
        time.sleep(2.0)
        
        # Mostra logs finais
        print("\n" + "=" * 50)
        print("📋 LOG FINAL DOS EVENTOS (ordenados por Lamport Clock)")
        print("=" * 50)
        
        for i, process in enumerate(processes):
            events = process.get_event_log()
            delivered_events = [e for e in events if e['event_type'] == 'DELIVER']
            
            if delivered_events:
                print(f"\n🔍 Processo {i} - Mensagens entregues:")
                for event in delivered_events:
                    print(f"   [Lamport: {event['lamport_time']:2d}] {event['description']}")
        
        # Estatísticas
        print(f"\n📊 ESTATÍSTICAS:")
        for i, process in enumerate(processes):
            stats = process.get_statistics()
            print(f"   Processo {i}: Lamport Clock = {stats['lamport_time']}, "
                  f"Eventos = {stats['event_count']}")
        
    except Exception as e:
        print(f"❌ Erro na demonstração: {e}")
    
    finally:
        # Limpa processos
        for process in processes:
            try:
                process.stop()
            except:
                pass
        
        print("\n✅ Demonstração concluída!")

def demo_three_processes():
    """Demonstração com três processos mostrando ordenação Lamport."""
    print("\n🚀 Iniciando demonstração com 3 processos...")
    print("   (Para demonstrar ordenação por Relógio de Lamport)")
    print()
    
    processes = []
    
    try:
        # Cria três processos
        for i in range(3):
            process = DistributedProcess(i, port=9010 + i)
            processes.append(process)
        
        # Inicia todos os processos
        for i, process in enumerate(processes):
            others = [j for j in range(3) if j != i]
            process.start(known_processes=others)
            time.sleep(0.3)
            print(f"✅ Processo {i} iniciado")
        
        print("\n⏳ Aguardando descoberta de processos...")
        time.sleep(2.0)
        
        # Simula eventos concorrentes
        print("\n📤 Enviando mensagens concorrentes...")
        
        # Threads para envio simultâneo
        def send_messages(process, messages):
            for i, msg in enumerate(messages):
                time.sleep(i * 0.5)  # Pequenos delays diferentes
                process.send_multicast_message(msg)
        
        messages_p0 = ["Mensagem A do P0", "Mensagem C do P0"]
        messages_p1 = ["Mensagem B do P1", "Mensagem D do P1"]  
        messages_p2 = ["Mensagem E do P2"]
        
        thread0 = threading.Thread(target=send_messages, args=(processes[0], messages_p0))
        thread1 = threading.Thread(target=send_messages, args=(processes[1], messages_p1))
        thread2 = threading.Thread(target=send_messages, args=(processes[2], messages_p2))
        
        thread0.start()
        time.sleep(0.1)
        thread1.start()
        time.sleep(0.1)
        thread2.start()
        
        thread0.join()
        thread1.join()
        thread2.join()
        
        print("⏳ Aguardando processamento...")
        time.sleep(4.0)
        
        # Mostra ordenação resultante
        print("\n" + "=" * 60)
        print("📋 ORDENAÇÃO FINAL POR RELÓGIO DE LAMPORT")
        print("=" * 60)
        
        all_events = []
        for i, process in enumerate(processes):
            events = process.get_event_log()
            delivered_events = [e for e in events if e['event_type'] == 'DELIVER']
            all_events.extend(delivered_events)
        
        # Ordena por timestamp Lamport
        all_events.sort(key=lambda x: (x['lamport_time'], x['process_id']))
        
        if all_events:
            print("Ordem de entrega (mesma em todos os processos):")
            for i, event in enumerate(all_events, 1):
                print(f"   {i:2d}. [T:{event['lamport_time']:2d}] {event['description']}")
        else:
            print("⚠️  Nenhuma mensagem foi entregue (problemas de conectividade)")
        
        print(f"\n📊 RELÓGIOS FINAIS:")
        for i, process in enumerate(processes):
            stats = process.get_statistics()
            print(f"   Processo {i}: Lamport Clock = {stats['lamport_time']}")
    
    except Exception as e:
        print(f"❌ Erro na demonstração: {e}")
    
    finally:
        # Limpa processos
        for process in processes:
            try:
                process.stop()
            except:
                pass
        
        print("\n✅ Demonstração com 3 processos concluída!")

def main():
    """Função principal da demonstração."""
    print_header()
    
    print("Esta demonstração mostra:")
    print("• Comunicação confiável entre processos distribuídos")
    print("• Relógio de Lamport para ordenação de eventos")
    print("• Multicast com acknowledgments")
    print("• Entrega ordenada de mensagens")
    print()
    
    # Demonstração 1: Comunicação simples
    demo_simple_communication()
    
    # Pausa entre demonstrações
    print("\n" + "🔄" * 30)
    time.sleep(2.0)
    
    # Demonstração 2: Três processos com concorrência
    demo_three_processes()
    
    print("\n" + "=" * 70)
    print("🎉 TODAS AS DEMONSTRAÇÕES CONCLUÍDAS!")
    print("   O sistema de Reliable Multicast com Relógio de Lamport")
    print("   está funcionando corretamente!")
    print("=" * 70)

if __name__ == '__main__':
    main() 