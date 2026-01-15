import os
import sqlite3

ORDERS_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "orders.db"))
PRODUCTS_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "products.db"))


def init_orders_db() -> None:
    """初始化订单数据库：建表并插入示例数据（若表为空）。"""
    os.makedirs(os.path.dirname(ORDERS_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(ORDERS_DB_PATH)
    try:
        cur = conn.cursor()
        # 建表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_no TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                items TEXT NOT NULL,
                amount REAL NOT NULL,
                logistics TEXT DEFAULT '',
                cancelable INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        # 仅在表为空时插入示例数据
        cur.execute("SELECT COUNT(*) FROM orders")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """
                INSERT INTO orders(
                    order_no, user_id, status, items, amount, logistics, cancelable
                ) VALUES (?,?,?,?,?,?,?)
                """,
                [
                    # 订单A1001：路由器 x1 + 网线 x2 = 298 + 15*2 = 328
                    ("A1001", "1", "待发货", "路由器 x1; 网线 x2", 328.0, "仓库已出库，等待揽收", 1),
                    # 订单A1002：键盘 x1 + 鼠标 x1 = 189 + 89 = 278
                    ("A1002", "1", "配送中", "键盘 x1; 鼠标 x1", 278.0, "已到达上海转运中心，派送中", 1),
                    # 订单A1003：显示器 x1 = 1088
                    ("A1003", "2", "已签收", "显示器 x1", 1088.0, "已签收：收件人 张三", 0),
                    # 订单A1004：夏科有线键鼠套装 x1 = 50
                    ("A1004", "1", "待支付", "夏科有线键鼠套装 x1", 50.0, "", 1),
                    # 订单A1005：无线耳机 x2 = 299*2 = 598
                    ("A1005", "2", "待发货", "无线耳机 x2", 598.0, "订单已确认，等待发货", 1),
                    # 订单A1006：移动硬盘 x1 + U盘 x1 = 399 + 59 = 458
                    ("A1006", "3", "配送中", "移动硬盘 x1; U盘 x1", 458.0, "已发货，运输中", 1),
                    # 订单A1007：摄像头 x1 = 199
                    ("A1007", "1", "待发货", "摄像头 x1", 199.0, "订单已确认，等待发货", 1),
                    # 订单A1008：音响 x1 = 399
                    ("A1008", "2", "已签收", "音响 x1", 399.0, "已签收：收件人 李四", 0),
                    # 订单A1009：打印机 x1 = 899
                    ("A1009", "3", "待发货", "打印机 x1", 899.0, "订单已确认，等待发货", 1),
                    # 订单A1010：充电宝 x2 + 数据线 x3 = 129*2 + 29*3 = 345
                    ("A1010", "1", "配送中", "充电宝 x2; 数据线 x3", 345.0, "已到达北京转运中心", 1),
                ],
            )
        conn.commit()
    finally:
        conn.close()


def init_products_db() -> None:
    """初始化商品数据库：建表并插入示例数据（若表为空）。"""
    os.makedirs(os.path.dirname(PRODUCTS_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(PRODUCTS_DB_PATH)
    try:
        cur = conn.cursor()
        # 建表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                brand TEXT,
                specifications TEXT,
                image_url TEXT,
                status TEXT DEFAULT '在售',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        # 仅在表为空时插入示例数据
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """
                INSERT INTO products(
                    product_id, product_name, description, category, price, stock, brand, specifications, image_url, status
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    ("P001", "夏科有线键鼠套装", "USB接口，即插即用，适合办公和日常使用", "电脑外设", 50.0, 100, "夏科", "接口：USB 2.0；键盘：104键；鼠标：1200DPI", "https://www.example.cn/product/P001", "在售"),
                    ("P002", "M20洗衣机", "10公斤大容量，智能变频，节能省水", "家用电器", 2580.0, 25, "M20", "容量：10kg；能效等级：一级；洗涤方式：波轮", "https://www.example.cn/product/P002", "在售"),
                    ("P003", "路由器", "千兆双频，WiFi6，适合家庭和小型办公室", "网络设备", 298.0, 50, "品牌A", "速率：AX3000；频段：2.4G/5G双频；接口：4个千兆网口", "https://www.example.cn/product/P003", "在售"),
                    ("P004", "网线", "超五类网线，支持千兆网络，长度可选", "网络设备", 15.0, 200, "品牌B", "类型：超五类；长度：1米/3米/5米可选", "https://www.example.cn/product/P004", "在售"),
                    ("P005", "键盘", "机械键盘，青轴，RGB背光", "电脑外设", 189.0, 30, "品牌C", "轴体：青轴；键数：87键；背光：RGB", "https://www.example.cn/product/P005", "在售"),
                    ("P006", "鼠标", "无线鼠标，2.4G连接，人体工学设计", "电脑外设", 89.0, 80, "品牌D", "连接：2.4G无线；DPI：1600；电池：AA电池x1", "https://www.example.cn/product/P006", "在售"),
                    ("P007", "显示器", "27英寸，4K分辨率，IPS面板", "电脑外设", 1088.0, 15, "品牌E", "尺寸：27英寸；分辨率：3840x2160；面板：IPS", "https://www.example.cn/product/P007", "在售"),
                    ("P008", "笔记本电脑", "14英寸轻薄本，Intel i5处理器，8GB内存，512GB SSD", "电脑设备", 4999.0, 20, "品牌F", "CPU：Intel i5-1135G7；内存：8GB；硬盘：512GB SSD；屏幕：14英寸", "https://www.example.cn/product/P008", "在售"),
                    ("P009", "无线耳机", "蓝牙5.0，降噪，续航30小时", "音频设备", 299.0, 60, "品牌G", "连接：蓝牙5.0；降噪：主动降噪；续航：30小时", "https://www.example.cn/product/P009", "在售"),
                    ("P010", "移动硬盘", "1TB容量，USB 3.0接口，便携设计", "存储设备", 399.0, 45, "品牌H", "容量：1TB；接口：USB 3.0；尺寸：2.5英寸", "https://www.example.cn/product/P010", "在售"),
                    ("P011", "U盘", "64GB容量，USB 3.0，高速传输", "存储设备", 59.0, 150, "品牌I", "容量：64GB；接口：USB 3.0；读取速度：100MB/s", "https://www.example.cn/product/P011", "在售"),
                    ("P012", "摄像头", "1080P高清，自动对焦，内置麦克风", "电脑外设", 199.0, 35, "品牌J", "分辨率：1080P；对焦：自动对焦；麦克风：内置", "https://www.example.cn/product/P012", "在售"),
                    ("P013", "音响", "2.1声道，低音炮，蓝牙连接", "音频设备", 399.0, 28, "品牌K", "声道：2.1；功率：30W；连接：蓝牙/AUX", "https://www.example.cn/product/P013", "在售"),
                    ("P014", "打印机", "激光打印，黑白，自动双面", "办公设备", 899.0, 18, "品牌L", "类型：激光；颜色：黑白；双面：自动", "https://www.example.cn/product/P014", "在售"),
                    ("P015", "扫描仪", "A4幅面，2400DPI，USB连接", "办公设备", 599.0, 22, "品牌M", "幅面：A4；分辨率：2400DPI；接口：USB", "https://www.example.cn/product/P015", "在售"),
                    ("P016", "投影仪", "1080P高清，3000流明，支持无线投屏", "显示设备", 2999.0, 12, "品牌N", "分辨率：1080P；亮度：3000流明；连接：HDMI/无线", "https://www.example.cn/product/P016", "在售"),
                    ("P017", "智能手表", "健康监测，运动追踪，50米防水", "智能设备", 1299.0, 40, "品牌O", "屏幕：1.4英寸；防水：50米；续航：7天", "https://www.example.cn/product/P017", "在售"),
                    ("P018", "充电宝", "20000mAh容量，快充，双USB输出", "配件", 129.0, 90, "品牌P", "容量：20000mAh；输出：双USB；快充：支持", "https://www.example.cn/product/P018", "在售"),
                    ("P019", "数据线", "Type-C转USB，1米长度，支持快充", "配件", 29.0, 300, "品牌Q", "接口：Type-C转USB；长度：1米；快充：支持", "https://www.example.cn/product/P019", "在售"),
                    ("P020", "手机支架", "可调节角度，桌面/车载两用", "配件", 39.0, 200, "品牌R", "角度：可调节；用途：桌面/车载；材质：铝合金", "https://www.example.cn/product/P020", "在售"),
                ],
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_orders_db()
    print(f"订单数据库已初始化：{ORDERS_DB_PATH}")
    init_products_db()
    print(f"商品数据库已初始化：{PRODUCTS_DB_PATH}")

