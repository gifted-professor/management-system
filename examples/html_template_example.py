#!/usr/bin/env python3
"""
HTML 模板化系统 - 使用示例

演示如何使用新的 Jinja2 模板系统生成仪表盘 HTML
"""
from datetime import date
from pathlib import Path

# 导入 HTML 生成器
from tech.html_generator import render_dashboard


def example_basic():
    """示例 1: 基础用法"""
    print("=" * 50)
    print("示例 1: 基础 HTML 渲染")
    print("=" * 50)

    html = render_dashboard(
        today=date.today(),
        action_rows=[],
        filters_html='<div class="filters">筛选器示例</div>',
        header_cells='<th>测试表头</th>',
        table_rows='<tr><td>测试行</td></tr>',
        sku_push_html='<div class="card"><h3>加推SKU示例</h3></div>',
        sku_return_html='<div class="card"><h3>高退货预警示例</h3></div>',
        low_margin_html='<div class="card"><h3>低毛利预警示例</h3></div>',
    )

    # 保存到临时文件
    output = Path('test_dashboard.html')
    output.write_text(html, encoding='utf-8')

    print(f"✅ HTML 已生成: {output}")
    print(f"   文件大小: {len(html):,} 字符")
    print(f"   包含 <html>: {'<html' in html}")
    print(f"   包含仪表盘: {'仪表盘' in html}")


def example_with_data():
    """示例 2: 带数据的完整示例"""
    print("\n" + "=" * 50)
    print("示例 2: 带数据的完整渲染")
    print("=" * 50)

    # 模拟客户数据
    action_rows = [
        {
            'priority_score': 95,
            'name': '张三',
            'phone': '13800138000',
            'platform': '微信',
            'customer_value': '高价值',
        },
        {
            'priority_score': 65,
            'name': '李四',
            'phone': '13900139000',
            'platform': '小红书',
            'customer_value': '中价值',
        },
        {
            'priority_score': 45,
            'name': '王五',
            'phone': '13700137000',
            'platform': '抖音',
            'customer_value': '低价值',
        },
    ]

    # 模拟筛选器 HTML
    filters_html = """
    <div class="filters">
        <label>关键词搜索：<input id="searchBox" type="search" placeholder="搜索客户..."></label>
        <select id="priorityFilter">
            <option value="">全部优先级</option>
            <option value="高(≥80)">高(≥80)</option>
            <option value="中(50-79)">中(50-79)</option>
        </select>
    </div>
    """

    # 模拟表头
    header_cells = """
    <th>标记完成</th>
    <th data-sort-method='number'>优先分</th>
    <th>姓名</th>
    <th>主要平台</th>
    <th>手机号</th>
    <th>价值层级</th>
    """

    # 模拟表格行
    table_rows = """
    <tr class="priority-high" data-key="13800138000" data-phone="13800138000" data-name="张三">
        <td><input type="checkbox" class="followup-checkbox"></td>
        <td data-sort-value="95">95</td>
        <td>张三</td>
        <td>微信</td>
        <td>13800138000</td>
        <td>高价值</td>
    </tr>
    <tr class="priority-mid" data-key="13900139000" data-phone="13900139000" data-name="李四">
        <td><input type="checkbox" class="followup-checkbox"></td>
        <td data-sort-value="65">65</td>
        <td>李四</td>
        <td>小红书</td>
        <td>13900139000</td>
        <td>中价值</td>
    </tr>
    """

    html = render_dashboard(
        today=date.today(),
        action_rows=action_rows,
        filters_html=filters_html,
        header_cells=header_cells,
        table_rows=table_rows,
        sku_push_html='<div class="card"><h3>加推SKU</h3><p>暂无数据</p></div>',
        sku_return_html='<div class="card"><h3>高退货预警</h3><p>暂无数据</p></div>',
        low_margin_html='<div class="card"><h3>低毛利预警</h3><p>暂无数据</p></div>',
        tags=['高价值流失', '长期未复购', '短期未复购'],
        platforms=['微信', '小红书', '抖音'],
        cooldown_days=7,
        cooldown_total=23,
    )

    # 保存到文件
    output = Path('test_dashboard_with_data.html')
    output.write_text(html, encoding='utf-8')

    print(f"✅ HTML 已生成: {output}")
    print(f"   客户数: {len(action_rows)}")
    print(f"   文件大小: {len(html):,} 字符")
    print(f"   标签: {3}")
    print(f"   平台: {3}")


def example_integration():
    """示例 3: 在现有代码中集成"""
    print("\n" + "=" * 50)
    print("示例 3: 集成到现有代码")
    print("=" * 50)

    print("""
在 generate_customer_alerts.py 中使用：

# 原有代码（简化版）
def write_html_dashboard(output_path, today, action_rows, ...):
    # 原来：内嵌 4000+ 行 HTML
    # html_template = f'''<!DOCTYPE html>...'''

    # 现在：使用模板系统
    from tech.html_generator import render_dashboard

    html = render_dashboard(
        today=today,
        action_rows=action_rows,
        filters_html=filters_html,
        header_cells=header_cells,
        table_rows=table_rows,
        sku_push_html=sku_push_html,
        sku_return_html=sku_return_html,
        low_margin_html=low_margin_html,
        # ... 其他参数
    )

    output_path.write_text(html, encoding='utf-8')

优势：
  ✅ 减少主文件 ~800 行代码
  ✅ HTML/CSS 独立管理
  ✅ 易于维护和扩展
    """)


if __name__ == '__main__':
    # 运行所有示例
    example_basic()
    example_with_data()
    example_integration()

    print("\n" + "=" * 50)
    print("✅ 所有示例运行完成！")
    print("=" * 50)
    print("\n生成的文件:")
    print("  - test_dashboard.html (基础示例)")
    print("  - test_dashboard_with_data.html (完整示例)")
    print("\n请在浏览器中打开查看效果。")
