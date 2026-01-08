#!/bin/bash
# 月度销售分析一键运行脚本

# 获取脚本所在目录
cd "$(dirname "$0")"

echo "================================================"
echo "🚀 月度销售分析工具"
echo "================================================"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请先安装 Python 3"
    read -p "按回车键退出..."
    exit 1
fi

# 检查数据文件是否存在
if [ ! -f "tech/账单汇总_全部.xlsx" ]; then
    echo "❌ 错误: 未找到数据文件 tech/账单汇总_全部.xlsx"
    read -p "按回车键退出..."
    exit 1
fi

# 运行分析脚本
python3 tech/analyze_monthly_sales.py

echo ""
echo "================================================"
echo "✅ 分析完成！"
echo "================================================"
echo ""
read -p "按回车键退出..."
