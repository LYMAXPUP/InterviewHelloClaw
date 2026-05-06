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
按以下类别整理邮件（每一封邮件都要且只能归到一类）：

#### 3.1.1 公司招聘邮件
由招聘公司发出与面试、招聘相关的邮件。 从邮件主题中识别关键词，满足其中一种就是此类别的邮件：
- 包含"面试"、"面试邀请"、"邀请面试"
- 包含"笔试"、"笔试通知"
- 简历筛选，比如"我们已经收到了您的申请，并将认真评估"、"如您的履历符合...将尽快与您取得联系，安排面试"、"我们会在10个工作日内处理，请您耐心等待"、"推荐您应聘xxx职位"<br>- 整体语气：积极、等待、待评估。
- 拒信：比如"很遗憾...我们认为你与本次招聘的岗位不匹配"<br>- "我们已将你的资料保存在公司人才库中"<br>- "很遗憾我们发现您的职业经历与该职位要求略有差异"<br>- "对于您的此次应聘，我们将不做下一步安排" 整体语气：遗憾、不匹配、入库、终止。
- 面试评价：比如"非常感谢您参加xxx的面试！为了进一步提升面试体验，诚邀您花费一分钟的时间填写下面的问卷"

#### 3.1.2 猎头招聘邮件
#### 3.1.3 系统通知

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

**注意：分类输出在数据入库之前完成**。分类输出完毕后，询问用户是否需要把邮件中与招聘相关的邮件存入MongoDB,
如果用户回答需要等肯定的语句，再执行下面的数据落库步骤。

## 4. 数据落库

调用 MongoDB tool 将”公司招聘邮件“这一类所有邮件批量存入/更新 MongoDB 数据库。

###  4.1 集合名称
`interviews`

### 4.2 数据结构

每条面试记录包含以下字段：

```json
{
  "unique_id": "company_position_starttime",
  "company_department": "公司名称（部门）",
  "position": "应聘职位",
  "start_time": "2025-04-13 14:00:00",
  "review": "",
  "interview_type": "一面",
  "status": "DOING",
  "source": "email",
  "created_at": "2025-04-10T10:30:00Z",
  "updated_at": "2025-04-10T10:30:00Z"
}
```

#### 4.2.1 字段说明

| 字段 | 类型 | 说明                                                                                                                                                                                                                                                                                          |
|------|------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| unique_id | string | 唯一标识，格式：`{公司}_{职位}_{start_time日期}`，用于防止重复插入。示例：- `腾讯_算法工程师_2025-04-13`（笔试/面试）- `字节跳动_后端开发_2025-04-01`示例：company = "腾讯", position = "算法工程师", start_time_date = "2025-04-13",unique_id = f"{company}_{position}_{start_time_date}", unique_id = re.sub(r'[^\w\u4e00-\u9fff]', '_', unique_id) |
| company_department | string | 发送面试邮件的公司（部门）名称，从邮件主题或发件人中提取                                                                                                                                                                                                                                                                |
| position | string | 应聘的职位名称，从邮件主题或内容中提取                                                                                                                                                                                                                                                                         |
| start_time | string | 关键时间节点，格式：`YYYY-MM-DD HH:MM:SS`。含义根据 interview_type 不同：<br>- **简历筛选**：邮件发送时间<br>- **笔试/面试**：邮件正文中邀请参加笔试/面试的具体时间<br>- 如有改时间邮件，需更新此字段                                                                                                                                                         |
| review | string | 面试复盘内容，预留1000字，初始为空字符串，面试后手动填写                                                                                                                                                                                                                                                              |
| interview_type | string | 面试类型，包含：`简历筛选`、`笔试` 、`一面` 、`二面`、`三面`、`四面`、 `HR面`、`offer`                                                                                                                                                                                                                                    |
| status | string | 当前状态：`DOING`（进行中）（默认）、`PASS`（通过）、`FAIL`（未通过） 。                                                                                                                                                                                                                                              |
| source | string | 记录来源：`email`（邮件）、`manual`（手动添加）。由该SKILL生成的面试记录来源均为`email`                                                                                                                                                                                                                                   |
| created_at | string | 记录创建时间（ISO格式）                                                                                                                                                                                                                                                                               |
| updated_at | string | 记录更新时间（ISO格式）                                                                                                                                                                                                                                                                               |


### 4.3 存入流程

#### 4.3.1 解析邮件内容，填充基础字段

解析3.1.1小节中”公司招聘邮件“这一类所有邮件，按照4.2小节的说明生成相应的数据结构并填充相应的字段，加入到文档列表中：

```python
documents = []
for email in emails:
    doc = {
      "unique_id": xx,
      "company_department": xx,
      "position": xx,
      "start_time": xx,
      "review": "",
      "interview_type": 详见4.3.1.1小节,
      "status": 详见4.3.1.2小节,
      "source": xx,
      "created_at": xx,
      "updated_at": xx
    }
    documents.append(doc)
```

##### 4.3.1.1 interview_type判断逻辑
面试流程顺序，不一定会经历所有阶段：
`简历筛选` → `笔试` → `一面` → `二面` → `三面` → `四面` → `HR面` → `offer`
从邮件主题中识别关键词：

**简历筛选 vs 终止：**
两者邮件主题可能都包含"感谢投递"，需通过正文内容区分：

| 类型 | 正文特征 | 处理方式 |
|------|----------|----------|
| **简历筛选** | - "我们已经收到了您的申请，并将认真评估"<br>- "如您的履历符合...将尽快与您取得联系，安排面试"<br>- "我们会在10个工作日内处理，请您耐心等待"<br>- "推荐您应聘xxx职位"<br>- 整体语气：积极、等待、待评估 | 新建记录，`status: DOING`，`interview_type: 简历筛选` |
| **终止（拒信）** | - "很遗憾...我们认为你与本次招聘的岗位不匹配"<br>- "我们已将你的资料保存在公司人才库中"<br>- "很遗憾我们发现您的职业经历与该职位要求略有差异"<br>- "对于您的此次应聘，我们将不做下一步安排"<br>- 整体语气：遗憾、不匹配、入库、终止 | **不新建记录**，而是查找该公司该职位最近的 `DOING` 状态记录，更新为 `status: FAIL` |

**面试邀请类：**
- 包含"面试"、"面试邀请"、"邀请面试"等，可以从数据库中查询相同的`{公司}_{职位}_*`前缀的记录，如果有`一面`，那当前就是`二面`，依此类推；
- 包含"笔试"、"笔试通知"，interview_type=`笔试`


##### 4.3.1.2 status判断逻辑
1. **DOING（进行中）**：数据库中没有该{公司}_{职位}的下一阶段公司招聘邮件，且start_time距离今天未超过5天
2. **PASS（通过）**：数据库中{公司}_{职位}下一阶段的公司招聘邮件，当前阶段为PASS
3. **FAIL（未通过）**：
   - 收到面试反馈问卷，正文包含"非常感谢您参加xxx的面试！为了进一步提升面试体验，诚邀您花费一分钟的时间填写下面的问卷"，这表示面试已结束且未通过。
   - 收到拒信，查找该{公司}_{职位}最近的 `DOING` 状态记录，更新为 `status: FAIL`
   - 每个阶段5天内未进入下一阶段，自动标记status为FAIL
      判定时间基准：以 `start_time` 为基准，示例：
      - 一面 start_time 是4月10日 → 4月15日前未收到二面邀请 → 一面状态改为FAIL
      - 简历筛选 start_time 是4月1日 → 4月6日前未收到笔试/一面邀请 → 简历筛选状态改为FAIL
      - 二面 start_time 是4月20日 → 4月25日前未收到三面/HR面邀请 → 二面状态改为FAIL

    
### 4.3.2 批量存入 MongoDB

**重要：使用批量操作，不要一条一条插入！**

#### 4.3.2.1 批量查询已存在的记录

```json
// 使用 $in 批量查询所有 unique_id
mongo_find collection="interviews" filter='{"unique_id": {"$in": ["腾讯_算法工程师_2025-04-13", "字节跳动_后端_2025-04-10", ...]}}' limit=50
```

#### 4.3.2.2 分离新增和更新

根据查询结果，将文档分为两类：
- **新增**：unique_id 不存在的记录
- **更新**：unique_id 已存在的记录

#### 4.3.2.3 批量插入新记录

```json
// 正确方式：使用 documents 参数一次性批量插入所有新记录
mongo_insert collection="interviews" documents='[
  {"unique_id": "腾讯_算法工程师_2025-04-13", "company_department": "腾讯", "position": "算法工程师", ...},
  {"unique_id": "字节跳动_后端_2025-04-10", "company_department": "字节跳动", "position": "后端", ...}
]'

// 错误方式：一条一条插入（效率低，会消耗大量迭代次数）
mongo_insert collection="interviews" document='{"unique_id": "腾讯_算法工程师_2025-04-13", ...}'
mongo_insert collection="interviews" document='{"unique_id": "字节跳动_后端_2025-04-10", ...}'
// ... 这样一条一条插入是错误的做法！
```

#### 4.3.2.4 批量更新已存在的记录

**重要：优先使用条件筛选 + multi=True 批量更新，减少迭代次数消耗！**

```json
// 方式1：如果所有更新内容相同，用条件筛选 + multi=True 一次性更新
mongo_update collection="interviews"
  filter='{"unique_id": {"$in": ["腾讯_算法工程师_2025-04-13", "字节跳动_后端_2025-04-10"]}}'
  update='{"$set": {"status": "DOING", "updated_at": "2025-04-14T10:00:00Z"}}'
  multi=true

// 方式2：如果每条记录更新内容不同，只能逐条更新（但这种情况应尽量避免）
mongo_update collection="interviews" filter='{"unique_id": "腾讯_算法工程师_2025-04-13"}' update='{"$set": {"start_time": "2025-04-13 16:00:00"}}' multi=false
mongo_update collection="interviews" filter='{"unique_id": "字节跳动_后端_2025-04-10"}' update='{"$set": {"status": "FAIL"}}' multi=false
```

#### 4.3.2.5 如果工具不支持批量操作

如果 MongoDB 工具不支持 `insert_many` 或 `bulk_update`，则：
1. 先批量查询获取已存在的 unique_id 列表
2. 遍历文档列表，收集需要插入和更新的操作
3. 依次执行（虽然不是真正的批量，但至少减少了查询次数）

#### 4.3.3 入库结果输出

**入库完成后只输出一行简短结果，不要逐条列出详情：**

```
✅ 已成功录入 X 条面试记录，Y 条更新，Z 条失败。
```

或如果全部失败：
```
❌ X 条面试记录录入失败。
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
```

