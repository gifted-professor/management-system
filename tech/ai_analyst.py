#!/usr/bin/env python3
"""
AI Data Analyst - Powered by DeepSeek
核心逻辑：加载数据 -> 发送表头给AI -> AI生成Python代码 -> 本地执行 -> 输出结果
"""
import os
import sys
import pandas as pd
import requests
import json
import re
import traceback
import warnings
from pathlib import Path
from typing import Optional

# 忽略 pandas 的 FutureWarning
warnings.filterwarnings('ignore')

# 配置
DEFAULT_API_KEY = "sk-0d0e2d8d0a0141dcb4728068ba3d04ff"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "tech" / "账单汇总_全部.xlsx"

class AIAnalyst:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or DEFAULT_API_KEY
        self.df = None
        self.df_path = DATA_FILE
        
    def load_data(self):
        """加载数据并进行预处理"""
        if not self.df_path.exists():
            # 尝试回退到旧文件
            legacy_path = BASE_DIR / "tech" / "账单汇总_截至10月前.xlsx"
            if legacy_path.exists():
                self.df_path = legacy_path
            else:
                raise FileNotFoundError(f"找不到数据文件: {self.df_path}")
                
        print(f"📊 正在加载数据: {self.df_path.name} ...")
        # 只读取第一张表
        try:
            self.df = pd.read_excel(self.df_path, engine='openpyxl')
            # 简单的预处理：转换日期列
            date_cols = [col for col in self.df.columns if '日期' in str(col) or '时间' in str(col)]
            for col in date_cols:
                self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
                
            # 数字列处理
            num_cols = ['收款额', '毛利', '打款金额', '退款金额']
            for col in num_cols:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)
                    
            print(f"✅ 数据加载完成: {len(self.df)} 行, {len(self.df.columns)} 列")
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            sys.exit(1)

    def get_schema_info(self) -> str:
        """获取数据的 Schema 信息（列名和类型）"""
        if self.df is None:
            return ""
            
        info = []
        info.append("DataFrame 变量名为 `df`。包含以下列：")
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            sample = str(self.df[col].dropna().iloc[0]) if not self.df[col].dropna().empty else "None"
            # 截断过长的样本
            if len(sample) > 50:
                sample = sample[:47] + "..."
            info.append(f"- {col} (类型: {dtype}, 示例: {sample})")
            
        return "\n".join(info)

    def ask(self, query: str) -> str:
        """核心方法：询问 AI 并执行，返回结果字符串"""
        if self.df is None:
            self.load_data()
            
        print(f"\n🤖 思考中: '{query}' ...")
        
        schema = self.get_schema_info()
        
        system_prompt = """你是一个 Python 数据分析助手。你的任务是将用户的自然语言问题转化为可执行的 Python Pandas 代码。
        
规则：
1. 数据已经加载到 pandas DataFrame 中，变量名为 `df`。
2. 你只需要输出 Python 代码，不要输出任何解释、Markdown 标记或 print 语句。
3. 代码的最后一行必须是一个表达式（expression），该表达式的结果就是问题的答案。或者将结果赋值给变量 `result`。
4. 不要重新加载数据，直接使用 `df`。
5. 如果需要聚合统计，请使用 groupby。
6. 如果涉及字符串匹配，请使用 str.contains。
7. 请处理可能的空值或类型不匹配。
8. 这是一个电商订单数据，'收款额'代表销售额，'毛利'代表利润。
9. 【重要】如果用户只是打招呼（如'你好'、'在吗'）或闲聊，请直接返回一个友好的字符串（例如："你好！我是您的数据助手，请问有什么可以帮您？"），不要返回 DataFrame。
10. 【重要】如果是查询数据，请尽量只选择相关的列进行展示，避免返回所有 60+ 列导致显示混乱。例如 `df[['姓名', '收款额']].head()`。
"""

        user_prompt = f"""
数据结构如下：
{schema}

用户问题：{query}

请生成 Python 代码：
"""

        try:
            code = self._call_deepseek(system_prompt, user_prompt)
            print(f"💻 生成代码:\n{code}")
            print("-" * 40)
            
            # 执行代码
            result = self._execute_code(code)
            
            # 格式化结果
            return self._format_result(result)
            
        except Exception as e:
            error_msg = f"❌ 处理出错: {str(e)}"
            print(error_msg)
            return error_msg

    def _call_deepseek(self, system: str, user: str) -> str:
        """调用 DeepSeek API"""
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.1, # 低温度以保证代码准确性
            "stream": False
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        
        # 清理代码：移除 markdown 标记
        code = re.sub(r'^```python\s*', '', content, flags=re.MULTILINE)
        code = re.sub(r'^```\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'```$', '', code, flags=re.MULTILINE)
        return code.strip()

    def _execute_code(self, code: str):
        """安全执行代码"""
        local_vars = {'df': self.df, 'pd': pd}
        
        try:
            # 尝试作为表达式执行 (eval)
            return eval(code, {}, local_vars)
        except SyntaxError:
            # 如果不是表达式，则作为语句块执行 (exec)
            exec(code, {}, local_vars)
            return local_vars.get('result')

    def _format_result(self, result) -> str:
        """格式化结果为字符串"""
        if isinstance(result, pd.DataFrame):
            if result.empty:
                return "结果为空。"
            else:
                return result.to_string()
        elif isinstance(result, pd.Series):
            return result.to_string()
        else:
            return str(result)

    def _display_result(self, result):
        """友好的结果展示（保留用于命令行）"""
        print("\n📈 分析结果：")
        print(self._format_result(result))

def main():
    if len(sys.argv) < 2:
        print("用法: python3 ai_analyst.py '你的问题'")
        print("示例: python3 ai_analyst.py '找出消费最高的5个客户'")
        return
        
    query = sys.argv[1]
    analyst = AIAnalyst()
    result = analyst.ask(query)
    print(f"\n📈 分析结果：\n{result}")

if __name__ == "__main__":
    main()
