# OCI Always Free Monitor 🚀

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Redis](https://img.shields.io/badge/Redis-7.0--alpine-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C.svg?logo=prometheus&logoColor=white)](https://prometheus.io)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5.svg?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)
[![Tests](https://img.shields.io/badge/Tests-41%20Passed-success.svg?logo=pytest&logoColor=white)](backend/tests/)

Dashboard moderno, responsivo e conteinerizado para monitoramento em tempo real e projetado dos recursos do plano **Always Free** da **Oracle Cloud Infrastructure (OCI)**. Previne cobranças acidentais, calcula a taxa de queima mensal (*burn-rate*), audita chamadas de API contra limites de cota, identifica **recursos órfãos** (discos desvinculados e IPs fixos desalocados) e oferece **observabilidade nativa para Prometheus e Kubernetes** (Liveness, Readiness, Startup Probes e Swagger/OpenAPI 100% tipado).

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
* **Reverse Proxy Nginx:** Servindo o bundle React estático e roteando chamadas `/api/`, `/metrics` e probes sem problemas de CORS.

### 10. Observabilidade Nativa & Prontidão para Kubernetes ☸️
* **Prometheus `/metrics`:** Exporta métricas padrão de runtime Python, tráfego HTTP e métricas de negócio OCI em tempo real via `prometheus-client`.
* **Kubernetes Lifecycle Probes:** Endpoints dedicados `/livez`, `/readyz` e `/startupz` com status codes semânticos (200 / 503).
* **Swagger/OpenAPI 100% Tipado:** Todos os endpoints com esquemas Pydantic v2 documentados em `/docs` e `/redoc`.

---

## 🏛️ Arquitetura do Sistema

```mermaid
flowchart TD
    subgraph K8S["Kubernetes Cluster & Observability"]
        PROM["Prometheus Server"] -->|Scrape GET /metrics| FastAPI_Backend
        K_LIVE["Kubelet (Liveness)"] -->|GET /livez| FastAPI_Backend
        K_READY["Kubelet (Readiness)"] -->|GET /readyz| FastAPI_Backend
        K_START["Kubelet (Startup)"] -->|GET /startupz| FastAPI_Backend
    end

    subgraph OCI["Oracle Cloud Infrastructure"]
        O1["Compute & Storage APIs"]
        O2["Networking & IP APIs"]
        O3["Database APIs"]
    end

    subgraph FastAPI_Backend["Backend (FastAPI & Async Worker)"]
        W["Background Worker (10 min)"]
        C["OCI Collector (SDK)"]
        R["REST API Routers (/api/v1/*)"]
        P["Observability Router (/metrics, /livez, /readyz, /startupz)"]
        W -->|Executa varredura| C
        C -->|Consulta recursos & conta chamadas| OCI
    end

    subgraph Cache["Cache & Estado"]
        RD[("Redis 7 (In-Memory)")]
        C -->|Salva inventários & cota diária| RD
        R -->|Leituras <3ms| RD
        P -->|Verifica saúde e gauges| RD
    end

    subgraph Web["Nginx & Frontend"]
        NX["Nginx Reverse Proxy (:3000)"]
        FE["React 18 SPA (Dashboard + Abas)"]
        NX -->|Proxy /api/, /metrics, probes| FastAPI_Backend
        NX -->|Serve estáticos| FE
    end

    FE -->|Forçar Coleta (POST /refresh)| NX
```

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Papel |
|---|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide React | SPA moderna com dashboard, alertas de órfãos e abas de inventário |
| **Web Server** | Nginx Alpine | Servidor web estático e proxy reverso para a API, métricas e probes |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, OCI SDK | API REST assíncrona, agregador e validador Pydantic v2 |
| **Observabilidade** | Prometheus Client Python | Exposição de métricas de processo, tráfego HTTP e gauges OCI em `/metrics` |
| **Orquestração K8s** | Probes Liveness, Readiness, Startup | Resiliência e integração nativa com Kubernetes e contêineres |
| **Cache** | Redis 7 Alpine (`--save ""`) | Cache volátil de altíssima velocidade e contador de chamadas de API |
| **Testes** | Pytest, Pytest-Asyncio, Pytest-Mock, HTTPX | Suíte com 100% de mocks para isolamento completo e testes E2E |
| **Orquestração Local**| Docker & Docker Compose | Inicialização completa da stack com um único comando |

---

## 📊 Observabilidade & Métricas com Prometheus (`/metrics`)

O endpoint `GET /metrics` implementa a especificação oficial do **Prometheus (versão 0.0.4 texto)**. Ele expõe métricas de latência HTTP e o estado dos recursos Always Free da OCI diretamente no scrape.

### Métricas Expostas

| Métrica | Tipo | Descrição |
|---|---|---|
| `http_requests_total` | Counter | Total de requisições HTTP recebidas por método, endpoint e status code |
| `http_request_duration_seconds` | Histogram | Latência de requisições HTTP em segundos |
| `oci_storage_block_allocated_gb` | Gauge | Total de GB alocados em volumes de boot e blocos |
| `oci_storage_block_limit_gb` | Gauge | Limite gratuito de armazenamento em blocos (200 GB) |
| `oci_storage_orphan_volumes_count` | Gauge | Quantidade de volumes órfãos (desvinculados de instâncias ativas) |
| `oci_storage_orphan_wasted_gb` | Gauge | Total de GB desperdiçados em volumes órfãos |
| `oci_storage_object_standard_gb` | Gauge | Uso de Object Storage Standard em GB |
| `oci_storage_object_archive_gb` | Gauge | Uso de Object Storage Archive em GB |
| `oci_compute_ampere_ocpus_allocated` | Gauge | Total de OCPUs alocadas em instâncias Ampere A1 (Arm) |
| `oci_compute_ampere_ocpus_limit` | Gauge | Limite de OCPUs Ampere A1 (4.0 OCPUs) |
| `oci_compute_ampere_memory_gb_allocated` | Gauge | Memória RAM alocada em instâncias Ampere A1 em GB |
| `oci_compute_ampere_memory_gb_limit` | Gauge | Limite de memória Ampere A1 (24 GB) |
| `oci_compute_ampere_instances_count` | Gauge | Número de instâncias Ampere A1 ativas |
| `oci_compute_amd_micro_instances` | Gauge | Número de instâncias AMD E2.1.Micro ativas (limite: 2) |
| `oci_network_vcns_count` | Gauge | Número de Virtual Cloud Networks (VCNs) ativas |
| `oci_network_reserved_ips_count` | Gauge | Quantidade de IPs públicos reservados em uso |
| `oci_network_unassigned_ips_count` | Gauge | Quantidade de IPs fixos reservados desalocados (órfãos) |
| `oci_network_ephemeral_ips_count` | Gauge | Quantidade de IPs públicos efêmeros |
| `oci_database_autonomous_count` | Gauge | Número de bancos autônomos ativos |
| `oci_database_storage_gb` | Gauge | Storage alocado em bancos autônomos em GB |
| `oci_api_calls_today` | Gauge | Total de chamadas OCI SDK realizadas no dia (UTC) |
| `oci_api_daily_limit` | Gauge | Limite diário configurado de chamadas OCI |
| `oci_collector_status` | Gauge | Status da coleta OCI (`1` = saudável, `0` = com erro) |
| `oci_collector_last_scrape_timestamp`| Gauge | Timestamp UNIX da última coleta bem-sucedida |

### Exemplo de Configuração no `prometheus.yml`

```yaml
scrape_configs:
  - job_name: "oci-always-free-monitor"
    scrape_interval: 30s
    metrics_path: "/metrics"
    static_configs:
      - targets: ["oci-backend:8000"]
```

---

## ☸️ Probes de Ciclo de Vida do Kubernetes

Projetado para rodar como Pod em clusters Kubernetes com resiliência de produção:

| Probe | Endpoint | Status Sucesso | Status Falha | Comportamento & Melhores Práticas |
|---|---|---|---|---|
| **Liveness Probe** | `GET /livez` | `200 OK` | `N/A` | Checa se o loop de eventos e processo estão vivos. **Não** falha por dependência externa para evitar reinicializações em cascata. |
| **Readiness Probe** | `GET /readyz` | `200 OK` | `503 Unavailable` | Checa conectividade ativa com o Redis e validade do arquivo OCI config. Remove o pod do balanceador caso o Redis caia. |
| **Startup Probe** | `GET /startupz` | `200 OK` | `503 Unavailable` | Retorna 200 apenas após o término do `lifespan` do FastAPI. Protege inicializações lentas em pods com recursos restritos. |
| **General Health** | `GET /healthz` | `200 OK` | `503 Unavailable` | Checagem consolidada geral da saúde da aplicação. |

### Exemplo de Manifesto Kubernetes (`Deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oci-always-free-monitor
  labels:
    app: oci-monitor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oci-monitor
  template:
    metadata:
      labels:
        app: oci-monitor
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: backend
          image: oci-always-free-backend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              name: http
          env:
            - name: REDIS_URL
              value: "redis://redis-service:6379/0"
            - name: OCI_CONFIG_FILE
              value: "/root/.oci/config"
          volumeMounts:
            - name: oci-credentials
              mountPath: /root/.oci
              readOnly: true
          # Startup Probe: aguarda inicialização da aplicação
          startupProbe:
            httpGet:
              path: /startupz
              port: 8000
            failureThreshold: 30
            periodSeconds: 5
          # Liveness Probe: verifica se a aplicação não travou
          livenessProbe:
            httpGet:
              path: /livez
              port: 8000
            periodSeconds: 10
            timeoutSeconds: 3
          # Readiness Probe: verifica conectividade com Redis e OCI
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8000
            periodSeconds: 10
            timeoutSeconds: 3
      volumes:
        - name: oci-credentials
          secret:
            secretName: oci-config-secret
```

---

## 📚 Documentação Swagger & OpenAPI

A API conta com documentação interativa gerada automaticamente e tipada via Pydantic v2:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **OpenAPI Schema (JSON):** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Catálogo de Endpoints

| Método | Endpoint | Tag / Grupo | Descrição | Códigos de Retorno |
|---|---|---|---|---|
| `GET` | `/` | General | Metadados da API, Swagger e Prometheus URLs | `200` |
| `GET` | `/metrics` | Observability & Metrics | Exposição de métricas Prometheus text 0.0.4 | `200` |
| `GET` | `/livez` | Kubernetes Probes | Liveness probe do Kubernetes | `200` |
| `GET` | `/readyz` | Kubernetes Probes | Readiness probe (Redis + OCI) | `200`, `503` |
| `GET` | `/startupz` | Kubernetes Probes | Startup probe de inicialização | `200`, `503` |
| `GET` | `/healthz` | Kubernetes Probes | Health check consolidado | `200`, `503` |
| `GET` | `/api/v1/health` | metrics | Health check retrocompatível | `200` |
| `GET` | `/api/v1/summary` | metrics | Resumo consolidado dos recursos OCI | `200`, `503` |
| `POST`| `/api/v1/refresh` | metrics | Forçar varredura imediata na OCI | `200`, `500` |
| `GET` | `/api/v1/storage/volumes`| metrics | Inventário de Boot e Block Volumes (órfãos) | `200`, `503` |
| `GET` | `/api/v1/network/inventory` | metrics | Inventário de VCNs, IPs públicos e LBs | `200`, `503` |
| `GET` | `/api/v1/database/inventory`| metrics | Inventário de Autonomous Databases | `200`, `503` |

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
| `DISABLE_BACKGROUND_WORKER` | `false` | Permite desabilitar o worker de fundo durante testes |

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
* **Métricas Prometheus:** `GET http://localhost:8000/metrics` (ou via proxy `http://localhost:3000/metrics`)
* **Kubernetes Liveness Probe:** `GET http://localhost:8000/livez`
* **Kubernetes Readiness Probe:** `GET http://localhost:8000/readyz`
* **Kubernetes Startup Probe:** `GET http://localhost:8000/startupz`
* **Resumo Geral & Métricas:** `GET http://localhost:3000/api/v1/summary`
* **Inventário de Volumes:** `GET http://localhost:3000/api/v1/storage/volumes`
* **Inventário de Rede:** `GET http://localhost:3000/api/v1/network/inventory`
* **Inventário de Bancos:** `GET http://localhost:3000/api/v1/database/inventory`
* **Forçar Nova Varredura:** `POST http://localhost:3000/api/v1/refresh`

### 3. Encerrar a Aplicação
```bash
docker compose down
```

---

## 🧪 Suíte de Testes

O projeto adota **Test-Driven Development (TDD)** com mocks abrangentes para permitir execução ágil sem depender da infraestrutura externa da Oracle:

```bash
# Executar todos os testes unitários (41 testes cobrindo collector, api, cache, config e observabilidade)
.venv/bin/pytest backend/tests/ -v

# Executar testes End-to-End contra a stack conteinerizada
.venv/bin/pytest tests/e2e/test_e2e_stack.py -v
```

---

## 🔒 Segurança de Credenciais & Resolução de Chaves

* O container do backend monta `~/.oci` e `~/.ssh` em modo **somente leitura** (`:ro`), garantindo que nenhuma alteração seja feita nas suas chaves do host.
* O módulo `config.py` implementa normalização defensiva do campo `key_file`: resolve automaticamente referências como `~` e ajusta caminhos absolutos do host para o contexto interno do container (`/root/.oci` ou `/root/.ssh`).
