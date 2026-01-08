#!/bin/bash
# 网络诊断脚本 - 检查 VPN 是否影响内网服务

echo "========================================"
echo "  内网服务网络诊断工具"
echo "========================================"
echo ""

PORT=8080

# 1. 检查所有网络接口
echo "📡 当前网络接口："
ifconfig | grep -E "^[a-z]|inet " | grep -v "inet6"
echo ""

# 2. 检测 VPN 连接
echo "🔍 检测 VPN 连接："
VPN_FOUND=0

# 检查常见 VPN 接口
if ifconfig | grep -q "utun"; then
    echo "   ⚠️  检测到 VPN 接口（utun）"
    VPN_FOUND=1
fi

if ifconfig | grep -q "tun0"; then
    echo "   ⚠️  检测到 VPN 接口（tun0）"
    VPN_FOUND=1
fi

if ifconfig | grep -q "ppp0"; then
    echo "   ⚠️  检测到 VPN 接口（ppp0）"
    VPN_FOUND=1
fi

if [ $VPN_FOUND -eq 0 ]; then
    echo "   ✅ 未检测到活动的 VPN 连接"
fi
echo ""

# 3. 获取局域网 IP
echo "🏠 局域网 IP 地址："
LAN_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | grep "192.168\|10\.\|172\." | awk '{print $2}' | head -n 1)

if [ -z "$LAN_IP" ]; then
    echo "   ❌ 未找到局域网 IP（可能 VPN 接管了所有流量）"
    echo ""
    echo "💡 建议："
    echo "   1. 关闭 VPN 后重新运行此脚本"
    echo "   2. 或配置 VPN 的分离隧道功能"
else
    echo "   ✅ $LAN_IP"
    echo ""
    echo "📋 员工访问链接："
    echo "   http://${LAN_IP}:${PORT}/客户预警仪表盘.html"
fi
echo ""

# 4. 检查默认网关
echo "🚪 默认网关："
netstat -rn | grep default | head -n 1
echo ""

# 5. 检查端口是否被占用
echo "🔌 端口 ${PORT} 状态："
if lsof -i :"${PORT}" >/dev/null 2>&1; then
    echo "   ⚠️  端口已被占用"
    lsof -i :"${PORT}"
else
    echo "   ✅ 端口空闲，可以启动服务"
fi
echo ""

# 6. 测试局域网连通性
if [ -n "$LAN_IP" ]; then
    echo "🔗 测试本机连通性："
    if curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://127.0.0.1:${PORT}" 2>/dev/null | grep -q "200\|000"; then
        if lsof -i :"${PORT}" >/dev/null 2>&1; then
            echo "   ✅ 服务正在运行且可访问"
        else
            echo "   ⚠️  服务未运行，请先启动 start_dashboard_server.command"
        fi
    else
        echo "   ⚠️  服务未运行"
    fi
fi

echo ""
echo "========================================"
echo "💡 诊断结果总结："
echo "========================================"

if [ $VPN_FOUND -eq 1 ]; then
    echo "⚠️  检测到 VPN 连接"
    echo ""
    echo "建议操作："
    echo "1. 【推荐】提供服务时临时关闭 VPN"
    echo "2. 或配置 VPN 排除局域网流量（192.168.0.0/16）"
    echo "3. 或使用电脑名称替代 IP："
    echo "   http://$(hostname | sed 's/.local//').local:${PORT}/客户预警仪表盘.html"
else
    if [ -n "$LAN_IP" ]; then
        echo "✅ 网络配置正常，可以正常提供服务"
        echo ""
        echo "📋 复制以下链接给员工："
        echo "   http://${LAN_IP}:${PORT}/客户预警仪表盘.html"
    else
        echo "❌ 无法获取局域网 IP，请检查网络连接"
    fi
fi

echo ""
echo "按任意键退出..."
read -n 1
