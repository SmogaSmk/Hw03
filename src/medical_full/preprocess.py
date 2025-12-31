#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import json
import os

def preprocess_medical_data(input_file, output_dir):
    print(f"开始预处理数据: {input_file}")
    
    diseases = []
    symptoms = set()
    drugs = set()
    checks = set()
    
    rel_disease_symptom = []
    rel_disease_drug = []
    rel_disease_check = []

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                disease_name = data.get('name')
                if not disease_name:
                    continue
                
                # 提取疾病属性 (Node: Disease)
                diseases.append({
                    'disease_id': disease_name, # 使用名称作为ID保证唯一性
                    'name': disease_name,
                    'desc': data.get('desc', ''),
                    'prevent': data.get('prevent', ''),
                    'cause': data.get('cause', ''),
                    'easy_get': data.get('easy_get', ''),
                    'cure_lasttime': data.get('cure_lasttime', ''),
                    'cured_prob': data.get('cured_prob', ''),
                    'cost_money': data.get('cost_money', '')
                })

                # 提取症状并建立关系 (Node: Symptom, Rel: has_symptom)
                for s in data.get('symptom', []):
                    symptoms.add(s)
                    rel_disease_symptom.append({'disease_id': disease_name, 'symptom_id': s})
                
                # 提取常用药品并建立关系 (Node: Drug, Rel: common_drug)
                for d in data.get('common_drug', []):
                    drugs.add(d)
                    rel_disease_drug.append({'disease_id': disease_name, 'drug_id': d})
                
                # 提取检查项并建立关系 (Node: Check, Rel: need_check)
                for c in data.get('check', []):
                    checks.add(c)
                    rel_disease_check.append({'disease_id': disease_name, 'check_id': c})

    except Exception as e:
        print(f"文件读取失败: {e}")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 保存节点文件
    pd.DataFrame(diseases).to_csv(f"{output_dir}/node_disease.csv", index=False, encoding='utf-8-sig')
    pd.DataFrame([{'name': s} for s in symptoms]).to_csv(f"{output_dir}/node_symptom.csv", index=False, encoding='utf-8-sig')
    pd.DataFrame([{'name': d} for d in drugs]).to_csv(f"{output_dir}/node_drug.csv", index=False, encoding='utf-8-sig')
    pd.DataFrame([{'name': c} for c in checks]).to_csv(f"{output_dir}/node_check.csv", index=False, encoding='utf-8-sig')

    # 保存关系文件
    pd.DataFrame(rel_disease_symptom).to_csv(f"{output_dir}/rel_has_symptom.csv", index=False, encoding='utf-8-sig')
    pd.DataFrame(rel_disease_drug).to_csv(f"{output_dir}/rel_common_drug.csv", index=False, encoding='utf-8-sig')
    pd.DataFrame(rel_disease_check).to_csv(f"{output_dir}/rel_need_check.csv", index=False, encoding='utf-8-sig')

    print(f"数据处理完成！输出目录: {output_dir}")
    print(f"疾病数量: {len(diseases)}")
    print(f"症状数量: {len(symptoms)}")
    print(f"药品数量: {len(drugs)}")
    print(f"检查项数量: {len(checks)}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_json = os.path.join(current_dir, "data", "medical.json")
    output_path = os.path.join(current_dir, "processed_data")
    
    # 执行预处理
    preprocess_medical_data(input_json, output_path)
