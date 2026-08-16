FROM node:20-slim

WORKDIR /srv

COPY web/package.json ./package.json
RUN npm install

COPY web ./

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
