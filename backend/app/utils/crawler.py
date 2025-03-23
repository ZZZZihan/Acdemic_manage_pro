import requests
from bs4 import BeautifulSoup
import logging
import re
from urllib.parse import urlparse

def extract_main_content(html, url):
    """
    从HTML中提取主要内容，尽量保留原始结构
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除不需要的元素，但保留更多内容
        for tag in soup(['script', 'style', 'iframe', 'form']):
            tag.decompose()
        
        # 尝试找到主要内容区域
        main_content = None
        
        # 常见的主要内容容器ID和类名
        content_selectors = [
            'article', 'main', '.content', '#content', '.post', '.article', 
            '.post-content', '.entry-content', '.main-content', '#main-content',
            '.blog-post', '.document', '.documentation', '.page-content', '.container'
        ]
        
        # 尝试找到主要内容区域
        for selector in content_selectors:
            if selector.startswith('.'):
                elements = soup.select(selector)
            elif selector.startswith('#'):
                element = soup.select_one(selector)
                elements = [element] if element else []
            else:
                elements = soup.find_all(selector)
            
            if elements:
                # 选择最长的内容区域
                main_content = max(elements, key=lambda x: len(str(x)))
                break
        
        # 如果没有找到主要内容区域，使用body
        if not main_content:
            main_content = soup.body
        
        # 如果仍然没有找到内容，使用整个HTML
        if not main_content:
            main_content = soup
        
        # 保留更多的格式和结构
        # 处理标题
        for heading in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_level = int(heading.name[1])
            heading_text = heading.get_text().strip()
            heading.replace_with(f'\n{"#" * heading_level} {heading_text}\n\n')
        
        # 处理段落
        for p in main_content.find_all('p'):
            p_text = p.get_text().strip()
            p.replace_with(f'{p_text}\n\n')
        
        # 处理列表
        for ul in main_content.find_all('ul'):
            list_html = '\n'
            for li in ul.find_all('li'):
                list_html += f'- {li.get_text().strip()}\n'
            ul.replace_with(f'{list_html}\n')
        
        for ol in main_content.find_all('ol'):
            list_html = '\n'
            for i, li in enumerate(ol.find_all('li'), 1):
                list_html += f'{i}. {li.get_text().strip()}\n'
            ol.replace_with(f'{list_html}\n')
        
        # 处理代码块
        for code in main_content.find_all('pre'):
            code_text = code.get_text().strip()
            code.replace_with(f'\n```\n{code_text}\n```\n\n')
        
        for code in main_content.find_all('code'):
            code_text = code.get_text().strip()
            code.replace_with(f'`{code_text}`')
        
        # 处理表格 - 简化为文本
        for table in main_content.find_all('table'):
            table_text = '表格内容：\n'
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                row_text = ' | '.join([cell.get_text().strip() for cell in cells])
                table_text += f'{row_text}\n'
            table.replace_with(f'\n{table_text}\n')
        
        # 处理引用
        for blockquote in main_content.find_all('blockquote'):
            quote_text = blockquote.get_text().strip().replace('\n', '\n> ')
            blockquote.replace_with(f'\n> {quote_text}\n\n')
        
        # 处理链接
        for a in main_content.find_all('a'):
            link_text = a.get_text().strip()
            link_url = a.get('href', '')
            if link_url and link_text:
                # 转换为相对URL
                if link_url.startswith('/'):
                    parsed_source = urlparse(url)
                    link_url = f"{parsed_source.scheme}://{parsed_source.netloc}{link_url}"
                a.replace_with(f'[{link_text}]({link_url})')
        
        # 处理图片
        for img in main_content.find_all('img'):
            alt_text = img.get('alt', '图片')
            img_url = img.get('src', '')
            if img_url:
                # 转换为绝对URL
                if img_url.startswith('/'):
                    parsed_source = urlparse(url)
                    img_url = f"{parsed_source.scheme}://{parsed_source.netloc}{img_url}"
                img.replace_with(f'\n![{alt_text}]({img_url})\n')
        
        # 提取文本
        text = main_content.get_text(separator='\n')
        
        # 清理文本，但保留更多格式
        text = re.sub(r'\n{3,}', '\n\n', text)  # 将多个换行减少为最多两个
        text = text.strip()
        
        # 提取标题
        title = soup.title.string if soup.title else ''
        title = title.strip() if title else ''
        
        return {
            'title': title,
            'content': text,
            'url': url
        }
    except Exception as e:
        logging.error(f"提取内容时出错: {e}")
        return {
            'title': '',
            'content': f"提取内容时出错: {str(e)}",
            'url': url
        }

def crawl_url(url):
    """
    爬取指定URL的内容
    """
    try:
        # 验证URL格式
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {
                'success': False,
                'message': '无效的URL格式',
                'data': None
            }
        
        # 设置请求头，模拟浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 如果请求失败，抛出异常
        
        # 检测编码
        response.encoding = response.apparent_encoding
        
        # 提取内容
        data = extract_main_content(response.text, url)
        
        return {
            'success': True,
            'message': '爬取成功',
            'data': data
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"请求错误: {e}")
        return {
            'success': False,
            'message': f'请求错误: {str(e)}',
            'data': None
        }
    except Exception as e:
        logging.error(f"爬取内容时出错: {e}")
        return {
            'success': False,
            'message': f'爬取内容时出错: {str(e)}',
            'data': None
        } 