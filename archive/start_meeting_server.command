#!/bin/bash
# 运营会议仪表盘 - 内网服务器启动脚本
# 双击运行后，员工可通过固定链接访问运营会议页面

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

# 获取本机IP
IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
PORT=8080

echo "========================================"
echo "  运营会议仪表盘服务器"
echo "========================================"
echo ""

# 检查运营会议.html是否存在
if [ ! -f "$SCRIPT_DIR/运营会议.html" ]; then
    echo "❌ 错误: 运营会议.html 文件不存在"
    echo "   请确保文件位于: $SCRIPT_DIR/运营会议.html"
    echo ""
    read -p "按回车键退出..."
    exit 1
fi

echo "✅ 服务启动成功！"
echo ""
echo "📋 访问链接："
echo "   http://${IP}:${PORT}/运营会议.html"
echo ""
echo "💡 使用说明："
echo "   1. 保持此窗口打开（关闭=服务停止）"
echo "   2. 员工可通过上述链接访问运营会议页面"
echo "   3. 更新内容后刷新页面即可看到最新数据"
echo ""
echo "🛑 停止服务：按 Ctrl+C 或关闭此窗口"
echo "========================================"
echo ""

# 启动 Python HTTP 服务器
python3 -m http.server ${PORT}
