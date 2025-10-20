# Frontend Builder Dockerfile - Vite + React (Build Only)
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build command
CMD ["npm", "run", "build"]
