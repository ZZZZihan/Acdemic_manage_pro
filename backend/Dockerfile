FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 设置环境变量
ENV FLASK_APP=run.py
ENV FLASK_CONFIG=production

# 暴露端口
EXPOSE 5003

# 启动命令
CMD ["python", "run.py"] 