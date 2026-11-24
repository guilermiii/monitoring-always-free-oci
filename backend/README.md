# OCI Always Free Monitor - Backend API & Collector 🚀

[![Docker Pulls](https://img.shields.io/docker/pulls/devguina/always-free-backend?logo=docker&logoColor=white)](https://hub.docker.com/r/devguina/always-free-backend)
[![Architectures](https://img.shields.io/badge/Architectures-linux%2Famd64%20%7C%20linux%2Farm64-blue.svg?logo=docker&logoColor=white)](#supported-architectures)
[![Base Image](https://img.shields.io/badge/Base-Python%203.11--Alpine-3776AB.svg?logo=python&logoColor=white)](https://alpinelinux.org/)
[![Security](https://img.shields.io/badge/Security-Non--Root%20(UID%201000)-success.svg?logo=security)](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Contêiner de alta performance contendo a API REST assíncrona (**FastAPI**), o coletor da **Oracle Cloud Infrastructure (OCI SDK)**, o mecanismo de cálculo de taxa de queima (*burn-rate*) e projeção mensal, detector de recursos órfãos, exportador de métricas **Prometheus** e probes nativas de ciclo de vida para **Kubernetes**.

---

## 🌟 Principais Recursos

* **Varredura Recursiva da OCI:** Coleta e agrega volumes de blocos, compute Ampere A1 (Arm) e AMD Micro, Object Storage, VCNs, IPs públicos e bancos autônomos.
* **Detecção de Recursos Órfãos:** Alerta automaticamente sobre Boot/Block Volumes não anexados e IPs fixos desalocados, evitando desperdício de cota.
* **Cache em Memória de Baixa Latência (<3ms):** Integrado ao Redis 7 com arquitetura *stale-while-revalidate*.
* **Auditoria de Chamadas de API:** Monitora chamadas contra limites diários da OCI (reset UTC) e previne *throttling*.
* **Modo Portfólio (Privacy Mode):** Anonimização e mascaramento automático de OCIDs, nomes e IPs para acessos públicos não autenticados.
* **Autenticação Administrativa Única:** Login seguro via JWT assinado (HS256) em cookie HttpOnly com atributos `Secure` e `SameSite=Lax`, rate limiting adaptativo e proteção contra força bruta.
* **Observabilidade Pronta para Produção:** Métricas nativas em formato oficial Prometheus (`GET /metrics`) e probes semânticas do Kubernetes (`/livez`, `/readyz`, `/startupz`).
* **Segurança Reforçada:** Execução com usuário não-privilegiado `appuser` (UID `1000:1000`), em estrita conformidade com o **Kubernetes Pod Security Standard (Restricted)**.

---

## 🏗️ Arquiteturas Suportadas

Construído e testado nativamente para múltiplas arquiteturas:
* `linux/amd64` (Servidores x86_64 tradicionais, Intel/AMD)
* `linux/arm64` (Oracle Cloud Ampere A1, AWS Graviton, Raspberry Pi 4/5, Apple Silicon)

Tags disponíveis:
* `latest`: Última versão estável da branch `main`.
* `sha-<commit>`: Tag imutável vinculada ao commit correspondente no GitHub.

---

## 🚀 Como Executar

### 1. Execução Rápida via `docker run`

Certifique-se de que o Redis esteja em execução na mesma rede Docker:

```bash
docker run -d \
  --name oci-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  -e REDIS_URL=redis://redis:6379/0 \
  -e OCI_CONFIG_FILE=/secrets/oci/config \
  -e SESSION_COOKIE_SECURE=false \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=admin \
  -v ~/.oci:/secrets/oci:ro \
  -v oci-backend-data:/app/data \
  devguina/always-free-backend:latest
```

### 2. Execução via `docker-compose.yml`

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: oci-redis
    restart: unless-stopped
    volumes:
      - oci-redis-data:/data

  backend:
    image: devguina/always-free-backend:latest
    container_name: oci-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - OCI_CONFIG_FILE=/secrets/oci/config
      - SESSION_COOKIE_SECURE=false
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=admin
    volumes:
      - ~/.oci:/secrets/oci:ro
      - oci-backend-data:/app/data
    depends_on:
      - redis

volumes:
  oci-redis-data:
  oci-backend-data:
```

---

## ⚙️ Variáveis de Ambiente

Todos os parâmetros operacionais seguros vêm **embutidos com valores padrão na imagem**, minimizando a necessidade de configurações manuais.

| Variável | Tipo | Padrão | Descrição |
| :--- | :---: | :---: | :--- |
| `REDIS_URL` | String | `redis://redis:6379/0` | Endereço de conexão com o banco Redis interno. |
| `SESSION_COOKIE_SECURE` | Bool | `true` | Ativa atributo `Secure` no cookie de sessão (obrigatório com HTTPS/Ingress; defina `false` para HTTP local). |
| `PORTFOLIO_MODE` | Bool | `true` | Ofusca agressivamente OCIDs e IPs públicos para visitantes não autenticados. |
| `ADMIN_USERNAME` | String | `admin` | Nome de usuário único para login na interface administrativa. |
| `ADMIN_PASSWORD_HASH` | String | *(vazio)* | Hash Bcrypt da senha de admin (`python3 -c "import bcrypt; print(bcrypt.hashpw(b'Senha', bcrypt.gensalt(12)).decode())"`). |
| `ADMIN_PASSWORD` | String | *(vazio)* | Senha em texto plano (usado apenas como fallback se `ADMIN_PASSWORD_HASH` estiver vazio). |
| `JWT_SECRET_KEY` | String | *(chave padrão)* | Chave secreta de 64 caracteres hexadecimais para assinatura de tokens JWT. |
| `JWT_ALGORITHM` | String | `HS256` | Algoritmo criptográfico utilizado pelo JWT. |
| `JWT_EXPIRATION_HOURS` | Int | `4` | Duração máxima da sessão administrativa autenticada (em horas). |
| `REFRESH_INTERVAL_SECONDS` | Int | `600` | Intervalo em segundos entre varreduras automáticas em segundo plano (10 min). |
| `CACHE_TTL_SECONDS` | Int | `900` | Tempo de vida (TTL) das chaves de resumo no Redis (15 min). |
| `PERSISTENT_DATA_DIR` | String | `/app/data` | Diretório de persistência do histórico diário de chamadas de API. |
| `ALLOWED_ORIGINS` | String | `*` | Origens permitidas para requisições CORS (ex: `https://meu-dominio.com`). |
| `OCI_CONFIG_FILE` | String | `/secrets/oci/config` | Caminho do arquivo de configuração do OCI SDK. |
| `OCI_CONFIG_PROFILE` | String | `DEFAULT` | Perfil do arquivo OCI config a ser utilizado. |
| `RATE_LIMIT_PUBLIC_PER_MINUTE` | Int | `60` | Limite de requisições por minuto por IP para endpoints públicos. |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | Int | `5` | Limite de requisições por minuto para login (prevenção de força bruta). |
| `OCI_API_DAILY_LIMIT` | Int | `10000` | Teto diário de segurança de chamadas aos SDKs da Oracle Cloud. |

---

## 🔒 Montagem de Volumes & Segurança

* **`/secrets/oci` (Somente Leitura):** Monte o diretório contendo o arquivo `config` e a chave privada RSA (`oci_api_key.pem`). O módulo de configuração resolve dinamicamente caminhos de chave `~` ou absolutos.
* **`/app/data` (Leitura e Escrita):** Diretório de persistência para retenção de cotas diárias de API across restarts.
* **Usuário Não-Privilegiado:** O processo roda com UID `1000` e GID `1000` (`appuser:appgroup`). Em Kubernetes, configure `securityContext.fsGroup: 1000`.

---

## ☸️ Exemplo de Manifesto Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oci-always-free-backend
  labels:
    app: oci-backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oci-backend
  template:
    metadata:
      labels:
        app: oci-backend
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
        - name: backend
          image: devguina/always-free-backend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - secretRef:
                name: backend-secrets
            - configMapRef:
                name: backend-config
          volumeMounts:
            - name: oci-credentials
              mountPath: /secrets/oci
              readOnly: true
            - name: backend-data
              mountPath: /app/data
          startupProbe:
            httpGet:
              path: /startupz
              port: 8000
            failureThreshold: 30
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /livez
              port: 8000
            periodSeconds: 10
            timeoutSeconds: 3
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8000
            periodSeconds: 10
            timeoutSeconds: 3
      volumes:
        - name: oci-credentials
          secret:
            secretName: oci-credentials
        - name: backend-data
          persistentVolumeClaim:
            claimName: oci-backend-pvc
```

---

## 📊 Endpoints de Observabilidade e Probes

* `GET /livez`: Liveness probe do Kubernetes (valida processo e loop assíncrono).
* `GET /readyz`: Readiness probe do Kubernetes (testa conectividade ativa com Redis e validade do config OCI).
* `GET /startupz`: Startup probe (garante que worker e hidratação de cache terminaram antes do tráfego).
* `GET /metrics`: Scrape de métricas oficiais em formato texto Prometheus (versão 0.0.4).
* `GET /docs`: Swagger UI interativo (100% tipado via Pydantic v2).

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte o repositório oficial no GitHub para mais detalhes.
