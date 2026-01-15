# services/product_mcp.py
import os
import sqlite3
from typing import Optional, List, Tuple
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("product_mcp")

# 数据库路径配置（从环境变量读取，默认使用项目内 data 目录）
DB_PATH = os.getenv("PRODUCT_DB_PATH", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../data/products.db")
))

def _fetch_product(product_id: str = None, product_name: str = None) -> Optional[Tuple]:
    """根据商品ID或名称查询单个商品"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        if product_id:
            cur.execute(
                """
                SELECT
                    product_id, product_name, description, category, price, stock,
                    brand, specifications, image_url, status, created_at, updated_at
                FROM products WHERE product_id = ?
                """,
                (product_id,),
            )
        elif product_name:
            cur.execute(
                """
                SELECT
                    product_id, product_name, description, category, price, stock,
                    brand, specifications, image_url, status, created_at, updated_at
                FROM products WHERE product_name LIKE ? AND status = '在售'
                LIMIT 1
                """,
                (f"%{product_name}%",),
            )
        else:
            return None
        return cur.fetchone()
    finally:
        conn.close()


def _search_products(keyword: str = None, category: str = None, max_price: float = None) -> List[Tuple]:
    """搜索商品，支持关键词、分类、价格筛选"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        query = "SELECT product_id, product_name, description, category, price, stock, brand, specifications, image_url, status FROM products WHERE status = '在售'"
        params = []
        
        if keyword:
            query += " AND (product_name LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if max_price is not None:
            query += " AND price <= ?"
            params.append(max_price)
        
        query += " ORDER BY price ASC LIMIT 10"
        
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        conn.close()


@mcp.tool()
def get_product_info(product_description: str) -> str:
    """
    根据商品描述或名称获取商品详细信息。
    
    Args:
        product_description: 商品描述或名称，例如："夏科有线键鼠套装"、"M20洗衣机"等
    
    Returns:
        商品详情的字符串描述，包括名称、价格、库存、规格等
    """
    print(f"[TOOL] 调用工具: get_product_info, 参数: product_description='{product_description}'")
    
    # 先尝试精确匹配商品名称
    record = _fetch_product(product_name=product_description)
    
    if record is None:
        # 如果精确匹配失败，尝试模糊搜索
        results = _search_products(keyword=product_description)
        if not results:
            return f"未找到与「{product_description}」相关的商品，请检查商品名称是否正确，或尝试使用其他关键词搜索。"
        # 返回第一个匹配结果
        record = results[0]
        # 调整字段顺序以匹配 _fetch_product 的返回格式
        record = (record[0], record[1], record[2], record[3], record[4], record[5], 
                 record[6], record[7], record[8], record[9], None, None)
    
    (product_id, product_name, description, category, price, stock,
     brand, specifications, image_url, status, created_at, updated_at) = record
    
    result = (
        f"商品ID：{product_id}\n"
        f"商品名称：{product_name}\n"
        f"分类：{category}\n"
        f"价格：{price} 元\n"
        f"库存：{stock} 件\n"
    )
    
    if brand:
        result += f"品牌：{brand}\n"
    if description:
        result += f"商品描述：{description}\n"
    if specifications:
        result += f"规格参数：{specifications}\n"
    if image_url:
        result += f"商品图片：{image_url}\n"
    
    result += f"状态：{status}"
    
    return result


@mcp.tool()
def search_products(keyword: str = None, category: str = None, max_price: float = None) -> str:
    """
    搜索商品，支持按关键词、分类、价格筛选。
    
    Args:
        keyword: 搜索关键词，会在商品名称和描述中搜索
        category: 商品分类，例如："电脑外设"、"家用电器"、"网络设备"
        max_price: 最高价格（元），只返回价格不超过此值的商品
    
    Returns:
        符合条件的商品列表
    """
    print(f"[TOOL] 调用工具: search_products, 参数: keyword='{keyword}', category='{category}', max_price={max_price}")
    
    results = _search_products(keyword=keyword, category=category, max_price=max_price)
    
    if not results:
        filters = []
        if keyword:
            filters.append(f"关键词「{keyword}」")
        if category:
            filters.append(f"分类「{category}」")
        if max_price:
            filters.append(f"价格≤{max_price}元")
        
        filter_str = "、".join(filters) if filters else "当前条件"
        return f"未找到符合{filter_str}的商品，请尝试调整搜索条件。"
    
    result = f"找到 {len(results)} 个符合条件的商品：\n\n"
    for i, (product_id, product_name, description, category, price, stock, brand, specifications, image_url, status) in enumerate(results, 1):
        result += f"{i}. {product_name}\n"
        result += f"   商品ID：{product_id}\n"
        result += f"   价格：{price} 元\n"
        result += f"   库存：{stock} 件\n"
        if brand:
            result += f"   品牌：{brand}\n"
        if description:
            result += f"   描述：{description[:50]}...\n" if len(description) > 50 else f"   描述：{description}\n"
        result += "\n"
    
    return result


@mcp.tool()
def get_product_basic_info(product_name: str) -> str:
    """
    获取指定商品的基本信息（价格和库存）。
    
    Args:
        product_name: 商品名称或描述，例如："夏科有线键鼠套装"、"M20洗衣机"等
    
    Returns:
        商品的基本信息，包括价格和库存状态
    """
    print(f"[TOOL] 调用工具: get_product_basic_info, 参数: product_name='{product_name}'")
    
    record = _fetch_product(product_name=product_name)
    if record is None:
        return f"未找到商品「{product_name}」，请检查商品名称是否正确。"
    
    product_id, product_name_db, _, category, price, stock, brand, _, _, status, _, _ = record
    
    # 检查商品状态
    if status != "在售":
        return f"商品「{product_name_db}」当前状态：{status}，暂不可购买。"
    
    # 确定库存状态
    if stock > 50:
        stock_status = "库存充足"
    elif stock > 10:
        stock_status = "库存正常"
    elif stock > 0:
        stock_status = "库存紧张"
    else:
        stock_status = "缺货"
    
    result = f"商品：{product_name_db}\n"
    result += f"价格：{price} 元\n"
    result += f"当前库存：{stock} 件\n"
    result += f"库存状态：{stock_status}\n"
    
    if stock == 0:
        result += "提示：该商品目前缺货，建议选择其他商品或稍后再试。"
    
    return result

if __name__ == "__main__":
    mcp.run(transport="stdio")