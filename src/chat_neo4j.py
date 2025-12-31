import sys
import json
import os
from backend.tugraph_connector import TuGraphConnector
from backend.kimi_client import KimiClient
from config import current_config


class TerminalMedicalChat:
    def __init__(self):
        self.tugraph = None
        self.kimi = None
        self.init_resources()

    def init_resources(self):
        print("正在初始化医疗知识图谱系统...")

        # 初始化TuGraph连接
        try:
            self.tugraph = TuGraphConnector()
            login_result = self.tugraph.login()
            if login_result['success']:
                print("TuGraph 知识图谱连接成功")
            else:
                print(f"TuGraph 连接失败: {login_result.get('error')}")
        except Exception as e:
            print(f"TuGraph 初始化错误: {e}")

        # 初始化Kimi客户端
        try:
            self.kimi = KimiClient(api_key=current_config.KIMI_API_KEY)
            print("Kimi AI 客户端连接成功")
        except Exception as e:
            print(f"Kimi AI 初始化错误: {e}")

    def extract_medical_info(self, user_message, temperature=0.5):
        """从用户消息中提取医疗信息"""
        prompt = """请从患者描述中提取关键医疗信息，返回JSON格式：
{
    "symptoms": ["症状1", "症状2", ...],
    "disease_name": "可能的疾病名（如果提到）",
    "severity": "严重程度描述",
    "duration": "持续时间"
}"""

        try:
            result = self.kimi.extract_structured_data(user_message, prompt, temperature=temperature)
            if result['success']:
                return result.get('parsed_data', {})
        except Exception as e:
            print(f"信息提取出错: {e}")
        return {}

    def search_knowledge_graph(self, extracted_data):
        """从知识图谱中搜索相关医疗信息"""
        if not self.tugraph or not self.tugraph._initialized:
            return "", []

        related_diseases = []
        disease_details = []

        try:
            # 根据症状查找疾病
            symptoms = extracted_data.get('symptoms', [])
            if isinstance(symptoms, str):
                symptoms = [symptoms]

            for symptom in symptoms:
                cypher = f"MATCH (d:Disease)-[:has_symptom]->(s:Symptom) WHERE s.name CONTAINS '{symptom}' RETURN d LIMIT 3"
                res = self.tugraph.execute_cypher(cypher)

                if res['success'] and res.get('data'):
                    for item in res['data']:
                        if isinstance(item, list) and item:
                            try:
                                disease_obj = json.loads(item[0]) if isinstance(item[0], str) else item[0]
                                props = disease_obj.get('properties', {})
                                if props.get('name') and props['name'] not in related_diseases:
                                    related_diseases.append(props['name'])
                                    disease_details.append(props)
                            except:
                                pass

            # 如果直接提到疾病名
            disease_name = extracted_data.get('disease_name', '')
            if disease_name:
                cypher = f"MATCH (d:Disease) WHERE d.name CONTAINS '{disease_name}' RETURN d LIMIT 1"
                res = self.tugraph.execute_cypher(cypher)

                if res['success'] and res.get('data') and res['data']:
                    item = res['data'][0]
                    if isinstance(item, list) and item:
                        try:
                            disease_obj = json.loads(item[0]) if isinstance(item[0], str) else item[0]
                            props = disease_obj.get('properties', {})
                            if props and props.get('name') not in related_diseases:
                                related_diseases.insert(0, props['name'])
                                disease_details.insert(0, props)
                        except:
                            pass

        except Exception as e:
            print(f"知识图谱查询出错: {e}")

        
        kg_context = ""
        if disease_details:
            kg_context = "\n=== 医疗知识图谱检索结果 ===\n"
            for i, detail in enumerate(disease_details[:3]):
                kg_context += f"\n【疾病{i+1}】{detail.get('name', '未知')}\n"
                if detail.get('desc'):
                    kg_context += f"描述：{detail['desc']}\n"
                if detail.get('cause'):
                    kg_context += f"病因：{detail['cause']}\n"
                if detail.get('prevent'):
                    kg_context += f"预防：{detail['prevent']}\n"
                if detail.get('cure_way'):
                    kg_context += f"治疗方式：{detail['cure_way']}\n"
            kg_context += "\n=== 知识图谱信息结束 ===\n"

        return kg_context, related_diseases

    def generate_medical_advice(self, user_message, kg_context, temperature=0.5):
        """生成医疗建议"""
        if kg_context:
            system_prompt = """你是专业的医疗AI助手。请严格基于提供的【医疗知识图谱检索结果】回答问题。

重要规则：
1. 诊断建议必须来自知识图谱中的疾病信息
2. 病因、预防、治疗方式必须引用知识图谱中的原文
3. 回答格式：先说明可能的疾病，再详细说明病因、预防措施、治疗建议
4. 在回答开头说明：【数据来源：医疗知识图谱】
5. 在回答末尾提醒：以上信息仅供参考，请及时就医"""
        else:
            system_prompt = """你是专业的医疗AI助手。

重要提示：知识图谱中未找到相关数据。

请基于医学知识给出建议，但必须：
1. 在开头说明：【提示：知识图谱中暂无相关数据，以下为AI通用医学建议】
2. 给出可能的原因和建议
3. 在末尾强调：以上仅为参考，请务必及时就医获取专业诊断"""

        rag_prompt = f"用户描述：{user_message}\n\n{kg_context}"

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': rag_prompt}
        ]

        try:
            response = self.kimi.chat_completion(messages, temperature=temperature, stream=False)
            return response
        except Exception as e:
            return f"抱歉，生成建议时遇到问题: {str(e)}"

    def chat(self, user_message, temperature=0.5, show_details=False):
        """处理单次对话"""
        print("\n" + "="*60)
        print("正在分析您的症状...")

        extracted_data = self.extract_medical_info(user_message, temperature)
        if show_details and extracted_data:
            print(f"提取信息: {json.dumps(extracted_data, ensure_ascii=False, indent=2)}")

        kg_context, related_diseases = self.search_knowledge_graph(extracted_data)

        if related_diseases:
            print(f"找到相关疾病: {', '.join(related_diseases[:3])}")
        else:
            print("知识图谱中未找到直接相关信息")
          
        advice = self.generate_medical_advice(user_message, kg_context, temperature)

        print("医疗AI助手回复:")
        print("-" * 40)
        print(advice)
        print("-" * 40)

        return advice

    def run(self):
        print("欢迎使用智能医疗对话系统")
        print("输入症状描述，获取专业医疗建议")

        temperature = 0.5
        show_details = False

        while True:
            try:
                user_input = input("\n请描述您的症状: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == 'quit':
                    print("感谢使用，祝您身体健康！")
                    break

                elif user_input.lower() == 'config':
                    print(f"\n当前配置:")
                    print(f"   - 随机度(temperature): {temperature}")
                    print(f"   - 显示详细信息: {show_details}")

                    try:
                        new_temp = input(f"输入新的随机度(0.0-1.0, 当前{temperature}): ").strip()
                        if new_temp:
                            temperature = max(0.0, min(1.0, float(new_temp)))

                        new_detail = input(f"显示详细信息? (y/n, 当前{'y' if show_details else 'n'}): ").strip().lower()
                        if new_detail in ['y', 'n']:
                            show_details = new_detail == 'y'

                        print(f"配置已更新: temperature={temperature}, 详细信息={show_details}")
                    except ValueError:
                        print("配置格式错误，保持原设置")
                    continue

                self.chat(user_input, temperature, show_details)

            except KeyboardInterrupt:
                print("\n用户中断，感谢使用！")
                break
            except Exception as e:
                print(f"系统错误: {e}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
智能医疗对话系统 - 使用说明

功能：
• 基于医疗知识图谱的症状分析
• AI驱动的医疗建议生成
• 交互式终端对话界面

使用方法：
  python terminal_chat.py              # 启动交互模式

交互命令：
  输入症状描述                         # 获取医疗建议
  config                               # 调整系统参数
  quit                                 # 退出系统

注意：本系统仅提供参考建议，不能替代专业医疗诊断！
        """)
        return

    # 启动终端对话系统
    try:
        chat_system = TerminalMedicalChat()
        chat_system.run()
    except Exception as e:
        print(f"系统启动失败: {e}")
        print("请检查配置文件和网络连接")


if __name__ == '__main__':
    main()
