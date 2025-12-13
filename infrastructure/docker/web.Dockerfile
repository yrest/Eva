FROM node:20-alpine AS builder

WORKDIR /app
COPY ../../package.json ../../pnpm-lock.yaml ../../pnpm-workspace.yaml ./
COPY ../../packages ./packages
COPY . ./apps/web

RUN corepack enable && pnpm install --frozen-lockfile
RUN pnpm --filter @eva/shared build
RUN pnpm --filter @eva/ui build
RUN pnpm --filter @eva/web build

FROM nginx:alpine

COPY --from=builder /app/apps/web/dist /usr/share/nginx/html
COPY infrastructure/docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
