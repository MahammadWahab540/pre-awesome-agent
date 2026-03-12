# Stage 1: Build
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve static output
FROM node:20-slim
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/out ./out
EXPOSE 8080
CMD ["serve", "-s", "out", "-l", "8080"]
