# OCI Always Free Monitor - Frontend Dashboard & Web Proxy 🌐

[![Docker Pulls](https://img.shields.io/docker/pulls/devguina/always-free-frontend?logo=docker&logoColor=white)](https://hub.docker.com/r/devguina/always-free-frontend)
[![Architectures](https://img.shields.io/badge/Architectures-linux%2Famd64%20%7C%20linux%2Farm64-blue.svg?logo=docker&logoColor=white)](#supported-architectures)
[![Base Image](https://img.shields.io/badge/Base-Nginx%20Alpine-009639.svg?logo=nginx&logoColor=white)](https://hub.docker.com/_/nginx)
[![Frontend Stack](https://img.shields.io/badge/Stack-React%2018%20%7C%20Vite%20%7C%20TailwindCSS-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Imagem conteinerizada de alta performance contendo o dashboard Single Page Application (**React 18 + Vite + Tailwind CSS**), servida por um servidor web **Nginx Alpine** endurecido com resolução dinâmica de DNS e proxy reverso resiliente.

---

## 🌟 Principais Recursos

* **Dashboard Visual Responsivo:** Visualização elegante de quotas e inventários da Oracle Cloud (Compute Ampere A1, AMD Micro, Volumes de Bloco, Object Storage, VCNs, IPs públicos e Bancos Autônomos).
* **Alertas Visuais em Destaque:** Alertas instantâneos para Boot/Block Volumes órfãos e IPs fixos não alocados (evitando cobranças ou desperdícios).
* **Trava de Acesso & Modo Portfólio:** Suporte a visualização pública anonimizada (`/portfolio`) e painel de login administrativo integrado.
* **Resolução Dinâmica de DNS Upstream:** Script inteligente em `/docker-entrypoint.d/15-set-resolver.sh` que detecta automaticamente o nameserver do cluster a partir de `/etc/resolv.conf`, prevenindo falhas de `CrashLoopBackOff` durante a inicialização em Kubernetes.
* **Cabeçalhos de Segurança HTTP:** Proteção nativa com `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy` e `Content-Security-Policy`.
* **Blindagem de Métricas Internas:** Bloqueia automaticamente acessos externos públicos indesejados a rotas de métricas Prometheus e probes internas (`deny all; return 404;`).
* **Probe de Saúde Nativa:** Endpoint dedicado `GET /nginx-health` retornando `200 OK` para checagem do pod pelo Kubernetes.
* **Roteamento SPA Completo:** Suporte a histórico HTML5 via `try_files $uri $uri/ /index.html;`.

---

## 🏗️ Arquiteturas Suportadas

Construído com suporte multi-arquitetura nativo:
* `linux/amd64` (Servidores x86_64, Intel/AMD)
* `linux/arm64` (Oracle Cloud Ampere A1, AWS Graviton, Raspberry Pi 4/5, Apple Silicon)

Tags disponíveis:
* `latest`: Última versão estável da branch `main`.
* `sha-<commit>`: Tag imutável vinculada ao commit correspondente no GitHub.

---

## 🚀 Como Executar

### 1. Execução Rápida via `docker run`

Certifique-se de que o backend esteja em execução na mesma rede Docker:

```bash
docker run -d \
  --name oci-frontend \
  --restart unless-stopped \
  -p 3000:80 \
  -e BACKEND_HOST=backend \
  -e BACKEND_PORT=8000 \
  devguina/always-free-frontend:latest
```

### 2. Execução via `docker-compose.yml`

```yaml
services:
  backend:
    image: devguina/always-free-backend:latest
    container_name: oci-backend
    restart: unless-stopped
    ports:
      - "8000:8000"

  frontend:
    image: devguina/always-free-frontend:latest
    container_name: oci-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    environment:
      - BACKEND_HOST=backend
      - BACKEND_PORT=8000
    depends_on:
      - backend
```

---

## ⚙️ Variáveis de Ambiente

O contêiner utiliza templates Nginx com `envsubst` seletivo (`NGINX_ENVSUBST_FILTER`), garantindo que apenas as variáveis de upstream sejam alteradas, mantendo todas as variáveis nativas do Nginx (`$host`, `$remote_addr`, `$uri`) intactas.

| Variável | Padrão | Descrição |
| :--- | :---: | :--- |
| `BACKEND_HOST` | `backend` | Nome do host ou Service do backend no Kubernetes / Docker Compose para proxy reverso de `/api/`. |
| `BACKEND_PORT` | `8000` | Porta em que o backend HTTP escuta requisições. |

> **Nota para Kubernetes com Ingress:** Se o seu Ingress Controller já rotear `/api` diretamente para o Service do backend e `/` para o frontend, você não precisa definir nenhuma variável no pod do frontend.

---

## ☸️ Exemplo de Manifesto Kubernetes & Ingress

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oci-always-free-frontend
  labels:
    app: oci-frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oci-frontend
  template:
    metadata:
      labels:
        app: oci-frontend
    spec:
      containers:
        - name: frontend
          image: devguina/always-free-frontend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 80
              name: http
          livenessProbe:
            httpGet:
              path: /nginx-health
              port: 80
            periodSeconds: 15
            timeoutSeconds: 3
          readinessProbe:
            httpGet:
              path: /nginx-health
              port: 80
            periodSeconds: 10
            timeoutSeconds: 3
---
apiVersion: v1
kind: Service
metadata:
  name: oci-frontend
spec:
  selector:
    app: oci-frontend
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: oci-monitor-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - monitor.seudominio.com
      secretName: oci-monitor-tls
  rules:
    - host: monitor.seudominio.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: oci-backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: oci-frontend
                port:
                  number: 80
```

---

## 🔍 Healthcheck & Probes

* `GET /nginx-health`: Retorna `HTTP 200 OK ("healthy")` para validação de integridade do pod Nginx.
* Rotas protegidas contra acesso público no domínio principal:
  * `/metrics` $\rightarrow$ `HTTP 404 (deny all)`
  * `/livez`, `/readyz`, `/startupz`, `/healthz` $\rightarrow$ `HTTP 404 (deny all)`

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte o repositório oficial no GitHub para mais detalhes.
