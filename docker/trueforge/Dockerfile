FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production \
    STANDALONE=false \
    HOST=0.0.0.0 \
    PORT=8790
# Pin the API contract used by Harness OS. Do not deploy floating `latest` here.
ARG TRUEFORGE_VERSION=0.2.0-rc.0
RUN npm install --omit=dev "@truefoundry/trueforge@${TRUEFORGE_VERSION}" \
    && npm cache clean --force
COPY entrypoint.sh /usr/local/bin/harness-trueforge-entrypoint
COPY bootstrap.mjs /usr/local/lib/harness-os/bootstrap.mjs
RUN chmod +x /usr/local/bin/harness-trueforge-entrypoint
EXPOSE 8790
ENTRYPOINT ["/usr/local/bin/harness-trueforge-entrypoint"]
