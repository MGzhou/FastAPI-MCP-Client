"""

"""

import io

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

# Create server
mcp = FastMCP("get image demo")

@mcp.tool
def get_one_iamge() -> Image:
    """
    获取一张图片
    """
    buffer = io.BytesIO()
    # 做一个模拟，读取一张图片
    with open(r"a.jpg", "rb") as f:
        buffer.write(f.read())
    return Image(data=buffer.getvalue(), format="jpeg")


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=21111)