#!/bin/bash

echo "========================================="
echo "OKX 支付监控系统 - 启动脚本"
echo "========================================="

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo "✗ 配置文件不存在！"
    echo ""
    echo "请先创建配置文件："
    echo "  cp config.json.example config.json"
    echo "  nano config.json"
    echo ""
    exit 1
fi

echo "✓ 配置文件存在"

# 停止旧服务
echo ""
echo "正在停止旧服务..."
pkill -f payment_monitor.py 2>/dev/null
pkill -f okx_monitor.py 2>/dev/null
pkill -f query_api.py 2>/dev/null
sleep 2
echo "✓ 旧服务已停止"

# 启动监控服务
echo ""
echo "启动 OKX 监控服务..."
nohup python3 okx_monitor.py > monitor.log 2>&1 &
MONITOR_PID=$!
echo "✓ 监控服务已启动 (PID: $MONITOR_PID)"

# 等待1秒
sleep 1

# 启动查询API
echo "启动查询API服务..."
nohup python3 query_api.py > query_api.log 2>&1 &
API_PID=$!
echo "✓ 查询API已启动 (PID: $API_PID)"

# 等待2秒让服务启动
sleep 2

# 检查进程状态
echo ""
echo "========================================="
echo "服务状态检查"
echo "========================================="

if ps -p $MONITOR_PID > /dev/null 2>&1; then
    echo "✓ 监控服务运行中 (PID: $MONITOR_PID)"
else
    echo "✗ 监控服务启动失败！请查看 monitor.log"
fi

if ps -p $API_PID > /dev/null 2>&1; then
    echo "✓ 查询API运行中 (PID: $API_PID)"
else
    echo "✗ 查询API启动失败！请查看 query_api.log"
fi

# 显示所有相关进程
echo ""
echo "========================================="
echo "当前运行的Python进程"
echo "========================================="
ps aux | grep -E "okx_monitor|query_api" | grep -v grep

echo ""
echo "========================================="
echo "日志文件"
echo "========================================="
echo "监控日志: monitor.log"
echo "API日志: query_api.log"
echo ""
echo "查看实时日志："
echo "  tail -f monitor.log"
echo "  tail -f query_api.log"
echo ""
echo "========================================="
echo "API地址"
echo "========================================="
echo "查询接口: http://你的服务器IP:6000/api/query"
echo "检查接口: http://你的服务器IP:6000/api/check"
echo "健康检查: http://你的服务器IP:6000/health"
echo ""
echo "========================================="
echo "启动完成！"
echo "========================================="
