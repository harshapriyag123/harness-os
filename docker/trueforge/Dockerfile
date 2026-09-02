FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production \
    STANDALONE=false \
    HOST=0.0.0.0 \
    PORT=8790
ARG TRUEFORGE_VERSION=latest
RUN npm install --omit=dev "@truefoundry/trueforge@${TRUEFORGE_VERSION}" \
    && npm cache clean --force
COPY entrypoint.sh /usr/local/bin/harness-trueforge-entrypoint
RUN chmod +x /usr/local/bin/harness-trueforge-entrypoint
EXPOSE 8790
ENTRYPOINT ["/usr/local/bin/harness-trueforge-entrypoint"]
