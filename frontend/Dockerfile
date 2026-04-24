FROM node:24.13.1-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=""
ARG VITE_USE_MSW="false"
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_USE_MSW=${VITE_USE_MSW}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.29-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
