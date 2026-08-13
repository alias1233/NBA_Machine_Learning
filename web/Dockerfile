# The site, server rendered by SvelteKit's Node adapter. Built from web/.
# See deploy/docker-compose.yml.

FROM node:22-slim AS build

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:22-slim

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /app

# Only what the built server runs: its own output and the packages it imports at runtime.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=build /build/build ./build

USER node

EXPOSE 3000

CMD ["node", "build/index.js"]
