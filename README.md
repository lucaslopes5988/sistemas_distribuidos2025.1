# Sistema de Reliable Multicast com Relógio de Lamport

Este projeto implementa um sistema distribuído que demonstra o protocolo de **Reliable Multicast** associado ao **Relógio de Lamport** para ordenação lógica de eventos em ambiente assíncrono.

## 🎯 Objetivo

Desenvolver uma aplicação distribuída que:
- Implementa comunicação confiável via multicast entre processos
- Utiliza o Relógio de Lamport para ordenação lógica de eventos
- Permite visualização em tempo real dos eventos e timestamps
- Demonstra conceitos fundamentais de sistemas distribuídos

## 🏗️ Arquitetura

O sistema é composto pelos seguintes componentes:

### Componentes Principais

1. **LamportClock** (`lamport_clock.py`)
   - Implementa o relógio lógico de Lamport
   - Gerencia incremento e sincronização de timestamps
   - Thread-safe para uso concorrente

2. **ReliableMulticast** (`reliable_multicast.py`)
   - Protocolo de multicast confiável
   - Acknowledgments e retransmissões
   - Ordenação de mensagens por timestamp

3. **NetworkManager** (`network.py`)
   - Comunicação via sockets TCP
   - Servidor para receber mensagens
   - Cliente para enviar mensagens

4. **DistributedProcess** (`process.py`)
   - Processo distribuído principal
   - Integra todos os componentes
   - Interface de usuário interativa

5. **Message** (`message.py`)
   - Estruturas de mensagens (Multicast, ACK)
   - Serialização JSON
   - Factory para criação de mensagens

### Componentes Auxiliares

- **Visualizador** (`visualizer.py`) - Monitor em tempo real
- **Sistema Principal** (`main.py`) - Scripts de execução
- **Testes** (`test_system.py`) - Validação automatizada

## 🚀 Instalação e Execução

### Pré-requisitos

- Python 3.7 ou superior
- Sistema operacional: Windows, Linux ou macOS

### Instalação

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd sist_dist_lamport

# Nenhuma dependência externa necessária
# O projeto usa apenas bibliotecas padrão do Python
```

### Execução

#### 1. Demonstração Automática (Recomendado)

```bash
# Executa demonstração com 3 processos
python main.py --demo

# Executa demonstração com N processos
python main.py --demo --num-processes 4
```
Observação importante: usar "python3" nos comandos ao invés "python" a depender de como a sua variável de ambiente python esteja configurada.

#### 2. Processos Individuais

Em terminais separados:

```bash
# Terminal 1 - Processo 0
python main.py 0 --processes 1,2

# Terminal 2 - Processo 1  
python main.py 1 --processes 0,2

# Terminal 3 - Processo 2
python main.py 2 --processes 0,1
```

#### 3. Visualizador (Opcional)

Em terminal separado:

```bash
python visualizer.py
```

#### 4. Testes Automatizados

```bash
python test_system.py
```

## 🎮 Como Usar

### Comandos do Processo

Após iniciar um processo, você pode usar os seguintes comandos:

- `msg <conteúdo>` - Envia mensagem multicast
- `log [n]` - Mostra log de eventos (últimos n)
- `stats` - Exibe estatísticas do processo
- `discover` - Descobre processos online
- `quit` - Para o processo

### Exemplo de Uso

```
P0> msg Olá mundo distribuído!
Mensagem enviada: a1b2c3d4...

P0> log 5
--- Log de Eventos (últimos 5) ---
[14:30:15] L:  1 SYSTEM   Processo 0 iniciado
[14:30:20] L:  2 SEND     Enviando: 'Olá mundo distribuído!' para todos
[14:30:20] L:  3 DELIVER  De P1 (T:4): 'Resposta do processo 1'
[14:30:25] L:  5 DELIVER  De P2 (T:6): 'Mensagem do processo 2'

P0> stats
--- Estatísticas do Processo 0 ---
process_id: 0
running: True
uptime: 0:02:15.123456
lamport_time: 5
address: localhost:8000
known_processes: 2
event_count: 12
Multicast:
  pending_messages: 0
  queue_size: 0
  delivered_messages: 8
  known_processes: 3
```

## 🔧 Algoritmos Implementados

### Relógio de Lamport

```python
# Evento local
timestamp = clock.tick()  # incrementa relógio

# Recebimento de mensagem
timestamp = clock.update(received_timestamp)  # sincroniza
# clock = max(local_clock, received_timestamp) + 1
```

### Multicast Confiável

1. **Envio**: Processo envia mensagem para todos os destinatários
2. **Acknowledgment**: Destinatários enviam ACK de volta
3. **Retransmissão**: Reenvia se ACK não recebido (timeout)
4. **Ordenação**: Entrega mensagens ordenadas por timestamp Lamport
5. **Detecção de Duplicatas**: Ignora mensagens já recebidas

### Ordenação por Timestamp

```python
# Critério de ordenação
if msg1.timestamp < msg2.timestamp:
    return msg1_first
elif msg1.timestamp == msg2.timestamp:
    return msg1 if msg1.sender_id < msg2.sender_id else msg2
else:
    return msg2_first
```

## 📊 Exemplo de Execução

```
=== Processo 0 ===
[8000] Processo iniciado
[8000] Enviou multicast: Primeira mensagem (T:1)
[8000] ACK recebido de 1 para mensagem (1/2)
[8000] ACK recebido de 2 para mensagem (2/2)
[8000] ✓ ENTREGOU mensagem: sender=1, timestamp=3, content='Resposta rápida'

=== Processo 1 ===  
[8001] Processo iniciado
[8001] Recebeu multicast: Primeira mensagem (T:1)
[8001] ✓ ENTREGOU mensagem: sender=0, timestamp=1, content='Primeira mensagem'
[8001] Enviou multicast: Resposta rápida (T:3)

=== Processo 2 ===
[8002] Processo iniciado  
[8002] Recebeu multicast: Primeira mensagem (T:1)
[8002] ✓ ENTREGOU mensagem: sender=0, timestamp=1, content='Primeira mensagem'
[8002] ✓ ENTREGOU mensagem: sender=1, timestamp=3, content='Resposta rápida'
```

## 📁 Estrutura do Projeto

```
sist_dist_lamport/
├── lamport_clock.py      # Relógio de Lamport
├── message.py            # Estruturas de mensagens
├── reliable_multicast.py # Protocolo multicast confiável
├── network.py            # Gerenciamento de rede
├── process.py            # Processo distribuído principal
├── main.py              # Script principal
├── visualizer.py        # Visualizador de eventos
├── test_system.py       # Testes automatizados
├── requirements.txt     # Dependências (vazio - só Python padrão)
└── README.md           # Documentação
```

## 🧪 Testes

Execute os testes automatizados:

```bash
python test_system.py
```

Testes incluem:
- ✅ Relógio de Lamport (incremento e sincronização)
- ✅ Serialização de mensagens
- ✅ Comunicação de rede básica
- ✅ Processo único
- ✅ Simulação completa com múltiplos processos

## 🔍 Características Técnicas

### Confiabilidade
- **Acknowledgments**: Confirmação de recebimento
- **Retransmissão**: Até 3 tentativas com timeout de 5s
- **Detecção de Duplicatas**: Mensagens não são reprocessadas

### Ordenação
- **Relógio de Lamport**: Ordenação causal de eventos
- **Desempate**: Por ID do processo em caso de timestamps iguais
- **Entrega Ordenada**: Mensagens entregues em ordem lógica

### Escalabilidade
- **Thread-Safe**: Componentes preparados para concorrência
- **Assíncrono**: Operações não bloqueantes
- **Modular**: Componentes independentes e reutilizáveis

## 🎓 Conceitos Demonstrados

1. **Sistemas Distribuídos**
   - Comunicação entre processos
   - Tolerância a falhas
   - Coordenação distribuída

2. **Relógio de Lamport**
   - Ordenação lógica de eventos
   - Relação causal entre eventos
   - Sincronização de relógios

3. **Multicast Confiável**
   - Entrega garantida
   - Acknowledgments
   - Retransmissão

4. **Programação Concorrente**
   - Threading
   - Locks e sincronização
   - Comunicação entre threads

## 👥 Autores

- **Equipe**: Beatriz Bacelar, Beatriz Cerqueira, Iasmim Marinho, Lucas Lopes, Reginaldo Silva
- **Disciplina**: Fundamentos de Computação Distribuída
- **Professor**: Raimundo Macedo
- **Data**: 16/07/2025

## 📄 Licença

Este projeto é desenvolvido para fins acadêmicos.

---

**Para dúvidas ou problemas, consulte a documentação no código ou execute os testes automatizados.**
