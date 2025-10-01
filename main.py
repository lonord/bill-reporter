#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单生成主程序
根据数据库和HTML文件的更新时间对比，自动生成需要更新的账单
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime, timezone
from generate_bill_report import (
    connect_database, 
    get_monthly_data, 
    get_annual_data, 
    get_all_years_data,
    get_recent_3_months_data,
    get_latest_update_time,
    get_annual_latest_update_time,
    get_summary_latest_update_time,
    generate_html,
    generate_annual_html,
    generate_summary_html,
    calculate_total_amount,
    format_amount
)

def get_database_update_times(conn):
    """获取数据库中所有年月和年份的最新更新时间"""
    monthly_times = {}
    annual_times = {}
    summary_time = None
    
    try:
        cursor = conn.cursor()
        
        # 获取所有年月的更新时间
        monthly_query = """
        SELECT 
            SUBSTR(TIME, 1, 4) as year,
            SUBSTR(TIME, 1, 7) as year_month,
            MAX(UPDATE_TIME) as latest_update
        FROM BILL 
        WHERE TYPE = '消费'
        GROUP BY SUBSTR(TIME, 1, 7)
        ORDER BY year_month
        """
        cursor.execute(monthly_query)
        monthly_results = cursor.fetchall()
        
        for year, year_month, update_time in monthly_results:
            if update_time:
                year_int = int(year)
                month_int = int(year_month.split('-')[1])
                monthly_times[(year_int, month_int)] = update_time
        
        # 获取所有年份的更新时间
        annual_query = """
        SELECT 
            SUBSTR(TIME, 1, 4) as year,
            MAX(UPDATE_TIME) as latest_update
        FROM BILL 
        WHERE TYPE = '消费'
        GROUP BY SUBSTR(TIME, 1, 4)
        ORDER BY year
        """
        cursor.execute(annual_query)
        annual_results = cursor.fetchall()
        
        for year, update_time in annual_results:
            if update_time:
                year_int = int(year)
                annual_times[year_int] = update_time
        
        # 获取汇总数据的更新时间
        summary_query = """
        SELECT MAX(UPDATE_TIME) 
        FROM BILL 
        WHERE TYPE = '消费'
        """
        cursor.execute(summary_query)
        summary_result = cursor.fetchone()
        if summary_result and summary_result[0]:
            summary_time = summary_result[0]
            
    except sqlite3.Error as e:
        print(f"查询数据库更新时间错误: {e}")
        return {}, {}, None
    
    return monthly_times, annual_times, summary_time

def get_html_file_modification_time(file_path):
    """获取HTML文件的修改时间（Unix时间戳）"""
    if not os.path.exists(file_path):
        return None
    
    try:
        mtime = os.path.getmtime(file_path)
        return mtime
    except OSError:
        return None

def needs_regeneration(db_time, html_time):
    """判断是否需要重新生成文件"""
    if db_time is None:
        return False
    if html_time is None:
        return True
    return db_time > html_time

def generate_monthly_bill(conn, year, month, output_dir):
    """生成月度账单"""
    print(f"正在生成 {year}年{month:02d}月账单...")
    
    # 获取月度数据
    data = get_monthly_data(conn, year, month)
    if not data:
        print(f"未找到{year}年{month:02d}月的消费数据")
        return False
    
    # 计算总金额
    total_amount = calculate_total_amount(data)
    print(f"总金额: {format_amount(total_amount)}")
    
    # 获取更新时间
    update_time = get_latest_update_time(conn, year, month)
    
    # 生成HTML
    html_content = generate_html(data, total_amount, update_time, year, month)
    
    # 保存文件
    output_file = os.path.join(output_dir, f"bill_{year}_{month:02d}.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"月度账单已生成: {output_file}")
    return True

def generate_annual_bill(conn, year, output_dir):
    """生成年度账单"""
    print(f"正在生成 {year}年度账单...")
    
    # 获取年度数据
    monthly_data = get_annual_data(conn, year)
    if not monthly_data:
        print(f"未找到{year}年的消费数据")
        return False
    
    # 计算总金额
    total_amount = sum([float(row[1]) for row in monthly_data])
    print(f"总金额: {format_amount(total_amount)}")
    
    # 获取更新时间
    update_time = get_annual_latest_update_time(conn, year)
    
    # 生成HTML
    html_content = generate_annual_html(monthly_data, total_amount, update_time, year)
    
    # 保存文件
    output_file = os.path.join(output_dir, f"bill_{year}_annual.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"年度账单已生成: {output_file}")
    return True

def generate_summary_bill(conn, output_dir):
    """生成汇总账单"""
    print("正在生成汇总账单...")
    
    # 获取最近3个月数据
    recent_months_data = get_recent_3_months_data(conn)
    print(f"找到 {len(recent_months_data)} 个月的数据")
    
    # 获取所有年份数据
    all_years_data = get_all_years_data(conn)
    print(f"找到 {len(all_years_data)} 年的数据")
    
    if not recent_months_data and not all_years_data:
        print("未找到任何消费数据")
        return False
    
    # 获取更新时间
    update_time = get_summary_latest_update_time(conn)
    
    # 生成HTML
    html_content = generate_summary_html(recent_months_data, all_years_data, update_time)
    
    # 保存文件
    output_file = os.path.join(output_dir, "bill_summary.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"汇总账单已生成: {output_file}")
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动生成需要更新的账单')
    parser.add_argument('--db', default='billing.sqlite', help='数据库文件路径 (默认: billing.sqlite)')
    parser.add_argument('--output', default='web', help='HTML账单输出目录 (默认: web)')
    
    args = parser.parse_args()
    
    db_path = args.db
    output_dir = args.output
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件 {db_path} 不存在")
        return 1
    
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 连接数据库
    conn = connect_database(db_path)
    if not conn:
        return 1
    
    try:
        # 获取数据库中的更新时间
        print("正在查询数据库更新时间...")
        monthly_times, annual_times, summary_time = get_database_update_times(conn)
        
        print(f"找到 {len(monthly_times)} 个月的数据")
        print(f"找到 {len(annual_times)} 年的数据")
        
        generated_count = 0
        skipped_monthly = 0
        skipped_annual = 0
        skipped_summary = 0
        
        # 1. 处理月度账单
        print("\n=== 检查月度账单 ===")
        for (year, month), db_time in monthly_times.items():
            html_file = os.path.join(output_dir, f"bill_{year}_{month:02d}.html")
            html_time = get_html_file_modification_time(html_file)
            
            if needs_regeneration(db_time, html_time):
                print(f"{year}年{month:02d}月需要重新生成 (数据库: {datetime.fromtimestamp(db_time, timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}, HTML: {datetime.fromtimestamp(html_time, timezone.utc).strftime('%Y-%m-%d %H:%M UTC') if html_time else '不存在'})")
                if generate_monthly_bill(conn, year, month, output_dir):
                    generated_count += 1
            else:
                skipped_monthly += 1
        
        if skipped_monthly > 0:
            print(f"跳过 {skipped_monthly} 个月度账单（无需更新）")
        
        # 2. 处理年度账单
        print("\n=== 检查年度账单 ===")
        for year, db_time in annual_times.items():
            html_file = os.path.join(output_dir, f"bill_{year}_annual.html")
            html_time = get_html_file_modification_time(html_file)
            
            if needs_regeneration(db_time, html_time):
                print(f"{year}年需要重新生成 (数据库: {datetime.fromtimestamp(db_time, timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}, HTML: {datetime.fromtimestamp(html_time, timezone.utc).strftime('%Y-%m-%d %H:%M UTC') if html_time else '不存在'})")
                if generate_annual_bill(conn, year, output_dir):
                    generated_count += 1
            else:
                skipped_annual += 1
        
        if skipped_annual > 0:
            print(f"跳过 {skipped_annual} 个年度账单（无需更新）")
        
        # 3. 处理汇总账单
        print("\n=== 检查汇总账单 ===")
        if summary_time:
            html_file = os.path.join(output_dir, "bill_summary.html")
            html_time = get_html_file_modification_time(html_file)
            
            if needs_regeneration(summary_time, html_time):
                print(f"汇总账单需要重新生成 (数据库: {datetime.fromtimestamp(summary_time, timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}, HTML: {datetime.fromtimestamp(html_time, timezone.utc).strftime('%Y-%m-%d %H:%M UTC') if html_time else '不存在'})")
                if generate_summary_bill(conn, output_dir):
                    generated_count += 1
            else:
                skipped_summary = 1
        
        if skipped_summary > 0:
            print("跳过汇总账单（无需更新）")
        
        print(f"\n=== 完成 ===")
        print(f"共生成了 {generated_count} 个账单文件")
        
        return 0
        
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
