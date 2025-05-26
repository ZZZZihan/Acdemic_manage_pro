import requests
import time
import logging

logger = logging.getLogger(__name__)

def check_deepseek_connection(timeout=10):
    """
    检查到DeepSeek API的网络连接
    
    Args:
        timeout: 超时时间（秒）
        
    Returns:
        tuple: (是否连接成功, 响应时间毫秒, 错误信息)
    """
    try:
        start_time = time.time()
        
        # 尝试连接到DeepSeek API
        response = requests.get(
            "https://api.deepseek.com",
            timeout=timeout,
            headers={"User-Agent": "Lab-Knowledge-Management/1.0"}
        )
        
        end_time = time.time()
        response_time = int((end_time - start_time) * 1000)  # 转换为毫秒
        
        if response.status_code in [200, 404, 405]:  # 这些状态码表示连接成功
            return True, response_time, None
        else:
            return False, response_time, f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, timeout * 1000, "连接超时"
    except requests.exceptions.ConnectionError as e:
        return False, 0, f"连接错误: {str(e)}"
    except Exception as e:
        return False, 0, f"未知错误: {str(e)}"

def get_network_status():
    """
    获取网络状态信息
    
    Returns:
        dict: 网络状态信息
    """
    deepseek_ok, deepseek_time, deepseek_error = check_deepseek_connection()
    
    status = {
        "deepseek": {
            "connected": deepseek_ok,
            "response_time_ms": deepseek_time,
            "error": deepseek_error
        },
        "recommendations": []
    }
    
    # 根据网络状态提供建议
    if not deepseek_ok:
        if "超时" in str(deepseek_error):
            status["recommendations"].append("网络连接超时，建议检查网络连接或稍后重试")
        elif "连接错误" in str(deepseek_error):
            status["recommendations"].append("无法连接到DeepSeek服务器，请检查网络设置")
        else:
            status["recommendations"].append("DeepSeek API服务异常，建议稍后重试")
    elif deepseek_time > 5000:  # 超过5秒
        status["recommendations"].append("网络延迟较高，API响应可能较慢")
    elif deepseek_time > 2000:  # 超过2秒
        status["recommendations"].append("网络延迟中等，建议耐心等待API响应")
    else:
        status["recommendations"].append("网络连接良好")
    
    return status

if __name__ == "__main__":
    # 测试网络连接
    status = get_network_status()
    print("网络状态检查结果:")
    print(f"DeepSeek连接: {'✓' if status['deepseek']['connected'] else '✗'}")
    print(f"响应时间: {status['deepseek']['response_time_ms']}ms")
    if status['deepseek']['error']:
        print(f"错误信息: {status['deepseek']['error']}")
    print("建议:")
    for rec in status['recommendations']:
        print(f"- {rec}") 