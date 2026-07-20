# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Use Taobao npm mirror for China
RUN npm config set registry https://registry.npmmirror.com

COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN npm install 2>/dev/null || \
    (npm install -g pnpm && pnpm install --frozen-lockfile)

COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
