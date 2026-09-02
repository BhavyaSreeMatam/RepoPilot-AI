# ---------- Build React/Vite app ----------
FROM node:22-alpine AS build

WORKDIR /app

# Install dependencies first for better Docker layer caching
COPY package*.json ./
RUN npm ci

# Copy frontend source
COPY . .

# In Docker/production, the browser talks to Nginx through /api
# Production Vite configuration.
# These values are compiled into the browser bundle at build time.
ARG VITE_API_BASE_URL=/api
ARG VITE_COGNITO_USER_POOL_ID
ARG VITE_COGNITO_USER_POOL_CLIENT_ID

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_COGNITO_USER_POOL_ID=$VITE_COGNITO_USER_POOL_ID
ENV VITE_COGNITO_USER_POOL_CLIENT_ID=$VITE_COGNITO_USER_POOL_CLIENT_ID

# Fail the image build instead of silently producing a frontend
# with missing Cognito configuration.
RUN test -n "$VITE_COGNITO_USER_POOL_ID" \
    && test -n "$VITE_COGNITO_USER_POOL_CLIENT_ID"

RUN npm run build


# ---------- Serve with Nginx ----------
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]