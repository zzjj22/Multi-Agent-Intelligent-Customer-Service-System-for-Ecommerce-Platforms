# services/order_mcp.py
import os
import sqlite3
from typing import Optional, Tuple
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("order_mcp")

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/orders.db")
)


def _fetch_order(order_no: str) -> Optional[Tuple[str, str, str, str, float, str, int, str]]:
    print(f"[DEBUG] 查询订单 {order_no}，数据库路径: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                order_no,
                user_id,
                status,
                items,
                amount,
                logistics,
                cancelable,
                updated_at
            FROM orders WHERE order_no=?
            """,
            (order_no,),
        )
        result = cur.fetchone()
        print(f"[DEBUG] 查询结果: {result}")
        return result
    finally:
        conn.close()


@mcp.tool()
def get_order(order_no: str, user_id: str) -> str:
    """
    获取指定订单号的订单详情。

    Args:
        order_no: 要查询的订单号
        user_id: 用户ID，用于权限校验

    Returns:
        订单详情的字符串描述
    """
    print(f"[TOOL] 调用工具: get_order, 参数: order_no='{order_no}', user_id='{user_id}'")
    record = _fetch_order(order_no)
    if record is None:
        return f"未找到订单号 {order_no} 的记录，请确认后再试。"

    order_no_db, user_id_db, status, items, amount, logistics, cancelable, updated_at = record
    if user_id != user_id_db:
        return f"订单 {order_no_db} 不属于当前用户，无权限查看。"

    return (
        f"订单号：{order_no_db}\n"
        f"用户ID：{user_id_db}\n"
        f"订单状态：{status}\n"
        f"商品信息：{items}\n"
        f"支付金额：{amount} 元\n"
        f"物流信息：{logistics if logistics else '暂无物流更新'}\n"
        f"可取消：{'是' if cancelable else '否'}\n"
        f"最近更新：{updated_at}"
    )

@mcp.tool()
def check_cancelable(order_no: str, user_id: str) -> str:
    """
    检查订单是否可以取消（基于表中的 cancelable/status 字段）。
    
    Args:
        order_no: 订单号
        user_id: 用户ID，用于权限校验
    
    Returns:
        订单是否可取消的信息
    """
    print(f"[TOOL] 调用工具: check_cancelable, 参数: order_no='{order_no}', user_id='{user_id}'")
    record = _fetch_order(order_no)
    if record is None:
        return f"未找到订单号 {order_no} 的记录，请确认后再试。"

    order_no_db, user_id_db, status, items, amount, logistics, cancelable, updated_at = record
    if user_id != user_id_db:
        return f"订单 {order_no_db} 不属于当前用户，无权限查看。"

    if cancelable:
        return f"订单 {order_no_db} 当前状态：{status}，允许取消。"
    return f"订单 {order_no_db} 当前状态：{status}，不可取消。"

@mcp.tool()
def refund_order(order_no: str, user_id: str) -> str:
    """
    提交取消/退款操作：若允许取消则更新状态为"退款中"并标记不可取消。
    
    Args:
        order_no: 订单号
        user_id: 用户ID，用于权限校验
    
    Returns:
        退款操作结果
    """
    print(f"[TOOL] 调用工具: refund_order, 参数: order_no='{order_no}', user_id='{user_id}'")
    record = _fetch_order(order_no)
    if record is None:
        return f"未找到订单号 {order_no} 的记录，请确认后再试。"

    order_no_db, user_id_db, status, items, amount, logistics, cancelable, updated_at = record
    if user_id != user_id_db:
        return f"订单 {order_no_db} 不属于当前用户，无权限操作。"

    if not cancelable:
        return f"订单 {order_no_db} 当前状态：{status}，不可取消/退款。"

    # 根据当前状态和物流信息，确定退款后的物流状态
    if status in ["待发货", "待支付"]:
        new_logistics = "订单已申请退款，商品未发出"
    elif status == "配送中":
        new_logistics = "订单已申请退款，正在拦截配送"
    elif status == "已签收":
        new_logistics = "订单已申请退款，等待退货处理"
    else:
        new_logistics = "订单已申请退款，处理中"

    # 更新订单状态为退款中，同步更新物流信息，并设置不可再次取消
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE orders
            SET status = ?, 
                logistics = ?,
                cancelable = 0, 
                updated_at = datetime('now')
            WHERE order_no = ?
            """,
            ("退款中", new_logistics, order_no_db),
        )
        conn.commit()
    finally:
        conn.close()

    return f"订单 {order_no_db} 已提交取消/退款申请，状态更新为：退款中。物流信息：{new_logistics}。"

if __name__ == "__main__":
    mcp.run(transport="stdio")