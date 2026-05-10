# -*- coding: utf-8 -*-
"""
面试状态判断脚本 - 根据 4.2.1.2 小节的逻辑判断 documents 的 status

输入：stdin 传入的 documents 列表（JSON 格式）
输出：stdout 输出带有正确 status 的 documents 列表（JSON 格式）

按照 `{company_department}_{position}_` 进行去重过滤，每次处理一种组合，
按 start_time 升序排列，从前往后判断每个 doc 的 status：
1. 有下一阶段的公司招聘邮件（start_time 比它大的）且不为拒信 → PASS
2. 没有下一阶段邮件，距离今天未超过5天，也没有拒信 → DOING
3. 其他情况 → FAIL（包括：start_time 超过5天没收到下一阶段邀请）
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Optional

# 修复 Windows 控制台编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stdin.encoding != 'utf-8':
    sys.stdin.reconfigure(encoding='utf-8')

# 面试流程顺序（用于判断下一阶段）
INTERVIEW_FLOW = [
    "简历筛选",
    "笔试",
    "一面",
    "二面",
    "三面",
    "四面",
    "HR面",
    "offer"
]


def get_next_stage(current_stage: str) -> Optional[str]:
    """获取当前阶段的下一阶段"""
    try:
        idx = INTERVIEW_FLOW.index(current_stage)
        if idx < len(INTERVIEW_FLOW) - 1:
            return INTERVIEW_FLOW[idx + 1]
    except ValueError:
        pass
    return None


def is_rejection(doc: dict) -> bool:
    """判断是否为拒信"""
    return doc.get("interview_type", "") == "拒信"


def parse_start_time(start_time_str: str) -> Optional[datetime]:
    """解析 start_time 字字符串为 datetime"""
    if not start_time_str:
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(start_time_str.strip(), fmt)
        except ValueError:
            continue
    return None


def determine_status(docs: list[dict], current_doc: dict, current_idx: int, today: datetime) -> str:
    """判断单个文档的 status"""
    current_start_time = parse_start_time(current_doc.get("start_time", ""))
    if not current_start_time:
        return "DOING"

    current_interview_type = current_doc.get("interview_type", "")

    # 检查是否有拒信
    has_rejection = False
    for doc in docs:
        if is_rejection(doc) and doc.get("company_department") == current_doc.get("company_department") \
           and doc.get("position") == current_doc.get("position"):
            rejection_time = parse_start_time(doc.get("start_time", ""))
            if rejection_time and rejection_time >= current_start_time:
                has_rejection = True
                break

    # 规则 1: 有下一阶段邮件 → PASS
    has_next_stage = False
    for i, doc in enumerate(docs):
        if i <= current_idx:
            continue
        doc_start_time = parse_start_time(doc.get("start_time", ""))
        if not doc_start_time:
            continue
        if doc_start_time > current_start_time and not is_rejection(doc):
            next_stage = get_next_stage(current_interview_type)
            doc_interview_type = doc.get("interview_type", "")
            if next_stage and doc_interview_type == next_stage:
                has_next_stage = True
                break
            if doc.get("company_department") == current_doc.get("company_department") \
               and doc.get("position") == current_doc.get("position"):
                has_next_stage = True
                break

    if has_next_stage:
        return "PASS"

    # 规则 2 & 3: 检查是否超过 5 天
    days_since_start = (today - current_start_time).days
    if days_since_start <= 5 and not has_rejection:
        return "DOING"

    return "FAIL"


def update_documents_status(documents: list[dict]) -> list[dict]:
    """更新 documents 中每条记录的 status"""
    if not documents:
        return []

    today = datetime.now()

    # 按 {company_department}_{position} 分组
    groups: dict[str, list[dict]] = {}
    for doc in documents:
        key = f"{doc.get('company_department', '')}_{doc.get('position', '')}"
        if key not in groups:
            groups[key] = []
        groups[key].append(doc)

    result_docs: list[dict] = []

    for docs in groups.values():
        docs_sorted = sorted(docs, key=lambda d: parse_start_time(d.get("start_time", "")) or datetime.min)

        for idx, doc in enumerate(docs_sorted):
            if doc.get("interview_type") == "拒信":
                continue

            doc["status"] = determine_status(docs_sorted, doc, idx, today)
            doc["updated_at"] = datetime.now().isoformat()
            result_docs.append(doc)

    return result_docs


def main() -> None:
    # 从 stdin 读取 JSON
    try:
        documents = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"JSON 解析失败: {str(e)}"}), ensure_ascii=False)
        sys.exit(1)

    # 处理 documents
    result_docs = update_documents_status(documents)

    # 输出到 stdout
    print(json.dumps(result_docs, ensure_ascii=False))


if __name__ == "__main__":
    main()