# Web image: builds the React app and serves it with Caddy, which also terminates HTTPS (automatic
# Let's Encrypt certificates) and forwards /api and /health to the backend container.
# Used by docker-compose.prod.yml (see DEPLOYMENT.md). Build context: frontend/.

FROM node:22-slim AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Empty (default): the app calls the same-origin path /api, which Caddy forwards to the backend.
# Set it only when the API is served from another origin, e.g. https://api.example.com/api.
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv
