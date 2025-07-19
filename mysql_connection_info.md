# MySQL 连接信息

## 容器信息
- **容器名称**: mysql-financial
- **镜像**: mysql/mysql-server:8.0
- **端口**: 3306 (主机端口) -> 3306 (容器端口)

## 数据库连接信息
- **主机**: localhost 或 127.0.0.1
- **端口**: 3306
- **用户名**: root
- **密码**: password123
- **数据库**: financial_db

## 连接命令示例

### 使用命令行连接
```bash
# 从主机连接
mysql -h localhost -P 3306 -u root -p

# 从容器内部连接
docker exec -it mysql-financial mysql -uroot -ppassword123
```

### 使用Python连接
```python
import mysql.connector

config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'password123',
    'database': 'financial_db'
}

conn = mysql.connector.connect(**config)
```

## 常用Docker命令

### 查看容器状态
```bash
docker ps
```

### 查看容器日志
```bash
docker logs mysql-financial
```

### 停止容器
```bash
docker stop mysql-financial
```

### 启动容器
```bash
docker start mysql-financial
```

### 删除容器
```bash
docker rm mysql-financial
```

## 注意事项
- 数据库数据会持久化在容器中
- 如果需要数据持久化到主机，可以使用卷挂载
- 默认创建的数据库是 `financial_db` 