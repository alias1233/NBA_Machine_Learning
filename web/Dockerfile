# The site, server rendered by SvelteKit's Node adapter. Built from web/.
# See deploy/docker-compose.yml.

# Pinned by digest, so the same commit cannot rebuild on a different runtime and set of operating
# system packages later. The tag is left beside it to say what the digest is. Move both together.
FROM node:22-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5 AS build

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:22-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /app

# Only what the built server runs. Every dependency here is a build one and adapter-node bundles
# what the site imports, so the output reaches for nothing but Node's own modules. The manifest is
# still copied, because it is what marks the output as modules rather than scripts.
COPY package.json ./

COPY --from=build /build/build ./build

USER node

EXPOSE 3000

CMD ["node", "build/index.js"]
