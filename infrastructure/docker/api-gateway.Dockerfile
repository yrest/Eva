FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/shared ./packages/shared
COPY services/api-gateway ./services/api-gateway

RUN corepack enable && pnpm install --frozen-lockfile
RUN pnpm --filter @eva/shared build
RUN pnpm --filter @eva/api-gateway build

FROM node:20-alpine

WORKDIR /app
COPY --from=builder /app/services/api-gateway/dist ./dist
COPY --from=builder /app/services/api-gateway/package.json ./
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 8000
CMD ["node", "dist/index.js"]
