# OCI Always Free Monitor 🚀

Dashboard moderno, responsivo e conteinerizado para monitoramento em tempo real e projetado dos recursos do plano **Always Free** da **Oracle Cloud Infrastructure (OCI)**. Previne custos acidentais, calcula a taxa de queima mensal (*burn-rate*) e identifica **discos órfãos** que consomem cota desnecessariamente.

---

## 🌟 Principais Funcionalidades

1. **Varredura Recursiva de Armazenamento de Blocos (200 GB Total):**
   * Agrega todos os Boot Volumes e Block Volumes em **todos os compartimentos** da tenancy.
   * **Detecção Automática de Discos Órfãos:** Alerta quando há volumes de boot ou blocos sem nenhuma máquina ativa vinculada, calculando exatamente quantos GB estão sendo desperdiçados.

2. **Compute Ampere A1 (Arm) & AMD Micro:**
   * Monitora alocação de até 4 OCPUs e 24 GB de memória RAM combinados.
   * Rastreia o consumo acumulado e projetado no mês (limite de 3.000 OCPU-horas e 18.000 GB-horas).
   * Contabiliza instâncias ativas `VM.Standard.E2.1.Micro` (limite de 2 simultâneas).

3. **Armazenamento de Objetos (Object Storage):**
   * Soma volumes de buckets no tier Standard (10 GB) e Arquivo/Infrequente (10 GB).

4. **Taxa de Queima (*Burn-Rate*) & Projeção Mensal:**
   * Calcula o consumo diário médio e extrapola linearmente até o último dia do ciclo de faturamento.
   * Notificações visuais caso o ritmo atual projete exceder qualquer limite gratuito antes do fechamento do mês.

5. **Performance Extrema & Alta Disponibilidade:**
   * Background Worker assíncrono que consulta a OCI e alimenta o cache **Redis** em memória (`--save ""`).
   * Endpoints REST respondem em **<5ms** direto da memória com arquitetura *stale-while-revalidate*.
   * Botão **"Sincronizar Agora"** para forçar atualização sob demanda.
   * **Reverse Proxy Nginx** servindo a SPA React e roteando chamadas `/api/` sem problemas de CORS.

---

## 🛠️ Stack Tecnológica

* **Frontend:** React 18, Vite, Tailwind CSS, Lucide React, Nginx Alpine.
* **Backend:** Python 3.11+, FastAPI, Uvicorn, OCI Python SDK, Pydantic v2.
* **Cache:** Redis 7 Alpine puramente em memória (sem persistência em disco para poupar I/O).
* **Orquestração:** Docker & Docker Compose.

---

## 🚀 Como Executar

### Pré-requisitos
* **Docker** e **Docker Compose** instalados.
* Credenciais da OCI configuradas na sua máquina em `~/.oci/config` com a respectiva chave RSA privada.

### 1. Iniciar a Aplicação
Execute na raiz do projeto:

```bash
docker compose up --build -d
```

### 2. Acessar o Dashboard
* **Frontend SPA:** [http://localhost:3000](http://localhost:3000)
* **Documentação Interativa da API (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Endpoint de Resumo Geral:** [http://localhost:3000/api/v1/summary](http://localhost:3000/api/v1/summary)
* **Inventário de Volumes:** [http://localhost:3000/api/v1/storage/volumes](http://localhost:3000/api/v1/storage/volumes)

### 3. Encerrar a Aplicação
```bash
docker compose down
```

---

## 🧪 Suíte de Testes

O projeto adota a metodologia **Test-Driven Development (TDD)** com 100% de mocks para desenvolvimento isolado e testes ponta a ponta:

```bash
# Executar suíte de testes unitários com mocks
.venv/bin/pytest backend/tests/ -v

# Executar testes End-to-End contra a stack em execução
.venv/bin/pytest tests/e2e/test_e2e_stack.py -v
```

---

## 🔒 Segurança de Credenciais & Normalização de Chave

O container backend monta `~/.oci` e `~/.ssh` em modo **somente leitura** (`:ro`).
O módulo `config.py` contém lógica defensiva inteligente para resolver a chave `.pem` mesmo que o caminho absoluto registrado no host difira do ambiente interno do container.
