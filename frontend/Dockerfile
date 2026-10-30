FROM nginx:1.27-alpine
COPY frontend/ /usr/share/nginx/html/
COPY docker/frontend-entrypoint.sh /docker-entrypoint.d/40-runtime-config.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-runtime-config.sh && chmod +x /docker-entrypoint.d/40-runtime-config.sh
EXPOSE 80

