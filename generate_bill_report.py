#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单明细生成器
从SQLite数据库中提取指定月份的消费数据，生成静态HTML页面
"""

import sqlite3
import os
import sys
import argparse
from datetime import datetime
from decimal import Decimal

def connect_database(db_path):
    """连接数据库"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        return None

def get_monthly_data(conn, year, month):
    """获取指定年月的消费数据"""
    # 格式化年月为字符串，确保月份是两位数
    year_str = str(year)
    month_str = f"{month:02d}"
    date_pattern = f"{year_str}-{month_str}-%"
    
    query = """
    SELECT TIME, AMOUNT, INFO, NOTE, SOURCE, UPDATE_TIME
    FROM BILL 
    WHERE TIME LIKE ? AND TYPE = '消费'
    ORDER BY TIME ASC
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (date_pattern,))
        data = cursor.fetchall()
        return data
    except sqlite3.Error as e:
        print(f"查询数据错误: {e}")
        return []

def get_latest_update_time(conn, year, month):
    """获取指定年月数据的最新更新时间"""
    # 格式化年月为字符串，确保月份是两位数
    year_str = str(year)
    month_str = f"{month:02d}"
    date_pattern = f"{year_str}-{month_str}-%"
    
    query = """
    SELECT MAX(UPDATE_TIME) 
    FROM BILL 
    WHERE TIME LIKE ? AND TYPE = '消费'
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (date_pattern,))
        result = cursor.fetchone()
        if result and result[0]:
            # 将Unix时间戳转换为可读格式
            update_time = datetime.fromtimestamp(result[0])
            return update_time.strftime('%Y-%m-%d %H:%M:%S')
        return "未知"
    except sqlite3.Error as e:
        print(f"获取更新时间错误: {e}")
        return "未知"

def calculate_total_amount(data):
    """计算总金额"""
    total = Decimal('0')
    for row in data:
        total += Decimal(str(row[1]))
    return total

def format_amount(amount):
    """格式化金额显示"""
    return f"¥{amount:.2f}"

def generate_html(data, total_amount, update_time, year, month):
    """生成HTML页面"""
    month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月", 
                   "七月", "八月", "九月", "十月", "十一月", "十二月"]
    month_name = month_names[month]
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{year}年{month_name}账单</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: white;
            color: #333;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
        }}
        .header {{
            padding: 20px 0;
            border-bottom: 1px solid #eee;
            position: relative;
        }}
        .header h1 {{
            margin: 0 0 20px 0;
            font-size: 1.4em;
            font-weight: 500;
            color: #333;
        }}
        .total-amount {{
            font-size: 3em;
            font-weight: bold;
            color: #333;
            margin: 20px 0;
        }}
        .update-time {{
            position: absolute;
            top: 20px;
            right: 0;
            font-size: 0.9em;
            color: #666;
            text-align: right;
        }}
        .sort-control {{
            position: absolute;
            top: 85px;
            right: 0;
            z-index: 10;
        }}
        .sort-select {{
            padding: 8px 12px;
            border: 1px solid #333;
            background: white;
            font-size: 0.9em;
            cursor: pointer;
        }}
        .transaction-list {{
            margin-top: 20px;
        }}
        .transaction-item {{
            padding: 15px 0 15px 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            position: relative;
        }}
        .transaction-decoration {{
            position: absolute;
            left: 0;
            top: 20px;
            bottom: 20px;
            width: 4px;
            border-radius: 2px;
            background-color: #6c757d;
        }}
        .transaction-decoration.cmbcc {{
            background-color: #dc3545;
        }}
        .transaction-decoration.alipay {{
            background-color: #007bff;
        }}
        .transaction-decoration.wechat {{
            background-color: #28a745;
        }}
        .transaction-item:last-child {{
            border-bottom: none;
        }}
        .transaction-left {{
            flex: 1;
            margin-right: 20px;
        }}
        .transaction-description {{
            font-size: 1em;
            color: #333;
            margin-bottom: 5px;
            line-height: 1.4;
        }}
        .transaction-meta {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.85em;
            color: #666;
        }}
        .transaction-note {{
            color: #666;
        }}
        .transaction-right {{
            text-align: right;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .transaction-amount {{
            font-size: 1em;
            font-weight: 500;
            color: #333;
            margin-bottom: 3px;
        }}
        .transaction-source {{
            font-size: 0.8em;
            color: #666;
        }}
    </style>
    <script>
        function sortTransactions() {{
            const select = document.getElementById('sortSelect');
            const transactionList = document.querySelector('.transaction-list');
            const transactions = Array.from(transactionList.querySelectorAll('.transaction-item'));
            
            if (select.value === 'amount') {{
                // 按金额降序排序
                transactions.sort((a, b) => {{
                    const amountA = parseFloat(a.querySelector('.transaction-amount').textContent.replace('¥', ''));
                    const amountB = parseFloat(b.querySelector('.transaction-amount').textContent.replace('¥', ''));
                    return amountB - amountA;
                }});
            }} else {{
                // 按时间排序（原始顺序）
                transactions.sort((a, b) => {{
                    const timeA = a.querySelector('.transaction-meta span').textContent;
                    const timeB = b.querySelector('.transaction-meta span').textContent;
                    return timeA.localeCompare(timeB);
                }});
            }}
            
            // 重新排列DOM元素
            transactions.forEach(transaction => transactionList.appendChild(transaction));
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="update-time">数据更新时间<br>{update_time}</div>
            <div class="sort-control">
                <select class="sort-select" id="sortSelect" onchange="sortTransactions()">
                    <option value="time">按时间排序</option>
                    <option value="amount">按金额排序</option>
                </select>
            </div>
            <h1>{year}年{month:02d}月账单</h1>
            <div class="total-amount">{format_amount(total_amount)}</div>
        </div>
        
        <div class="transaction-list">"""

    # 添加交易数据
    for row in data:
        time_str = row[0]
        amount = row[1]
        info = row[2] or ""
        note = row[3] or ""
        source = row[4] or ""
        
        # 格式化时间显示 (只显示月-日 时:分)
        try:
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            formatted_time = dt.strftime('%m-%d %H:%M')
        except:
            formatted_time = time_str
        
        # 格式化支付方式显示
        source_display = source.upper() if source else ""
        
        # 处理备注显示
        note_display = ""
        if note and note.strip() and note != '/':
            note_display = f'<span class="transaction-note">{note}</span>'
        
        # 确定装饰条颜色
        decoration_class = ""
        if source_display == "ALIPAY":
            decoration_class = "alipay"
        elif source_display == "WECHAT":
            decoration_class = "wechat"
        elif source_display == "CMBCC":
            decoration_class = "cmbcc"

        
        html_content += f"""
            <div class="transaction-item">
                <div class="transaction-decoration {decoration_class}"></div>
                <div class="transaction-left">
                    <div class="transaction-description">{info}</div>
                    <div class="transaction-meta">
                        <span>{formatted_time}</span>
                        {note_display}
                    </div>
                </div>
                <div class="transaction-right">
                    <div class="transaction-amount">{format_amount(amount)}</div>
                    <div class="transaction-source">{source_display}</div>
                </div>
            </div>"""

    html_content += """
        </div>
    </div>
</body>
</html>"""
    
    return html_content

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='生成指定月份的账单明细HTML页面')
    parser.add_argument('year', type=int, help='年份 (例如: 2025)')
    parser.add_argument('month', type=int, help='月份 (1-12)')
    parser.add_argument('--db', default='billing.sqlite', help='数据库文件路径 (默认: billing.sqlite)')
    
    args = parser.parse_args()
    
    # 验证月份范围
    if not (1 <= args.month <= 12):
        print("错误: 月份必须在1-12之间")
        sys.exit(1)
    
    return args

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    year = args.year
    month = args.month
    db_path = args.db
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件 {db_path} 不存在")
        return
    
    # 连接数据库
    conn = connect_database(db_path)
    if not conn:
        return
    
    try:
        # 获取指定年月数据
        print(f"正在提取{year}年{month}月消费数据...")
        data = get_monthly_data(conn, year, month)
        
        if not data:
            print(f"未找到{year}年{month}月的消费数据")
            return
        
        print(f"找到 {len(data)} 条消费记录")
        
        # 计算总金额
        total_amount = calculate_total_amount(data)
        print(f"总金额: {format_amount(total_amount)}")
        
        # 获取最新更新时间
        update_time = get_latest_update_time(conn, year, month)
        print(f"数据更新时间: {update_time}")
        
        # 生成HTML
        print("正在生成HTML页面...")
        html_content = generate_html(data, total_amount, update_time, year, month)
        
        # 确保web目录存在
        web_dir = "web"
        if not os.path.exists(web_dir):
            os.makedirs(web_dir)
        
        # 保存HTML文件，命名规则为 bill_yyyy_MM.html
        output_file = os.path.join(web_dir, f"bill_{year}_{month:02d}.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML页面已生成: {output_file}")
        print("生成完成！")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
