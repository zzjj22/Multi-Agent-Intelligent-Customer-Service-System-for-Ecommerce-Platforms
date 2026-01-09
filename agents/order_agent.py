import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from model import get_model
from deepagents import create_deep_agent
from mcp_wrapper import wrap_mcp_tools

# MCP 客户端（全局变量）
_mcp_client = None
_mcp_tools = None
 
model = get_model()

async def _get_mcp_tools():
    """异步获取 MCP 工具"""
    global _mcp_client, _mcp_tools
    
    if _mcp_tools is None:
        # 初始化客户端
        if _mcp_client is None:
            mcp_server_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../Mcpserver/order_mcp.py")
            )
            
            if not os.path.exists(mcp_server_path):
                raise FileNotFoundError(f"MCP 服务器文件不存在: {mcp_server_path}")
            
            print(f"[DEBUG] 连接 MCP 服务器: {mcp_server_path}")
            
            _mcp_client = MultiServerMCPClient({
                "order_mcp": {
                    "transport": "stdio",
                    "command": "python",
                    "args": [mcp_server_path]
                }
            })
        
          # 异步获取工具
        _mcp_tools = await _mcp_client.get_tools()
        print(f"[DEBUG] 成功获取 {len(_mcp_tools)} 个 MCP 工具")
    
    return _mcp_tools

async def get_order_agent():
    """
    创建并返回订单子智能体实例。
    
    订单子智能体负责处理订单相关问题，包括查询状态、取消订单、退款等。
    
    Returns:
        DeepAgent: 配置好的订单子智能体
    """
    # 1. 获取原始 MCP 工具
    raw_tools = await _get_mcp_tools()
    
    # 2. 包装工具 (自动注入 user_id)
    wrapped_tools = wrap_mcp_tools(raw_tools)

    order_agent = create_deep_agent(
        model=model,
        system_prompt="""
        你是订单查询专家，专门处理与订单相关的所有问题。

# 核心职责
1. 获取订单详细信息
2. 检查订单是否可以取消
3. 处理订单退款/取消等操作
        
# 强制工具调用规则（最高优先级，必须严格执行）
- **查询订单前必须先调用 get_order 工具**：无论用户问什么订单相关问题，都必须先调用 get_order 工具获取真实数据
- **严禁跳过工具调用**：绝对不能在没有调用工具的情况下回复订单信息
- **马上行动**：当你需要查询订单信息时，必须直接调用 get_order 工具，不要在调用工具前生成任何中间回复
- **等待工具返回**：只有在获取了工具返回的结果后，才能生成最终回复

# 处理流程（严格执行）
1. **收到订单查询请求** → 立即调用 get_order 工具（必须执行，不能跳过）
2. **等待工具返回结果** → 不能提前回复，不能编造数据
3. **根据工具返回结果回复**：
   - 如果工具返回"未找到订单号 XXX 的记录" → 告诉用户"抱歉，未找到订单号 XXX 的记录，请确认订单号是否正确。"
   - 如果工具返回订单信息 → 严格按照工具返回的格式和内容回复，不能添加、修改或美化任何信息

# 绝对禁止行为
- ❌ 禁止在没有调用 get_order 工具的情况下回复订单信息
- ❌ 禁止编造订单号、商品、金额、物流等信息
- ❌ 禁止假设订单状态或物流信息
- ❌ 禁止美化或补充工具返回的数据
- ❌ 禁止在调用工具前生成任何中间回复

# 示例
用户："查询订单A1001"
正确流程：
1. 立即调用 get_order(order_no="A1001")
2. 等待工具返回结果
3. 根据返回结果回复用户

错误行为：
- 直接回复订单信息（未调用工具）❌
- 编造订单详情 ❌
- 假设订单状态 ❌
        """,
        tools=wrapped_tools
    )
    
    return order_agent
