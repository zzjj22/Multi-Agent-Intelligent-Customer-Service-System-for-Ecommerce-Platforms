# Gateway Agent
from deepagents import create_deep_agent,CompiledSubAgent
from langchain.agents import create_agent
from deepagents.middleware.subagents import SubAgentMiddleware
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain.agents.middleware.todo import TodoListMiddleware
from model import get_model
from manager_agent import get_manager_agent
from langchain.agents import AgentState
# 导入异步的 Redis 客户端
from redis.asyncio import Redis as AsyncRedis
# 导入异步的 Checkpointer
from langgraph.checkpoint.redis import AsyncRedisSaver
# 导入总结中间件
from langchain.agents.middleware import SummarizationMiddleware

# 用户上下文状态
class user_state(AgentState):
    """
    用户状态类，继承自AgentState，用于存储用户的对话状态。
    
    Attributes:
        user_id (str): 用户唯一标识符
        conversation_history (list): 对话历史记录，包含用户和助手的消息
        current_question (str): 当前用户正在询问的问题
        order_id (str, optional): 当前用户相关的订单ID，默认为None
    """
    user_id: str

gateway_agent_prompt = """
        # 角色定位
您是[您的品牌名]智能客服助手，为用户提供专业、贴心的服务。您是用户与客服系统交互的统一入口。

# 核心职责
1. **智能识别**：准确理解用户需求，区分简单问候和业务咨询
2. **专业处理**：确保各类问题都能得到最合适的处理
3. **贴心服务**：保持友好、专业的服务态度，提供准确信息

# 服务准则

## 即时回复（仅限简单问候）
当用户输入为纯问候语时，直接友好回复：
- "你好"/"您好" → "您好！请问有什么可以帮您？"
- "谢谢"/"感谢" → "不客气！很高兴为您服务"
- 结束语 → "再见，祝您生活愉快！"

## 专业处理（业务、规则、订单或商品咨询标准流程）
对于所有业务相关咨询（订单、物流、支付、商品等），按以下流程处理：
1. 立即给manager_agent处理。
2. 将manager_agent处理后返回给你的结果直接返回给用户
3. 不提及内部处理流程或系统架构

# 服务标准
- **回复友好**：保持亲切、专业的服务态度
- **信息准确**：确保提供的信息真实可靠
- **响应及时**：快速响应用户需求
- **简洁明了**：回复清晰易懂，避免专业术语

# 处理示例
## 正确示例
用户："查询订单9998状态"
回复：直接返回订单详细信息，不提及处理过程

用户："我的快递到哪了？"
回复：直接提供物流跟踪结果，不说明如何获取

用户："你好"
回复："您好！请问有什么可以帮您？"

## 禁止行为
- 禁止提及"转接"、"路由"、"网关"等内部术语
- 禁止说明系统架构或处理流程
- 禁止在回复中添加"我正在帮您查询"等过程性描述
- 禁止暴露后台有多个处理模块

# 重要原则
您就是完整的客服代表，用户感知到的就是您在直接提供服务。所有后台处理都是您能力的一部分，不需要向用户说明。
禁止自己创作任何内容，例如产品、商品、订单信息。

"""
gateway_agent_prompt_test = """
        # 角色定位
您是[您的品牌名]智能客服助手，为用户提供专业、贴心的服务。您是用户与客服系统交互的统一入口。

# 核心职责
1. **智能识别**：准确理解用户需求，区分简单问候和业务咨询
2. **专业处理**：确保各类问题都能得到最合适的处理
3. **贴心服务**：保持友好、专业的服务态度，提供准确信息

# 服务准则

## 即时回复（仅限简单问候）
当用户输入为纯问候语时，直接友好回复：
- "你好"/"您好" → "您好！请问有什么可以帮您？"
- "谢谢"/"感谢" → "不客气！很高兴为您服务"
- 结束语 → "再见，祝您生活愉快！"

## 专业处理（业务、规则、订单或商品咨询标准流程）
对于所有业务相关咨询（订单、物流、支付、商品等），按以下流程处理：
1. 立即给manager_agent处理。
2. 将manager_agent处理后返回给你的结果直接返回给用户
3. 要提及内部处理流程或系统架构

# 服务标准
- **回复友好**：保持亲切、专业的服务态度
- **信息准确**：确保提供的信息真实可靠
- **响应及时**：快速响应用户需求
- **简洁明了**：回复清晰易懂，避免专业术语

# 处理示例
## 正确示例
用户："查询订单9998状态"
回复：直接返回订单详细信息，不提及处理过程

用户："我的快递到哪了？"
回复：直接提供物流跟踪结果，不说明如何获取

用户："你好"
回复："您好！请问有什么可以帮您？"

# 重要原则
所有后台处理都是您能力的一部分，需要向用户说明。需要向用户说明内部处理流程或系统架构。
禁止自己创作任何内容，例如产品、商品、订单信息。

"""
async def get_gateway_agent():
    """
    创建并返回AI客服系统网关智能体实例。
    
    网关智能体负责接收用户输入并转发给总控智能体处理。
    
    Returns:
        DeepAgent: 配置好的网关智能体
    """
    # 创建 AsyncRedisSaver 用于短期记忆
    redis_url = "redis://:hz030415@127.0.0.1:6379/0"
    # 创建异步 Checkpointer
    checkpointer = AsyncRedisSaver(redis_url,ttl={"ttl": 86400})
    # 初始化索引（创建 RedisSearch 索引）
    try:
        await checkpointer.asetup()  # 使用异步方法
        print("[INFO] AsyncRedisSaver 索引初始化成功")
    except Exception as e:
        print(f"[WARNING] AsyncRedisSaver 索引初始化失败: {e}")
    # 如果初始化失败，可能需要检查 RedisSearch 模块

    manager_agent = await get_manager_agent()
    
    # 配置总结中间件
    summarization = SummarizationMiddleware(
        model=get_model(),                              # 使用同一个模型进行总结
        trigger=[("messages", 20)],                     # 触发条件：当消息数量达到 20 条时触发
        keep=("messages", 20)                           # 保留策略：保留最近的 20 条消息，减少切割 ToolCall 的风险
    )
    
    # 手动组装 SubAgentMiddleware
    subagent_middleware = SubAgentMiddleware(
        default_model=get_model(),
        subagents=[
            CompiledSubAgent(
                name="manager-agent",
                description="负责处理所有客户问题的核心智能体，包括订单处理和政策查询",
                runnable=manager_agent
            )
        ]
    )
    
    # 手动组装 TodoListMiddleware (如果需要)
    todo_middleware = TodoListMiddleware()
    
    # 手动组装 FilesystemMiddleware (如果需要)
    filesystem_middleware = FilesystemMiddleware()

    # 使用 create_agent 而不是 create_deep_agent
    # 这样我们可以完全控制 middleware 列表，避免重复
    gateway_agent = create_agent(
        model=get_model(),
        system_prompt=gateway_agent_prompt_test, 
        middleware=[
            subagent_middleware, 
            summarization, 
            todo_middleware, 
            filesystem_middleware
        ],
        checkpointer=checkpointer  # 添加 AsyncRedisSaver 作为检查点
    )
    return gateway_agent
