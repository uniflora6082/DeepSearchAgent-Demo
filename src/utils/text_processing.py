"""
文本处理工具函数
用于清理LLM输出、解析JSON等
"""

import json
import re
from typing import Any, Dict, List
from json.decoder import JSONDecodeError


def clean_json_tags(text: str) -> str:
    """
    清理文本中的JSON标签
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    # 移除```json 和 ```标签
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = re.sub(r'```', '', text)
    
    return text.strip()


def clean_markdown_tags(text: str) -> str:
    """
    清理文本中的Markdown标签
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    # 移除```markdown 和 ```标签
    text = re.sub(r'```markdown\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = re.sub(r'```', '', text)
    
    return text.strip()


def remove_reasoning_from_output(text: str) -> str:
    """
    移除输出中的推理过程文本
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    stripped_text = text.strip()
    cleaned_text = clean_json_tags(stripped_text)

    if cleaned_text.lstrip().startswith(("{", "[")):
        return cleaned_text.strip()

    json_fragment = _extract_balanced_json(cleaned_text)
    if json_fragment:
        fragment_start = cleaned_text.find(json_fragment)
        prefix = cleaned_text[:fragment_start].strip()
        if len(prefix) <= 200 and re.search(
            r'(?:json|reasoning|analysis|explanation|推理|思考|解释|说明|输出|结果)',
            prefix,
            flags=re.IGNORECASE,
        ):
            return cleaned_text[fragment_start:].strip()

    return stripped_text


def _extract_balanced_json(text: str) -> str:
    """返回文本中的第一个完整 JSON object/array 字符串。"""
    start = re.search(r'[\{\[]', text)
    if not start:
        return ""

    opening = text[start.start()]
    closing = "}" if opening == "{" else "]"
    stack = [closing]
    in_string = False
    escaped = False

    for index in range(start.start() + 1, len(text)):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char in "{[":
            stack.append("}" if char == "{" else "]")
        elif char in "}]":
            if not stack or char != stack[-1]:
                return ""
            stack.pop()
            if not stack:
                return text[start.start():index + 1]

    return ""


def _parse_balanced_json_sequence(text: str) -> tuple[bool, Any]:
    """解析文本中连续出现的 JSON object/array。"""
    values = []
    position = 0

    while position < len(text):
        if values:
            while position < len(text) and text[position].isspace():
                position += 1

            if position >= len(text) or text[position] != ",":
                break

            position += 1

            while position < len(text) and text[position].isspace():
                position += 1

        fragment = _extract_balanced_json(text[position:])
        if not fragment:
            break

        fragment_start = text.find(fragment, position)
        between = text[position:fragment_start].strip()
        if values and between:
            break

        try:
            values.append(json.loads(fragment))
        except JSONDecodeError:
            break

        position = fragment_start + len(fragment)

    if len(values) > 1:
        return True, values
    if values:
        return True, values[0]

    return False, None


def extract_clean_response(text: str) -> Any:
    """
    提取并清理响应中的JSON内容
    
    Args:
        text: 原始响应文本
        
    Returns:
        解析后的JSON内容
    """
    candidates = [
        text.strip(),
        clean_json_tags(text),
        remove_reasoning_from_output(clean_json_tags(text)),
    ]

    for candidate in candidates:
        if not candidate:
            continue

        try:
            return json.loads(candidate)
        except JSONDecodeError:
            pass

        found_json, parsed_json = _parse_balanced_json_sequence(candidate)
        if found_json:
            return parsed_json

    cleaned_text = remove_reasoning_from_output(clean_json_tags(text))
    
    # 如果所有方法都失败，返回错误信息
    print(f"无法解析JSON响应: {cleaned_text[:200]}...")
    return {"error": "JSON解析失败", "raw_text": cleaned_text}


def update_state_with_search_results(search_results: List[Dict[str, Any]], 
                                   paragraph_index: int, state: Any) -> Any:
    """
    将搜索结果更新到状态中
    
    Args:
        search_results: 搜索结果列表
        paragraph_index: 段落索引
        state: 状态对象
        
    Returns:
        更新后的状态对象
    """
    if 0 <= paragraph_index < len(state.paragraphs):
        # 获取最后一次搜索的查询（假设是当前查询）
        current_query = ""
        if search_results:
            # 从搜索结果推断查询（这里需要改进以获取实际查询）
            current_query = "搜索查询"
        
        # 添加搜索结果到状态
        state.paragraphs[paragraph_index].research.add_search_results(
            current_query, search_results
        )
    
    return state


def validate_json_schema(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    验证JSON数据是否包含必需字段
    
    Args:
        data: 要验证的数据
        required_fields: 必需字段列表
        
    Returns:
        验证是否通过
    """
    return all(field in data for field in required_fields)


def truncate_content(content: str, max_length: int = 20000) -> str:
    """
    截断内容到指定长度
    
    Args:
        content: 原始内容
        max_length: 最大长度
        
    Returns:
        截断后的内容
    """
    if len(content) <= max_length:
        return content
    
    # 尝试在单词边界截断
    truncated = content[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # 如果最后一个空格位置合理
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."


def format_search_results_for_prompt(search_results: List[Dict[str, Any]], 
                                   max_length: int = 20000) -> List[str]:
    """
    格式化搜索结果用于提示词
    
    Args:
        search_results: 搜索结果列表
        max_length: 每个结果的最大长度
        
    Returns:
        格式化后的内容列表
    """
    formatted_results = []
    
    for result in search_results:
        content = result.get('content', '')
        if content:
            truncated_content = truncate_content(content, max_length)
            formatted_results.append(truncated_content)
    
    return formatted_results
