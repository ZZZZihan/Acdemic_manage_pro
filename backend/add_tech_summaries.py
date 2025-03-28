import requests
import json
import time
from datetime import datetime
from app import create_app, db
from app.models import TechSummary, User
from app.utils.crawler import crawl_url
from app.utils.llm_api import llm_service

# 嵌入式相关的技术文章URL列表
embedded_articles = [
    {
        "url": "https://www.embedded.com/embedded-systems-design-software-and-programming/",
        "title": "嵌入式系统设计与软件编程基础",
        "summary_type": "经验",
        "tags": "嵌入式系统,软件设计,编程基础"
    },
    {
        "url": "https://www.embedded.com/real-time-operating-systems/",
        "title": "实时操作系统在嵌入式系统中的应用",
        "summary_type": "经验",
        "tags": "RTOS,实时系统,操作系统"
    },
    {
        "url": "https://www.embedded.com/embedded-systems-hardware-design/",
        "title": "嵌入式系统硬件设计实践",
        "summary_type": "经验",
        "tags": "硬件设计,电路设计,PCB"
    },
    {
        "url": "https://www.embedded.com/embedded-systems-software-testing/",
        "title": "嵌入式系统软件测试方法",
        "summary_type": "经验",
        "tags": "软件测试,单元测试,集成测试"
    },
    {
        "url": "https://www.embedded.com/embedded-systems-security/",
        "title": "嵌入式系统安全防护技术",
        "summary_type": "经验",
        "tags": "安全防护,加密,认证"
    },
    {
        "url": "https://www.embedded.com/embedded-systems-communication-protocols/",
        "title": "嵌入式系统通信协议详解",
        "summary_type": "经验",
        "tags": "通信协议,I2C,SPI,UART"
    },
    {
        "url": "https://www.embedded.com/embedded-systems-power-management/",
        "title": "嵌入式系统电源管理技术",
        "summary_type": "经验",
        "tags": "电源管理,低功耗,节能"
    },
    {
        "url": "https://www.embedded.com/embedded-systems-debugging-techniques/",
        "title": "嵌入式系统调试技巧",
        "summary_type": "经验",
        "tags": "调试,故障排除,性能优化"
    },
    {
        "url": "https://www.embedded.com/embedded-systems-iot/",
        "title": "物联网中的嵌入式系统开发",
        "summary_type": "经验",
        "tags": "物联网,IoT,无线通信"
    },
    {
        "url": "https://www.embedded.com/embedded-systems-ai/",
        "title": "嵌入式系统中的AI应用",
        "summary_type": "经验",
        "tags": "人工智能,机器学习,边缘计算"
    }
]

def add_tech_summaries():
    app = create_app()
    with app.app_context():
        # 获取管理员用户
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("未找到管理员用户，请先创建管理员账户")
            return

        for article in embedded_articles:
            try:
                print(f"正在处理文章: {article['title']}")
                
                # 爬取文章内容
                crawl_result = crawl_url(article['url'])
                if not crawl_result['success']:
                    print(f"爬取失败: {crawl_result['message']}")
                    continue
                
                content = crawl_result['data']['content']
                
                # 使用DeepSeek进行总结
                summary_result = llm_service.summarize_content(
                    content=content,
                    url=article['url'],
                    provider='deepseek'
                )
                
                if not summary_result['success']:
                    print(f"总结失败: {summary_result['message']}")
                    continue
                
                # 创建技术总结
                tech_summary = TechSummary(
                    title=article['title'],
                    content=summary_result['data']['summary'],
                    summary_type=article['summary_type'],
                    tags=article['tags'],
                    user_id=admin.id,
                    source_url=article['url']
                )
                
                db.session.add(tech_summary)
                db.session.commit()
                
                print(f"成功添加技术总结: {article['title']}")
                
                # 避免请求过于频繁
                time.sleep(2)
                
            except Exception as e:
                print(f"处理文章时出错: {str(e)}")
                db.session.rollback()
                continue

if __name__ == '__main__':
    add_tech_summaries() 