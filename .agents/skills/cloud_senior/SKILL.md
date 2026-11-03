# Role & Objetivo
Você é um Arquiteto de Cloud sênior, especialista em Oracle Cloud Infrastructure (OCI), DevOps e Engenheiro Full-Stack (Python/FastAPI e React/Tailwind). 
Sua missão é projetar, estruturar e implementar do zero a aplicação **OCI Always Free Monitor**: um dashboard moderno, responsivo e conteinerizado que roda localmente para monitorar cotas, alocações e o consumo acumulado de recursos do plano Always Free da OCI, prevenindo custos acidentais.

---

## 1. Stack Tecnológica
* **Backend:** Python 3.11+, FastAPI, Uvicorn, OCI Python SDK (`oci`), Redis client (`redis-py` assíncrono), Pydantic v2.
* **Cache & Mensageria:** Redis 7 (Alpine), operando puramente em memória (sem persistência AOF/RDB para evitar desgaste de I/O local).
* **Frontend:** React 18+ (Vite), Tailwind CSS, Lucide React (ícones), Recharts (para gráficos e projeções de consumo).
* **Infraestrutura:** Docker e Docker Compose, com multi-stage build para servir o frontend integrado ao FastAPI ou containers desacoplados via compose.

---

## 2. Requisitos de Negócio e Cotas Always Free

O coletor deve monitorar com precisão os seguintes limites da OCI:
1. **Armazenamento de Blocos (Total: 200 GB):**
   * Somar recursivamente todos os Boot Volumes e Block Volumes em **todos os compartimentos** da tenancy (usando busca recursiva a partir do root compartment).
   * Identificar e sinalizar **Discos Órfãos** (Boot Volumes que não possuem nenhuma instância associada).
2. **Compute Ampere A1 (Arm):**
   * Limite de 4 OCPUs e 24 GB de memória RAM combinados.
   * Total acumulado de até 3.000 OCPU-horas e 18.000 GB-horas no mês corrente.
3. **Compute AMD Micro:**
   * Limite de 2 instâncias ativas com shape `VM.Standard.E2.1.Micro`.
4. **Armazenamento de Objetos (Object Storage):**
   * Limite de 10 GB no tier Standard e 10 GB no tier Infrequente/Arquivo.
5. **Tráfego de Saída (Data Egress):**
   * Limite de 10 TB/mês para a internet.
6. **Projeção de Consumo (Burn-Rate):**
   * Calcular a taxa de queima diária média e projetar o consumo final até o último dia do ciclo de faturamento mensal:
     Consumo_Projetado = (Consumo_Atual / Dias_Transcorridos) * Dias_Totais_Do_Mes

---

## 3. Arquitetura de Coleta e Cache (Redis + Worker)

Para evitar latência de 2 a 5 segundos nas chamadas da OCI e prevenir rate limiting (`HTTP 429`):
* **Background Worker:** Crie uma rotina assíncrona que executa a cada 10 minutos (configurável via variável de ambiente), consome as APIs da OCI, processa as regras de negócio e salva o payload final consolidado no Redis na chave `oci:free_tier:summary` com TTL de 15 minutos.
* **Fallback & Stale Cache:** Se a API da OCI falhar ou expirar o tempo limite, o backend deve continuar servindo a última leitura válida armazenada com o timestamp da coleta (`stale-while-revalidate`).
* **FastAPI Endpoints:**
  * `GET /api/v1/summary`: Retorna em <5ms os dados consolidados gravados no Redis.
  * `POST /api/v1/refresh`: Força a execução manual do worker em background, invalidando o cache e retornando os dados atualizados.
  * `GET /api/v1/storage/volumes`: Retorna a lista detalhada de volumes com status de vinculação (instância anexada vs. órfão).

---

## 4. Cuidados Especiais de Execução e OCI SDK

1. **Normalização do Caminho de Chave (`key_file`):**
   * O container montará o diretório local em `/root/.oci:ro`.
   * No arquivo `~/.oci/config`, a diretiva `key_file` frequentemente contém caminhos absolutos do host (ex.: `/home/user/.oci/chave.pem`).
   * No carregamento da configuração via `oci.config.from_file()`, implemente uma lógica defensiva: se o arquivo apontado em `key_file` não existir no caminho absoluto informado, extraia o nome base do arquivo e aponte para `/root/.oci/<nome_do_arquivo.pem>`.
2. **Latência da Usage API vs. Block Storage:**
   * A `UsageapiClient` possui delay de 4 a 24 horas para métricas financeiras.
   * Para capacidade de discos e instâncias ativas, consulte **obrigatoriamente** o inventário direto (`BlockstorageClient` e `ComputeClient`) para refletir o estado real e imediato.
3. **Tratamento de Permissões:**
   * Capture e formate erros de permissões (ex.: permissão de chave privada aberta ou falta de privilégio IAM no compartimento), retornando mensagens amigáveis no log e na UI.

---

## 5. Interface do Usuário (React + Tailwind)

A interface deve ser moderna, limpa e com tema escuro (Dark Theme prioritário):
* **Header:** Status da conexão com a OCI, tenancy identificada, data/hora da última sincronização e botão interativo "Sincronizar Agora" com estado de loading.
* **Cards de Visão Geral (Gauges / Barras de Progresso):**
  * Storage de Bloco (GB utilizados / 200 GB).
  * OCPUs Ampere (Alocadas / 4 OCPUs) e RAM Ampere (Alocada / 24 GB).
  * Instâncias Micro AMD (Ativas / 2).
  * Object Storage (GB consumidos / 10 GB).
  * Cores dinâmicas: Verde (<75%), Laranja (75%–90%), Vermelho (>90%).
* **Seção de Alerta de Discos Órfãos:** Um card de destaque quando houver volumes de boot ou blocos sem vínculo ativo, indicando quanto espaço em GB eles estão desperdiçando.
* **Card de Projeção Mensal (Burn-Rate):** Indicador visual alertando se a projeção de OCPU-horas ou Egress corre risco de exceder o teto gratuito antes do fechamento do mês.

---

## 6. Estrutura do Repositório Sugerida
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py             # Normalização do ~/.oci/config
│   ├── services/
│   │   ├── oci_collector.py  # Interação com OCI SDK (Compute, Storage, Usage)
│   │   ├── cache.py          # Gerenciamento de conexão e payloads no Redis
│   │   └── worker.py         # Tarefas periódicas de coleta
│   └── routers/
│       └── metrics.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tailwind.config.js
│   └── src/
│       ├── components/       # Cards, ProgressBars, Alertas
│       ├── hooks/            # SWR ou React Query para polling
│       └── App.jsx

---

## 7. Instruções de Entrega
1. Forneça o código funcional dos arquivos principais (sem omitir regras críticas de normalização de chave e busca recursiva de compartimentos).
2. Configure o `docker-compose.yml` garantindo que o Redis inicie com `--save ""` e que o volume `~/.oci` seja montado em modo somente leitura (`:ro`).
3. Adicione instruções claras no README para execução local rápida com um único comando `docker compose up --build`.



