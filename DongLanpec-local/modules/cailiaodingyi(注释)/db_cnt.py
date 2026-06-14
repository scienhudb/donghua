import pymysql


def get_connection(host, port, user, password, database):
    """
    创建并返回MySQL数据库连接对象
    
    参数说明:
        host: 数据库服务器地址（例如：'localhost' 或 '127.0.0.1'）
        port: 数据库端口号（MySQL默认通常是3306）
        user: 登录数据库的用户名
        password: 登录数据库的密码
        database: 要连接的数据库名称
    
    返回值:
        返回一个MySQL数据库连接对象，用于执行后续的数据库操作
    """
    return pymysql.connect(
        host=host,           # 数据库主机地址
        port=port,           # 数据库端口号
        user=user,           # 数据库用户名
        password=password,   # 数据库密码
        database=database,   # 要连接的数据库名
        charset='utf8mb4',   # 设置字符集为utf8mb4，支持中文和emoji等所有Unicode字符
        cursorclass=pymysql.cursors.DictCursor  # 使用字典游标，查询结果以字典形式返回（键为列名）
    )
