# RAG 企业级知识库问答系统

基于 **LangChain** + **通义千问 (Qwen)** + **Chroma** 的企业级 RAG 知识库问答平台。

## 功能特性

- 🔐 **用户认证**：注册、登录、JWT 鉴权、密码修改
- 💬 **知识库问答**：基于 RAG 架构，回答精准引用知识库来源
- 📚 **知识库管理**：支持 PDF/TXT/CSV/MD/DOCX 文档上传与管理
- 🔄 **多用户多会话**：每个用户独立会话，历史记录永久保存
- ⚡ **流式响应**：SSE 实时打字机效果
- 🎨 **现代 UI**：React + Ant Design 5，支持暗色模式
- 🐳 **Docker 一键部署**

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM | 通义千问 (Qwen-Max) |
| Embedding | Ollama (bge-m3) |
| 后端 | Python FastAPI |
| RAG 框架 | LangChain + Chroma |
| 数据库 | PostgreSQL 16 / SQLite |
| 缓存 | Redis |
| 前端 | React 18 + TypeScript + Ant Design 5 |
| 部署 | Docker Compose |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- Ollama（用于本地 embedding）
- PostgreSQL 16 / Redis（可选，Docker 版本需要）

### 1. 配置 Ollama Embedding

```bash
# 安装 Ollama (Windows: https://ollama.com/download/windows)
ollama pull bge-m3
```

### 2. 配置环境变量

```bash
cp .env.example backend/.env
# 编辑 backend/.env：填入通义千问 API Key 与至少 32 字符的 JWT_SECRET
# OPENAI_API_KEY=sk-your-qwen-api-key
# JWT_SECRET=<使用安全随机字符串>
```

**获取 API Key**：访问 [阿里百炼平台](https://bailian.console.aliyun.com/) 注册并获取。
本地默认使用 SQLite（`DATABASE_URL=sqlite+aiosqlite:///./rag.db`）。如需创建初始管理员，请显式填写 `INITIAL_ADMIN_USERNAME`、`INITIAL_ADMIN_EMAIL` 和强密码 `INITIAL_ADMIN_PASSWORD`；项目不再创建 `admin / 123456`。

### 3. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.lock
python -m alembic upgrade head

# 前端
cd frontend
npm ci
```

### 4. 启动服务

```bash
# 终端 1：启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 终端 2：启动前端
cd frontend
npm run dev
```

### 5. 访问系统

- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs
- 管理员：仅在配置 `INITIAL_ADMIN_*` 后创建

### Docker 部署（可选）

```bash
# 配置通义千问 API Key
export OPENAI_API_KEY=sk-your-qwen-api-key
export JWT_SECRET=<至少 32 字符的随机字符串>

# 启动全部服务
docker-compose up -d

# 访问
# 前端：http://localhost:3000
# API：http://localhost:8000
```

> **国内网络问题**：如果 Docker 拉取镜像慢，请参考方案计划中的第 8 节解决方案。

## 项目结构

```
LangChainRAG/
├── backend/           # FastAPI 后端
│   └── app/
│       ├── api/       # API 路由
│       ├── models/    # 数据库模型
│       ├── schemas/   # Pydantic 模型
│       ├── services/  # 业务逻辑
│       ├── rag/       # RAG 核心
│       └── tasks/     # Celery 任务
├── frontend/          # React 前端
│   └── src/
│       ├── pages/     # 页面组件
│       ├── components/# UI 组件
│       ├── api/       # API 请求
│       └── stores/    # 状态管理
└── docker-compose.yml
```

## 常见问题

**Q: Ollama 连接失败？**
确保 Ollama 正在运行：`ollama serve`，且已拉取模型：`ollama pull bge-m3`

**Q: 通义千问 API 调用失败？**
检查 `backend/.env` 中的 `OPENAI_API_KEY` 是否填写了阿里云百炼的 API Key

**Q: 没有 PostgreSQL？**
本地开发默认使用 SQLite，无需安装 PostgreSQL。Docker 部署会自动启动 PostgreSQL；已有旧数据库首次启用迁移时，确认 schema 已同步后执行 `python -m alembic stamp head`，新数据库执行 `python -m alembic upgrade head`。

**Q: 前端代理 API 失败？**
Vite 已配置代理 `/api` → `http://localhost:8000`，确保后端在 8000 端口运行。
非同源部署时设置 `VITE_API_BASE_URL`，例如 `https://api.example.com/api/v1`。
