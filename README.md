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
# linux机器上运行mongoDB
mkdir -p ./data/mongodb/data
mkdir -p ./data/mongodb/log
source config.ini
# mongoDB二进制文件可使用：https://pan.baidu.com/s/1yjoGvKMUYV2jXzbeHGroYA?pwd=j6c9%20

# windows启动后端
pip install uvicorn
uvicorn src.main:app --reload --port 8000

# windows启动前端
cd frontend
npm install
npm run dev
```
访问 http://localhost:5173 即可使用 Web 界面。

# 效果图
与Agent对话读取面试邮件，后续可存入MongoDB数据库
<img width="2538" height="1263" alt="image" src="https://github.com/user-attachments/assets/717f0be8-aab8-4637-93db-edd6ca94c589" />
在“求职”页签展示面试进度甘特图







