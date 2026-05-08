#!/bin/bash
# 统一启动脚本 - 构建前端并启动 FastAPI 服务

set -e

echo "=== 产品经理多Agent协作工作站 ==="

# 构建前端
echo "1. 构建前端..."
cd frontend
npm run build
cd ..

# 复制 standalone 文件到正确位置
echo "2. 准备前端文件..."
mkdir -p frontend/.next/standalone
cp -r frontend/.next/standalone/* frontend/.next/standalone/ 2>/dev/null || true

# 启动后端服务
echo "3. 启动后端服务 (FastAPI)..."
echo "   服务地址: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""

python3 -m uvicorn pm_workstation.api.app:create_app --host 0.0.0.0 --port 8000 --factory
