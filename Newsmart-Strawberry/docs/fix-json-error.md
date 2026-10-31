# JSON 解析错误修复说明

## 问题描述

用户遇到错误：
```
Unexpected token 'I', "Internal S"... is not valid JSON
POST http://localhost:5173/api/auth/initialize 500 (Internal Server Error)
```

## 根本原因

1. **后端返回 500 错误时，默认返回纯文本 "Internal Server Error"**
2. **前端代码假设所有响应都是 JSON，直接调用 `response.json()`**
3. **JSON 解析器遇到 "Internal Server Error"文本，抛出语法错误**

## 修复内容

### 1. 后端修复 (`backend/server/main.py`)

添加全局异常处理器，确保所有错误都返回 JSON 格式：

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，返回 JSON 格式的错误信息"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误，请稍后重试",
            "error_type": type(exc).__name__,
        },
    )
```

### 2. 前端修复

#### 2.1 `web/src/stores/user.js`

添加安全解析函数：
```javascript
async function safeParseResponse(response) {
  const text = await response.text()
  try {
    return JSON.parse(text)
  } catch {
    return { detail: text || `HTTP ${response.status}: ${response.statusText}` }
  }
}
```

所有 `response.json()` 替换为 `safeParseResponse(response)`

#### 2.2 `web/src/apis/detect_api.js`

同样添加 `safeParseResponse` 函数并替换所有 `response.json()` 调用

#### 2.3 `web/src/apis/auth_api.js`

添加 `safeParseJson` 函数用于安全解析

#### 2.4 `web/src/apis/base.js`

改进错误处理逻辑：
```javascript
// 先获取响应文本，再尝试解析为 JSON
const responseText = await response.text()
try {
  errorData = JSON.parse(responseText)
  errorMessage = errorData.detail || errorData.message || errorMessage
} catch {
  // 如果不是 JSON，使用响应文本作为错误信息
  if (responseText) {
    errorMessage = responseText
  }
}
```

## 测试场景

### 场景 1: 数据库未初始化
- **修复前**: 前端报 JSON 语法错误
- **修复后**: 前端显示 "服务器内部错误，请稍后重试"

### 场景 2: 后端服务崩溃
- **修复前**: 前端报 JSON 语法错误
- **修复后**: 前端显示具体的错误信息

### 场景 3: 网络超时
- **修复前**: 可能报 JSON 语法错误
- **修复后**: 正确显示网络错误信息

## 部署建议

1. **重新构建前端**：
   ```bash
   cd web
   pnpm build
   ```

2. **重启后端服务**：
   ```bash
   docker compose restart api-dev
   ```

3. **清除浏览器缓存**：
   - 按 F12 打开开发者工具
   - 右键点击刷新按钮
   - 选择"清空缓存并硬性重新加载"

## 验证方法

1. 查看后端日志：
   ```bash
   docker logs api-dev --tail 50
   ```

2. 测试 API 响应：
   ```bash
   # 模拟 500 错误
   curl -i http://localhost:8000/api/auth/initialize
   ```

3. 前端应该显示友好的错误提示，而不是 JSON 语法错误
