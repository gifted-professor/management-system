#!/bin/bash
# 智能数据分析师 - 交互式入口

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

echo "========================================"
echo "🤖 AI 数据分析师"
echo "========================================"
echo "请输入您想了解的数据问题（输入 'q' 退出）"
echo "示例："
echo " - '找出消费最高的5个客户'"
echo " - '统计各省份的销售额排名'"
echo " - '找出所有买过羽绒服且退货率大于30%的客户'"
echo "========================================"

while true; do
    echo ""
    read -p "🤔 请输入问题: " query
    
    if [[ "$query" == "q" || "$query" == "exit" || "$query" == "quit" ]]; then
        echo "👋 再见！"
        break
    fi
    
    if [[ -z "$query" ]]; then
        continue
    fi
    
    # 调用 Python 脚本
    python3 "$SCRIPT_DIR/tech/ai_analyst.py" "$query"
done
