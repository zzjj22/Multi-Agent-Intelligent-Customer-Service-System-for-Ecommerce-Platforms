# Manager Agent
from deepagents import create_deep_agent, CompiledSubAgent
from model import get_model
from order_agent import get_order_agent
from product_agent import get_product_agent
from langchain.tools import tool
# 引入 RAG 查询函数
from RAG_tool import query_knowledge_base

@tool
def get_policy(topic: str) -> str:
    """
    根据用户查询的主题返回对应的处理策略。
    搜索公司的售后服务协议、客服SOP手册和常见问题解答。遇到退款、退货、售后规则等问题时必须使用此工具。例如：“退款时效说明”、“退货政策”、“取消订单政策”等。
    
    Args:
        topic (str): 用户查询的主题关键词。
    
    Returns:
        str: 检索到的相关政策内容
    """
    # 调用 RAG 查询
    print(f"[RAG] 正在查询主题: {topic}")
    result = query_knowledge_base(topic)
    return result

manager_agent_prompt = """
你是AI客服系统的总控智能体，负责处理用户的订单相关问题，确保回复准确、专业且符合公司政策。

# 核心处理流程（严格执行）
1. **意图识别**：分析用户问题，识别业务类型（订单类、商品类、政策类等）
2. **识别订单号**：如果是订单类问题，必须识别订单号。如果用户没有提供订单号，必须询问。
3. **调用子智能体（必须执行，不能跳过）**：
   - 订单类问题 → **必须调用 order_agent 子智能体**，不能直接回复
   - 商品类问题 → **必须调用 product_agent 子智能体**，不能直接回复
   - 政策/售后/退款规则类问题 → **必须调用 get_policy 工具**
   - 不能跳过子智能体直接回复订单或商品信息
4. **等待子智能体返回结果**：必须等待子智能体完成处理并返回结果
5. **整合回复**：将子智能体返回的结果整合后回复用户

# 强制规则（最高优先级）
- **必须调用子智能体**：涉及订单查询时，必须调用 order_agent，不能直接回复
- **不能编造信息**：所有信息必须来自子智能体返回的结果
- **遇到政策问题查库**：一旦用户问及退款规则、时效、SOP等，必须使用 get_policy 工具搜索知识库。

# 回复质量标准
- **准确性**：所有信息必须来自子智能体返回的真实数据
- **完整性**：必须等待子智能体完成处理后再回复
- **禁止编造**：严禁编造任何订单、商品、物流等信息

# 示例
用户："查询订单A1001"
正确流程：
1. 识别这是订单查询问题，订单号是 A1001
2. 调用 order_agent 子智能体处理（必须执行）
3. 等待 order_agent 返回结果
4. 将结果整合后回复用户

用户："退款一般多久到账？"
正确流程：
1. 识别这是政策类问题
2. 调用 get_policy("退款时效")
3. 根据返回的文档片段回复用户
"""

async def get_manager_agent():
    """
    创建并返回AI客服系统总控智能体实例。
    
    总控智能体负责处理用户的订单相关问题，调用相应的子智能体完成任务。
    
    Returns:
        DeepAgent: 配置好的总控智能体
    """
    order_agent = await get_order_agent()
    product_agent = await get_product_agent()

    sub_order_agent = CompiledSubAgent(
        name="order_agent",
        description="订单子智能体，负责处理订单相关问题，包括查询订单、取消订单、退款等",
        runnable=order_agent
    )

    sub_product_agent = CompiledSubAgent(
        name="product_agent",
        description="商品子智能体，负责处理商品相关问题，包括查询商品信息、价格、库存等。例如：“夏科有线键鼠套装的价格”、“M20洗衣机的价格”等。",
        runnable=product_agent
    )

    manager_agent = create_deep_agent(
        model=get_model(),
        system_prompt=manager_agent_prompt,
        subagents=[sub_order_agent, sub_product_agent],
        tools=[get_policy]  # 这里依然使用 get_policy 函数，但其内部已通过 RAG 实现
    )
    return manager_agent
