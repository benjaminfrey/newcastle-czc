FROM node:24-slim AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# The guided builder's preview route: on only for the LAN copy (compose.lan.yml).
ARG VITE_GUIDE_PREVIEW=
ENV VITE_GUIDE_PREVIEW=$VITE_GUIDE_PREVIEW
RUN npm run build

FROM caddy:2
COPY --from=build /web/dist /srv
