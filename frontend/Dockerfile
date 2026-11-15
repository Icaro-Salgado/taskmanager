# syntax=docker/dockerfile:1

# Build: install the locked dependencies and produce the static files in /app/dist.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve: nginx serves the static files and proxies the API, the admin site and its static files to
# the api service, so the browser sees one origin and the API needs no CORS settings.
FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
