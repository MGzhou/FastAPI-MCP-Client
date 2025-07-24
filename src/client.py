#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Author : MGzhou
@Desc   : mcp client
'''

from fastapi import HTTPException
import json
from fastmcp import Client
from fastmcp.client.transports import SSETransport
from openai import AsyncOpenAI
import time
from typing import AsyncGenerator, Dict, Any, List, Tuple
from types import SimpleNamespace
import asyncio
from loguru import logger
import traceback

"""单轮对话，不会进行多轮调用工具"""

class MCPClient:
    def __init__(self, config):
        self.config = config
        self.sessions: Dict[str, Client] = {}  # {server_url: Client}
        self.tool_mapping: Dict[str, Tuple[str, Client]] = {}  # {tool_name: (server_url, Client)}
        self.available_tools: Dict[str, List[Dict]] = {}  # {server_url: tools}
        self.client = AsyncOpenAI(base_url=config["openai"]["base_url"], api_key=config["openai"]["api_key"])
        self.model_name = config["openai"]["model_name"]

    async def connect_to_servers(self, server_urls: List[str]) -> bool:
        """连接多个mcp服务器并构建工具映射表"""
        async def connect_and_map_tools(url: str):
            try:
                transport = SSETransport(url)
                session = Client(transport)
                await session.__aenter__()
                self.sessions[url] = session
                
                # 获取该服务器的工具列表
                tools = await session.list_tools()
                for tool in tools:
                    if tool.name in self.tool_mapping:
                        logger.warning(f"工具名冲突: {tool.name} 已经存在于 {self.tool_mapping[tool.name][0]}")
                    self.tool_mapping[tool.name] = (url, session)

                    self.available_tools[url] = [{
                            "type": "function",
                            "function": {
                                "name": tool.name,              # 考虑如果工具名称一样，就加一个可以解析的前缀
                                "description": tool.description,
                                "parameters": tool.inputSchema
                            }
                        } for tool in tools]
                
                logger.info(f"成功连接服务器 {url}，注册 {len(tools)} 个工具")
                return True
            except Exception as e:
                logger.error(f"连接服务器 {url} 失败: {e}")
                return False

        # 并行连接所有服务器
        # [True, False, True]
        results = await asyncio.gather(*[connect_and_map_tools(url) for url in server_urls])
        # 至少一个成功（至少一个 True），any(results) 返回 True
        return any(results)

    def get_all_tools(self) -> List[Dict]:
        """获取所有服务器的合并工具列表"""
        return [tool for tools in self.available_tools.values() for tool in tools]

    def get_mcp_server_url(self, tool_name) -> str:
        """通过工具名称获取其mcp服务url"""
        if tool_name not in self.tool_mapping:
            return ""
        else:
            mcp_server_url, _ = self.tool_mapping[tool_name]
            return mcp_server_url

    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """通过工具名直接调用工具（自动路由）"""
        if tool_name not in self.tool_mapping:
            raise ValueError(f"找不到工具: {tool_name}")
            
        _, session = self.tool_mapping[tool_name]
        return await session.call_tool(tool_name, arguments)
    
    async def process_query_stream(self, messages: list) -> AsyncGenerator[Dict[str, Any], None]:
        """
        大模型使用mcp工具回答用户问题
        """
        try:
            if not self.tool_mapping:
                raise HTTPException(status_code=500, detail="没有可用的工具")
            if len(messages) == 0:
                raise HTTPException(status_code=500, detail="消息不能为空")
            # 消息截断
            messages = self.truncate_messages(messages, self.config["max_history_content_len"], self.config["max_history_messages"])

            if len(messages) == 0:
                raise HTTPException(status_code=500, detail="消息长度超出限制")
            
            # 获取所有mcp工具
            available_tools = self.get_all_tools()

            # 1 工具规划
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=available_tools
            )

            message = response.choices[0].message

            # 不返回查询工具的content, 在qwen3中是思考内容
            # if message.content:
            #     yield {"type": "content", "data": message.content}

            # 2 处理工具调用
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    mcp_server_url = self.get_mcp_server_url(tool_name)
                    try:
                        messages.append({
                            "role": "assistant",
                            "tool_calls": [{
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }]
                        })
                        # 2.1 调用工具, 注意fastmcp和mcp的client返回格式不完全一致
                        result = await self.call_tool(tool_name, tool_args)
                        # 解析工具结果
                        result_type = result.content[0].type
                        result_is_error = result.is_error
                        
                        if result_is_error:
                            logger.error(f"调用工具失败,错误信息{repr(str(result.content))}")
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": "调用工具失败"
                            })
                            tool_result = {
                                "type":"text",
                                "data":"调用工具失败",
                                "is_error": True
                            }
                        else:
                            if result_type == "text":
                                tool_result = {
                                    "type":"text",
                                    "data": result.content[0].text,
                                    "is_error": False
                                }
                                tool_content = result.content[0].text
                            elif result_type == "image":
                                tool_result = {
                                    "type":"image",
                                    "data": result.content[0].data,         #图片的base64数据
                                    "mime_type":result.content[0].mimeType, # 图片格式，如image/jpeg
                                    "is_error": False
                                }
                                tool_content = "已完成任务"
                            elif result_type == "audio":
                                tool_result = {
                                    "type":"audio",
                                    "data": result.content[0].data,         #视频的base64数据
                                    "mime_type":result.content[0].mimeType, # 视频格式
                                    "is_error": False
                                }
                                tool_content = "已完成任务"
                            else:
                                logger.info(f"mcp工具返回未知格式, {str(result.content)}")
                                tool_result = {
                                    "type":result_type,
                                    "data": str(result.content),
                                    "is_error": False
                                }
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_content
                            })
                        yield {
                            "type": "tool", 
                            "data": {
                                "tool_mcp_server": mcp_server_url,
                                "tool_name":tool_name,
                                "tool_args":tool_args,
                                "tool_result": tool_result
                            }
                        }

                    except Exception as e:
                        logger.error(repr(f"调用工具失败: {traceback.format_exc()}"))
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": "工具调用失败"
                        })
                        yield {
                            "type": "tool", 
                            "data": {
                                "tool_mcp_server": mcp_server_url,
                                "tool_name": tool_name,
                                "tool_args": tool_args,
                                "tool_result": {
                                    "type":"text",
                                    "data": "调用工具失败",
                                    "is_error": True
                                }
                            }
                        }

                # 3 根据工具结果回复用户问题
                stream = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=True
                )
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield {"type": "content", "data": delta.content}
            else:
                yield {"type": "warning", "data": "本次提问没有使用工具"}
                # 普通问答
                stream = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=True
                )
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield {"type": "content", "data": delta.content}
                
        except Exception as e:
            yield {"type": "error", "data": f"程序运行出错: {str(e)}"}

    def truncate_messages(self, messages, max_content_length=10, max_messages=5):
        """
        截断messages列表
        """
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        messages = messages[::-1]
        new_messages = []
        total_length = 0
        for msg in messages:
            if total_length + len(msg["content"]) > max_content_length:
                break
            new_messages.append(msg)
            total_length += len(msg["content"])
        return new_messages[::-1]
    
    async def disconnect_all(self):
        """断开所有mcp服务器连接"""
        for url, session in self.sessions.items():
            try:
                await session.__aexit__(None, None, None)
                logger.info(f"已断开服务器连接: {url}")
            except Exception as e:
                logger.error(f"断开服务器 {url} 时出错: {e}")
        self.sessions.clear()
