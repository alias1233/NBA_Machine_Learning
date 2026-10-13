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

# Node needs package.json to run the build output as ES modules.
COPY package.json ./

COPY --from=build /build/build ./build

USER node

EXPOSE 3000

CMD ["node", "build/index.js"]
