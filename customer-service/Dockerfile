# --- STAGE 1: Build & Dependency Installation ---
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

FROM node:20-alpine AS runner

ENV NODE_ENV=production
WORKDIR /app

COPY package*.json ./

# FIX HERE: Install ONLY production dependencies directly in Stage 2
RUN npm install --only=production

# Copy application files from builder stage
COPY --from=builder /app ./

EXPOSE 3000

CMD ["node", "app/server.js"]