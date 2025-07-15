# 🚀 FastAPI-MCP-Client

基于 FastAPI 实现的 MCP Client接口服务，支持通过 SSE 实现流式返回模型响应结果。

## 📁 文件结构

```
bash复制编辑src/
├── app.py          # FastAPI 应用主入口，定义接口路由
├── client.py       # MCP Client逻辑，封装大模型与工具交互
├── config.json     # 配置文件，包含大模型 API 设置等
```

---

## ✨ 特性特点

- ✅ **结构清晰**：代码简单，便于二次开发
- 🔧 **动态选择服务**：支持通过接口参数选择使用的 MCP 服务
- ⚙️ **多服务并发支持**：单次请求可同时使用多个 SSE MCP 服务（工具）
- 📤 **流式输出**：使用 SSE 协议返回响应，实现实时输出体验

---

## ⚠️ 注意事项

- 所有 MCP 工具（Tool）**名称必须唯一**，也就是工具函数名需要唯一
- 后端大模型需要支持 **Tool Call** 能力。如果不支持，需要手动修改 `client.py` 中的 `process_query_stream()` 实现tool call逻辑
- 当前仅支持基于 **SSE 协议** 的 MCP 服务接入

---

## 🚀 快速开始

### 1. 安装依赖

建议使用 Python 3.10+ 版本，安装依赖

```
pip install -r requirements.txt
```

### 2 配置大模型

根据下面配置说明修改 `src/config.json`

```json
{
    // openai风格的大模型接口
    "openai": {
        "base_url": "http://192.168.1.3:11434/v1",
        "api_key": "ollama-empty-key",
        "model_name": "qwen3:4b"
    },
    "max_history_messages": 10,		// 历史信息保留数量限制
    "max_history_content_len": 8096	// 历史信息保留长度限制(包括最新输入提问)
}
```

### 3. 启动服务

```
cd src
python app.py
```

服务启动后，默认接口地址为：`http://127.0.0.1:8003/`

---

## 🧪 测试Demo

### 1 启动测试的mcp服务

```
cd demo/mcp-server-sample
python time_server.py
```

获取时间的mcp服务默认接口地址为：`http://127.0.0.1:21113/sse`

> 还有两个mcp服务例子，可以自行测试

## 2 测试请求

请求例子代码是 `demo\req.py` ，根据所需的mcp服务修改 mcp_list参数，以及修改提问

> 前面启动了一个获取时间的mcp服务，现在提问获取伦敦的现在时间，模型就会调用工具完成任务

```
mcp_list = ["http://127.0.0.1:21113/sse"]
query = "查询伦敦现在是多少点"  # 问题
```

sse 结果

```json
data: {"type": "tool", "data": {"tool_mcp_server": "http://127.0.0.1:21113/sse", "tool_name": "get_time", "tool_args": {"time_zone": "Europe/London"}, "tool_result": {"type": "text", "data": "{\"time\":\"2025-07-15 14:16:38 BST+0100\"}", "is_error": false}}}
data: {"type": "content", "data": "<think>"}
data: {"type": "content", "data": "\n"}
data: {"type": "content", "data": "嗯"}
.
.
.
<省略>
data: {"type": "content", "data": "）。"}
data: [DONE]
```

合并sse结果

```
[调用工具: {'tool_mcp_server': 'http://127.0.0.1:21113/sse', 'tool_name': 'get_time', 'tool_args': {'time_zone': 'Europe/London'}, 'tool_result': {'type': 'text', 'data': '{"time":"2025-07-15 14:16:38 BST+0100"}', 'is_error': False}}]
<think>
嗯，用户问的是伦敦现在的时间，我需要先确认当前的时区。伦敦使用的是英国夏令时，也就是BST，也就是UTC+1。不过，用户可能需要的是精确到小时和分钟的时间，而不仅仅是日期。根据之前的回复，时间显示为2025-07-15 14:16:38 BST+0100。我需要检查这个时间是否正确。

首先，我需要确认系统的时间是否正确。假设当前日期是2025年7月15日，那么伦敦的时区是BST，也就是UTC+1。这时候，我需要确认一下是
否正确，因为夏令时通常在3月最后一个星期日开始，到10月最后一个星期日结束。所以7月的时候确实是夏令时，时间应该是UTC+1。那这个
时间看起来是对的。

然后，用户可能想要的是当前的时间，而不仅仅是日期。所以应该以14:16:38作为当前时间，但可能用户需要的是小时和分钟，而不需要秒数。所以可以回答伦敦现在的时间是下午2点16分，或者用24小时制的话是14:16。不过要确认是否需要更精确的时间，比如秒数。不过一般情况下，可能不需要秒数，所以可以简化回答。

另外，用户可能是在询问当前的实时时间，所以需要确保这个时间是最近的，而不是过去的。比如，如果系统时间是2025年7月15日，那么这
个时间就是正确的。不过如果用户现在提问的时间是2025年7月15日之后，可能需要调整。不过根据之前的回复，系统给出的时间是2025-07-15 14:16:38，所以可能需要确认这个时间是否正确，或者用户是否在测试这个功能。

另外，用户可能没有说明是否需要考虑夏令时，但根据之前的回复，已经正确应用了BST时区，所以应该没问题。因此，回答用户伦敦现在的
时间是14:16，也就是下午2点16分，使用BST时间，UTC+1。
</think>

伦敦现在的当地时间是**14:16**（下午2点16分），处于**BST时区**（英国夏令时，UTC+1）。
```

---

**sse 返回字典包含的type说明**

```python
# 1 type=tool 是调用工具的结果数据，
# 包含mcp服务tool_mcp_server，工具名称tool_name、调用工具参数tool_args、工具返回结果tool_result、工具是否调用出错is_error
{"type": "tool", "data": {xxx}}

# 2 type=content 是大模型根据工具的结果回答用户提问的内容
{"type": "content", "data": "嗯"}

# 3 type=error 说明本次请求出错
{'type':'error', 'data': "<错误信息>"}

# 4  type=warning 说明本次提问没有使用工具，由大模型直接回答
{"type": "warning", "data": "本次提问没有使用工具"}
```

## 📄 License

本项目采用 Apache-2.0 license 开源发布。
