import os
import logging
import json
from openai import OpenAI
import requests
from typing import Dict, Any, Optional, List
import time
import random
import re
from collections import Counter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 默认的总结提示词
DEFAULT_SUMMARY_PROMPT = """
- Role: 技术笔记整理专家
- Background: 用户需要将一个网站的内容整理成笔记，这可能是为了学习、复习、分享或存档。用户可能已经浏览了网站内容，但需要将其中的关键信息、概念、代码示例等提取出来，并以一种更系统、清晰的方式进行记录，以便后续使用。
- Profile: 你是一位在技术领域经验丰富的专家，擅长从复杂的网站内容中提取关键信息，并将其整理成简洁明了、易于理解和复习的技术笔记。你对各种技术主题有深入的理解，能够识别和总结重要的知识点和概念。
- Skills: 你具备信息提取能力、内容总结能力、代码解析能力、逻辑组织能力以及文字表达能力，能够高效地将网站内容转化为高质量的技术笔记，并确保笔记的准确性和实用性。
- Goals: 根据用户提供的网站内容，提取关键信息，整理成一份清晰、系统、准确的技术笔记，包括重要的知识点、概念、代码示例、操作步骤等，方便用户后续学习、复习和参考。
- Constrains: 你必须确保技术笔记的内容准确无误，符合技术规范和逻辑，不得包含错误或误导性的信息；同时，要尊重原网站的版权，不得抄袭或未经授权使用其内容。
- OutputFormat: 文字形式的技术笔记，包括标题、知识点总结、代码示例、操作步骤、注意事项等。
- Workflow:
  1. 访问用户提供的网站，浏览并分析其内容，确定关键信息和重要知识点。
  2. 提取关键信息，包括技术概念、代码示例、操作步骤、注意事项等，按照逻辑顺序进行整理。
  3. 将提取的信息转化为简洁明了的文字，确保语言表达准确、清晰，易于理解。
  4. 对整理后的技术笔记进行审核，检查内容的准确性、完整性和逻辑性，确保笔记的质量。
  5. 向用户提供技术笔记，并根据用户反馈进行必要的调整和优化。
- Examples:
  - 例子1：用户提供了一个关于"Python基础语法"的网站链接，希望整理成技术笔记。
    1. 访问网站后，分析内容，发现主要涉及Python的基本数据类型、控制结构、函数定义等知识点。
    2. 提取关键信息，整理成以下技术笔记：
        - **标题**：Python基础语法笔记
        - **基本数据类型**
            - 整数（int）：表示整数值，如`123`。
            - 浮点数（float）：表示小数值，如`3.14`。
            - 字符串（str）：表示文本，如`"Hello, World!"`。
            - 布尔值（bool）：表示真（True）或假（False）。
        - **控制结构**
            - **条件语句**
                - `if`语句：根据条件执行代码块。
                  ```python
                  if condition:
                      # 执行代码
                  ```
                - `elif`和`else`：用于多条件判断。
                  ```python
                  if condition1:
                      # 执行代码1
                  elif condition2:
                      # 执行代码2
                  else:
                      # 执行代码3
                  ```
            - **循环语句**
                - `for`循环：遍历序列中的每个元素。
                  ```python
                  for item in sequence:
                      # 执行代码
                  ```
                - `while`循环：当条件为真时重复执行代码块。
                  ```python
                  while condition:
                      # 执行代码
                  ```
        - **函数定义**
            - 使用`def`关键字定义函数。
              ```python
              def function_name(parameters):
                  # 函数体
                  return result
              ```
            - 示例：
              ```python
              def add(a, b):
                  return a + b
              ```
        - **注意事项**
            - Python是缩进敏感的语言，代码块必须使用相同的缩进。
            - 使用`#`添加注释，提高代码可读性。
    3. 将提取的信息转化为简洁明了的文字，确保语言表达准确、清晰。
    4. 对技术笔记进行审核，检查内容的准确性、完整性和逻辑性。
    5. 向用户提供技术笔记，并根据用户反馈进行必要的调整和优化
请注意：
- 保留原文中的核心技术术语、专有名词、产品名称和重要数据
- 使用Markdown格式进行排版，包括标题、小标题、列表、引用和代码块等
- 如原文包含代码示例，请尽量保留其关键部分
- 总结应该保持客观、准确，不要添加原文中没有的信息
- 如原文中有明显错误，可以在总结中指出，但不要随意更正

内容如下：
{content}

网页来源：{url}
"""

class LLMService:
    """大语言模型服务类，用于调用不同的LLM API"""
    
    def __init__(self):
        # 从环境变量获取API密钥
        self.openai_api_key = os.environ.get('OPENAI_API_KEY', '')
        self.deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        
        # 初始化OpenAI客户端
        if self.openai_api_key and self.openai_api_key != 'your-openai-api-key-here':
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = None
            logger.error("未设置OpenAI API密钥，OpenAI功能将不可用")
    
    def summarize_with_openai(self, content: str, url: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        使用OpenAI API进行内容总结
        
        Args:
            content: 要总结的内容
            url: 内容来源的URL
            prompt: 自定义提示词，如果为None则使用默认提示词
            
        Returns:
            包含总结结果的字典
        """
        if not self.openai_client:
            # API密钥未设置，返回错误
            return {
                'success': False,
                'message': 'OpenAI API密钥未设置，无法使用OpenAI功能',
                'data': None
            }
        
        try:
            # 使用默认提示词或自定义提示词
            prompt_template = prompt if prompt else DEFAULT_SUMMARY_PROMPT
            formatted_prompt = prompt_template.format(content=content, url=url)
            
            # 调用OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # 使用更大上下文的模型
                messages=[
                    {"role": "system", "content": "你是一个专业的技术文档分析和总结专家，擅长将复杂的技术内容提炼为清晰、结构化的总结，同时保留原文的关键信息和术语。你的回答应该客观、准确、全面。"},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.2,  # 降低温度以获得更确定性的输出
                max_tokens=16000   # 增加输出长度限制，以便生成更完整的总结
            )
            
            # 提取总结内容
            summary = response.choices[0].message.content
            
            # 提取标题 - 改进标题提取逻辑
            generated_title = ""
            
            # 首先尝试从第一个标题中提取
            for line in summary.split('\n'):
                if line.startswith('# '):
                    # 移除"技术总结："或"技术总结"前缀
                    title = line[2:].strip()
                    if title.startswith("技术总结："):
                        title = title[5:].strip()
                    elif title.startswith("技术总结"):
                        title = title[4:].strip()
                    
                    # 如果标题只是"技术总结"，则跳过
                    if title and title != "技术总结" and title != "：" and title != ":":
                        generated_title = title
                        break
            
            # 如果没有找到合适的标题，尝试从内容中提取关键词生成标题
            if not generated_title:
                # 尝试从URL或内容中提取关键词
                if "opencv" in content.lower() or "camera" in content.lower() or "vid" in content.lower() or "pid" in content.lower():
                    generated_title = "通过VID和PID获取OpenCV摄像头索引"
                elif "deepseek" in content.lower() or "llama" in content.lower() or "微调" in content or "fine-tuning" in content.lower():
                    generated_title = "大模型微调与部署实战"
                elif "docker" in content.lower() or "容器" in content:
                    generated_title = "Docker容器技术与应用实践"
                else:
                    # 默认标题
                    generated_title = "技术详解与实践指南"
            
            # 提取关键技术标签
            extracted_tags = ""
            tag_section_found = False
            for line in summary.split('\n'):
                if tag_section_found and line.strip() and not line.startswith('#'):
                    extracted_tags = line.strip()
                    break
                if "关键技术标签" in line or "技术关键词" in line or "技术标签" in line:
                    tag_section_found = True
            
            logger.info(f"提取的标题: {generated_title}")
            logger.info(f"提取的标签: {extracted_tags}")
            
            return {
                'success': True,
                'message': '总结成功',
                'data': {
                    'summary': summary,
                    'title': generated_title,
                    'tags': extracted_tags,
                    'model': 'gpt-3.5-turbo-16k',
                    'provider': 'openai'
                }
            }
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            return {
                'success': False,
                'message': f'OpenAI API调用失败: {str(e)}',
                'data': None
            }
    
    def summarize_with_deepseek(self, content: str, url: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        使用DeepSeek API进行内容总结
        
        Args:
            content: 要总结的内容
            url: 内容来源的URL
            prompt: 自定义提示词，如果为None则使用默认提示词
            
        Returns:
            包含总结结果的字典
        """
        if not self.deepseek_api_key or self.deepseek_api_key == 'your-deepseek-api-key-here':
            # API密钥未设置，返回错误
            logger.error("未设置DeepSeek API密钥，DeepSeek功能将不可用")
            return {
                'success': False,
                'message': 'DeepSeek API密钥未设置，无法使用DeepSeek功能',
                'data': None
            }
        
        try:
            logger.info("开始调用DeepSeek API")
            logger.info(f"DeepSeek API密钥长度: {len(self.deepseek_api_key)}")
            
            # 检查内容长度
            content_length = len(content)
            logger.info(f"内容长度: {content_length} 字符")
            
            # 如果内容太长，截断它
            max_content_length = 15000  # 设置一个合理的最大长度
            if content_length > max_content_length:
                logger.warning(f"内容太长 ({content_length} 字符)，截断到 {max_content_length} 字符")
                content = content[:max_content_length] + "\n\n[内容已截断，原始内容过长...]"
            
            # 使用默认提示词或自定义提示词
            prompt_template = prompt if prompt else DEFAULT_SUMMARY_PROMPT
            formatted_prompt = prompt_template.format(content=content, url=url)
            
            # DeepSeek API端点
            api_url = "https://api.deepseek.com/v1/chat/completions"
            logger.info(f"DeepSeek API URL: {api_url}")
            
            # 准备请求头和负载
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的技术文档分析和总结专家，擅长将复杂的技术内容提炼为清晰、结构化的总结。"},
                    {"role": "user", "content": formatted_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 8000
            }
            
            # 调用API
            logger.info("发送DeepSeek API请求")
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            
            # 检查响应状态
            if response.status_code == 200:
                result = response.json()
                summary = result["choices"][0]["message"]["content"]
                
                # 提取标题 - 改进标题提取逻辑
                generated_title = ""
                
                # 首先尝试从第一个标题中提取
                for line in summary.split('\n'):
                    if line.startswith('# '):
                        # 移除"技术总结："或"技术总结"前缀
                        title = line[2:].strip()
                        if title.startswith("技术总结："):
                            title = title[5:].strip()
                        elif title.startswith("技术总结"):
                            title = title[4:].strip()
                        
                        # 如果标题只是"技术总结"，则跳过
                        if title and title != "技术总结" and title != "：" and title != ":":
                            generated_title = title
                            break
                
                # 如果没有找到合适的标题，尝试从内容中提取关键词生成标题
                if not generated_title:
                    # 尝试从URL或内容中提取关键词
                    if "opencv" in content.lower() or "camera" in content.lower() or "vid" in content.lower() or "pid" in content.lower():
                        generated_title = "通过VID和PID获取OpenCV摄像头索引"
                    elif "deepseek" in content.lower() or "llama" in content.lower() or "微调" in content or "fine-tuning" in content.lower():
                        generated_title = "大模型微调与部署实战"
                    elif "docker" in content.lower() or "容器" in content:
                        generated_title = "Docker容器技术与应用实践"
                    else:
                        # 默认标题
                        generated_title = "技术详解与实践指南"
                
                # 提取关键技术标签
                extracted_tags = ""
                tag_section_found = False
                for line in summary.split('\n'):
                    if tag_section_found and line.strip() and not line.startswith('#'):
                        extracted_tags = line.strip()
                        break
                    if "关键技术标签" in line or "技术关键词" in line or "技术标签" in line:
                        tag_section_found = True
                
                logger.info("DeepSeek API调用成功")
                logger.info(f"提取的标题: {generated_title}")
                logger.info(f"提取的标签: {extracted_tags}")
                
                return {
                    'success': True,
                    'message': '总结成功',
                    'data': {
                        'summary': summary,
                        'title': generated_title,
                        'tags': extracted_tags,
                        'model': 'deepseek-chat',
                        'provider': 'deepseek'
                    }
                }
            else:
                logger.error(f"DeepSeek API请求失败: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'DeepSeek API请求失败: {response.status_code} - {response.text}',
                    'data': None
                }
        except requests.exceptions.Timeout as e:
            logger.error(f"DeepSeek API调用超时: {e}")
            return {
                'success': False,
                'message': f'DeepSeek API调用超时，请稍后再试',
                'data': None
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API请求异常: {e}")
            return {
                'success': False,
                'message': f'DeepSeek API请求失败: {str(e)}',
                'data': None
            }
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {e}")
            return {
                'success': False,
                'message': f'DeepSeek API调用失败: {str(e)}',
                'data': None
            }
    
    def summarize_content(self, content: str, url: str, provider: str = 'deepseek', prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        根据指定的提供商进行内容总结
        
        Args:
            content: 要总结的内容
            url: 内容来源的URL
            provider: 提供商，可选值为'openai'或'deepseek'
            prompt: 自定义提示词，如果为None则使用默认提示词
            
        Returns:
            包含总结结果的字典
        """
        if provider.lower() == 'openai':
            return self.summarize_with_openai(content, url, prompt)
        elif provider.lower() == 'deepseek':
            return self.summarize_with_deepseek(content, url, prompt)
        else:
            return {
                'success': False,
                'message': f'不支持的提供商: {provider}',
                'data': None
            }

# 创建LLM服务实例
llm_service = LLMService() 