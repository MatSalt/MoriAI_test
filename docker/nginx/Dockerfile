# Nginx Dockerfile - Static File Hosting with HTTPS
FROM nginx:alpine

# Install OpenSSL (already included in alpine, but explicit for clarity)
RUN apk add --no-cache openssl

# Create SSL certificate directory
RUN mkdir -p /etc/nginx/certs

# Generate self-signed SSL certificate
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/certs/nginx.key \
    -out /etc/nginx/certs/nginx.crt \
    -subj "/C=KR/ST=Seoul/L=Seoul/O=MoriAI/OU=Development/CN=localhost"

# Copy custom nginx configuration
COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
