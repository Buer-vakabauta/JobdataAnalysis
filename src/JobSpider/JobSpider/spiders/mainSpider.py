import scrapy
import json
import hmac
import hashlib
import time
from urllib.parse import quote

class MainspiderSpider(scrapy.Spider):
    name = "mainSpider"
    allowed_domains = ["q.yingjiesheng.com", "youngapi.yingjiesheng.com"]
    
    # 密钥（JS代码中:Pi.HmacSHA256(a, "abfc8f9dcf8c3f3d8aa294ac5f2cf2cc7767e5592590f39c3f503271dd68562b").toString(Pi.enc.Hex)）
    SECRET_KEY = "abfc8f9dcf8c3f3d8aa294ac5f2cf2cc7767e5592590f39c3f503271dd68562b"
    
    def generate_sign(self, url_path):
        """
        生成sign签名
        使用HmacSHA256算法
        """
        signature = hmac.new(
            self.SECRET_KEY.encode('utf-8'),
            url_path.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def get_headers(self, sign):
        """获取请求头"""
        return {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "origin": "https://q.yingjiesheng.com",
            "referer": "https://q.yingjiesheng.com/",
            "sign": sign,
        }

    def start_requests(self):
        # Ii.filterDictDataUrl
        base_path = "/open/noauth/job/search"
        
        # 获取当前时间戳（秒）
        timestamp = int(time.time())
        
        # 根据JS代码，先构建基础URL：api_key和timestamp
        # var a = baseUrl + "?api_key=51job&timestamp=" + timestamp;
        url_path = f"{base_path}?api_key=51job&timestamp={timestamp}"
        
        # 其他参数
        extra_params = {
            "version": "2.3.5",
            "keyword": "嵌入式",
            "jobarea": "090200",
            "pagesize": 20,
            "pageno": 1,
            "searchType": 2,
            "scene": 7,
        }
        
        # 按照JS代码的逻辑拼接参数
        # i.push("&" + t + "=" + encodeURIComponent(e[t]));
        for key, value in extra_params.items():
            if value:
                # 处理字符串中的单引号（JS代码中有这个逻辑）
                if isinstance(value, str):
                    value = value.replace("'", "")
                # encodeURIComponent对应quote
                encoded_value = quote(str(value), safe='')
                url_path += f"&{key}={encoded_value}"
        
        # 生成签名
        sign = self.generate_sign(url_path)
        
        # 完整URL
        full_url = "https://youngapi.yingjiesheng.com" + url_path
        
        self.logger.info(f'请求URL: {full_url}')
        self.logger.info(f'签名字符串: {url_path}')
        self.logger.info(f'生成的sign: {sign}')
        
        yield scrapy.Request(
            url=full_url,
            method="GET",
            headers=self.get_headers(sign),
            callback=self.parse,
            errback=self.errback_httpbin,
            dont_filter=True,
            meta={
                'extra_params': extra_params,
                'timestamp': timestamp
            }
        )
    
    def errback_httpbin(self, failure):
        """错误处理"""
        self.logger.error(f'请求失败: {failure}')
        # 如果有response，打印响应内容
        if hasattr(failure.value, 'response'):
            response = failure.value.response
            self.logger.error(f'响应状态: {response.status}')
            self.logger.error(f'响应内容: {response.text[:500]}')

    def parse(self, response):
        """解析响应"""
        self.logger.info(f'响应状态码: {response.status}')
        
        if response.status == 400:
            self.logger.error(f'400错误 - 响应内容: {response.text}')
            return
        
        try:
            data = json.loads(response.text)
            self.logger.info(f'API响应: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}')
            
            # 检查API返回的状态
            if 'code' in data:
                if data['code'] != 0 and data['code'] != 200:
                    self.logger.error(f"API返回错误码: {data.get('code')}, 消息: {data.get('message', '未知错误')}")
                    return
            
            # 解析职位列表
            if 'resultbody' in data:
                job_list=data['resultbody']['searchData']['joblist']['items']
                for job in job_list:
                    job_property=json.loads(job['property'])
                    yield {
                        
                        '职位名称': job_property.get('jobTitle'),
                        '公司名称': job_property.get('companyName'),
                        '经纬度': [job.get('lat'), job.get('lon')],
                        '薪资': job.get('providesalary'),
                        '城市': job.get('jobarea'),
                        '学历要求': job.get('degree'),    
                        '经验要求': job.get('workyear'),
                        '公司性质': job.get('cotype'),
                        '行业': job.get('companyIndustryType1Str'),
                        #'企业标签': job.get('sesameLabelList'),
                        '发布时间': job.get('issuedate')
                    }
                
                # 翻页逻辑
                extra_params = response.meta.get('extra_params')
                current_page = extra_params.get('pageno', 1)
                
                # 如果当前页有数据，继续请求下一页（限制爬取页数）
                if len(job_list) > 0 and current_page < 3:  # 限制爬取3页
                    next_page = current_page + 1
                    self.logger.info(f'等待中...3s')
                    time.sleep(3)  # 遵守下载延迟
                    self.logger.info(f'准备爬取第 {next_page} 页...')
                    # 更新参数
                    extra_params['pageno'] = next_page
                    timestamp = int(time.time())
                    
                    # 重新构建URL和签名
                    base_path = "/open/noauth/job/search"
                    url_path = f"{base_path}?api_key=51job&timestamp={timestamp}"
                    
                    for key, value in extra_params.items():
                        if value:
                            if isinstance(value, str):
                                value = value.replace("'", "")
                            encoded_value = quote(str(value), safe='')
                            url_path += f"&{key}={encoded_value}"
                    
                    sign = self.generate_sign(url_path)
                    full_url = "https://youngapi.yingjiesheng.com" + url_path
                    
                    yield scrapy.Request(
                        url=full_url,
                        method="GET",
                        headers=self.get_headers(sign),
                        callback=self.parse,
                        dont_filter=True,
                        meta={
                            'extra_params': extra_params,
                            'timestamp': timestamp
                        }
                    )
            else:
                self.logger.warning(f'响应中没有data字段: {data}')
                
        except json.JSONDecodeError as e:
            self.logger.error(f'JSON解析失败: {e}')
            self.logger.error(f'响应内容: {response.text[:1000]}')