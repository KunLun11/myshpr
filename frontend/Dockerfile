FROM node:22-alpine AS base
WORKDIR /app
RUN corepack enable

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund --prefer-offline

# dev
FROM base AS dev
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# prod
FROM base AS build
COPY . .
RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

FROM node:22-alpine AS prod
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]