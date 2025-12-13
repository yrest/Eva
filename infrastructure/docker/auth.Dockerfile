FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/shared ./packages/shared
COPY services/auth ./services/auth

RUN corepack enable && pnpm install --frozen-lockfile
RUN pnpm --filter @eva/shared build
RUN pnpm --filter @eva/auth build

FROM node:20-alpine

WORKDIR /app
COPY --from=builder /app/services/auth/dist ./dist
COPY --from=builder /app/services/auth/package.json ./
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 8001
CMD ["node", "dist/index.js"]
