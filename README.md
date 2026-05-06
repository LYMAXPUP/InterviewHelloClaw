# 面试助手（龙虾版）
基于HelloClaw/HelloAgent框架二次开发的AI面试进度跟踪网页版助手。

# 安装依赖
```
pip install -r requirements.txt
```

# 配置文件
```
# 编辑.env填写API Key
cp .env.example .env
```

# 运行项目
```
# 运行mongoDB

# 启动后端
pip install uvicorn
uvicorn src.main:app --reload --port 8000

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```
访问 http://localhost:5173 即可使用 Web 界面。



