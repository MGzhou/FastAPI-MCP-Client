from fastmcp import FastMCP
import json

# 创建MCP服务器
mcp = FastMCP("add-server")

# 我的工具:
@mcp.tool()
def add(a: str, b: str) -> str:
    """
    两个数相加
    Args:
        a(str): 加数1
        b(str): 加数2
    Return: 
        相加结果
        {"result": result}
    """
    print(f"输入参数：obj1:{a}，obj2:{b}")
    result = int(a) + int(b)
    return json.dumps({"result": result}, ensure_ascii=False)

if __name__ == "__main__":
    # mcp.run(transport="stdio")
    mcp.run(transport="sse", host="0.0.0.0", port=21112)