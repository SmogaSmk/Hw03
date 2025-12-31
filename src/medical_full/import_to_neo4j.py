#!/usr/bin/env python3
# coding: utf-8
import os
import pandas as pd
from py2neo import Node, Relationship
from config import current_config
from neo4j_connector import Neo4jConnector

# 使用统一的 Neo4j 连接器
neo4j = Neo4jConnector()
test_res = neo4j.test_connection()
if not test_res['success']:
    print(test_res['message'])
    exit(1)
else:
    print(test_res['message'])

graph = neo4j.graph

def import_diseases(csv_path):
    print(f"开始导入疾病节点: {csv_path}")
    df = pd.read_csv(csv_path)
    count = 0
    for _, row in df.iterrows():
        props = {
            'name': row['name'],
            'desc': str(row.get('desc', '')),
            'prevent': str(row.get('prevent', '')),
            'cause': str(row.get('cause', '')),
            'easy_get': str(row.get('easy_get', '')),
            'cure_lasttime': str(row.get('cure_lasttime', '')),
            'cured_prob': str(row.get('cured_prob', '')),
            'cost_money': str(row.get('cost_money', ''))
        }
        node = Node('Disease', **props)
        graph.merge(node, 'Disease', 'name')
        count += 1
        if count % 1000 == 0:
            print(f"已处理 {count} 个疾病节点...")
    print(f"疾病节点导入完成，共 {count} 条。")

def import_related_nodes(csv_path, label):
    print(f"开始导入 {label} 节点: {csv_path}")
    df = pd.read_csv(csv_path)
    id_col = df.columns[0]
    count = 0
    for _, row in df.iterrows():
        name = str(row[id_col]).strip()
        if name:
            node = Node(label, name=name)
            graph.merge(node, label, 'name')
            count += 1
    print(f"{label} 节点导入完成，共 {count} 条。")

def import_relationships(csv_path, rel_type, start_label, end_label):
    print(f"开始导入关系 {rel_type}: {csv_path}")
    df = pd.read_csv(csv_path)
    start_col = 'disease_id'
    end_col = df.columns[1]
    
    count = 0
    for _, row in df.iterrows():
        start_node = graph.nodes.match(start_label, name=row[start_col]).first()
        end_node = graph.nodes.match(end_label, name=row[end_col]).first()
        
        if start_node and end_node:
            rel = Relationship(start_node, rel_type, end_node)
            graph.merge(rel)
            count += 1
            if count % 2000 == 0:
                print(f"已建立 {count} 条 {rel_type} 关系...")
    print(f"关系 {rel_type} 导入完成，共 {count} 条。")

if __name__ == "__main__":
    DATA_DIR = "processed_data"
    
    # 1. 导入主要节点
    import_diseases(os.path.join(DATA_DIR, "node_disease.csv"))
    
    # 2. 导入辅助节点
    import_related_nodes(os.path.join(DATA_DIR, "node_symptom.csv"), "Symptom")
    import_related_nodes(os.path.join(DATA_DIR, "node_drug.csv"), "Drug")
    import_related_nodes(os.path.join(DATA_DIR, "node_check.csv"), "Check")
    
    # 3. 导入关系
    import_relationships(os.path.join(DATA_DIR, "rel_has_symptom.csv"), "HAS_SYMPTOM", "Disease", "Symptom")
    import_relationships(os.path.join(DATA_DIR, "rel_common_drug.csv"), "TREATED_BY_DRUG", "Disease", "Drug")
    import_relationships(os.path.join(DATA_DIR, "rel_need_check.csv"), "DIAGNOSED_BY", "Disease", "Check")
    
    print("\n" + "="*30)
    print("📊 数据导入统计结果：")
    for label in ["Disease", "Symptom", "Drug", "Check"]:
        count = graph.run(f"MATCH (n:{label}) RETURN count(n) as c").evaluate()
        print(f"节点 {label}: {count}")
    
    for rel in ["HAS_SYMPTOM", "TREATED_BY_DRUG", "DIAGNOSED_BY"]:
        count = graph.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) as c").evaluate()
        print(f"关系 {rel}: {count}")
    print("="*30)
