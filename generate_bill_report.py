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
from datetime import datetime, timezone, timedelta
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
            update_time = datetime.fromtimestamp(result[0], timezone.utc)
            return update_time.strftime('%Y-%m-%d %H:%M UTC')
        return "未知"
    except sqlite3.Error as e:
        print(f"获取更新时间错误: {e}")
        return "未知"

def get_annual_data(conn, year):
    """获取指定年份的月度汇总数据"""
    year_str = str(year)
    date_pattern = f"{year_str}-%"
    
    query = """
    SELECT 
        SUBSTR(TIME, 1, 7) as month,
        SUM(AMOUNT) as total_amount,
        COUNT(*) as transaction_count,
        MAX(UPDATE_TIME) as latest_update
    FROM BILL 
    WHERE TIME LIKE ? AND TYPE = '消费'
    GROUP BY SUBSTR(TIME, 1, 7)
    ORDER BY month ASC
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (date_pattern,))
        data = cursor.fetchall()
        return data
    except sqlite3.Error as e:
        print(f"查询年度数据错误: {e}")
        return []

def get_annual_latest_update_time(conn, year):
    """获取指定年份数据的最新更新时间"""
    year_str = str(year)
    date_pattern = f"{year_str}-%"
    
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
            update_time = datetime.fromtimestamp(result[0], timezone.utc)
            return update_time.strftime('%Y-%m-%d %H:%M UTC')
        return "未知"
    except sqlite3.Error as e:
        print(f"获取年度更新时间错误: {e}")
        return "未知"

def get_all_years_data(conn):
    """获取所有年份的消费数据汇总"""
    query = """
    SELECT 
        SUBSTR(TIME, 1, 4) as year,
        SUM(AMOUNT) as total_amount,
        COUNT(*) as transaction_count,
        MAX(UPDATE_TIME) as latest_update
    FROM BILL 
    WHERE TYPE = '消费'
    GROUP BY SUBSTR(TIME, 1, 4)
    ORDER BY year DESC
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        return data
    except sqlite3.Error as e:
        print(f"查询所有年份数据错误: {e}")
        return []

def get_recent_3_months_data(conn):
    """获取最近3个月的消费数据汇总"""
    # 先获取数据库中最新一条数据的时间
    latest_time_query = """
    SELECT MAX(TIME) 
    FROM BILL 
    WHERE TYPE = '消费'
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(latest_time_query)
        result = cursor.fetchone()
        
        if not result or not result[0]:
            print("未找到任何消费数据")
            return []
        
        # 解析最新数据的时间
        latest_time_str = result[0]
        latest_time = datetime.strptime(latest_time_str, '%Y-%m-%d %H:%M:%S')
        latest_year = latest_time.year
        latest_month = latest_time.month
        
        print(f"数据库中最新的消费数据时间: {latest_year}年{latest_month}月")
        
    except sqlite3.Error as e:
        print(f"查询最新数据时间错误: {e}")
        return []
    except ValueError as e:
        print(f"解析时间格式错误: {e}")
        return []
    
    # 从最新数据所在的月份开始往前取3个月
    months = []
    for i in range(3):
        target_year = latest_year
        target_month = latest_month - i
        
        # 处理跨年情况
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        months.append((target_year, target_month))
    
    # 按时间倒序排列
    months.sort(reverse=True)
    
    monthly_data = []
    for year, month in months:
        year_str = str(year)
        month_str = f"{month:02d}"
        date_pattern = f"{year_str}-{month_str}-%"
        
        query = """
        SELECT 
            SUM(AMOUNT) as total_amount,
            COUNT(*) as transaction_count,
            MAX(UPDATE_TIME) as latest_update
        FROM BILL 
        WHERE TIME LIKE ? AND TYPE = '消费'
        """
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, (date_pattern,))
            result = cursor.fetchone()
            if result and result[0] is not None:
                # 有数据的情况
                monthly_data.append((year, month, float(result[0]), result[1], result[2]))
            else:
                # 没有数据的情况，显示为0
                monthly_data.append((year, month, 0.0, 0, None))
        except sqlite3.Error as e:
            print(f"查询{year}年{month}月数据错误: {e}")
            # 即使查询出错，也添加一个0金额的条目
            monthly_data.append((year, month, 0.0, 0, None))
    
    return monthly_data

def get_summary_latest_update_time(conn):
    """获取汇总数据的最新更新时间"""
    query = """
    SELECT MAX(UPDATE_TIME) 
    FROM BILL 
    WHERE TYPE = '消费'
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        if result and result[0]:
            # 将Unix时间戳转换为可读格式
            update_time = datetime.fromtimestamp(result[0], timezone.utc)
            return update_time.strftime('%Y-%m-%d %H:%M UTC')
        return "未知"
    except sqlite3.Error as e:
        print(f"获取汇总更新时间错误: {e}")
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

def generate_annual_html(monthly_data, total_amount, update_time, year):
    """生成年度账单HTML页面"""
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{year}年度账单</title>
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
        .monthly-list {{
            margin-top: 20px;
        }}
        .monthly-item {{
            display: block;
            padding: 20px 0;
            border-bottom: 1px solid #eee;
            position: relative;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
        }}
        .monthly-item:last-child {{
            border-bottom: none;
        }}
        .monthly-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .month-label {{
            font-size: 1.1em;
            font-weight: 500;
            color: #333;
        }}
        .month-amount {{
            font-size: 1.1em;
            font-weight: 500;
            color: #333;
        }}
        .progress-bar-container {{
            width: 100%;
            height: 12px;
            background-color: #f0f0f0;
            border-radius: 6px;
            overflow: hidden;
            position: relative;
        }}
        .progress-bar {{
            height: 100%;
            background-color: #007bff;
            border-radius: 6px;
            transition: width 0.3s ease;
        }}
    </style>
    <script>
        function sortMonthlyData() {{
            const select = document.getElementById('sortSelect');
            const monthlyList = document.querySelector('.monthly-list');
            const monthlyItems = Array.from(monthlyList.querySelectorAll('.monthly-item'));
            
            if (select.value === 'amount') {{
                // 按金额降序排序
                monthlyItems.sort((a, b) => {{
                    const amountA = parseFloat(a.querySelector('.month-amount').textContent.replace('¥', ''));
                    const amountB = parseFloat(b.querySelector('.month-amount').textContent.replace('¥', ''));
                    return amountB - amountA;
                }});
            }} else {{
                // 按时间排序（原始顺序）
                monthlyItems.sort((a, b) => {{
                    const monthA = a.querySelector('.month-label').textContent;
                    const monthB = b.querySelector('.month-label').textContent;
                    return monthA.localeCompare(monthB);
                }});
            }}
            
            // 重新排列DOM元素
            monthlyItems.forEach(item => monthlyList.appendChild(item));
        }}
        
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="update-time">数据更新时间<br>{update_time}</div>
            <div class="sort-control">
                <select class="sort-select" id="sortSelect" onchange="sortMonthlyData()">
                    <option value="time">按时间排序</option>
                    <option value="amount">按金额排序</option>
                </select>
            </div>
            <h1>{year}年度账单</h1>
            <div class="total-amount">{format_amount(total_amount)}</div>
        </div>
        
        <div class="monthly-list">"""

    # 计算最大金额用于进度条比例
    max_amount = max([float(row[1]) for row in monthly_data]) if monthly_data else 1
    
    # 添加月度数据
    for row in monthly_data:
        month_str = row[0]  # 格式: YYYY-MM
        amount = float(row[1])
        transaction_count = row[2]
        
        # 提取月份数字
        month_num = int(month_str.split('-')[1])
        month_display = f"{month_num:02d}月"
        
        # 计算进度条宽度百分比
        progress_width = (amount / max_amount) * 100 if max_amount > 0 else 0
        
        # 生成月度账单文件名
        month_filename = f"bill_{year}_{month_num:02d}.html"
        
        html_content += f"""
            <a href="{month_filename}" class="monthly-item">
                <div class="monthly-header">
                    <div class="month-label">{month_display}</div>
                    <div class="month-amount">{format_amount(amount)}</div>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {progress_width:.1f}%"></div>
                </div>
            </a>"""

    html_content += """
        </div>
    </div>
</body>
</html>"""
    
    return html_content

def generate_summary_html(recent_months_data, all_years_data, update_time):
    """生成历史账单汇总HTML页面"""
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>历史账单汇总</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: white;
            color: #333;
        }}
        .container {{
            max-width: 1000px;
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
            font-size: 1.8em;
            font-weight: 500;
            color: #333;
        }}
        .update-time {{
            position: absolute;
            top: 20px;
            right: 0;
            font-size: 0.9em;
            color: #666;
            text-align: right;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section-title {{
            font-size: 1.2em;
            font-weight: 500;
            color: #333;
            margin-bottom: 20px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-item {{
            background-color: #e3f2fd;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            text-decoration: none;
            color: inherit;
            transition: background-color 0.3s ease;
        }}
        .summary-item:hover {{
            background-color: #bbdefb;
        }}
        .summary-period {{
            font-size: 1em;
            font-weight: 500;
            color: #333;
            margin-bottom: 10px;
        }}
        .summary-amount {{
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }}
        .years-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        .year-item {{
            background-color: #e3f2fd;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            text-decoration: none;
            color: inherit;
            transition: background-color 0.3s ease;
        }}
        .year-item:hover {{
            background-color: #bbdefb;
        }}
        .year-period {{
            font-size: 0.9em;
            font-weight: 500;
            color: #333;
            margin-bottom: 8px;
        }}
        .year-amount {{
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="update-time">数据更新时间<br>{update_time}</div>
            <h1>历史账单汇总</h1>
        </div>
        
        <div class="section">
            <div class="section-title">最近3个月消费汇总</div>
            <div class="summary-grid">"""

    # 添加最近3个月数据
    for year, month, amount, transaction_count, latest_update in recent_months_data:
        month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月", 
                       "七月", "八月", "九月", "十月", "十一月", "十二月"]
        month_name = month_names[month]
        
        # 生成月度账单文件名
        month_filename = f"bill_{year}_{month:02d}.html"
        
        html_content += f"""
                <a href="{month_filename}" class="summary-item">
                    <div class="summary-period">{year}年{month:02d}月</div>
                    <div class="summary-amount">{format_amount(amount)}</div>
                </a>"""

    html_content += """
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">各年份消费汇总</div>
            <div class="years-grid">"""

    # 添加所有年份数据
    for row in all_years_data:
        year = row[0]
        amount = float(row[1])
        transaction_count = row[2]
        
        # 生成年度账单文件名
        year_filename = f"bill_{year}_annual.html"
        
        html_content += f"""
                <a href="{year_filename}" class="year-item">
                    <div class="year-period">{year}年</div>
                    <div class="year-amount">{format_amount(amount)}</div>
                </a>"""

    html_content += """
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return html_content

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='生成账单明细HTML页面')
    parser.add_argument('year', type=int, nargs='?', help='年份 (例如: 2025)，不指定则生成汇总页面')
    parser.add_argument('--month', type=int, help='月份 (1-12)，不指定则生成年度账单')
    parser.add_argument('--summary', action='store_true', help='生成历史账单汇总页面')
    parser.add_argument('--db', default='billing.sqlite', help='数据库文件路径 (默认: billing.sqlite)')
    
    args = parser.parse_args()
    
    # 验证月份范围（如果指定了月份）
    if args.month is not None and not (1 <= args.month <= 12):
        print("错误: 月份必须在1-12之间")
        sys.exit(1)
    
    # 如果没有指定年份且没有指定summary，则默认为summary
    if args.year is None and not args.summary:
        args.summary = True
    
    return args

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    year = args.year
    month = args.month
    summary = args.summary
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
        # 确保web目录存在
        web_dir = "web"
        if not os.path.exists(web_dir):
            os.makedirs(web_dir)
        
        if summary:
            # 生成历史账单汇总页面
            print("正在生成历史账单汇总页面...")
            
            # 获取最近3个月数据
            recent_months_data = get_recent_3_months_data(conn)
            print(f"找到 {len(recent_months_data)} 个月的数据")
            
            # 获取所有年份数据
            all_years_data = get_all_years_data(conn)
            print(f"找到 {len(all_years_data)} 年的数据")
            
            if not recent_months_data and not all_years_data:
                print("未找到任何消费数据")
                return
            
            # 获取最新更新时间
            update_time = get_summary_latest_update_time(conn)
            print(f"数据更新时间: {update_time}")
            
            # 生成HTML
            print("正在生成汇总HTML页面...")
            html_content = generate_summary_html(recent_months_data, all_years_data, update_time)
            
            # 保存HTML文件
            output_file = os.path.join(web_dir, "bill_summary.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"汇总HTML页面已生成: {output_file}")
            
        elif month is not None:
            # 生成月度账单
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
            
            # 保存HTML文件，命名规则为 bill_yyyy_MM.html
            output_file = os.path.join(web_dir, f"bill_{year}_{month:02d}.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"HTML页面已生成: {output_file}")
            
        else:
            # 生成年度账单
            print(f"正在提取{year}年度消费数据...")
            monthly_data = get_annual_data(conn, year)
            
            if not monthly_data:
                print(f"未找到{year}年的消费数据")
                return
            
            print(f"找到 {len(monthly_data)} 个月的数据")
            
            # 计算总金额
            total_amount = sum([float(row[1]) for row in monthly_data])
            print(f"总金额: {format_amount(total_amount)}")
            
            # 获取最新更新时间
            update_time = get_annual_latest_update_time(conn, year)
            print(f"数据更新时间: {update_time}")
            
            # 生成HTML
            print("正在生成年度HTML页面...")
            html_content = generate_annual_html(monthly_data, total_amount, update_time, year)
            
            # 保存HTML文件，命名规则为 bill_yyyy_annual.html
            output_file = os.path.join(web_dir, f"bill_{year}_annual.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"年度HTML页面已生成: {output_file}")
        
        print("生成完成！")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
