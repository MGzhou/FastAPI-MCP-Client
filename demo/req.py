import requests
import json

def stream_chat(url:str, data:dict):
    """请求流式聊天接口并处理返回的事件流"""
    
    headers = {"Content-Type": "application/json"}
    
    try:
        with requests.post(url, json=data, headers=headers, stream=True) as response:
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                print(response.text)
                return

            print("开始接收流式响应...")
            for line in response.iter_lines():
                if line:  # 过滤掉保持连接的空行
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        event_data = decoded_line[6:]  # 去掉"data: "前缀
                        # 处理结束标记
                        if event_data == "[DONE]":
                            print("\n\n--------------\n流式传输结束")
                            break
                        
                        try:
                            data = json.loads(event_data)
                            handle_event(data)
                        except json.JSONDecodeError:
                            print(f"无法解析的JSON数据: {event_data}")

    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")

def handle_event(data: dict):
    """处理不同类型的事件数据"""
    if "type" not in data:
        print(f"未知事件类型: {data}")
        return
    if data["type"] == "content":
        # 处理普通消息
        print(f"{data['data']}", end="", flush=True)
    elif data["type"] == "tool":
        # 处理工具调用开始
        print(f"\n[调用工具: {data['data']}]")
    elif data["type"] == "error":
        # 处理错误
        print(f"\n[错误: {data['data']}]")
    elif data["type"] == "warning":
        print(f"\n[警告: {data['data']}]")

if __name__ == "__main__":
    url = "http://127.0.0.1:8003/chat"
    mcp_list = ["http://127.0.0.1:21113/sse"]
    query = "查询伦敦现在是多少点"
    data = {
        "messages": [{"role":"user", "content":query}],
        "mcp_list":mcp_list
    }
    stream_chat(url, data)


