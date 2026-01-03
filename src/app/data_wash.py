import json
import pandas as pd
import os
import re
from typing import List, Dict, Union
from datetime import datetime
import argparse
import io
import requests
import time

api_key='8d8887938848e63233b090f373ad959b'#高德地图的API密钥

def read_json_data(file_path: str) -> pd.DataFrame:
    """
    读取JSON文件并转换为DataFrame

    参数:
        file_path: JSON文件路径
    
    返回:
        pd.DataFrame: 包含职位数据的DataFrame
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    return df


def read_latest_json(data_dir: str = '../data') -> pd.DataFrame:
    """
    读取data目录下最新的JSON文件
    
    参数:
        data_dir: 数据目录路径，默认为'../data'
    
    返回:
        pd.DataFrame: 包含职位数据的DataFrame
    """
    # 获取所有JSON文件
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    
    if not json_files:
        raise FileNotFoundError(f"在 {data_dir} 目录下没有找到JSON文件")
    
    # 按修改时间排序，获取最新的文件
    latest_file = max(json_files, key=lambda f: os.path.getmtime(os.path.join(data_dir, f)))
    
    file_path = os.path.join(data_dir, latest_file)
    print(f"读取文件: {latest_file}")
    
    return read_json_data(file_path)


def read_all_json_files(data_dir: str = 'data') -> pd.DataFrame:
    """
    读取data目录下所有JSON文件并合并
    
    参数:
        data_dir: 数据目录路径，默认为'data'
    
    返回:
        pd.DataFrame: 合并后的DataFrame
    """
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    
    if not json_files:
        raise FileNotFoundError(f"在 {data_dir} 目录下没有找到JSON文件")
    
    all_data = []
    for file in json_files:
        file_path = os.path.join(data_dir, file)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_data.extend(data)
    
    df = pd.DataFrame(all_data)
    print(f"共读取 {len(json_files)} 个文件，合计 {len(df)} 条数据")
    
    return df


def clean_salary(salary_str):
    """
    清洗薪资数据，统一转换为k/月
    
    支持的格式：
    - 4-6千
    - 1.2-2万
    - 8千-1.6万
    - 10-15万/年
    - 8千-1.6万·14薪
    - 15k-20k
    - 50/天
    - 200-300/天
    - 面议
    """
    if pd.isna(salary_str) or not salary_str:
        return {'min_salary': None, 'max_salary': None, 'avg_salary': None}
    
    salary_str = str(salary_str).strip()
    
    # 处理特殊情况：面议、待遇优厚等
    if any(keyword in salary_str for keyword in ['面议', '待遇', '薪资面议', '面谈', '协商']):
        return {'min_salary': None, 'max_salary': None, 'avg_salary': None}
    
    # 单位转换辅助函数
    def convert_to_k_per_month(val, unit, is_yearly=False, is_daily=False, num_months=12):
        """
        将薪资统一转换为k/月
        
        参数:
            val: 数值
            unit: 单位（千/万/k/K）
            is_yearly: 是否为年薪
            is_daily: 是否为日薪
            num_months: 月数（如14薪就是14）
        """
        val = float(val)
        
        # 如果是日薪，先转为月薪（按22个工作日计算）
        if is_daily:
            # 日薪默认单位是元，需要转为千
            val_k = (val * 22) / 1000
        else:
            # 先转换单位到k
            if unit in ['万', 'W', 'w']:
                val_k = val * 10
            else:  # 千, k, K
                val_k = val
            
            # 如果是年薪，除以12转为月薪
            if is_yearly:
                val_k = val_k / 12
            # 如果有多薪制，除以月数
            elif num_months > 12:
                val_k = val_k * 12 / num_months
        
        return val_k
    
    # ===== 优先检测日薪格式 =====
    # 模式: 日薪 - "50/天" "200-300/天" "150元/天"
    is_daily = bool(re.search(r'/天|每天|日薪|/日', salary_str))
    
    if is_daily:
        # 移除干扰字符
        salary_core = re.sub(r'/天|每天|日薪|/日|元', '', salary_str).strip()
        
        # 日薪区间: "200-300"
        pattern_daily_range = r'([\d.]+)\s*[-~至]\s*([\d.]+)'
        match_daily_range = re.search(pattern_daily_range, salary_core)
        
        if match_daily_range:
            min_val = match_daily_range.group(1)
            max_val = match_daily_range.group(2)
            
            min_salary = convert_to_k_per_month(min_val, None, is_daily=True)
            max_salary = convert_to_k_per_month(max_val, None, is_daily=True)
            avg_salary = (min_salary + max_salary) / 2
            
            return {
                'min_salary': round(min_salary, 1),
                'max_salary': round(max_salary, 1),
                'avg_salary': round(avg_salary, 1)
            }
        
        # 单一日薪: "150"
        pattern_daily_single = r'([\d.]+)'
        match_daily_single = re.search(pattern_daily_single, salary_core)
        
        if match_daily_single:
            val = match_daily_single.group(1)
            salary = convert_to_k_per_month(val, None, is_daily=True)
            
            return {
                'min_salary': round(salary, 1),
                'max_salary': round(salary, 1),
                'avg_salary': round(salary, 1)
            }
    
    # 检测是否为年薪
    is_yearly = bool(re.search(r'/年|每年|年薪', salary_str))
    
    # 提取薪资月数（如14薪、13薪）
    months_match = re.search(r'[·\*×xX]?\s*(\d+)\s*薪', salary_str)
    num_months = int(months_match.group(1)) if months_match else 12
    
    # 移除干扰字符，保留核心薪资部分
    salary_core = re.sub(r'[·\*×xX]\s*\d+\s*薪', '', salary_str)
    salary_core = re.sub(r'/年|每年|年薪|/月|每月|月薪|元', '', salary_core)
    salary_core = salary_core.strip()
    
    # ===== 模式匹配（按优先级） =====
    
    # 模式1: 跨单位区间 - "8千-1.6万" "1.2k-2万"
    pattern1 = r'([\d.]+)\s*([千万kKwW])\s*[-~至]\s*([\d.]+)\s*([千万kKwW])'
    match1 = re.search(pattern1, salary_core)
    
    if match1:
        min_val = match1.group(1)
        min_unit = match1.group(2)
        max_val = match1.group(3)
        max_unit = match1.group(4)
        
        min_salary = convert_to_k_per_month(min_val, min_unit, is_yearly, False, num_months)
        max_salary = convert_to_k_per_month(max_val, max_unit, is_yearly, False, num_months)
        avg_salary = (min_salary + max_salary) / 2
        
        return {
            'min_salary': round(min_salary, 1),
            'max_salary': round(max_salary, 1),
            'avg_salary': round(avg_salary, 1)
        }
    
    # 模式2: 同单位区间 - "4-6千" "1.2-2万" "10-15k"
    pattern2 = r'([\d.]+)\s*[-~至]\s*([\d.]+)\s*([千万kKwW])'
    match2 = re.search(pattern2, salary_core)
    
    if match2:
        min_val = match2.group(1)
        max_val = match2.group(2)
        unit = match2.group(3)
        
        min_salary = convert_to_k_per_month(min_val, unit, is_yearly, False, num_months)
        max_salary = convert_to_k_per_month(max_val, unit, is_yearly, False, num_months)
        avg_salary = (min_salary + max_salary) / 2
        
        return {
            'min_salary': round(min_salary, 1),
            'max_salary': round(max_salary, 1),
            'avg_salary': round(avg_salary, 1)
        }
    
    # 模式3: 纯数字区间（无单位，默认千） - "4-6"
    pattern3 = r'^([\d.]+)\s*[-~至]\s*([\d.]+)$'
    match3 = re.search(pattern3, salary_core)
    
    if match3:
        min_val = match3.group(1)
        max_val = match3.group(2)
        
        min_salary = convert_to_k_per_month(min_val, '千', is_yearly, False, num_months)
        max_salary = convert_to_k_per_month(max_val, '千', is_yearly, False, num_months)
        avg_salary = (min_salary + max_salary) / 2
        
        return {
            'min_salary': round(min_salary, 1),
            'max_salary': round(max_salary, 1),
            'avg_salary': round(avg_salary, 1)
        }
    
    # 模式4: 单一数值 - "8千" "2万" "15k"
    pattern4 = r'([\d.]+)\s*([千万kKwW])'
    match4 = re.search(pattern4, salary_core)
    
    if match4:
        val = match4.group(1)
        unit = match4.group(2)
        
        salary = convert_to_k_per_month(val, unit, is_yearly, False, num_months)
        
        return {
            'min_salary': round(salary, 1),
            'max_salary': round(salary, 1),
            'avg_salary': round(salary, 1)
        }
    
    # 无法解析
    return {'min_salary': None, 'max_salary': None, 'avg_salary': None}

def city_clean(city, detail_address):
    """
    归一化城市字段为:xx市-xx区 或 xx市-xx市(县级市)
    Args:
        city (str): 城市名称
        detail_address (str): 详细地址
    Returns:
        str or None: 归一化后的城市字段,格式为'第一级-第二级',找不到则返回None
    """
    # 处理空值情况
    if not detail_address or not isinstance(detail_address, str):
        return None
    
    # 检查city是否已经是合适的格式
    # 合适的格式应该是:xx市-xx区/县/市,不能是:武汉-江夏区(缺少"市")
    if city and '-' in city:
        parts = city.split('-')
        # 检查第一部分是否以"市"结尾
        if len(parts) == 2 and parts[0].endswith('市'):
            return city
        # 否则继续处理
    
    # 解析详细地址,提取省级行政单位后的两级
    # 使用更精确的匹配:确保"市"是第一级行政单位的结尾
    # 匹配:省份(可选) + 地级市(必须以市/州/盟结尾) + 区县(必须以区/县/市等结尾)
    pattern = r'(?:.*?(?:省|自治区|特别行政区))?\s*([^省]+?(?:市|州|盟|地区))\s*([^市州盟地区]+?(?:区|县|市|旗|自治县|自治旗))'
    
    match = re.search(pattern, detail_address)
    
    if not match:
        return None
    
    city_level = match.group(1).strip()
    district_level = match.group(2).strip()
    
    # 处理直辖市的情况(北京、上海、天津、重庆)
    direct_cities = ['北京', '上海', '天津', '重庆']
    for dc in direct_cities:
        if dc in city_level:
            # 直辖市格式:北京市-朝阳区
            return f"{city_level}-{district_level}"
    
    # 返回规范格式
    return f"{city_level}-{district_level}"

def coord_clean(coordinate, detail_address):
    """
    如果原始坐标为空或0,调用高德api通过详细地址获取经纬度
    Args:
        coordinate (str): 原始坐标字符串
        detail_address (str): 详细地址
    Returns:
        tuple: [经度, 纬度] 
    """
    if coordinate and isinstance(coordinate, list) and len(coordinate)== 2:
        if int(float(coordinate[0])) and int(float(coordinate[1])):
            return coordinate
    url=f'https://restapi.amap.com/v3/geocode/geo?key={api_key}&address={detail_address}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == '1' and data['geocodes']:
            location = data['geocodes'][0]['location']
            longitude, latitude = map(float, location.split(','))
            time.sleep(0.4)#延时等待,避免频率过高
            print(f"获取坐标中...")
            return [latitude,longitude]
    return [None, None]

def city_clean(city, detail_address):
    """
    归一化城市字段为: xx市-xx区 / xx市-xx县 / xx市-xx新区
    找不到合适结果返回 None
    """

    if not city or not detail_address:
        return None

    city = city.strip()

    # 1. 已经是合格格式，直接返回
    if re.fullmatch(r".+市-.+(区|县|新区)", city):
        return city

    # 2. 提取 city_name（去掉可能的"市"）
    city_name = city.replace("市", "")

    # 3. 从 detail_address 中提取区 / 县 / 新区
    district_pattern = re.compile(
        rf"{city_name}市(.+?(区|县|新区))"
    )
    match = district_pattern.search(detail_address)

    if not match:
        return None

    district = match.group(1)

    # 4. 拼接标准格式
    return f"{city_name}市-{district}"

def clean_job_data(df, days_limit=None, remove_duplicates=True, flag=0):
    """
    完整的职位数据清洗函数
    
    参数:
        df: 原始DataFrame
        days_limit: 保留最近N天的数据，None表示不限制
        remove_duplicates: 是否去除重复数据
        flag:用于描述要进行的清洗操作的状态量,6位二进制数,每一位对应要执行的操作,0表示执行,1表示不执行
    
    返回:
        pd.DataFrame: 清洗后的数据
    """
    # 创建副本，避免修改原始数据
    df_clean = df.copy()
    
    # ===== 重要：重置索引，避免索引对齐问题 =====
    df_clean = df_clean.reset_index(drop=True)
    
    print(f"原始数据: {len(df_clean)} 条")
    
    # 记录原始列
    original_columns = df_clean.columns.tolist()
    original_column_count = len(original_columns)
    
    # 1. 去除重复数据（基于jobid）
    if remove_duplicates and 'jobid' in df_clean.columns:
        before_count = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=['jobid'], keep='first')
        # ===== 重要：去重后重置索引 =====
        df_clean = df_clean.reset_index(drop=True)
        removed = before_count - len(df_clean)
        print(f"去除重复数据: {removed} 条，剩余 {len(df_clean)} 条")
    
    # 2. 清洗薪资数据
    if '薪资' in df_clean.columns and flag & 0b000001 == 0:
        print("正在清洗薪资数据...")
        
        # ===== 修复：逐行处理，确保索引对齐 =====
        salary_results = []
        failed_cases = []
        
        for idx, salary_value in enumerate(df_clean['薪资']):
            try:
                result = clean_salary(salary_value)
                salary_results.append(result)
            except Exception as e:
                # 记录失败的案例
                failed_cases.append({
                    'index': idx,
                    'salary': salary_value,
                    'error': str(e)
                })
                salary_results.append({'min_salary': None, 'max_salary': None, 'avg_salary': None})
        
        # 转换为DataFrame
        salary_df = pd.DataFrame(salary_results)
        
        # ===== 验证数据长度一致 =====
        if len(salary_df) != len(df_clean):
            print(f"警告：薪资数据长度({len(salary_df)})与原数据({len(df_clean)})不一致！")
            return df_clean
        
        # 直接赋值（因为索引已经对齐）
        df_clean['薪资下限(k)'] = salary_df['min_salary'].values
        df_clean['薪资上限(k)'] = salary_df['max_salary'].values
        df_clean['平均薪资(k)'] = salary_df['avg_salary'].values
        
        # 统计薪资清洗结果
        valid_salary = df_clean['平均薪资(k)'].notna().sum()
        invalid_salary = df_clean['平均薪资(k)'].isna().sum()
        print(f"薪资数据清洗完成: {valid_salary}/{len(df_clean)} 条有效, {invalid_salary} 条无效")
        
    # 3. 处理发布时间
    if '发布时间' in df_clean.columns and flag & 0b0010 == 0:
        df_clean['发布时间'] = pd.to_datetime(df_clean['发布时间'], errors='coerce')
        
        if days_limit is not None:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days_limit)
            before_count = len(df_clean)
            df_clean = df_clean[df_clean['发布时间'] >= cutoff_date]
            # ===== 重要：筛选后重置索引 =====
            df_clean = df_clean.reset_index(drop=True)
            removed = before_count - len(df_clean)
            print(f"筛选最近 {days_limit} 天数据: 移除 {removed} 条，剩余 {len(df_clean)} 条")
    
    # 4. 处理经纬度数据
    if '经纬度' in df_clean.columns or ('城市' in df_clean.columns and '公司名称' in df_clean.columns) and flag & 0b000100 == 0:
        area_results=[]
        for idx,coord in enumerate(df_clean['经纬度']):
            if not coord:
                area_results.append({'index': idx, '省份': None,'区域': None,'详细地址':None})
            else:
                result=clean_area(coord, df_clean.at[idx, '城市'], df_clean.at[idx, '公司名称'])
                area_results.append({'index': idx, '省份': result['province'], '区域': result['district'], '详细地址': result['detail_address']})
            #延时等待(一秒至多访问3次):
            print(f"正在处理第 {idx} 条数据...")
            time.sleep(0.4)
        area_df=pd.DataFrame(area_results)
        df_clean['省份']=area_df['省份'].values
        df_clean['区域']=area_df['区域'].values
        df_clean['详细地址']=area_df['详细地址'].values
                
    # 5. 归一化城市字段
    if '城市' in df_clean.columns and '详细地址' in df_clean.columns and flag & 0b010000 == 0:
        df_clean['城市'] = df_clean.apply(lambda x: city_clean(x['城市'], x['详细地址']), axis=1)

    # 6. 处理学历要求
    if '学历要求' in df_clean.columns and flag & 0b001000 == 0:
        education_map = {
            '不限': 0,
            '初中': 1,
            '中专': 2,
            '高中': 2,
            '大专': 3,
            '本科': 4,
            '硕士': 5,
            '博士': 6
        }
        df_clean['学历等级'] = df_clean['学历要求'].map(education_map)
    
    # 7. 处理经验要求
    if '经验要求' in df_clean.columns and flag & 0b100000 == 0:
        df_clean['经验年限'] = df_clean['经验要求'].str.extract(r'(\d+)').astype(float)
        df_clean['经验年限'] = df_clean['经验年限'].fillna(0)
    
    # 8. 移除空值过多的行（只考虑原始列）
    null_counts = df_clean[original_columns].isnull().sum(axis=1)
    max_nulls = original_column_count * 0.5
    before_count = len(df_clean)
    df_clean = df_clean[null_counts <= max_nulls]
    # ===== 筛选后重置索引 =====
    df_clean = df_clean.reset_index(drop=True)
    removed = before_count - len(df_clean)
    if removed > 0:
        print(f"移除空值过多的行: {removed} 条")
    
    print(f"\n最终数据: {len(df_clean)} 条")
    if '平均薪资(k)' in df_clean.columns:
        valid_pct = df_clean['平均薪资(k)'].notna().sum() / len(df_clean) * 100
        print(f"薪资数据完整性: {valid_pct:.1f}%")
    
    return df_clean

def save_cleaned_data(df, output_dir='../washdata', file_prefix='cleaned_jobs'):
    """
    保存清洗后的数据到指定目录（在输出目录下创建以文件名+时间戳命名的子目录存放文件）
    
    参数:
        df: 清洗后的DataFrame
        output_dir: 输出目录路径
        file_prefix: 文件名前缀
    
    返回:
        dict: 保存的时间戳文件路径字典
    """
    # 获取绝对路径
    output_dir = os.path.abspath(output_dir)
    
    # 创建主目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)
    print(f"数据将保存到: {output_dir}")
    
    # 添加时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 在主目录下创建一个子目录，名称与清洗数据文件相同（file_prefix_timestamp）
    subdir_name = f"{file_prefix}_{timestamp}"
    subdir_path = os.path.join(output_dir, subdir_name)
    os.makedirs(subdir_path, exist_ok=True)
    print(f"清洗结果子目录: {subdir_path}")
    
    # 定义时间戳文件路径（放在子目录下）
    files = {
        'json': os.path.join(subdir_path, f'{file_prefix}_{timestamp}.json'),
        'csv': os.path.join(subdir_path, f'{file_prefix}_{timestamp}.csv'),
        'excel': os.path.join(subdir_path, f'{file_prefix}_{timestamp}.xlsx'),
    }
    
    # 保存为JSON
    df.to_json(files['json'], orient='records', force_ascii=False, indent=4)
    print(f"✓ JSON文件已保存: {os.path.basename(files['json'])}")
    
    # 保存为CSV（UTF-8 with BOM，Excel可以正确打开中文）
    df.to_csv(files['csv'], index=False, encoding='utf-8-sig')
    print(f"✓ CSV文件已保存: {os.path.basename(files['csv'])}")
    
    # 保存为Excel
    try:
        df.to_excel(files['excel'], index=False, engine='openpyxl')
        print(f"✓ Excel文件已保存: {os.path.basename(files['excel'])}")
    except Exception as e:
        print(f"✗ Excel保存失败: {e}")
        files['excel'] = None
    
    # 同时在主目录下保留一个最新版本（不带时间戳，方便后续直接使用)
    latest_files = {
        'json': os.path.join(output_dir, f'{file_prefix}_latest.json'),
        'csv': os.path.join(output_dir, f'{file_prefix}_latest.csv'),
        'excel': os.path.join(output_dir, f'{file_prefix}_latest.xlsx'),
    }
    
    df.to_json(latest_files['json'], orient='records', force_ascii=False, indent=4)
    df.to_csv(latest_files['csv'], index=False, encoding='utf-8-sig')
    try:
        df.to_excel(latest_files['excel'], index=False, engine='openpyxl')
    except:
        pass
    
    print(f"\n✓ 最新版本已保存为 '{file_prefix}_latest.*'（位于 {output_dir}）")
    
    # 保存数据统计信息到子目录
    stats_file = os.path.join(subdir_path, f'data_stats_{timestamp}.txt')
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write(f"数据清洗统计报告\n")
        f.write(f"=" * 50 + "\n")
        f.write(f"清洗时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总记录数: {len(df)}\n\n")
        
        f.write(f"数据概览:\n")
        f.write(f"-" * 50 + "\n")
        try:
            f.write(df.describe().to_string())
        except Exception:
            f.write("无法生成describe()\n")
        f.write(f"\n\n")
        
        f.write(f"字段信息:\n")
        f.write(f"-" * 50 + "\n")
        try:
            buf = io.StringIO()
            df.info(buf=buf, verbose=True)
            info_str = buf.getvalue()
            f.write(info_str)
        except Exception:
            f.write("无法生成 info()\n")
        
        if '平均薪资(k)' in df.columns:
            f.write(f"\n\n薪资统计:\n")
            f.write(f"-" * 50 + "\n")
            try:
                f.write(f"平均薪资: {df['平均薪资(k)'].mean():.2f}k\n")
                f.write(f"中位数薪资: {df['平均薪资(k)'].median():.2f}k\n")
                f.write(f"最高薪资: {df['薪资上限(k)'].max():.2f}k\n")
                f.write(f"最低薪资: {df['薪资下限(k)'].min():.2f}k\n")
            except Exception:
                f.write("无法计算薪资统计\n")
    
    #复制一份统计报告为latest_stats.txt到主目录
    os.system(f'copy "{stats_file}" "{os.path.join(output_dir, "latest_stats.txt")}"')
    
    print(f"✓ 统计报告已保存: {os.path.basename(stats_file)}")
    
    print(f"\n" + "=" * 50)
    print(f"所有文件保存完成！共 {len(df)} 条记录")
    print(f"保存路径（子目录）: {subdir_path}")
    print(f"主目录中的最新文件: {output_dir}")
    print("=" * 50)
    
    return files


#main函数,命令行传参完成功能
if __name__=="__main__":
    parser = argparse.ArgumentParser(description="数据清洗工具")
    parser.add_argument('--data_dir', type=str, default='../data', help='数据目录路径')
    parser.add_argument('--days_limit', type=int, default=None, help='保留最近N天的数据')
#    parser.add_argument('--remove_duplicates', action='store_true', help='是否去除重复数据')
    parser.add_argument('--output_file', type=str, default='cleaned_jobs_data.csv', help='输出文件路径')
    parser.add_argument('--data_path', type=str, default='all', help='数据文件选择,all表示全部文件,latest表示最新文件,单个文件直接写文件名')
    parser.add_argument('--flag', type=int, default=0, help='清洗操作标志位,6位二进制数,每一位对应要执行的操作,0表示执行,1表示不执行,从低到高依次为:薪资清洗,发布时间处理,经纬度处理,城市归一化,学历处理,经验处理')
    
#输出参数
    parser.add_argument('--output_dir', type=str, default='../washdata', help='输出目录路径')
    parser.add_argument('--file_prefix', type=str, default='cleaned_jobs', help='文件名前缀')


    args = parser.parse_args()

    # 读取数据
    if args.data_path == 'latest':
        df_raw = read_latest_json(data_dir=args.data_dir)
    elif args.data_path == 'all':
        df_raw = read_all_json_files(data_dir=args.data_dir)
    else:
        path = os.path.join(args.data_dir, args.data_path)
        df_raw = read_json_data(file_path=path)


    # 清洗数据
    df_cleaned = clean_job_data(
        df_raw,
        days_limit=args.days_limit,
        remove_duplicates=True
    )

    # 保存清洗后的数据
    save_cleaned_data(df_cleaned, output_dir='../washdata', file_prefix='cleaned_jobs')

