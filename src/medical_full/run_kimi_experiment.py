#!/usr/bin/env python3
# coding: utf-8
import os
import json
import random
from itertools import product
from typing import List, Dict
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import current_config

# 配置参数
DATA_PATH      = "data/medQA_mock.csv"  
OUT_DIR        = "experiments_output"
SAMPLE_N       = 3            
RANDOM_SEED    = 42

# 使用 Kimi 配置
OPENAI_API_KEY  = current_config.KIMI_API_KEY
OPENAI_BASE_URL = "https://api.moonshot.cn/v1"
MODEL_NAME      = "kimi-k2-turbo-preview"

# 三种医疗Prompt模板
PROMPT_TEMPLATES: Dict[str, str] = {
    "详细结构版": """
作为医疗数据分析专家，请从以下医患对话中提取结构化信息：

患者主诉：{question}
医生诊断建议：{answer}

请严格按照JSON格式提取以下五大核心要素：

1. 疾病信息(diseases): 
   - 疾病标准名称

2. 症状描述(symptoms):
   - 主要症状名称

3. 药物治疗(drugs):
   - 药品通用名称

4. 检查项目(checks):
   - 检查具体项目

5. 非药物治疗(treatments):
   - 物理治疗或生活方式干预或康复训练

要求：尽量保证字段完整性和医学术语标准化。

输出示例：
{{
    "diseases": [
        {{
            "name": "高血压"
        }}
    ],
    "symptoms": [
        {{
            "name": "头痛"
        }}
    ],
    "drugs": [
        {{
            "name": "硝苯地平"
        }}
    ],
    "checks": [
        {{
            "name": "血压监测"
        }}
    ],
    "treatments": [
        {{
            "name": "低盐饮食"
        }}
    ]
}}
""",

    "简洁高效版": """
提取以下医疗文本的关键信息：

症状：{question}
诊断治疗：{answer}

要求：直接返回简洁的JSON格式，包含以下五大字段：
- diseases: 疾病信息[]
- symptoms: 症状信息[]  
- drugs: 药物信息[]
- checks: 检查项目[]
- treatments: 非药物治疗[]
如果某个字段没有信息，请留空列表 []

要求：返回json格式。
""",

    "示例引导版": """
作为临床医生，请根据以下示例的病例和提取结果进行结构化信息提取：

示例输入：
患者情况:最近有发烧、腹泻的情况是怎么回事？
医疗建议:可能是肠胃炎，建议可以口服吗叮啉，雷尼替丁，疏肝健胃丸等药物一块治疗，可以化验大便，注意补水，忌生冷食物，多吃蔬菜水果。
示例输出:{{"diseases": ["肠胃炎"], "symptoms": ["发烧","腹泻"], "drugs": ["吗丁啉","雷尼替丁","疏肝健胃丸"], "checks": ["化验大便"], "treatments": ["注意补水", "忌生冷食物","多吃蔬菜水果"]}}

请进行专业分析并提取：
患者情况：{question}
医疗建议：{answer}
要求：返回JSON格式分析结果。
"""
}

# 三种 temperature
TEMP_LIST = [0.0, 0.5, 0.8]

# 随机取数据测试
def load_data(path: str, n: int = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    if n and len(df) > n:
        df = df.sample(n=n, random_state=RANDOM_SEED)
    return df

# 大模型调用
def build_chain(tpl: str, temp: float):
    prompt = ChatPromptTemplate.from_template(tpl)
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        openai_api_base=OPENAI_BASE_URL,
        model=MODEL_NAME,
        temperature=temp,
    )
    return prompt | llm | StrOutputParser()

# 提取json文件中文本
def safe_parse_json(text: str) -> Dict:
    try:
        return json.loads(text)
    except Exception:
        # 处理可能的 markdown 代码块或冗余文本
        st, ed = text.find("{"), text.rfind("}")
        if st >= 0 and ed > st:
            try:
                return json.loads(text[st:ed+1])
            except Exception:
                pass
        return {}

def run_experiment(df: pd.DataFrame):
    os.makedirs(OUT_DIR, exist_ok=True)
    records: List[Dict] = df.to_dict(orient="records")
    
    for (st_name, st_tpl), temp in product(PROMPT_TEMPLATES.items(), TEMP_LIST):
        chain = build_chain(st_tpl, temp)
        csv_file = os.path.join(OUT_DIR, f"{st_name}_T{temp}.csv")
        print(f"[+] Running {st_name} + T={temp} -> {csv_file}")
        
        rows = []
        for item in records:
            question = item["question"]
            answer   = item["answer"]
            try:
                raw = chain.invoke({"question": question, "answer": answer})
                js  = safe_parse_json(raw)
            except Exception as e:
                print(f"Error invoking chain: {e}")
                js = {}
                
            # 把 list[dict] 或 list[str] 转成「空格分隔」字符串
            def join_field(key):
                val = js.get(key, [])
                if not isinstance(val, list):
                    return ""
                items = [
                    str(entry).strip()
                    for v in val
                    if v and (entry := (v.get("name") if isinstance(v, dict) else v))
                ]
                return " ".join(items)
            
            rows.append({
                "diseases"  : join_field("diseases"),
                "symptoms"  : join_field("symptoms"),
                "drugs"     : join_field("drugs"),
                "checks"    : join_field("checks"),
                "treatments": join_field("treatments")
            })
            
        pd.DataFrame(rows).to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"[-] Done {csv_file}")
        
        # 输出转化结果示例
        print(f"------------ 转化结果 - {st_name} T={temp} ------------")
        top3 = pd.read_csv(csv_file, keep_default_na=False).head(3)
        for idx, row in top3.iterrows():
            print(f"Row{idx + 1} | ds:{row['diseases']} | sy:{row['symptoms']} | dr:{row['drugs']} | ch:{row['checks']} | tr:{row['treatments']}")
        print("-" * 80)

if __name__ == "__main__":
    if not os.path.exists(DATA_PATH):
        print(f"错误：找不到数据文件 {DATA_PATH}")
        exit(1)
        
    df = load_data(DATA_PATH, SAMPLE_N)
    print("数据载入完成，数量 =", len(df))
    run_experiment(df)
