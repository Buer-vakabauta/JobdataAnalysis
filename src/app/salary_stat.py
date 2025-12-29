import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy import stats

# 设置中文字体和样式
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

class SalaryAnalyzer:
    """薪资数据分析类"""
    
    def __init__(self, df):
        """
        初始化分析器
        
        参数:
            df: 清洗后的DataFrame
        """
        self.df = df.copy()
        # 过滤掉薪资为空的数据
        self.df_valid = self.df[self.df['平均薪资(k)'].notna()].copy()
        
        print(f"总数据: {len(self.df)} 条")
        print(f"有效薪资数据: {len(self.df_valid)} 条")
        print(f"数据有效率: {len(self.df_valid)/len(self.df)*100:.1f}%")
    
    def basic_statistics(self):
        """基础统计信息"""
        print("\n" + "="*60)
        print("薪资基础统计")
        print("="*60)
        
        salary_stats = self.df_valid['平均薪资(k)'].describe()
        
        print(f"\n平均薪资: {salary_stats['mean']:.2f}k")
        print(f"中位数薪资: {salary_stats['50%']:.2f}k")
        print(f"标准差: {salary_stats['std']:.2f}k")
        print(f"最低薪资: {salary_stats['min']:.2f}k")
        print(f"最高薪资: {salary_stats['max']:.2f}k")
        print(f"\n25%分位数: {salary_stats['25%']:.2f}k")
        print(f"75%分位数: {salary_stats['75%']:.2f}k")
        
        # 薪资区间分布
        bins = [0, 5, 10, 15, 20, 30, 50, 100]
        labels = ['0-5k', '5-10k', '10-15k', '15-20k', '20-30k', '30-50k', '50k+']
        self.df_valid['薪资区间'] = pd.cut(
            self.df_valid['平均薪资(k)'], 
            bins=bins, 
            labels=labels
        )
        
        print("\n薪资区间分布:")
        print(self.df_valid['薪资区间'].value_counts().sort_index())
        
        return salary_stats
    
    def plot_salary_distribution(self, save_path='../output/salary_distribution.png'):
        """
        绘制薪资分布图（直方图 + KDE核密度估计）
        """
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 直方图 + KDE
        ax1 = axes[0, 0]
        sns.histplot(
            data=self.df_valid, 
            x='平均薪资(k)', 
            bins=50, 
            kde=True, 
            ax=ax1,
            color='skyblue',
            edgecolor='black',
            alpha=0.7
        )
        ax1.axvline(
            self.df_valid['平均薪资(k)'].mean(), 
            color='red', 
            linestyle='--', 
            linewidth=2,
            label=f'平均值: {self.df_valid["平均薪资(k)"].mean():.1f}k'
        )
        ax1.axvline(
            self.df_valid['平均薪资(k)'].median(), 
            color='green', 
            linestyle='--', 
            linewidth=2,
            label=f'中位数: {self.df_valid["平均薪资(k)"].median():.1f}k'
        )
        ax1.set_xlabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('职位数量', fontsize=12, fontweight='bold')
        ax1.set_title('薪资分布直方图与核密度估计', fontsize=14, fontweight='bold', pad=20)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. 薪资区间条形图
        ax2 = axes[0, 1]
        salary_range_counts = self.df_valid['薪资区间'].value_counts().sort_index()
        colors = plt.cm.viridis(np.linspace(0, 1, len(salary_range_counts)))
        bars = ax2.bar(
            range(len(salary_range_counts)), 
            salary_range_counts.values,
            color=colors,
            edgecolor='black',
            alpha=0.8
        )
        ax2.set_xticks(range(len(salary_range_counts)))
        ax2.set_xticklabels(salary_range_counts.index, rotation=45)
        ax2.set_xlabel('薪资区间', fontsize=12, fontweight='bold')
        ax2.set_ylabel('职位数量', fontsize=12, fontweight='bold')
        ax2.set_title('薪资区间分布', fontsize=14, fontweight='bold', pad=20)
        
        # 在柱子上添加数值标签
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width()/2., 
                height,
                f'{int(height)}\n({height/len(self.df_valid)*100:.1f}%)',
                ha='center', 
                va='bottom',
                fontsize=9
            )
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 3. 累积分布图
        ax3 = axes[1, 0]
        sorted_salary = np.sort(self.df_valid['平均薪资(k)'])
        cumulative = np.arange(1, len(sorted_salary) + 1) / len(sorted_salary) * 100
        ax3.plot(sorted_salary, cumulative, linewidth=2, color='purple')
        ax3.axhline(50, color='red', linestyle='--', alpha=0.5, label='50%分位')
        ax3.axhline(75, color='orange', linestyle='--', alpha=0.5, label='75%分位')
        ax3.set_xlabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax3.set_ylabel('累积百分比 (%)', fontsize=12, fontweight='bold')
        ax3.set_title('薪资累积分布曲线', fontsize=14, fontweight='bold', pad=20)
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # 4. 小提琴图
        ax4 = axes[1, 1]
        parts = ax4.violinplot(
            [self.df_valid['平均薪资(k)'].values], 
            positions=[0],
            widths=0.7,
            showmeans=True,
            showmedians=True
        )
        for pc in parts['bodies']:
            pc.set_facecolor('lightblue')
            pc.set_alpha(0.7)
        ax4.set_ylabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax4.set_title('薪资分布小提琴图', fontsize=14, fontweight='bold', pad=20)
        ax4.set_xticks([0])
        ax4.set_xticklabels(['所有职位'])
        ax4.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # 保存图片
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ 薪资分布图已保存: {save_path}")
        
        plt.show()
    
    def plot_salary_by_education(self, save_path='../output/salary_by_education.png'):
        """
        按学历要求分析薪资（箱线图）
        """
        # 过滤掉学历为空的数据
        df_edu = self.df_valid[self.df_valid['学历要求'].notna()].copy()
        
        # 按学历等级排序
        education_order = ['不限', '初中', '中专', '高中', '大专', '本科', '硕士', '博士']
        df_edu['学历要求'] = pd.Categorical(
            df_edu['学历要求'], 
            categories=education_order, 
            ordered=True
        )
        df_edu = df_edu.sort_values('学历要求')
        
        fig, axes = plt.subplots(1, 2, figsize=(18, 7))
        
        # 1. 箱线图
        ax1 = axes[0]
        sns.boxplot(
            data=df_edu,
            x='学历要求',
            y='平均薪资(k)',
            ax=ax1,
            palette='Set2'
        )
        ax1.set_xlabel('学历要求', fontsize=12, fontweight='bold')
        ax1.set_ylabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax1.set_title('不同学历要求的薪资分布（箱线图）', fontsize=14, fontweight='bold', pad=20)
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 添加样本数量标签
        for i, education in enumerate(df_edu['学历要求'].cat.categories):
            count = len(df_edu[df_edu['学历要求'] == education])
            if count > 0:
                ax1.text(i, ax1.get_ylim()[1] * 0.95, f'n={count}', 
                        ha='center', fontsize=9, color='red')
        
        # 2. 小提琴图
        ax2 = axes[1]
        sns.violinplot(
            data=df_edu,
            x='学历要求',
            y='平均薪资(k)',
            ax=ax2,
            palette='muted',
            inner='box'
        )
        ax2.set_xlabel('学历要求', fontsize=12, fontweight='bold')
        ax2.set_ylabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax2.set_title('不同学历要求的薪资分布（小提琴图）', fontsize=14, fontweight='bold', pad=20)
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # 保存图片
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 学历薪资分析图已保存: {save_path}")
        
        plt.show()
        
        # 打印统计信息
        print("\n" + "="*60)
        print("学历与薪资统计分析")
        print("="*60)
        
        for education in education_order:
            edu_data = df_edu[df_edu['学历要求'] == education]['平均薪资(k)']
            if len(edu_data) > 0:
                print(f"\n{education}:")
                print(f"  样本数: {len(edu_data)}")
                print(f"  平均薪资: {edu_data.mean():.2f}k")
                print(f"  中位数: {edu_data.median():.2f}k")
                print(f"  标准差: {edu_data.std():.2f}k")
                print(f"  最高薪资: {edu_data.max():.2f}k")
    
    def plot_salary_by_company_type(self, save_path='../output/salary_by_company_type.png'):
        """
        按公司性质分析薪资
        """
        # 过滤掉公司性质为空的数据
        df_company = self.df_valid[self.df_valid['公司性质'].notna()].copy()
        
        # 统计各公司性质的数量，只保留样本数>10的
        company_counts = df_company['公司性质'].value_counts()
        valid_companies = company_counts[company_counts > 10].index
        df_company = df_company[df_company['公司性质'].isin(valid_companies)]
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 12))
        
        # 1. 箱线图
        ax1 = axes[0]
        sns.boxplot(
            data=df_company,
            x='公司性质',
            y='平均薪资(k)',
            ax=ax1,
            palette='Set3'
        )
        ax1.set_xlabel('公司性质', fontsize=12, fontweight='bold')
        ax1.set_ylabel('平均薪资 (k/月)', fontsize=12, fontweight='bold')
        ax1.set_title('不同公司性质的薪资分布', fontsize=14, fontweight='bold', pad=20)
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 添加样本数量
        for i, company in enumerate(df_company['公司性质'].unique()):
            count = len(df_company[df_company['公司性质'] == company])
            ax1.text(i, ax1.get_ylim()[1] * 0.95, f'n={count}', 
                    ha='center', fontsize=9, color='red')
        
        # 2. 平均薪资对比柱状图
        ax2 = axes[1]
        company_salary = df_company.groupby('公司性质')['平均薪资(k)'].agg(['mean', 'median', 'count'])
        company_salary = company_salary.sort_values('mean', ascending=False)
        
        x = np.arange(len(company_salary))
        width = 0.35
        
        bars1 = ax2.bar(x - width/2, company_salary['mean'], width, 
                       label='平均值', alpha=0.8, color='steelblue')
        bars2 = ax2.bar(x + width/2, company_salary['median'], width,
                       label='中位数', alpha=0.8, color='coral')
        
        ax2.set_xlabel('公司性质', fontsize=12, fontweight='bold')
        ax2.set_ylabel('薪资 (k/月)', fontsize=12, fontweight='bold')
        ax2.set_title('不同公司性质的平均薪资对比', fontsize=14, fontweight='bold', pad=20)
        ax2.set_xticks(x)
        ax2.set_xticklabels(company_salary.index, rotation=45, ha='right')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 在柱子上添加数值
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        
        # 保存图片
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 公司性质薪资分析图已保存: {save_path}")
        
        plt.show()
        
        # 打印统计信息
        print("\n" + "="*60)
        print("公司性质与薪资统计")
        print("="*60)
        print(company_salary.to_string())
    
    def comprehensive_analysis(self):
        """综合分析：学历溢价效应"""
        print("\n" + "="*60)
        print("学历溢价效应分析")
        print("="*60)
        
        df_edu = self.df_valid[self.df_valid['学历要求'].notna()].copy()
        
        # 计算学历溢价（相对于大专）
        education_salary = df_edu.groupby('学历要求')['平均薪资(k)'].mean().sort_values()
        
        if '大专' in education_salary.index:
            baseline = education_salary['大专']
            print(f"\n以大专薪资({baseline:.2f}k)为基准:")
            
            for edu, salary in education_salary.items():
                if edu != '大专':
                    premium = ((salary - baseline) / baseline) * 100
                    print(f"  {edu}: {salary:.2f}k (溢价 {premium:+.1f}%)")
        
        return education_salary


def main():
    """主函数：执行完整的薪资分析"""
    import os
    
    # 读取清洗后的数据
    df = pd.read_csv('../washdata/cleaned_jobs_latest.csv')
    
    # 创建输出目录
    os.makedirs('../output', exist_ok=True)
    
    # 初始化分析器
    analyzer = SalaryAnalyzer(df)
    
    # 1. 基础统计
    analyzer.basic_statistics()
    
    # 2. 薪资分布分析
    analyzer.plot_salary_distribution()
    
    # 3. 学历与薪资分析
    analyzer.plot_salary_by_education()
    
    # 4. 公司性质与薪资分析
    analyzer.plot_salary_by_company_type()
    
    # 5. 综合分析
    analyzer.comprehensive_analysis()
    
    print("\n" + "="*60)
    print("所有分析完成！")
    print("="*60)


if __name__ == "__main__":
    main()