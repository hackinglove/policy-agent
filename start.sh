#!/bin/bash
# ============================================================
#  Policy Insight 一键部署启动脚本
#  用法: chmod +x start.sh && ./start.sh
# ============================================================

set -e

# ---------- 颜色定义 ----------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# ---------- 辅助函数 ----------
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; }
step()    { echo -e "\n${BLUE}==>${NC} ${BLUE}$1${NC}"; }

# ---------- 项目根目录 ----------
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     Policy Insight · 一键部署启动脚本            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ==================== Step 1: 检查 Python ====================
step "Step 1/6: 检查 Python 环境"

if command -v python3 &>/dev/null; then
    SYS_PYTHON="python3"
elif command -v python &>/dev/null; then
    SYS_PYTHON="python"
else
    error "未检测到 Python，请先安装 Python 3.8+"
    exit 1
fi

PY_VERSION=$($SYS_PYTHON --version 2>&1)
info "检测到系统 Python: $PY_VERSION"

# ==================== Step 2: 创建虚拟环境 ====================
step "Step 2/6: 创建虚拟环境"

if [ -d "$VENV_DIR" ] && [ -f "$PYTHON" ]; then
    info "虚拟环境已存在，跳过创建"
else
    warn "正在创建虚拟环境..."
    $SYS_PYTHON -m venv "$VENV_DIR"
    info "虚拟环境创建完成: $VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"
info "虚拟环境已激活"

# ==================== Step 3: 安装依赖 ====================
step "Step 3/6: 安装 Python 依赖"

$PIP install --upgrade pip -q 2>/dev/null
info "pip 已更新"

$PIP install -r requirements.txt -q
info "所有依赖安装完成"

# ==================== Step 4: 安装 Playwright 浏览器 ====================
step "Step 4/6: 安装 Playwright 浏览器引擎"

if $PYTHON -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(headless=True); b.close(); p.stop()" 2>/dev/null; then
    info "Playwright 浏览器已就绪，跳过安装"
else
    warn "正在下载 Chromium 浏览器（首次运行需要，约 100MB）..."
    $PYTHON -m playwright install chromium
    info "Playwright 浏览器安装完成"
fi

# ==================== Step 5: 初始化配置文件 ====================
step "Step 5/6: 检查配置文件"

# .env 文件
if [ -f "$PROJECT_DIR/.env" ]; then
    info ".env 配置文件已存在"
else
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        warn ".env 已从模板创建，请稍后在系统设置中填写 API Key 等信息"
    else
        cat > "$PROJECT_DIR/.env" << 'EOF'
# AI Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Notification Configuration
WEBHOOK_URL=
PUSHPLUS_TOKEN=

# Crawler Configuration
LOG_LEVEL=INFO
HEADLESS=True
EOF
        warn ".env 配置文件已创建，请稍后在系统设置中填写 API Key 等信息"
    fi
fi

# config.yaml 文件
if [ -f "$PROJECT_DIR/config.yaml" ]; then
    info "config.yaml 已存在"
else
    warn "config.yaml 不存在，请确保该文件已正确配置"
fi

# sources.json 文件
if [ -f "$PROJECT_DIR/sources.json" ]; then
    info "sources.json 已存在"
else
    echo "[]" > "$PROJECT_DIR/sources.json"
    warn "sources.json 已创建（空列表），可在源站管理中添加"
fi

# web 目录
if [ -f "$PROJECT_DIR/web/index.html" ]; then
    info "前端文件已就绪"
else
    error "未找到 web/index.html，请确保前端文件完整"
    exit 1
fi

# ==================== Step 6: 启动服务 ====================
step "Step 6/6: 启动 Policy Insight 服务"

# 检查端口是否被占用
PORT=8000
if lsof -i :$PORT &>/dev/null; then
    warn "端口 $PORT 已被占用，正在关闭旧进程..."
    lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
    sleep 1
    info "旧进程已关闭"
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║           ✅  所有准备工作已完成！                ║"
echo "║                                                  ║"
echo "║   🌐  访问地址: http://localhost:$PORT              ║"
echo "║   📖  按 Ctrl+C 停止服务                         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 启动 FastAPI 服务
$PYTHON server.py
