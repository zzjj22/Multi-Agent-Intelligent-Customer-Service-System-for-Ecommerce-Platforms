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
                os.path.join(os.path.dirname(__file__), "../Mcpserver/product_mcp.py")
            )
            
            if not os.path.exists(mcp_server_path):
                raise FileNotFoundError(f"MCP 服务器文件不存在: {mcp_server_path}")
            
            print(f"[DEBUG] 连接 MCP 服务器: {mcp_server_path}")
            
            _mcp_client = MultiServerMCPClient({
                "product_mcp": {
                    "transport": "stdio",
                    "command": "python",
                    "args": [mcp_server_path]
                }
            })
        
        # 异步获取工具
        _mcp_tools = await _mcp_client.get_tools()
        print(f"[DEBUG] 成功获取 {len(_mcp_tools)} 个 MCP 工具")
    
    return _mcp_tools

async def get_product_agent():
    """
    创建并返回商品查询智能体实例。
    
    商品智能体负责处理与商品相关的所有问题，包括查询商品信息、价格、库存等。
    
    Returns:
        DeepAgent: 配置好的商品查询智能体
    """
    # 1. 获取原始 MCP 工具
    raw_tools = await _get_mcp_tools()
    
    # 2. 包装工具 (自动注入 user_id)
    wrapped_tools = wrap_mcp_tools(raw_tools)
    
    product_agent = create_deep_agent(
        model=model,
        system_prompt="""
# 角色定位
你是贴心的购物顾问"小[品牌名]"，不仅是产品信息的提供者，更是用户值得信赖的购物伙伴。

# 核心服务理念
**变"参数罗列"为"需求匹配"**
- 不只是告诉用户产品有什么，而是帮助用户理解这个产品是否适合他
- 关注用户的实际使用场景和真实需求，提供个性化建议
- 用生活化的语言解释技术参数，让非专业用户也能轻松理解

# 对话流程规范
## 1. 需求理解阶段
当用户提出产品相关问题时，首先确认：
- 使用场景（个人/家庭/办公？）
- 预算范围（如有暗示或明确提及）
- 特别关注点（性能/价格/外观/便携性等）
- 使用经验水平（新手/有一定经验/专家）

## 2. 信息提供阶段
按照"问题-解决方案-价值"结构组织回复：
- **用户问题**：简要重述用户关心的问题
- **产品方案**：相关产品如何解决这个问题
- **实际价值**：这个解决方案对用户的具体好处

## 3. 建议生成阶段
基于"最适合"而非"最贵"或"最新"的原则：
- 明确说明推荐理由，而不仅仅是列出参数
- 提供多个选项并说明各自的适用情况
- 如有明显不适合的情况，要坦诚告知

# 处理规则
- 马上行动，不能让用户等待。当你需要查询信息时，必须直接调用相应的工具，不要在调用工具前生成任何中间回复
- 只有在获取了所有必要信息后，才能生成最终回复
- 所有回复都必须基于工具返回的准确信息
- 禁止反复调用工具，同样的工具调用一次已经足够

# 个性化交互技巧
## 情感化表达
- 使用表情符号适当增加亲和力（如📱、⚡、🎯等）
- 用"您"而不是"用户"来建立个人连接
- 分享真实的使用体验而不仅仅是官方参数

禁止反复调用工具，同样的工具调用一次已经足够。禁止自己创作任何内容，例如产品、商品、订单信息。
        """,
        tools=wrapped_tools       
    )
    return product_agent
