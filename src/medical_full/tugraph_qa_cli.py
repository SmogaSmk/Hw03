#!/usr/bin/env python3
# coding: utf-8
import os
import re
import json
from tugraph_connector import TuGraphConnector
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import current_config

# 1. 初始化资源
print("正在连接 TuGraph 和 AI 服务 (Kimi)...")

llm = ChatOpenAI(
    model="kimi-k2-turbo-preview",
    openai_api_key=current_config.KIMI_API_KEY,
    openai_api_base="https://api.moonshot.cn/v1",
    temperature=0
)

tugraph = TuGraphConnector(
    host=current_config.TUGRAPH_HOST,
    port=current_config.TUGRAPH_PORT,
    user=current_config.TUGRAPH_USER,
    password=current_config.TUGRAPH_PASSWORD,
    graph_name='medical'  # 默认使用 medical 图谱
)

test_res = tugraph.test_connection()
if not test_res['success']:
    print(f"⚠️ TuGraph 连接警告: {test_res.get('error')}")
    print("将以降级模式继续运行...")
else:
    print(f"✅ {test_res['message']}")

# 2. 将自然语言转化为 cypher 语句的 Prompt 模板
cypher_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一名 TuGraph Cypher 专家。
知识图谱Schema:
- 节点：Disease、Symptom、Drug、Check，属性只有 name:str
- 关系：
  (d:Disease)-[:has_symptom]->(s:Symptom)
  (d:Disease)-[:common_drug]->(dr:Drug)
  (d:Disease)-[:need_check]->(c:Check)

用户问题会被转化为一条 Cypher 查询，要求：
1. 仅返回必要的节点或属性，不要返回整个路径。
2. 必须先从用户问题中提取核心医疗实体（如：把“我感冒三天了”提取为“感冒”）。
3. 如果不确定实体全名，可以使用 `WHERE n.name CONTAINS '关键词'`。
4. 不得修改/删除数据。
5. 只输出一条可执行的 Cypher 语句，不要解释，不要 Markdown 代码块。
注意：TuGraph 的关系名是小写的 (has_symptom, common_drug, need_check)。"""),
    ("human", "{question}")
])
cypher_chain = cypher_prompt | llm | StrOutputParser()

# 3. 执行 Cypher 并处理结果
def _exec_cypher(cypher: str) -> str:
    try:
        if re.search(r"\b(delete|remove|set|merge|create|drop)\b", cypher, flags=re.I):
            return "验证失败：查询语句包含写操作，已拦截。"
        
        result = tugraph.execute_cypher(cypher.strip().strip(";"))
        
        if not result['success']:
            return f"图数据库查询失败: {result.get('error')}"
        
        data = result.get('data', [])
        if not data:
            return "知识库中目前没有找到相关具体条目。"
        
        lines = []
        for item in data:
            if isinstance(item, dict):
                lines.append("；".join(f"{k}：{v}" for k, v in item.items()))
            elif isinstance(item, list):
                lines.append("；".join([str(x) for x in item]))
            else:
                lines.append(str(item))
        
        return "。".join(lines) + "。"
    except Exception as e:
        return f"查询过程中出现问题：{str(e)}"

# 4. 生成自然语言回答的 Prompt 模板
answer_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是友善的医疗知识助手。请根据查询结果用一句话回答用户问题，尽量简洁。若结果为空，请礼貌说明。"),
    ("human", "用户问题：{question}\n查询结果：{result}")
])
answer_chain = answer_prompt | llm | StrOutputParser()

# 5. 完整问诊逻辑
def chat(question: str) -> str:
    try:
        cypher = cypher_chain.invoke({"question": question})
        cypher = cypher.strip().strip("`").strip(";")
        
        print(f"\n[DEBUG Cypher]: {cypher}")
        
        result = _exec_cypher(cypher)
        
        return answer_chain.invoke({"question": question, "result": result})
    except Exception as e:
        return f"抱歉，我处理这个问题时遇到了点麻烦：{str(e)}"

if __name__ == "__main__":
    print("\n" + "="*50)
    print("您好！我是集成 TuGraph 的医疗知识助手。")
    print("我可以基于图数据库回答：疾病症状、检查项目、用药建议等。")
    print("输入“退出”可结束对话。")
    print("="*50 + "\n")
    
    while True:
        try:
            q = input("📝 [TuGraph] 您：").strip()
            if not q:
                continue
            lower_text = q.lower()
            if any(k in lower_text for k in {"退出", "exit", "quit"}):
                print("\n助手：感谢使用 TuGraph 对话系统，再见！")
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
