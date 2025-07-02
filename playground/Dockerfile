FROM oven/bun:1 AS base
WORKDIR /usr/src/app

FROM base AS install

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile 
COPY . .

ARG ENVIRONMENT
ENV NODE_ENV=$ENVIRONMENT
RUN bun run build

FROM nginx:alpine AS prod

COPY --from=install /usr/src/app/dist /usr/share/nginx/html

EXPOSE 80
