FROM node:16-alpine

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm install

# 复制项目文件
COPY . .

# 接收API地址作为构建参数，默认使用后端服务名
ARG VITE_API_URL=http://backend:5003
ENV VITE_API_URL=${VITE_API_URL}

# 构建生产版本
RUN npm run build

# 安装简单的HTTP服务器来提供静态内容
RUN npm install -g http-server

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["http-server", "dist", "-p", "8080"] 