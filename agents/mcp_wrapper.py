from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableConfig
from pydantic import create_model, BaseModel

def wrap_mcp_tool_with_user_id(original_tool: StructuredTool):
    """
    包装 MCP 工具：
    1. 修改 Schema：对 LLM 隐藏 user_id 参数
    2. 运行时注入：从 config 中自动提取 thread_id 作为 user_id
    """
    
    # 定义包装后的执行函数
    async def wrapped_func(config: RunnableConfig, **kwargs):
        # 尝试从 config 的 configurable 中获取 thread_id
        # main.py 中传递的是: config={"configurable": {"thread_id": user_id}}
        user_id = config.get("configurable", {}).get("thread_id")
        
        # 如果获取不到（比如测试环境），给个默认值
        if not user_id:
            print(f"[WRAPPER] 警告: 未在 config 中找到 thread_id，使用默认值 '1'")
            user_id = "1"
            
        print(f"[WRAPPER] 拦截工具调用 {original_tool.name}，自动注入 user_id={user_id}")
        
        # 构造包含 user_id 的完整参数
        input_args = kwargs.copy()
        input_args["user_id"] = user_id
        
        # 调用原始 MCP 工具
        # 注意：MCP 工具通常是 StructuredTool，直接调用 ainvoke
        return await original_tool.ainvoke(input_args, config=config)

    # 动态创建新的参数 Schema（排除 user_id 字段）
    old_schema = original_tool.args_schema
    new_fields = {}

    if isinstance(old_schema, dict):
        # 如果是字典类型 (JSON Schema)
        properties = old_schema.get("properties", {})
        for name, prop in properties.items():
            if name != "user_id":
                # 简单处理：这里我们假设都是 string，实际可能需要更复杂的类型映射
                # 但对于 MCP 工具来说，大部分基本类型可以简化处理
                # 如果能获取到 python 类型最好，但在 dict schema 下很难
                # 这里使用 object 或 string 作为通用类型
                new_fields[name] = (str, ...) # 默认为必填字符串，简化处理
    elif issubclass(old_schema, BaseModel):
        # 如果是 Pydantic 模型
        for name, field in old_schema.model_fields.items():
            if name != "user_id":
                new_fields[name] = (field.annotation, field)
    else:
        # 其他情况，直接复制原 schema (如果不包含 user_id)
        # 或者抛出异常
        print(f"[WRAPPER] 警告: 无法解析工具 {original_tool.name} 的 args_schema 类型: {type(old_schema)}")
        pass

    # 使用 create_model 创建新的 Pydantic 模型
    NewSchema = create_model(f"{original_tool.name}Input", **new_fields)
    
    # 返回包装后的新工具
    return StructuredTool.from_function(
        coroutine=wrapped_func,
        name=original_tool.name,
        description=original_tool.description,
        args_schema=NewSchema
    )

def wrap_mcp_tools(tools: list[StructuredTool]) -> list[StructuredTool]:
    """批量包装工具列表"""
    return [wrap_mcp_tool_with_user_id(tool) for tool in tools]
