#!/usr/bin/env python3
# coding: utf-8
"""
Kimi (Moonshot) API客户端
"""

import json
import os
from typing import Optional, Dict, Any, List
from openai import OpenAI


class KimiClient:
    """Kimi (Moonshot) API客户端"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('KIMI_API_KEY', '')
        if not self.api_key:
            print("警告: 未配置KIMI_API_KEY")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="XXX"
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.6,
        model: str = "kimi-k2-turbo-preview",
        max_tokens: int = 4000,
        stream: bool = False
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {'success': False, 'error': '未配置KIMI_API_KEY'}

        try:
            if stream:
                return self._stream_completion(messages, temperature, model, max_tokens)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            } if response.usage else {}

            return {
                'success': True,
                'content': content,
                'usage': usage,
                'model': model,
                'temperature': temperature
            }

        except Exception as e:
            return {'success': False, 'error': f'错误: {str(e)}'}

    def _stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        model: str,
        max_tokens: int
    ):
        """流式输出生成器"""
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def extract_structured_data(
        self,
        text: str,
        prompt_template: str,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """从文本中提取结构化数据"""
        full_prompt = f"{prompt_template}\n\n{text}" if prompt_template else text

        messages = [
            {'role': 'system', 'content': '你是一个专业的医疗信息提取助手。请严格按照JSON格式返回提取结果，不要包含其他文字说明。'},
            {'role': 'user', 'content': full_prompt}
        ]

        result = self.chat_completion(messages, temperature=temperature)

        if result['success']:
            content = result['content'].strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

            try:
                result['parsed_data'] = json.loads(content)
                result['content'] = content
            except json.JSONDecodeError:
                # 尝试将单引号替换为双引号
                try:
                    fixed_content = content.replace("'", '"')
                    result['parsed_data'] = json.loads(fixed_content)
                    result['content'] = fixed_content
                except:
                    result['parsed_data'] = None
                    result['parse_error'] = '无法解析为JSON格式'

        return result

    def generate_cypher(
        self,
        natural_query: str,
        schema_info: str = "",
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """将自然语言查询转换为Cypher语句"""
        system_prompt = """你是一个Neo4j Cypher查询专家。根据用户的自然语言问题，生成对应的Cypher查询语句。

知识图谱Schema信息：
- 节点类型：Disease(疾病), Symptom(症状), Drug(药品), Food(食物), Check(检查), Department(科室)
- 关系类型：has_symptom, common_drug, recommand_drug, need_check, do_eat, no_eat, belongs_to, acompany_with
- Disease节点属性：name, desc, cause, prevent, cure_way, cured_prob

请只返回Cypher语句，不要包含其他说明文字。"""

        if schema_info:
            system_prompt += f"\n\n补充Schema信息：\n{schema_info}"

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"请将以下问题转换为Cypher查询：\n{natural_query}"}
        ]

        result = self.chat_completion(messages, temperature=temperature)

        if result['success']:
            cypher = result['content'].strip()
            if cypher.startswith('```'):
                lines = cypher.split('\n')
                cypher = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
            result['cypher'] = cypher

        return result
