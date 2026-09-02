FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production \
    STANDALONE=false \
    HOST=0.0.0.0 \
    PORT=8790
# Pin the published server release instead of floating `latest` so Render
# rebuilds keep the same HTTP API contract used by Harness OS.
ARG TRUEFORGE_VERSION=0.1.4
RUN npm install --omit=dev "@truefoundry/trueforge@${TRUEFORGE_VERSION}" \
    && npm cache clean --force
COPY entrypoint.sh /usr/local/bin/harness-trueforge-entrypoint
COPY bootstrap.mjs /usr/local/lib/harness-os/bootstrap.mjs
RUN chmod +x /usr/local/bin/harness-trueforge-entrypoint
EXPOSE 8790
ENTRYPOINT ["/usr/local/bin/harness-trueforge-entrypoint"]
