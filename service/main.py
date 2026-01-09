import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from langchain_mcp_adapters.client import MultiServerMCPClient 
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
import uvicorn
import json
import redis
import sys
import os

# 添加agents目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../agents')))
from gateway_agent import get_gateway_agent

# 全局 gateway_agent 实例（异步初始化）
gateway_agent = None

""" 
# Redis连接配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = "hz030415"
# 创建Redis连接
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True) 
"""

# 创建FastAPI应用
app = FastAPI(title="AI智能客服系统", description="在线AI智能客服API", version="1.0.0")
# 静态文件服务
# 使用绝对路径确保正确性
html_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '../html'))
app.mount("/html", StaticFiles(directory=html_directory), name="html")

@app.on_event("startup")
async def startup_event():
    """应用启动时异步初始化 gateway_agent"""
    global gateway_agent
    try:
        logging.info("[STARTUP] 开始初始化 gateway_agent...")
        gateway_agent = await get_gateway_agent()
        logging.info("[STARTUP] gateway_agent 初始化成功")
    except Exception as e:
        logging.error(f"[STARTUP] gateway_agent 初始化失败: {e}", exc_info=True)
        raise

@app.get("/")
async def root():
    """根路径，重定向到前端页面"""
    return JSONResponse(content={"message": "AI智能客服系统API", "docs": "/docs"})
@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse(content={"status": "healthy"})

@app.get("/api/chat_history/{user_id}")
async def get_chat_history(user_id: str):
    """获取用户的对话历史（从 AsyncRedisSaver 读取）"""
    try:
        if gateway_agent is None:
            raise HTTPException(status_code=503, detail="Agent is not initialized yet.")
        
        # 使用全局的 gateway_agent 实例
        config = {"configurable": {"thread_id": user_id}}
        
        # 从 AsyncRedisSaver 获取当前状态（使用异步方法）
        state = await gateway_agent.aget_state(config)
        
        if not state or not state.values or "messages" not in state.values:
            return JSONResponse(content={"history": []})
        
        # 转换 LangChain 消息对象为字典格式
        messages = state.values["messages"]
        history = []
        seen_ids = set()  # 用于去重
        
        for msg in messages:
            # 跳过系统消息和工具消息
            msg_class = msg.__class__.__name__
            if msg_class in ["SystemMessage", "ToolMessage", "ToolMessageChunk"]:
                continue
            
            # 使用消息 ID 去重（如果消息有 id 属性）
            msg_id = getattr(msg, "id", None) or str(hash(str(msg.content)))
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)
            
            # 正确判断消息类型
            if msg_class == "HumanMessage":
                role = "user"
            elif msg_class in ["AIMessage", "AIMessageChunk"]:
                role = "assistant"
            else:
                # 未知类型，跳过或记录警告
                logging.warning(f"未知消息类型: {msg_class}, 内容: {getattr(msg, 'content', 'N/A')}")
                continue
            
            if hasattr(msg, "content"):
                history.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                history.append(msg)
        
        return JSONResponse(content={"history": history})
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] 获取对话历史失败 (user_id={user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")

@app.post("/api/chat/{user_id}")
async def chat_with_agent(user_id: str, request: Request):
    """与AI智能客服对话"""
    try:
        logging.info(f"[API] 收到用户 {user_id} 的消息请求")
        
        # 获取请求体
        data = await request.json()
        user_message = data.get("message")
        logging.info(f"[API] 用户消息: {user_message[:50] if user_message else 'None'}...")

        if not user_message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")

        if gateway_agent is None:
            raise HTTPException(status_code=503, detail="Agent is not initialized yet.")

        # 使用全局的 gateway agent 实例（已在模块加载时创建）
        logging.info(f"[API] 使用全局 gateway agent")

        # 【自愈逻辑】检查并清理脏数据
        config = {"configurable": {"thread_id": user_id}}
        state = await gateway_agent.aget_state(config)
        if state and "messages" in state.values:
            msgs = state.values["messages"]
            if len(msgs) > 0:
                last_msg = msgs[-1]
                # 如果最后一条是 Assistant 且有工具调用，但后续没有 ToolMessage，说明上次崩溃了
                if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                    logging.warning(f"[API] 检测到未完成的工具调用 (ID: {last_msg.tool_calls[0]['id']})，正在尝试修复状态...")
                    # 解决方案：手动将状态回滚（更新为一个不包含这条坏消息的新状态）
                    # 这里的做法是：发送一条 system 消息来"覆盖"或"重置"当前的不一致状态
                    # 或者更暴力一点：直接告诉 LLM 上次出错了
                    
                    # 简单修复：注入一条伪造的 ToolMessage 表示失败，让流程闭环
                    from langchain_core.messages import ToolMessage
                    fake_tool_output = ToolMessage(
                        tool_call_id=last_msg.tool_calls[0]['id'],
                        content="Error: Tool execution failed or was interrupted. Please retry."
                    )
                    await gateway_agent.aupdate_state(config, {"messages": [fake_tool_output]})
                    logging.info("[API] 已注入伪造的工具输出以修复状态闭环。")

        # 构建消息格式（LangChain 标准格式）
        user_msg = HumanMessage(content=user_message)
        
        # 调用agent，AsyncRedisSaver 会根据 thread_id 自动恢复历史状态
        logging.info(f"[API] 调用 agent.ainvoke，用户消息: {user_message[:50]}...")
        try:
            result = await gateway_agent.ainvoke(
                {"messages": [user_msg]},  # 只传入新消息，历史由 AsyncRedisSaver 管理
                config=config,
            )
            logging.info(f"[API] agent 调用完成，返回类型: {type(result)}")
        except Exception as e:
            logging.error(f"[API] agent.ainvoke 异常: {e}", exc_info=True)
            raise

        if not isinstance(result, dict) or "messages" not in result:
            logging.error(f"[API] agent 返回格式异常: {result}")
            raise HTTPException(status_code=500, detail="Agent 返回格式异常")

        # 获取完整对话记录（AsyncRedisSaver 已自动保存）
        full_chat_history = result.get("messages") or []
        logging.info(f"[API] agent 返回的消息数量: {len(full_chat_history)}")
        
        # 返回AI回复
        if not full_chat_history:
            ai_response = ""
            logging.warning("[API] agent 返回的消息列表为空")
        else:
            last_msg = full_chat_history[-1]
            if isinstance(last_msg, dict):
                ai_response = last_msg.get("content", "")
            else:
                ai_response = getattr(last_msg, "content", "") or ""
            logging.info(f"[API] AI 回复内容长度: {len(ai_response)} 字符")
        
        # 调试打印
        state = await gateway_agent.aget_state(config)
        if state and "messages" in state.values:
            msgs = state.values["messages"]
            print(f"DEBUG: 当前消息数量: {len(msgs)}")
            if len(msgs) > 0 and isinstance(msgs[0], SystemMessage):
                print(f"DEBUG: 第一条消息内容: {msgs[0].content[:50]}...")


        return JSONResponse(content={"response": ai_response, "role": "assistant"})
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        logging.error(f"[API] 对话接口异常 (user_id={user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

@app.post("/api/init_chat/{user_id}")
async def init_chat(user_id: str):
    """初始化对话（使用 AsyncRedisSaver）"""
    try:
        if gateway_agent is None:
            raise HTTPException(status_code=503, detail="Agent is not initialized yet.")
        
        # 使用全局的 gateway_agent 实例
        config = {"configurable": {"thread_id": user_id}}
        
        # 检查是否已有对话历史（使用异步方法）
        state = await gateway_agent.aget_state(config)
        
        if state and state.values and "messages" in state.values and len(state.values["messages"]) > 0:
            # 已有历史，返回现有历史
            messages = state.values["messages"]
            history = []
            for msg in messages:
                if hasattr(msg, "content"):
                    role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
                    history.append({"role": role, "content": msg.content})
                elif isinstance(msg, dict):
                    history.append(msg)
            return JSONResponse(content={"history": history})
        else:
            # 没有历史，初始化对话
            from langchain_core.messages import HumanMessage, AIMessage
            initial_messages = [
                HumanMessage(content="我的订单怎么还没到？"),
                AIMessage(content="请告诉我你要查询的订单号？")
            ]
            
            # 通过 ainvoke 初始化，AsyncRedisSaver 会自动保存
            await gateway_agent.ainvoke(
                {"messages": initial_messages},
                config=config
            )
            
            # 返回初始化的历史
            history = [
                {"role": "user", "content": "我的订单怎么还没到？"},
                {"role": "assistant", "content": "请告诉我你要查询的订单号？"}
            ]
            return JSONResponse(content={"history": history})
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] 初始化对话失败 (user_id={user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"初始化对话失败: {str(e)}")
        
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
