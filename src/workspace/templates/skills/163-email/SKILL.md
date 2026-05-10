---
name: email-processor
description: "网易邮箱查看、整理，以及需要通过邮箱获取信息时调用此Skill。"
---

# 工作流程

## 1. 解析用户时间需求

从用户输入中提取时间信息，支持以下格式：

### 相对时间
- "最近N天"、"过去N天"、"前N天" -> `--days N`
- "昨天" -> 默认行为（无需参数）
- "今天" -> `--days 0`

### 具体日期范围
- "2025/12/1到2025/12/12"、"2025-12-01~2025-12-12"、"12月1号到12月12号" -> `--since 2025-12-01 --before 2025-12-13`
- 注意：`--before` 是不包含的，所以结束日期要+1天

### 多个离散日期
- "12月1号和12月5号"、"2025/12/1 + 2025/12/5 + 2025/12/10" -> `--dates "2025-12-01,2025-12-05,2025-12-10"`

### 时间点描述（转换为具体日期）
- "今天下午" -> 今天日期
- "昨天上午" -> 昨天日期
- "12.4号" -> 2025-12-04（假设当前年份）

**重要规则：**
- 如果用户没有指定时间，默认查询昨天的邮件

## 2. 执行脚本

在 Skill 路径下执行脚本：

```bash
cd <Skill路径>
python scripts/recent_mail_report.py [参数]
```

### 参数说明
- `--since YYYY-MM-DD`：开始日期（包含）
- `--before YYYY-MM-DD`：结束日期（不包含）
- `--days N`：最近N天
- `--dates "D1,D2,D3"`：多个具体日期，逗号分隔

### 示例
```bash
# 查询昨天的邮件（默认）
python scripts/recent_mail_report.py

# 查询最近3天
python scripts/recent_mail_report.py --days 3

# 查询2025年12月1日到12月12日
python scripts/recent_mail_report.py --since 2025-12-01 --before 2025-12-13

# 查询12月1日、5日、10日三天的邮件
python scripts/recent_mail_report.py --dates "2025-12-01,2025-12-05,2025-12-10"
```

## 3. 整理输出

读取脚本输出的 JSON，检查是否存在查询结果被截断的情况：
对比total_messages数量和item列表中的数量是否相等，
如果获取的item数量 < total_messages数量, 说明消息太多被截断，此时请按10天一次分批查询汇总结果。
（比如要查4.1~4.12号的邮件，可以拆分为4.1~4.10,4.11~4.12两次查询，如果10天一次还是截断，
就再拆分成5天一次，3天一次，1天一次，依此类推，必须保证单次查询的返回结果中item数量=总数，否则就切分多次查）。

### 3.1 邮件分类
按以下类别整理邮件（每一封邮件都要且只能归到一类）。
如果邮件属于"公司招聘邮件"这一类别，需要写入临时文件 `interview_emails.json`（先将文件里的旧信息清空，再写入本次新增的）：直接复制 items 中对应的字段
脚本输出格式示例：
```json
{
  "mailbox": "liu***jj@163.com",
  "folder": "INBOX",
  "window": { "since": "2026-05-06", "before": "2026-05-09" },
  "total_messages": 9,
  "items": [
    {
      "subject": "【小红书】面试满意度调研",
      "from": "xhs_recruit@xiaohongshu.com",
      "date": "2026-05-08 14:30:12 +0800",
      "preview": "body { padding: 5px 20px; } p { color: #000000; ... 感谢您参加 2026-05-08 14:00:00 Agent研发专家-AI Coding方向 的面试..."
    },
    {
      "subject": "感谢您应聘高德-AI应用后端工程师-开放平台专项职位",
      "from": "<Amap_talent@autonavi.com>",
      "date": "2026-05-07 08:10:06 +0800",
      "preview": "p { line-height: 24px; } 柳源，您好！ 感谢您应聘高德-AI应用后端工程师..."
    }
  ]
}
```

写入 `interview_emails.json` 示例：
```json
[
  {
    "subject": "【小红书】面试满意度调研",
    "from": "xhs_recruit@xiaohongshu.com",
    "date": "2026-05-08 14:30:12 +0800",
    "preview": "body { padding: 5px 20px; } p { color: #000000; ... 感谢您参加 2026-05-08 14:00:00 Agent研发专家-AI Coding方向 的面试..."
  },
  {
    "subject": "感谢您应聘高德-AI应用后端工程师-开放平台专项职位",
    "from": "<Amap_talent@autonavi.com>",
    "date": "2026-05-07 08:10:06 +0800",
    "preview": "p { line-height: 24px; } XX，您好！ 感谢您应聘高德-AI应用后端工程师..."
  }
]
```
**只保留这四个字段：**
- `subject`：邮件主题
- `from`：发件人
- `date`：邮件时间
- `preview`：邮件正文预览（**原样复制，不要修改**）

#### 3.1.1 公司招聘邮件

由招聘公司直接发出、与岗位应聘流程相关的邮件。

**强制规则：以下关键词只要出现在主题中，必须归入公司招聘邮件：** `面试`、`笔试`、`测评`、`offer`、`录用`、`录取`、`感谢投递`、`感谢应聘`、`感谢申请`、`感谢您应聘`、`招聘通知`、`面试结果`。

如果主题不明确，看正文是否含以下特征（命中任意一条即归入）：
- `很遗憾` + `不匹配`/`略有差异`/`不做下一步安排` → 拒信类
- `简历筛选`、`等待评估`、`用人部门评估`、`认真评估` → 流程中
- `面试反馈`、`面试评价`、`面试满意度`、`面试调研` → 问卷类

#### 3.1.2 猎头招聘邮件
由第三方猎头公司或招聘平台（非雇主公司直接）发出，内容为推荐职位、邀约沟通。关键词：
- 发件人域名含 `lietou`、`headhunter`、`hunter` 等
- 正文含"为您推荐"、"岗位匹配"、"机会推荐"、"猎头顾问"
- 来自招聘平台（智联招聘、猎聘等）的**职位推荐**类邮件

#### 3.1.3 系统通知
不满足以上两类的所有其他邮件归入此类。常见包括：邮箱安全通知、验证码、GitHub 通知、社交平台通知、账号验证、营销推广等。

### 3.2 输出格式要求

**每一类邮件逐一列出每封邮件内容（最多列10条，剩余的省略）**，不能只贴 JSON 或只报数量。使用以下格式输出：

```
## 📊 查询概况
查询时间范围：YYYY 年 M 月 D 日 ~ YYYY 年 M 月 D 日，共 XX 封邮件

## 📝 公司招聘邮件（X 封）
| 主题 | 发件人 | 时间 | 摘要 |
|------|------|------|------|
| xxx 面试邀请 | xxx@company.com | 2026-04-07 | 一面，4月10日下午2点 |
| 感谢投递xx公司 | xxx@company.com | 2026-04-01 | 感谢投递简历，简历筛选中 |

（如果该类没有邮件，写：无）

## 💼 猎头招聘邮件（X 封）
| 主题 | 发件人 | 时间 | 摘要 |
|------|------|------|------|
| ... | ... | ... | ... |

（如果该类没有邮件，写：无）

## 🔔 系统通知（X 封）
| 主题 | 发件人 | 时间 | 摘要 |
|------|------|------|------|
| ... | ... | ... | ... |

（如果该类没有邮件，写：无）
```

**每封邮件只展示以下 4 个字段：**
- 主题
- 发件人
- 时间
- 一句话摘要

如果 `total_messages = 0`，就直接告诉用户：该时间段没有需要汇报的新邮件。
注意：分类输出在数据入库之前完成。分类输出完毕后，询问用户是否需要把邮件中与招聘相关的邮件存入MongoDB, 如果用户回答需要等肯定的语句，再执行下面的数据落库步骤。

## 4. 数据落库

调用 MongoDB tool 将`interview_emails.json`中的公司招聘邮件批量存入 MongoDB 数据库。

###  4.1 集合名称
`interviews`

### 4.2 存入流程

#### 4.2.1 解析邮件内容

对于`interview_emails.json`中的每条数据，解析并转化为以下数据格式，追加到列表中用于后续批量插入：
原始数据：
```json
[
  {
    "subject": "【小红书】面试满意度调研",
    "from": "xhs_recruit@xiaohongshu.com",
    "date": "2026-05-08 14:30:12 +0800",
    "preview": "body { padding: 5px 20px; } p { color: #000000; ... 感谢您参加 2026-05-08 14:00:00 Agent研发专家-AI Coding方向 的面试..."
  },
  {
    "subject": "感谢您应聘高德-AI应用后端工程师-开放平台专项职位",
    "from": "<Amap_talent@autonavi.com>",
    "date": "2026-05-07 08:10:06 +0800",
    "preview": "p { line-height: 24px; } XX，您好！ 感谢您应聘高德-AI应用后端工程师..."
  }
]
```
转化后的数据形式：
```python
documents = []
for email in emails:
    doc = {
      "unique_id": xx,
      "company_department": xx,
      "position": xx,
      "start_time": xx,
      "review": "",
      "interview_type": xx,
      "status": xx
      "source": xx,
      "created_at": xx,
      "updated_at": xx
    }
    documents.append(doc)
```
doc参数说明：

| 字段                 | 类型     | 说明                                                                                                                                                                                                                                                                                |
|--------------------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| unique_id          | string | 唯一标识，格式：`{company_department}_{position}_{date}`，用于防止重复插入。示例：- `腾讯_算法工程师_2025-04-13`（笔试/面试）- `字节跳动_后端开发_2025-04-01`示例：company = "腾讯", position = "算法工程师", start_time_date = "2025-04-13",unique_id = f"{company}_{position}_{start_time_date}", unique_id = re.sub(r'[^\w\u4e00-\u9fff]', '_', unique_id) |
| company_department | string | 发送面试邮件的公司（部门）名称，从邮件主题或发件人中提取                                                                                                                                                                                                                                                      |
| position           | string | 应聘的职位名称，从邮件主题或内容中提取                                                                                                                                                                                                                                                               |
| start_time         | string | 关键时间节点，格式：`YYYY-MM-DD HH:MM:SS`。含义根据 interview_type 不同：<br>- **简历筛选**：`date`的时间<br>- **笔试/面试**：邮件正文中邀请参加笔试/面试的具体时间<br>- 如有改时间邮件，需更新此字段                                                                                                                                            |
| review             | string | 面试复盘内容，预留1000字，初始为空字符串，面试后手动填写                                                                                                                                                                                                                                                    |
| interview_type     | string | 面试类型，包含：`简历筛选`、`笔试` 、`一面` 、`二面`、`三面`、`四面`、 `HR面`、`offer`、`拒信`                                                                                                                                                                                                                     |
| status             | string | 当前状态：`DOING`（进行中）（默认）、`PASS`（通过）、`FAIL`（未通过） 。                                                                                                                                                                                                                                    |
| source             | string | 记录来源：`email`（邮件）、`manual`（手动添加）。由该SKILL生成的面试记录来源均为`email`                                                                                                                                                                                                                         |
| created_at         | string | 记录创建时间（ISO格式）                                                                                                                                                                                                                                                                     |
| updated_at         | string | 记录更新时间（ISO格式）                                                                                                                                                                                                                                                                     |


##### 4.2.1.1 interview_type判断逻辑
面试流程顺序，不一定会经历所有阶段：
`简历筛选` → `笔试` → `一面` → `二面` → `三面` → `四面` → `HR面` → `offer`
从邮件主题中识别关键词：

**简历筛选 vs 拒信：**
两者邮件主题可能都包含"感谢投递"，需通过正文内容区分：

| 类型     | 正文特征 | 处理方式 |
|--------|----------|----------|
| **简历筛选** | - "我们已经收到了您的申请，并将认真评估"<br>- "如您的履历符合...将尽快与您取得联系，安排面试"<br>- "我们会在10个工作日内处理，请您耐心等待"<br>- "推荐您应聘xxx职位"<br>- 整体语气：积极、等待、待评估 | 新建记录，`status: DOING`，`interview_type: 简历筛选` |
| **拒信** | - "很遗憾...我们认为你与本次招聘的岗位不匹配"<br>- "我们已将你的资料保存在公司人才库中"<br>- "很遗憾我们发现您的职业经历与该职位要求略有差异"<br>- "对于您的此次应聘，我们将不做下一步安排"<br>- 整体语气：遗憾、不匹配、入库、终止 | **不新建记录**，而是查找该公司该职位最近的 `DOING` 状态记录，更新为 `status: FAIL` |

**面试类：**
- 包含"面试"、"面试邀请"、"邀请面试"等，可以从数据库中查询相同的`{公司}_{职位}_*`前缀的记录，如果有`一面`，那当前就是`二面`，依此类推；
- 包含"笔试"、"笔试通知"，interview_type=`笔试`


##### 4.2.1.2 status判断逻辑

**调用脚本自动判断 status（通过 stdin/stdout 传递数据）：**

```bash
python scripts/update_interview_status.py
```

### 4.2.2 批量存入 MongoDB

使用mongoDB工具 **bulk_upsert** 将修改后的documents批量插入数据库。

```json
// 批量 upsert：以 unique_id 为键，存在则更新，不存在则插入
mongo_bulk_upsert collection="interviews" documents='[
  {"unique_id": "腾讯_算法工程师_2025-04-13", "company_department": "腾讯", "position": "算法工程师", "start_time": "2025-04-13 14:00:00", "review": "", "interview_type": "一面", "status": "DOING", "source": "email", "created_at": "2025-04-13T10:00:00Z", "updated_at": "2025-04-13T10:00:00Z"},
  {"unique_id": "字节跳动_后端_2025-04-10", "company_department": "字节跳动", "position": "后端", ...}
]' key_field="unique_id"
```

参数说明：
- `documents`：待存入的文档列表（JSON 数组）
- `key_field`：用于判断是否存在的唯一键字段，固定为 `unique_id`

#### 4.2.3 入库结果输出

工具会自动返回结果，格式为：
```
成功处理 X 条文档到集合 'interviews'：新增 Y 条，更新 Z 条
```

或如果失败：
```
批量 upsert 失败: [错误信息]
```

**禁止**在入库阶段再次输出每封面试邮件的详细信息（已在分类整理阶段展示过），也**禁止**输出"需要注意的面试"等额外分析。

## 5. 更新面试状态

当用户告知面试结果或收到后续邮件时，更新对应记录的 status 和 review 字段：

```json
// 更新为通过
mongo_update collection="interviews" filter='{"unique_id": "腾讯_算法工程师_2025-04-13"}' update='{"$set": {"status": "PASS", "updated_at": "2025-04-14T10:00:00Z"}}' multi=false

// 更新为未通过并填写复盘
mongo_update collection="interviews" filter='{"unique_id": "腾讯_算法工程师_2025-04-13"}' update='{"$set": {"status": "FAIL", "review": "面试复盘内容...", "updated_at": "2025-04-16T10:00:00Z"}}' multi=false
```

### 收到下一阶段面试邀请时的处理

当收到某公司的下一阶段面试邀请时：

1. **将上一阶段标记为PASS**
2. **创建新的面试记录**（新阶段）

示例：收到二面邀请
```json
// 1. 将一面标记为通过
mongo_update collection="interviews" filter='{"unique_id": "腾讯_算法工程师_2025-04-13"}' update='{"$set": {"status": "PASS", "updated_at": "2025-04-14T10:00:00Z"}}' multi=false

// 2. 创建二面记录
mongo_insert collection="interviews" document='{"unique_id": "腾讯_算法工程师_2025-04-20", "company_department": "腾讯", "position": "算法工程师", "start_time": "2025-04-20 14:00:00", "review": "", "status": "DOING", "interview_type": "二面", "source": "email", "created_at": "2025-04-14T10:30:00Z", "updated_at": "2025-04-14T10:30:00Z"}'
```

## 查询面试记录

用户可以查询所有面试记录或特定条件的记录：

```json
// 查询所有面试
mongo_find collection="interviews" filter='{}' sort='{"start_time": -1}' limit=20

// 查询进行中的面试
mongo_find collection="interviews" filter='{"status": "DOING"}' sort='{"start_time": 1}' limit=20

// 查询某公司的面试
mongo_find collection="interviews" filter='{"company_department": "腾讯"}' limit=20

// 查询简历筛选阶段的记录
mongo_find collection="interviews" filter='{"interview_type": "简历筛选"}' limit=20