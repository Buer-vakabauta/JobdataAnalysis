# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

import json
import os
from datetime import datetime

class JobspiderPipeline:
    """保存为Json"""
    def open_spider(self, spider):
        """爬虫开始时打开文件"""
        # 项目根目录（src/JobSpider/JobSpider/）
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        # data目录路径
        data_dir = os.path.join(project_root, 'data')
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 添加时间戳到文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'jobs_data_{timestamp}.json'
        
        self.file_path = os.path.join(data_dir, file_name)
        self.file = open(self.file_path, 'w', encoding='utf-8')
        self.items = []
        
        spider.logger.info(f'数据将保存到: {self.file_path}')
    
    def close_spider(self, spider):
        """爬虫结束时关闭文件"""
        json.dump(self.items, self.file, ensure_ascii=False, indent=4)
        self.file.close()
        spider.logger.info(f'数据已保存到 {self.file_path}，共 {len(self.items)} 条记录')

    def process_item(self, item, spider):
        """处理每个item"""
        self.items.append(dict(item))
        return item
    
    
