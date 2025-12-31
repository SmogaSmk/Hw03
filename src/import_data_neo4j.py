
import os
import json
import time
from py2neo import Graph
from dotenv import load_dotenv

load_dotenv()

class MedicalGraphImporter:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_path = os.path.join(base_dir, 'data', 'medical.json')
        
        if not os.path.exists(self.data_path):
            print(f"数据文件不存在: {self.data_path}")
            print("请将 medical.json 放入 data/ 目录")
        
        host = os.getenv('NEO4J_HOST', '127.0.0.1')
        port = os.getenv('NEO4J_BOLT_PORT', '7691')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')

        try:
            self.g = Graph(f"bolt://{host}:{port}", auth=(user, password))
            print(f"Neo4j 连接成功: bolt://{host}:{port}")
        except Exception as e:
            print(f"Neo4j 连接失败: {e}")
            raise

        self.BATCH_SIZE = 500

    def print_progress(self, iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filled_length = int(length * iteration // total)
        bar = fill * filled_length + '-' * (length - filled_length)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
        if iteration == total:
            print()

    def create_indexes(self):
        labels = ['Disease', 'Drug', 'Food', 'Check', 'Department', 'Producer', 'Symptom']
        
        for label in labels:
            try:
                query = f"CREATE CONSTRAINT FOR (n:{label}) REQUIRE n.name IS UNIQUE"
                self.g.run(query)
                print(f"  - {label}: name 唯一约束已创建")
            except Exception as e_new:
                err_str = str(e_new).lower()
                if "already exists" in err_str or "equivalent constraint" in err_str:
                     print(f"  - {label}: 唯一约束已存在 (跳过)")
                else:
                    try:
                        query = f"CREATE CONSTRAINT ON (n:{label}) ASSERT n.name IS UNIQUE"
                        self.g.run(query)
                        print(f"  - {label}: name 唯一约束已创建 (旧版语法)")
                    except Exception as e_old:
                        if "already exists" in str(e_old).lower():
                             print(f"  - {label}: 唯一约束已存在 (旧版语法)")
                        else:
                            print(f"  - {label}: 索引创建失败")
                            print(f"    新语法错误: {e_new}")
                            print(f"    旧语法错误: {e_old}")

    def read_nodes(self):
        print("\n正在读取 JSON 数据...")
        start_time = time.time()
        
        data_sets = {
            'drugs': set(), 'foods': set(), 'checks': set(), 
            'departments': set(), 'producers': set(), 'symptoms': set(), 'diseases': set()
        }
        
        rels = {
            'check': [], 'recommand_eat': [], 'not_eat': [], 'do_eat': [],
            'department': [], 'common_drug': [], 'drug_producer': [],
            'recommand_drug': [], 'symptom': [], 'acompany': [], 'category': []
        }
        
        disease_infos = []

        if not os.path.exists(self.data_path):
            print(f"数据文件未找到: {self.data_path}")
            return None

        total_lines = sum(1 for _ in open(self.data_path, encoding='utf-8'))
        current_line = 0

        with open(self.data_path, encoding='utf-8') as f:
            for line in f:
                current_line += 1
                if current_line % 1000 == 0:
                    self.print_progress(current_line, total_lines, prefix='读取进度:', suffix='Doing', length=40)
                
                try:
                    data_json = json.loads(line)
                    disease = data_json['name']
                    data_sets['diseases'].add(disease)
                    
                    disease_dict = {
                        'name': disease,
                        'desc': data_json.get('desc', ''),
                        'prevent': data_json.get('prevent', ''),
                        'cause': data_json.get('cause', ''),
                        'easy_get': data_json.get('easy_get', ''),
                        'cure_department': data_json.get('cure_department', []),
                        'cure_way': data_json.get('cure_way', []),
                        'cure_lasttime': data_json.get('cure_lasttime', ''),
                        'cured_prob': data_json.get('cured_prob', '')
                    }
                    disease_infos.append(disease_dict)

                    if 'symptom' in data_json:
                        data_sets['symptoms'].update(data_json['symptom'])
                        rels['symptom'].extend([[disease, s] for s in data_json['symptom']])

                    if 'acompany' in data_json:
                        rels['acompany'].extend([[disease, a] for a in data_json['acompany']])

                    if 'cure_department' in data_json:
                        dept = data_json['cure_department']
                        data_sets['departments'].update(dept)
                        if len(dept) == 1:
                            rels['category'].append([disease, dept[0]])
                        if len(dept) == 2:
                            rels['department'].append([dept[1], dept[0]])
                            rels['category'].append([disease, dept[1]])

                    if 'common_drug' in data_json:
                        data_sets['drugs'].update(data_json['common_drug'])
                        rels['common_drug'].extend([[disease, d] for d in data_json['common_drug']])

                    if 'recommand_drug' in data_json:
                        data_sets['drugs'].update(data_json['recommand_drug'])
                        rels['recommand_drug'].extend([[disease, d] for d in data_json['recommand_drug']])

                    if 'not_eat' in data_json:
                        data_sets['foods'].update(data_json['not_eat'])
                        rels['not_eat'].extend([[disease, f] for f in data_json['not_eat']])

                    if 'do_eat' in data_json:
                        data_sets['foods'].update(data_json['do_eat'])
                        rels['do_eat'].extend([[disease, f] for f in data_json['do_eat']])

                    if 'recommand_eat' in data_json:
                        data_sets['foods'].update(data_json['recommand_eat'])
                        rels['recommand_eat'].extend([[disease, f] for f in data_json['recommand_eat']])

                    if 'check' in data_json:
                        data_sets['checks'].update(data_json['check'])
                        rels['check'].extend([[disease, c] for c in data_json['check']])

                    if 'drug_detail' in data_json:
                        for item in data_json['drug_detail']:
                            if '(' in item:
                                parts = item.split('(')
                                producer = parts[0]
                                drug = parts[-1].replace(')', '')
                                data_sets['producers'].add(producer)
                                rels['drug_producer'].append([producer, drug])

                except Exception as e:
                    continue
        
        self.print_progress(total_lines, total_lines, prefix='读取进度:', suffix='完成', length=40)
        print(f"读取完成，共 {current_line} 条疾病数据，耗时 {time.time() - start_time:.2f}s")
        return data_sets, disease_infos, rels

    def batch_create_nodes(self, label, nodes_set):
        nodes_list = list(nodes_set)
        total = len(nodes_list)
        if total == 0: return

        print(f"正在创建 {label} 节点 ({total}个)...")
        
        query = f"""
        UNWIND $batch AS name
        MERGE (n:{label} {{name: name}})
        """
        for i in range(0, total, self.BATCH_SIZE):
            batch = nodes_list[i:i + self.BATCH_SIZE]
            self.g.run(query, batch=batch)
            self.print_progress(min(i + self.BATCH_SIZE, total), total, prefix=f'   {label}', suffix='Done', length=30)

    def batch_create_disease_nodes(self, disease_infos):

        query = """
        UNWIND $batch AS row
        MERGE (d:Disease {name: row.name})
        SET d.desc = row.desc,
            d.prevent = row.prevent,
            d.cause = row.cause,
            d.easy_get = row.easy_get,
            d.cure_department = row.cure_department,
            d.cure_way = row.cure_way,
            d.cure_lasttime = row.cure_lasttime,
            d.cured_prob = row.cured_prob
        """

        for i in range(0, total, self.BATCH_SIZE):
            batch = disease_infos[i:i + self.BATCH_SIZE]
            self.g.run(query, batch=batch)
            self.print_progress(min(i + self.BATCH_SIZE, total), total, prefix='   Disease', suffix='Done', length=30)

    def batch_create_relationships(self, start_label, end_label, rel_data, rel_type, rel_name):
        """通用批量创建关系"""
        # 去重
        unique_rels = set([f"{r[0]}###{r[1]}" for r in rel_data])
        parsed_rels = [{'start': item.split('###')[0], 'end': item.split('###')[1]} for item in unique_rels]
        total = len(parsed_rels)
        
        if total == 0: return

        print(f"正在创建 {rel_type} 关系 ({total}条)...")
        
        # 批量匹配并创建关系
        # 注意: 这里依赖之前的 CREATE INDEX，否则 MATCH 会很慢
        query = f"""
        UNWIND $batch AS row
        MATCH (source:{start_label} {{name: row.start}})
        MATCH (target:{end_label} {{name: row.end}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r.name = '{rel_name}'
        """

        for i in range(0, total, self.BATCH_SIZE):
            batch = parsed_rels[i:i + self.BATCH_SIZE]
            try:
                self.g.run(query, batch=batch)
            except Exception as e:
                print(f"  批次错误: {e}")
            self.print_progress(min(i + self.BATCH_SIZE, total), total, prefix=f'   {rel_type}', suffix='Done', length=30)

    def build_all(self):
        total_start = time.time()
        
        self.create_indexes()

        result = self.read_nodes()
        if not result: return
        data_sets, disease_infos, rels = result

        print("\n--- 阶段1: 批量创建节点 ---")
        self.batch_create_nodes('Drug', data_sets['drugs'])
        self.batch_create_nodes('Food', data_sets['foods'])
        self.batch_create_nodes('Check', data_sets['checks'])
        self.batch_create_nodes('Department', data_sets['departments'])
        self.batch_create_nodes('Producer', data_sets['producers'])
        self.batch_create_nodes('Symptom', data_sets['symptoms'])
        self.batch_create_disease_nodes(disease_infos)

        # 3. 创建关系
        print("\n--- 阶段2: 批量创建关系 ---")
        # (StartLabel, EndLabel, Data, RelType, RelPropName)
        mappings = [
            ('Disease', 'Symptom', rels['symptom'], 'has_symptom', '症状'),
            ('Disease', 'Drug', rels['common_drug'], 'common_drug', '常用药品'),
            ('Disease', 'Drug', rels['recommand_drug'], 'recommand_drug', '好评药品'),
            ('Disease', 'Food', rels['do_eat'], 'do_eat', '宜吃'),
            ('Disease', 'Food', rels['not_eat'], 'no_eat', '忌吃'),
            ('Disease', 'Food', rels['recommand_eat'], 'recommand_eat', '推荐食谱'),
            ('Disease', 'Check', rels['check'], 'need_check', '诊断检查'),
            ('Disease', 'Department', rels['category'], 'belongs_to', '所属科室'),
            ('Disease', 'Disease', rels['acompany'], 'acompany_with', '并发症'),
            ('Department', 'Department', rels['department'], 'belongs_to', '属于'),
            ('Producer', 'Drug', rels['drug_producer'], 'drugs_of', '生产药品')
        ]

        for mapping in mappings:
            self.batch_create_relationships(*mapping)

        print("\n" + "=" * 50)
        print(f"知识图谱构建完成! 总耗时: {time.time() - total_start:.2f}s")
        print("=" * 50)

if __name__ == '__main__':
    importer = MedicalGraphImporter()
    importer.build_all()
