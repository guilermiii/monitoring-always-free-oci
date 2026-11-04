# OCI Always Free Monitor 🚀

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Redis](https://img.shields.io/badge/Redis-7.0--alpine-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)
[![Tests](https://img.shields.io/badge/Tests-26%20Passed-success.svg?logo=pytest&logoColor=white)](backend/tests/)

Dashboard moderno, responsivo e conteinerizado para monitoramento em tempo real e projetado dos recursos do plano **Always Free** da **Oracle Cloud Infrastructure (OCI)**. Previne cobranças acidentais, calcula a taxa de queima mensal (*burn-rate*), audita chamadas de API contra limites de cota e identifica **recursos órfãos** (discos desvinculados e IPs fixos desalocados) que consomem cota desnecessariamente.

---

## 🌟 Principais Funcionalidades

### 1. Varredura Recursiva de Armazenamento de Blocos (200 GB Total)
* Agrega Boot Volumes e Block Volumes em **todos os compartimentos** ativos da tenancy.
* **Detecção Automática de Discos Órfãos:** Alerta com destaque visual quando há volumes sem nenhuma máquina ativa vinculada, calculando exatamente a quantidade de GB e cota desperdiçada.
* Filtra e desconsidera volumes no estado `TERMINATED` para evitar falsos positivos de cota.

### 2. Compute Ampere A1 (Arm) & AMD Micro
* Monitora alocação combinada de até **4 OCPUs** e **24 GB de memória RAM** nas instâncias Ampere A1.
* Rastreia o consumo acumulado e projetado no mês (limites de 3.000 OCPU-horas e 18.000 GB-horas).
* Contabiliza instâncias `VM.Standard.E2.1.Micro` ativas (limite de 2 simultâneas).

### 3. Armazenamento de Objetos (Object Storage)
* Agrega volumes de buckets nos tiers **Standard** (10 GB) e **Arquivo/Infrequente** (10 GB).

### 4. Rede & Conectividade Always Free
* **VCNs (Virtual Cloud Networks):** Rastreia até 2 VCNs gratuitas e suas respectivas sub-redes IPv4/IPv6.
* **IPs Públicos (Reservados & Efêmeros):** Monitora a cota de 1 IP reservado gratuito e emite alerta de **IP Fixo Órfão/Ocioso** caso exista IP estático desvinculado de qualquer VNIC.
* **Load Balancers:** Monitora 1 Flexible Load Balancer (10 Mbps) e 1 Network Load Balancer (NLB).
* **OCI Bastion:** Rastreia até 2 instâncias do serviço gerenciado de Bastion para acesso seguro.

### 5. Bancos de Dados Always Free (Autonomous Database)
* Monitora até 2 instâncias autônomas (ATP, ADW, JSON, APEX) e soma de armazenamento de até 40 GB.
* Exibe workload type, storage alocado e estado de ciclo de vida (`AVAILABLE`, `STOPPED`, etc.).

### 6. Rastreamento de Chamadas de API OCI & Cota Diária 🛡️
* **Contador de API em Tempo Real:** Mede com precisão cada chamada realizada aos SDKs da OCI durante as varreduras.
* **Persistência Diária no Redis (UTC):** Acumula o volume diário com reset automático à meia-noite UTC (TTL defensivo de 48h).
* **Widget Visual no Header:** Exibe total de chamadas hoje, percentual consumido, total da última varredura e limite configurado.
* **Prevenção Contra Throttling:** Badges de status dinâmicos (`safe` <70%, `warning` 70–90%, `danger` >90%) para respeitar a taxa máxima de 3.000 req/min da OCI.

### 7. Taxa de Queima (*Burn-Rate*) & Projeção Mensal
* Calcula o consumo médio diário e extrapola linearmente até o último dia do ciclo de faturamento.
* Notificações visuais e badges de aviso caso a projeção aponte risco de exceder os limites gratuitos antes do fim do mês.

### 8. Frontend Dinâmico com Abas de Inventário
* Interface construída com Tailwind CSS e Lucide Icons, organizada em abas contextuais:
  * 📁 **Resumo & Discos:** Visão geral da tenancy, métricas de compute/storage e inventário completo de volumes de boot e blocos.
  * 🌐 **Rede & Conectividade:** Painel detalhado de VCNs, Subnets, IPs públicos (com alerta de órfãos), Load Balancers e Bastions.
  * 🗄️ **Bancos de Dados:** Tabela de bancos autônomos com tamanho, tipo e status operacional.

### 9. Alta Performance & Baixa Latência (<3ms)
* **Background Worker Assíncrono:** Consulta a API da OCI em background e popula o Redis.
* **Arquitetura Stale-While-Revalidate:** Endpoints REST respondem a partir da memória do Redis em menos de 3ms.
* **Sincronização Sob Demanda:** Botão *"Sincronizar Agora"* no Header para acionar uma nova varredura instantaneamente.
* **Reverse Proxy Nginx:** Servindo o bundle React estático e roteando chamadas `/api/` sem problemas de CORS.

---

## 🏛️ Arquitetura do Sistema

```mermaid
flowchart TD
    subgraph OCI["Oracle Cloud Infrastructure"]
        O1["Compute & Storage APIs"]
        O2["Networking & IP APIs"]
        O3["Database APIs"]
    end

    subgraph Backend_Worker["Backend (FastAPI & Async Worker)"]
        W["Background Worker (10 min)"]
        C["OCI Collector (SDK)"]
        R["REST API Routers (/api/v1/*)"]
        W -->|Executa varredura| C
        C -->|Consulta recursos & conta chamadas| OCI
    end

    subgraph Cache["Cache & Estado"]
        RD[("Redis 7 (In-Memory)")]
        C -->|Salva inventários & cota diária| RD
        R -->|Leituras <3ms| RD
    end

    subgraph Web["Nginx & Frontend"]
        NX["Nginx Reverse Proxy (:3000)"]
        FE["React 18 SPA (Dashboard + Abas)"]
        NX -->|Proxy /api/| R
        NX -->|Serve estáticos| FE
    end

    FE -->|Forçar Coleta (POST /refresh)| NX
```

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Papel |
|---|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide React | SPA moderna com dashboard, alertas de órfãos e abas de inventário |
| **Web Server** | Nginx Alpine | Servidor web estático e proxy reverso para a API |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, OCI SDK | API REST assíncrona, agregador e validador Pydantic v2 |
| **Cache** | Redis 7 Alpine (`--save ""`) | Cache volátil de altíssima velocidade e contador de chamadas de API |
| **Testes** | Pytest, Pytest-Asyncio, Pytest-Mock, HTTPX | Suíte com 100% de mocks para isolamento completo e testes E2E |
| **Orquestração**| Docker & Docker Compose | Inicialização completa da stack com um único comando |

---

## ⚙️ Variáveis de Ambiente

As seguintes variáveis podem ser configuradas no arquivo `docker-compose.yml` ou em um arquivo `.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `REFRESH_INTERVAL_SECONDS` | `600` (10 min) | Intervalo entre varreduras automáticas em background |
| `CACHE_TTL_SECONDS` | `900` (15 min) | Tempo de expiração (TTL) das chaves de métricas no Redis |
| `REDIS_URL` | `redis://redis:6379/0` | String de conexão para o Redis |
| `OCI_API_DAILY_LIMIT` | `10000` | Limite de segurança diário para chamadas de API OCI |
| `OCI_API_RATE_LIMIT_PER_MIN`| `3000` | Taxa máxima de referência por minuto da OCI |
| `OCI_CONFIG_FILE` | `~/.oci/config` | Caminho do arquivo de configuração do OCI SDK |
| `OCI_CONFIG_PROFILE` | `DEFAULT` | Perfil do OCI config a ser utilizado |

---

## 🚀 Como Executar

### Pré-requisitos
* **Docker** e **Docker Compose** instalados.
* Credenciais da OCI configuradas na máquina local em `~/.oci/config` com a chave privada correspondente.

### 1. Iniciar a Aplicação
Na raiz do projeto, execute:

```bash
docker compose up --build -d
```

### 2. Acessar o Dashboard e Endpoints
* **Frontend SPA:** [http://localhost:3000](http://localhost:3000)
* **Documentação Swagger (OpenAPI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Resumo Geral & Métricas:** `GET http://localhost:3000/api/v1/summary`
* **Inventário de Volumes:** `GET http://localhost:3000/api/v1/storage/volumes`
* **Inventário de Rede (VCNs, IPs, LBs, Bastions):** `GET http://localhost:3000/api/v1/network/inventory`
* **Inventário de Bancos Autônomos:** `GET http://localhost:3000/api/v1/database/inventory`
* **Forçar Nova Varredura:** `POST http://localhost:3000/api/v1/refresh`

### 3. Encerrar a Aplicação
```bash
docker compose down
```

---

## 🧪 Suíte de Testes

O projeto adota **Test-Driven Development (TDD)** com mocks abrangentes para permitir execução ágil sem depender da infraestrutura externa da Oracle:

```bash
# Executar todos os testes unitários (26 testes cobrindo collector, api, cache e config)
.venv/bin/pytest backend/tests/ -v

# Executar testes End-to-End contra a stack conteinerizada
.venv/bin/pytest tests/e2e/test_e2e_stack.py -v
```

---

## 🔒 Segurança de Credenciais & Resolução de Chaves

* O container do backend monta `~/.oci` e `~/.ssh` em modo **somente leitura** (`:ro`), garantindo que nenhuma alteração seja feita nas suas chaves do host.
* O módulo `config.py` implementa normalização defensiva do campo `key_file`: resolve automaticamente referências como `~` e ajusta caminhos absolutos do host para o contexto interno do container (`/root/.oci` ou `/root/.ssh`).
