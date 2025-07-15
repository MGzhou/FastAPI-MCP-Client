
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Author : MGzhou
@Desc   : fastapi app
'''

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
from pydantic import BaseModel
from typing import AsyncGenerator
from loguru import logger
import traceback

from client import MCPClient

# 设置日志，将其打印到文件中, 日志轮转，10MB轮转，最多保留5个
logger.add("logs/app.log", rotation="10 MB", retention=5)

with open("config.json", "r") as f:
    CONFIG = json.load(f)

# 定义请求模型
class ChatRequest(BaseModel):
    messages: list[dict]
    mcp_list: list

app = FastAPI()

@app.post("/chat")
async def chat_stream(chat_params: ChatRequest) -> StreamingResponse:
    """流式聊天接口"""
    client = MCPClient(CONFIG)
    connected = await client.connect_to_servers(chat_params.mcp_list)
    if not connected:
        logger.error("连接所有MCP服务均失败")
        raise HTTPException(status_code=500, detail="连接所有MCP服务均失败")

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in client.process_query_stream(chat_params.messages):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(repr(f"程序运行出错: {traceback.format_exc()}"))
            yield f"data: {json.dumps({'type':'error', 'data': str(e)})}\n\n"
        finally:
            await client.disconnect_all()
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)











