#!/bin/bash

echo "========================================="
echo "OKX 支付监控系统 - 停止脚本"
echo "========================================="

# 停止监控服务
if pgrep -f "okx_monitor.py" > /dev/null; then
    echo "正在停止监控服务..."
    pkill -f okx_monitor.py
    sleep 1

    if pgrep -f "okx_monitor.py" > /dev/null; then
        echo "⚠️  进程未停止，强制终止..."
        pkill -9 -f okx_monitor.py
    fi
    echo "✓ 监控服务已停止"
else
    echo "ℹ️  监控服务未运行"
fi

# 停止查询API
if pgrep -f "query_api.py" > /dev/null; then
    echo "正在停止查询API..."
    pkill -f query_api.py
    sleep 1

    if pgrep -f "query_api.py" > /dev/null; then
        echo "⚠️  进程未停止，强制终止..."
        pkill -9 -f query_api.py
    fi
    echo "✓ 查询API已停止"
else
    echo "ℹ️  查询API未运行"
fi

# 停止旧版服务（如果还在运行）
if pgrep -f "payment_monitor.py" > /dev/null; then
    echo "正在停止旧版监控服务..."
    pkill -f payment_monitor.py
    echo "✓ 旧版服务已停止"
fi

echo ""
echo "========================================="
echo "检查剩余进程"
echo "========================================="

REMAINING=$(ps aux | grep -E "okx_monitor|query_api|payment_monitor" | grep -v grep)

if [ -z "$REMAINING" ]; then
    echo "✓ 所有服务已停止"
else
    echo "以下进程仍在运行:"
    echo "$REMAINING"
fi

echo ""
echo "========================================="
echo "停止完成！"
echo "========================================="
