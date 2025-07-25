# 环境变量设置说明

## 概述

为了安全起见，敏感信息（如API密钥）现在通过环境变量进行配置，而不是直接写在配置文件中。

## 设置步骤

### 1. 设置环境变量

在运行应用之前，请设置以下环境变量：

```bash
# QWEN API 配置
export QWEN_API_KEY="your_actual_qwen_api_key_here"
```

### 2. 创建 .env 文件（推荐）

在项目根目录创建 `.env` 文件：

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，填入实际的API密钥
vim .env
```

`.env` 文件内容示例：
```env
# QWEN API 配置
QWEN_API_KEY=sk-e68b5fd9481c49a1a81cf63684d4d48b

# 其他配置（可选）
# DATABASE_PASSWORD=your_database_password_here
# MILVUS_HOST=localhost
# MILVUS_PORT=19530
```

### 3. 加载环境变量

#### 方法1：使用 python-dotenv（推荐）

安装 python-dotenv：
```bash
pip install python-dotenv
```

在应用启动时加载：
```python
from dotenv import load_dotenv
load_dotenv()
```

#### 方法2：手动设置

```bash
# Linux/Mac
export QWEN_API_KEY="your_api_key_here"

# Windows
set QWEN_API_KEY=your_api_key_here
```

## 配置文件更新

配置文件 `src/conf/config.yaml` 中的敏感信息已更新为使用环境变量：

```yaml
api:
  qwen:
    api_key: "${QWEN_API_KEY}"  # 从环境变量读取
    # ... 其他配置
```

## 验证设置

运行以下命令验证环境变量是否正确设置：

```bash
# 检查环境变量
echo $QWEN_API_KEY

# 运行测试
python test_custom_react.py
```

## 安全注意事项

1. **不要提交 .env 文件**：确保 `.env` 文件已添加到 `.gitignore`
2. **使用强密码**：API密钥应该足够复杂
3. **定期轮换**：定期更新API密钥
4. **限制权限**：只给必要的权限

## 故障排除

### 问题1：API密钥未找到
```
错误：API key is required
```
**解决方案**：确保环境变量 `QWEN_API_KEY` 已正确设置

### 问题2：环境变量未加载
```
错误：${QWEN_API_KEY} 被当作字符串处理
```
**解决方案**：检查环境变量是否正确设置，或使用 python-dotenv 加载 .env 文件

### 问题3：配置文件格式错误
```
错误：YAML格式错误
```
**解决方案**：检查配置文件中的语法，确保环境变量格式正确 `${VARIABLE_NAME}` 