#!/usr/bin/env python3
# coding: utf-8
import os
import re
import json
from neo4j_connector import Neo4jConnector
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import current_config

# 1. 自动连接 Neo4j 和 LLM
print("正在连接 Neo4j 和 AI 服务 (Kimi)...")

# 使用项目中已有的 Kimi 配置
llm = ChatOpenAI(
    model="kimi-k2-turbo-preview",
    openai_api_key=current_config.KIMI_API_KEY,
    openai_api_base="https://api.moonshot.cn/v1",
    temperature=0
)

# 使用统一的 Neo4j 连接器
neo4j = Neo4jConnector()
test_res = neo4j.test_connection()
if not test_res['success']:
    print(f"⚠️ {test_res['message']}")
else:
    print(f"{test_res['message']}")

# 2. 将自然语言转化为 cypher 语句的 Prompt 模板
cypher_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一名 Neo4j Cypher 专家。
知识图谱Schema:
- 节点：Disease、Symptom、Drug、Check、Treatment，属性只有 name:str
- 关系：
  (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
  (d:Disease)-[:TREATED_BY_DRUG]->(dr:Drug)
  (d:Disease)-[:DIAGNOSED_BY]->(c:Check)
  (d:Disease)-[:TREATED_BY]->(t:Treatment)

用户问题会被转化为一条 Cypher 查询，要求：
1. 仅返回必要的节点或属性，不要返回整个路径
2. 不得修改/删除数据
3. 用中文别名返回时，请用 name 属性
4. 只输出一条可执行的 Cypher 语句，不要解释，不要 Markdown 代码块"""),
    ("human", "{question}")
])
cypher_chain = cypher_prompt | llm | StrOutputParser()

# 3. 执行 Cypher 并处理结果
def _exec_cypher(cypher: str) -> str:
    try:
        # 只允许读语句
        if re.search(r"\b(delete|remove|set|merge|create|drop)\b", cypher, flags=re.I):
            return "验证失败：查询语句包含写操作，已拦截。"
        
        # 调试信息：打印生成的 Cypher
        # print(f"DEBUG: 执行 Cypher -> {cypher}")
        
        data = neo4j.data(cypher)
        if not data:
            return "知识库中目前没有找到相关具体条目。"
        
        # 将结果 list[dict] 拼成自然语言描述
        lines = []
        for d in data:
            line_parts = []
            for k, v in d.items():
                # 兼容直接返回节点对象的情况
                val = v.get('name') if hasattr(v, 'get') and 'name' in v else v
                line_parts.append(f"{k}：{val}")
            lines.append("；".join(line_parts))
        
        return "。".join(lines) + "。"
    except Exception as e:
        return f"数据库查询过程中出现问题：{str(e)}"

# 4. 生成自然语言回答的 Prompt 模板
answer_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是友善的医疗知识助手。请根据查询结果用一句话回答用户问题，尽量简洁。若结果为空，请礼貌说明。"),
    ("human", "用户问题：{question}\n查询结果：{result}")
])
answer_chain = answer_prompt | llm | StrOutputParser()

# 5. 完整问诊逻辑
def chat(question: str) -> str:
    try:
        # 生成 Cypher
        cypher = cypher_chain.invoke({"question": question})
        cypher = cypher.strip().strip("`").strip(";")  # 移除可能的 markdown 标记和分号
        
        # 执行查询
        result = _exec_cypher(cypher)
        
        # 生成回答
        return answer_chain.invoke({"question": question, "result": result})
    except Exception as e:
        return f"抱歉，我处理这个问题时遇到了点麻烦：{str(e)}"

if __name__ == "__main__":
    print("\n" + "="*50)
    print("您好！我是集成 Neo4j 的医疗知识助手。")
    print("我可以基于知识图谱回答：疾病症状、检查项目、用药建议、科室分类等。")
    print("输入“退出”可结束对话。")
    print("="*50 + "\n")
    
    while True:
        try:
            q = input("📝 您：").strip()
            if not q:
                continue
            lower_text = q.lower()
            if any(k in lower_text for k in {"退出", "exit", "quit", "算了"}):
                print("\n助手：感谢您的咨询，再见！")
                break
                
            print("🤖 助手：", end="", flush=True)
            res = chat(q)
            print(res)
            print("-" * 30)
        except KeyboardInterrupt:
            print("\n对话已终止。")
            break
        except Exception as e:
            print(f"\n运行时错误: {e}")