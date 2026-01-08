#!/bin/bash
# 客户预警仪表盘 - 内网服务器启动脚本
# 双击运行后，员工可通过固定链接访问最新仪表盘

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

# 获取本机IP
IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
PORT=8080

echo "========================================"
echo "  客户预警仪表盘服务器"
echo "========================================"
echo ""

# ========== 定时任务检查与安装 ==========
CRON_JOB="0 8 * * * cd \"$SCRIPT_DIR\" && ./run_customer_dashboard.command >> \"$SCRIPT_DIR/logs/auto_update.log\" 2>&1"
CRON_EXISTS=$(crontab -l 2>/dev/null | grep -F "run_customer_dashboard.command" | wc -l)

if [ "$CRON_EXISTS" -eq 0 ]; then
    echo "⏰ 定时任务检测"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "当前未配置自动更新定时任务。"
    echo ""
    echo "是否设置每天早上8点自动生成最新数据？"
    echo "  - 输入 y 安装（推荐）"
    echo "  - 输入 n 跳过（需手动运行 run_customer_dashboard.command）"
    echo ""
    read -p "请选择 [y/n]: " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 创建日志目录
        mkdir -p "$SCRIPT_DIR/logs"

        # 备份现有crontab
        crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true

        # 添加新的定时任务
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ 定时任务安装成功！"
            echo "   📅 执行时间: 每天早上 8:00"
            echo "   📝 日志位置: $SCRIPT_DIR/logs/auto_update.log"
            echo ""
            echo "   查看定时任务: crontab -l"
            echo "   删除定时任务: crontab -e (然后删除对应行)"
            echo ""
        else
            echo "❌ 定时任务安装失败，请手动配置或稍后重试"
            echo ""
        fi
    else
        echo ""
        echo "ℹ️  已跳过定时任务配置"
        echo "   如需手动配置，运行: crontab -e"
        echo "   添加行: $CRON_JOB"
        echo ""
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
else
    echo "✅ 定时任务已配置（每天早上8点自动更新）"
    echo ""
fi

# ========== 启动后端服务 ==========
echo "🚀 正在启动后台服务..."
# 杀死可能存在的旧进程 (避免端口冲突)
pkill -f "tech/contact_server.py" 2>/dev/null || true

# 启动 Contact Server (后台运行)
nohup python3 tech/contact_server.py > "$SCRIPT_DIR/logs/contact_server.log" 2>&1 &
CONTACT_SERVER_PID=$!
echo "✅ 后台服务已启动 (PID: $CONTACT_SERVER_PID)"
echo "   端口: 5005 (AI助手/数据回写)"

# 注册退出清理函数
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    kill $CONTACT_SERVER_PID 2>/dev/null || true
    echo "✅ 服务已停止"
    exit
}
trap cleanup SIGINT SIGTERM EXIT

# ========== 启动HTTP服务器 ==========
echo "✅ 前端服务启动成功！"
echo ""
echo "📋 员工访问链接（复制给员工）："
echo "   http://${IP}:${PORT}/客户预警仪表盘.html"
echo ""
echo "💡 使用说明："
echo "   1. 保持此窗口打开（关闭=服务停止）"
echo "   2. 每天早上8点会自动生成新数据"
echo "   3. 员工刷新页面即可看到最新数据"
echo ""
echo "🛑 停止服务：按 Ctrl+C 或关闭此窗口"
echo "========================================"
echo ""

# 启动 Python HTTP 服务器
python3 -m http.server "${PORT}"
