# Stage 1: Build the React Application
FROM --platform=$BUILDPLATFORM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Upgrade Alpine base packages to prevent OS CVEs
RUN apk update && apk upgrade --no-cache

ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000 \
    NAMESERVER=127.0.0.11 \
    NGINX_ENVSUBST_FILTER="BACKEND_|NAMESERVER"

# Detect DNS nameserver from /etc/resolv.conf before envsubst runs
RUN printf '#!/bin/sh\nNS=$(awk '"'"'/nameserver/ {print $2; exit}'"'"' /etc/resolv.conf 2>/dev/null || true)\nexport NAMESERVER="${NS:-127.0.0.11}"\n' > /docker-entrypoint.d/15-set-resolver.envsh && \
    chmod +x /docker-entrypoint.d/15-set-resolver.envsh

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
