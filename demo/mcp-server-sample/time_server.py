from fastmcp import FastMCP
import json
import pytz
from datetime import datetime


# 创建MCP服务器
mcp = FastMCP("time-server")

# 我的工具:
@mcp.tool()
def get_time(time_zone: str) -> dict:
    """
    获取当前时间
    Args:
        time_zone(str): 标准时区标识符，例如上海时区为 'Asia/Shanghai'
    Return: 
        当前时间
        {"time": time}
    """
    print(f"输入参数：time_zone:{time_zone}")
    # 根据时区获取时间
    tz = pytz.timezone(time_zone)
    current_time = datetime.now(tz)
    t = current_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")
    # return json.dumps({"time": t}, ensure_ascii=False)
    return {"time": t}



if __name__ == "__main__":
    # mcp.run(transport="stdio")
    mcp.run(transport="sse", host="127.0.0.1", port=21113)