FROM nginx:1.25-alpine

# Install apache2-utils for htpasswd
RUN apk add --no-cache apache2-utils

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY infrastructure/nginx/nginx.conf /etc/nginx/nginx.conf

# Create directories for SSL (if needed)
RUN mkdir -p /etc/nginx/ssl

# Create htpasswd file for admin areas (login: admin, password: Vitte2024Admin!)
RUN htpasswd -bc /etc/nginx/.htpasswd admin 'Vitte2024Admin!'

# Set correct permissions
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
