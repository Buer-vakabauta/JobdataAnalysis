import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
import json

# 设置中文字体
import matplotlib
matplotlib.rcParams['font.family'] = 'Microsoft YaHei'
matplotlib.rcParams['axes.unicode_minus'] = False


class GeoAnalyzer:
    """地理空间分析类"""
    
    def __init__(self, df):
        """
        初始化分析器
        
        参数:
            df: 清洗后的DataFrame（包含地理信息）
        """
        self.df = df.copy()
        
        # 过滤有效的地理数据
        self.df_geo = self.df[
            (self.df['详细地址'].notna()) & 
            (self.df['省份'].notna()) &
            (self.df['地区'].notna())
        ].copy()
        
        
        
        # 修正区域字段
        self.df_geo = self._fix_district_field(self.df_geo)
        
        print(f"总数据: {len(self.df)} 条")
        print(f"有效地理数据: {len(self.df_geo)} 条 ({len(self.df_geo)/len(self.df)*100:.1f}%)")
    
    def _fix_district_field(self, df):
        """
        修正区域字段：从详细地址中提取区县信息
        
        参数:
            df: DataFrame
            
        返回:
            修正后的DataFrame
        """
        import re
        
        def extract_district(row):
            """
            从详细地址中提取区县
            
            优先级：
            1. 如果区域字段有效且不是市级单位，直接使用
            2. 从详细地址中提取
            3. 从城市字段中提取（如"成都-双流区"）
            """
            district = row.get('区域', '')
            address = row.get('详细地址', '')
            city = row.get('地区', '')

            # 市级单位关键词（这些不是区县）
            city_keywords = ['市', '省']
            
            # 1. 检查现有区域字段是否有效
            if pd.notna(district) and district:
                # 如果区域以"市"或"省"结尾，说明是市级/省级单位，需要重新提取
                if not any(district.endswith(kw) for kw in city_keywords):
                    # 检查是否是有效的区县（以区、县、旗等结尾）
                    if re.search(r'(区|县|旗)', district):
                        return district
            # 2. 从详细地址中提取
            if pd.notna(address) and address:
                match = re.search(r'(区|县|旗)', address)
                if match:
                    return match.group()
            return None

        df['区域'] = df.apply(extract_district, axis=1)
        return df

    def city_overview(self, save_path='../output/city_overview.png'):
        """
        城市招聘量对比分析
        """
        print("\n" + "="*60)
        print("城市招聘量分析")
        print("="*60)
        
        # 统计各省份/城市的职位数量
        province_counts = self.df_geo['省份'].value_counts()
        city_counts = self.df_geo['城市'].value_counts().head(20)
        
        print(f"\n省份分布（前10）:")
        print(province_counts.head(10))
        
        print(f"\n城市分布（前20）:")
        print(city_counts)
        
        # 可视化
        fig, axes = plt.subplots(2, 2, figsize=(18, 14))
        
        # 1. 省份职位数量柱状图
        ax1 = axes[0, 0]
        colors1 = plt.cm.viridis(np.linspace(0, 1, len(province_counts)))
        bars1 = ax1.barh(range(len(province_counts)), province_counts.values, color=colors1)
        ax1.set_yticks(range(len(province_counts)))
        ax1.set_yticklabels(province_counts.index)
        ax1.set_xlabel('职位数量', fontsize=12, fontweight='bold')
        ax1.set_title('各省份职位数量分布', fontsize=14, fontweight='bold', pad=20)
        ax1.invert_yaxis()
        
        # 添加数值标签
        for i, bar in enumerate(bars1):
            width = bar.get_width()
            ax1.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{int(width)}', ha='left', va='center', fontsize=9)
        
        # 2. 城市职位数量（前20）
        ax2 = axes[0, 1]
        colors2 = plt.cm.plasma(np.linspace(0, 1, len(city_counts)))
        bars2 = ax2.barh(range(len(city_counts)), city_counts.values, color=colors2)
        ax2.set_yticks(range(len(city_counts)))
        ax2.set_yticklabels(city_counts.index, fontsize=9)
        ax2.set_xlabel('职位数量', fontsize=12, fontweight='bold')
        ax2.set_title('TOP20城市职位数量', fontsize=14, fontweight='bold', pad=20)
        ax2.invert_yaxis()
        
        for i, bar in enumerate(bars2):
            width = bar.get_width()
            ax2.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{int(width)}', ha='left', va='center', fontsize=8)
        
        # 3. 城市平均薪资对比（前15）
        ax3 = axes[1, 0]
        city_salary = self.df_geo.groupby('城市')['平均薪资(k)'].agg(['mean', 'count'])
        city_salary = city_salary[city_salary['count'] >= 5]  # 至少5个样本
        city_salary = city_salary.sort_values('mean', ascending=False).head(15)
        
        bars3 = ax3.barh(range(len(city_salary)), city_salary['mean'].values, 
                        color='coral', alpha=0.8)
        ax3.set_yticks(range(len(city_salary)))
        ax3.set_yticklabels(city_salary.index)
        ax3.set_xlabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax3.set_title('TOP15城市平均薪资', fontsize=14, fontweight='bold', pad=20)
        ax3.invert_yaxis()
        
        for i, bar in enumerate(bars3):
            width = bar.get_width()
            count = int(city_salary.iloc[i]['count'])
            ax3.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{width:.1f}k (n={count})', ha='left', va='center', fontsize=9)
        
        # 4. 职位数量vs平均薪资散点图
        ax4 = axes[1, 1]
        city_stats = self.df_geo.groupby('城市').agg({
            '平均薪资(k)': 'mean',
            'jobid': 'count'
        }).rename(columns={'jobid': 'count'})
        city_stats = city_stats[city_stats['count'] >= 3]
        
        scatter = ax4.scatter(
            city_stats['count'], 
            city_stats['平均薪资(k)'],
            s=city_stats['count']*10,
            alpha=0.6,
            c=city_stats['平均薪资(k)'],
            cmap='RdYlGn'
        )
        
        # 标注主要城市
        for city, row in city_stats.nlargest(10, 'count').iterrows():
            ax4.annotate(
                city, 
                (row['count'], row['平均薪资(k)']),
                fontsize=9,
                alpha=0.8
            )
        
        ax4.set_xlabel('职位数量', fontsize=12, fontweight='bold')
        ax4.set_ylabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax4.set_title('城市职位数量与平均薪资关系', fontsize=14, fontweight='bold', pad=20)
        ax4.grid(True, alpha=0.3)
        
        plt.colorbar(scatter, ax=ax4, label='平均薪资(k)')
        
        plt.tight_layout()
        
        # 保存图片
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ 城市分析图已保存: {save_path}")
        
        plt.show()
    
    def city_district_analysis(self, city_keyword, save_path=None):
        """
        分析指定城市的区域分布
        
        参数:
            city_keyword: 城市关键词（如"成都"、"重庆"）
            save_path: 保存路径
        """
        # 筛选城市数据
        df_city = self.df_geo[
            self.df_geo['城市'].str.contains(city_keyword, na=False) |
            self.df_geo['省份'].str.contains(city_keyword, na=False) |
            self.df_geo['详细地址'].str.contains(city_keyword, na=False)
        ].copy()
        
        if len(df_city) == 0:
            print(f"⚠ 未找到关键词'{city_keyword}'相关的数据")
            return
        
        print(f"\n" + "="*60)
        print(f"{city_keyword}市区域分析")
        print("="*60)
        print(f"数据量: {len(df_city)} 条")
        
        # 统计区域分布（使用修正后的区域字段）
        district_counts = df_city['区域'].value_counts().head(15)
        
        print(f"\n区域职位数量分布:")
        print(district_counts)
        
        # 显示区域样本
        print(f"\n区域示例:")
        for district in district_counts.head(5).index:
            count = district_counts[district]
            print(f"  {district}: {count} 个职位")
        
        # 可视化
        fig, axes = plt.subplots(2, 2, figsize=(18, 14))
        
        # 1. 区域职位数量
        ax1 = axes[0, 0]
        colors = plt.cm.Set3(np.linspace(0, 1, len(district_counts)))
        bars = ax1.barh(range(len(district_counts)), district_counts.values, color=colors)
        ax1.set_yticks(range(len(district_counts)))
        ax1.set_yticklabels(district_counts.index)
        ax1.set_xlabel('职位数量', fontsize=12, fontweight='bold')
        ax1.set_title(f'{city_keyword}各区域职位数量', fontsize=14, fontweight='bold', pad=20)
        ax1.invert_yaxis()
        
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax1.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{int(width)}', ha='left', va='center', fontsize=10)
        
        # 2. 区域平均薪资
        ax2 = axes[0, 1]
        district_key = '区域' if '区域' in df_city.columns else '区县'
        district_salary = df_city.groupby(district_key)['平均薪资(k)'].agg(['mean', 'count'])
        district_salary = district_salary[district_salary['count'] >= 3]
        district_salary = district_salary.sort_values('mean', ascending=False).head(15)
        
        bars2 = ax2.barh(range(len(district_salary)), district_salary['mean'].values, 
                        color='lightcoral', alpha=0.8)
        ax2.set_yticks(range(len(district_salary)))
        ax2.set_yticklabels(district_salary.index)
        ax2.set_xlabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax2.set_title(f'{city_keyword}各区域平均薪资', fontsize=14, fontweight='bold', pad=20)
        ax2.invert_yaxis()
        
        for i, bar in enumerate(bars2):
            width = bar.get_width()
            count = int(district_salary.iloc[i]['count'])
            ax2.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{width:.1f}k (n={count})', ha='left', va='center', fontsize=9)
        
        # 3. 学历要求分布
        ax3 = axes[1, 0]
        edu_counts = df_city['学历要求'].value_counts()
        edu_order = ['不限', '中专', '高中', '大专', '本科', '硕士', '博士']
        edu_counts = edu_counts.reindex([e for e in edu_order if e in edu_counts.index])
        
        ax3.pie(edu_counts.values, labels=edu_counts.index, autopct='%1.1f%%',
               startangle=90, colors=plt.cm.Pastel1(range(len(edu_counts))))
        ax3.set_title(f'{city_keyword}学历要求分布', fontsize=14, fontweight='bold', pad=20)
        
        # 4. 经验要求分布
        ax4 = axes[1, 1]
        df_city['经验分类'] = pd.cut(
            df_city['经验年限'],
            bins=[-0.1, 0, 1, 3, 5, 10, 100],
            labels=['应届生', '1年', '1-3年', '3-5年', '5-10年', '10年+']
        )
        exp_counts = df_city['经验分类'].value_counts().sort_index()
        
        colors4 = plt.cm.viridis(np.linspace(0, 1, len(exp_counts)))
        bars4 = ax4.bar(range(len(exp_counts)), exp_counts.values, color=colors4)
        ax4.set_xticks(range(len(exp_counts)))
        ax4.set_xticklabels(exp_counts.index, rotation=45)
        ax4.set_ylabel('职位数量', fontsize=12, fontweight='bold')
        ax4.set_title(f'{city_keyword}经验要求分布', fontsize=14, fontweight='bold', pad=20)
        
        for bar in bars4:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        # 保存图片
        if save_path is None:
            save_path = f'../output/{city_keyword}_district_analysis.png'
        
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ {city_keyword}区域分析图已保存: {save_path}")
        
        plt.show()
    
    def create_city_heatmap(self, city_keyword, output_file=None):
        """
        创建城市职位分布热力图
        
        参数:
            city_keyword: 城市关键词
            output_file: 输出HTML文件路径
        """
        # 筛选城市数据
        df_city = self.df_geo[
            self.df_geo['城市'].str.contains(city_keyword, na=False) |
            self.df_geo['省份'].str.contains(city_keyword, na=False)
        ].copy()
        
        if len(df_city) == 0:
            print(f"⚠ 未找到关键词'{city_keyword}'相关的数据")
            return
        
        print(f"\n生成{city_keyword}热力图...")
        print(f"数据点: {len(df_city)} 个")
        
        # 计算中心点
        center_lat = df_city['纬度'].mean()
        center_lon = df_city['经度'].mean()
        
        # 创建地图
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles='OpenStreetMap'
        )
        
        # 准备热力图数据
        heat_data = [[row['纬度'], row['经度'], row['平均薪资(k)']] 
                     for idx, row in df_city.iterrows() 
                     if pd.notna(row['平均薪资(k)'])]
        
        # 添加热力图层
        HeatMap(
            heat_data,
            min_opacity=0.3,
            max_opacity=0.8,
            radius=15,
            blur=20,
            gradient={
                0.0: 'blue',
                0.3: 'lime',
                0.5: 'yellow',
                0.7: 'orange',
                1.0: 'red'
            }
        ).add_to(m)
        
        # 添加标记聚合（点击可查看详情）
        marker_cluster = MarkerCluster(name='职位详情').add_to(m)
        
        for idx, row in df_city.head(100).iterrows():  # 只显示前100个标记
            popup_html = f"""
            <div style="width: 200px">
                <h4>{row['职位名称']}</h4>
                <p><b>公司:</b> {row['公司名称']}</p>
                <p><b>薪资:</b> {row['薪资']}</p>
                <p><b>学历:</b> {row['学历要求']}</p>
                <p><b>经验:</b> {row['经验要求']}</p>
                <p><b>地址:</b> {row.get('详细地址', '未知')}</p>
            </div>
            """
            
            folium.Marker(
                location=[row['纬度'], row['经度']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(marker_cluster)
        
        # 添加图层控制
        folium.LayerControl().add_to(m)
        
        # 保存地图
        if output_file is None:
            output_file = f'../output/{city_keyword}_heatmap.html'
        
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        m.save(output_file)
        
        print(f"✓ 热力图已保存: {output_file}")
        print(f"  在浏览器中打开查看!")
        
        return m
    
    def salary_geo_distribution(self, save_path='../output/salary_geo_distribution.png'):
        """
        薪资地理分布可视化
        """
        print("\n" + "="*60)
        print("薪资地理分布分析")
        print("="*60)
        
        fig, axes = plt.subplots(1, 2, figsize=(18, 7))
        
        # 1. 不同城市的薪资箱线图（前10个城市）
        ax1 = axes[0]
        top_cities = self.df_geo['城市'].value_counts().head(10).index
        df_top_cities = self.df_geo[self.df_geo['城市'].isin(top_cities)]
        
        sns.boxplot(
            data=df_top_cities,
            x='城市',
            y='平均薪资(k)',
            ax=ax1,
            palette='Set2'
        )
        ax1.set_xlabel('城市', fontsize=12, fontweight='bold')
        ax1.set_ylabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax1.set_title('TOP10城市薪资分布箱线图', fontsize=14, fontweight='bold', pad=20)
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 2. 薪资与地理位置的散点图
        ax2 = axes[1]
        scatter = ax2.scatter(
            self.df_geo['经度'],
            self.df_geo['纬度'],
            c=self.df_geo['平均薪资(k)'],
            s=50,
            alpha=0.6,
            cmap='RdYlGn',
            edgecolors='black',
            linewidth=0.5
        )
        
        ax2.set_xlabel('经度', fontsize=12, fontweight='bold')
        ax2.set_ylabel('纬度', fontsize=12, fontweight='bold')
        ax2.set_title('职位地理分布与薪资关系', fontsize=14, fontweight='bold', pad=20)
        
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label('平均薪资 (k/月)', fontsize=10)
        
        plt.tight_layout()
        
        # 保存图片
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ 薪资地理分布图已保存: {save_path}")
        
        plt.show()
    
    def industry_city_cross_analysis(self, save_path='../output/industry_city_cross.png'):
        """
        行业与城市的交叉分析
        """
        print("\n" + "="*60)
        print("行业-城市交叉分析")
        print("="*60)
        
        # 选择前8个城市和前10个行业
        top_cities = self.df_geo['城市'].value_counts().head(8).index
        top_industries = self.df_geo['行业'].value_counts().head(10).index
        
        df_cross = self.df_geo[
            (self.df_geo['城市'].isin(top_cities)) &
            (self.df_geo['行业'].isin(top_industries))
        ]
        
        # 创建交叉表
        cross_table = pd.crosstab(
            df_cross['行业'],
            df_cross['城市']
        )
        
        # 可视化
        fig, axes = plt.subplots(1, 2, figsize=(20, 8))
        
        # 1. 热力图
        ax1 = axes[0]
        sns.heatmap(
            cross_table,
            annot=True,
            fmt='d',
            cmap='YlOrRd',
            ax=ax1,
            cbar_kws={'label': '职位数量'}
        )
        ax1.set_xlabel('城市', fontsize=12, fontweight='bold')
        ax1.set_ylabel('行业', fontsize=12, fontweight='bold')
        ax1.set_title('行业-城市职位数量分布热力图', fontsize=14, fontweight='bold', pad=20)
        
        # 2. 平均薪资热力图
        ax2 = axes[1]
        salary_cross = df_cross.groupby(['行业', '城市'])['平均薪资(k)'].mean().unstack()
        
        sns.heatmap(
            salary_cross,
            annot=True,
            fmt='.1f',
            cmap='RdYlGn',
            ax=ax2,
            cbar_kws={'label': '平均薪资(k)'}
        )
        ax2.set_xlabel('城市', fontsize=12, fontweight='bold')
        ax2.set_ylabel('行业', fontsize=12, fontweight='bold')
        ax2.set_title('行业-城市平均薪资热力图', fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # 保存图片
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ 行业城市交叉分析图已保存: {save_path}")
        
        plt.show()


def main():
    """主函数"""
    import os
    
    # 读取数据
    df = pd.read_json('../washdata/cleaned_jobs_latest.json')
    
    # 创建输出目录
    os.makedirs('../output', exist_ok=True)
    
    # 初始化分析器
    analyzer = GeoAnalyzer(df)
    
    # 1. 城市概览分析
    analyzer.city_overview()
    
    # 2. 成都市区域分析
    analyzer.city_district_analysis('成都')
    
    # 3. 重庆市区域分析
    analyzer.city_district_analysis('重庆')
    
    # 4. 创建成都热力图
    analyzer.create_city_heatmap('成都')
    
    # 5. 创建重庆热力图
    analyzer.create_city_heatmap('重庆')
    
    # 6. 薪资地理分布
    analyzer.salary_geo_distribution()
    
    # 7. 行业城市交叉分析
    analyzer.industry_city_cross_analysis()
    
    print("\n" + "="*60)
    print("地理空间分析完成！")
    print("="*60)
    
if __name__ == '__main__':
    main()