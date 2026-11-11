FROM node:24.22.1-bookworm-slim AS build
RUN npm install --global pnpm@11.25.0
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web
RUN pnpm build
FROM nginxinc/nginx-unprivileged:1.30-trixie@sha256:ec0f7ecb1fbd84959ac114e65fb36074ffc97d4d51db0f18ee925162d889dcef
USER root
RUN apt-get update && apt-get upgrade -y && apt-get purge -y nginx-module-geoip nginx-module-image-filter nginx-module-njs nginx-module-xslt curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
USER 101:101
EXPOSE 8080
