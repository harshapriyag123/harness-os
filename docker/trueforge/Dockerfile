FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production \
    STANDALONE=false \
    HOST=0.0.0.0 \
    PORT=8790
ARG TRUEFORGE_VERSION=latest
RUN npm install --omit=dev "@truefoundry/trueforge@${TRUEFORGE_VERSION}" \
    && npm cache clean --force
COPY start.js /app/start.js
EXPOSE 8790
CMD ["node", "/app/start.js"]
