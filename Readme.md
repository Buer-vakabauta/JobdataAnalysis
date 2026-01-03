# 前程无忧招聘数据分析

## 0.目录结构

```
├─app 存放应用
│  │  area_stat.ipynb    地区数据分析
│  │  area_stat.py		 地区数据分析api
│  │  data_wash.ipynb    数据清洗
│  │  data_wash.py       数据清洗api
│  │  salary_stat.ipynb  薪资分析
│  │  salary_stat.py     薪资分析api
│  │  统计维度分析.md      统计维度建议
│          
├─data 存放爬取的原始数据
│          
├─JobSpider 爬虫文件
│  │  data_example.txt 服务器返回的数据示例
│  │  parse_data_test.ipynb 解析返回数据
│  │  run.txt 启动爬虫的命令(需在当前目录)
│  │  scrapy.cfg   
│  └─JobSpider 爬虫主文件
│      │  items.py
│      │  middlewares.py
│      │  pipelines.py 保存爬取数据
│      │  settings.py 设置
│      │  __init__.py
│      │  
│      ├─spiders 爬虫应用
│      │  │  mainSpider.py 主应用(包含爬虫的相关配置)
│      │  │  __init__.py    
│              
├─output #数据分析生成的结果(图片/网页)
│      
└─washdata 清洗后的数据(latest是最近清洗的数据,.txt文档是清洗的日志文件)
```



## 1. 数据获取

> 使用Scrapy爬虫框架,爬取前程无忧,应届生搜索界面的数据信息进行数据分析,数据以大学生应聘为主

**可配置的参数**:

```python
#JobSpider\JobSpider\spiders\mainSpider.py
key_words = "嵌入式"#搜索的关键词
job_area = "090200"#默认成都090200
page_no = 1#爬取的起始页
page_count=3#要爬取的页数
```

**爬取字段示例**:

```json
{
        "公司标签": [
            "旗下品牌同行前5%",
            "专精特新企业",
            "拥有节能环保技术",
            "港澳台投资企业",
        ],
        "职位名称": "嵌入式软件开发工程师",
        "公司名称": "深圳市芯智科技",
        "经纬度": [
            "22.551758",
            "113.951318"
        ],
        "jobid": "168576286",
        "薪资": "1-2万·13薪",
        "城市": "深圳-南山区",
        "学历要求": "本科",
        "经验要求": "1年及以上",
        "公司性质": "外资（非欧美）",
        "行业": "电子技术/半导体/集成电路",
        "发布时间": "2025-12-30 15:49:25"
    }
```
**数据说明**:

实验中爬取数据均来自**成都/重庆/深圳**三地(不排除搜索引擎中极少量来自其他地区的数据)关于**嵌入式/物联网**的招聘情况

## 2.数据清洗

### **2.1 清洗规则:**

1. 去除重复数据:

   基于jobid去重,取先出现的数据

2. 清洗薪资数据:

   - 将薪资数据归一化为k/月

   - 使用归一化薪资添加新字段(下限/上限/平均值)

   - 支持格式:

     - 4-6千

     - 1.2-2万
     - 8千-1.6万
     - 10-15万/年
     - 8千-1.6万·14薪
     - 15k-20k
     - 50/天
     - 200-300/天
     - 面议

3. 处理发布时间:

   按传入的时间段筛选数据(基于发布时间字段)

4. 处理经纬度数据
	- 调用高德地图api,通过经纬度或公司名称和城市字段查询详细位置
	- 添加字段:省份/区域/详细地址

5. 归一化城市字段:
	
   - 对4中的**详细地址**进行拆分
   
   - 将原本不规范的城市字段归一化为:`xx市-xx区`
   
   - 便于后续地区分析
   
6. 处理学历要求:

  讲不同学历映射为**学历等级**,映射如下:

  ```json
  {
      '不限': 0,
      '初中': 1,
      '中专': 2,
      '高中': 2,
      '大专': 3,
      '本科': 4,
      '硕士': 5,
  }
  ```

7. 其他

  进行简单去空,填空处理

  并移出缺少信息过多的数据

### **2.2 清洗脚本**

提供脚本对数据进行一键清洗:

脚本参数设置:

```python
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
```

也可以自行调用文件中的有关函数针对性的清理(文件中提供了读取和保存文件的接口)

## 3.数据分析

对薪资和位置信息这两个维度进行了重点分析

详见:`app\area_stat.ipynb`和`app\data_wash.ipynb`文件中的有关说明和演示