# 常见问题排查指南

## 1. 初始化管理员报错 500

### 错误现象
```
POST http://localhost:5173/api/auth/initialize 500 (Internal Server Error)
Unexpected token 'I', "Internal S"... is not valid JSON
```

### 可能原因

#### 1.1 数据库未初始化（最常见）

**症状**：首次部署，数据库表不存在

**解决方法**：
```bash
# 查看后端日志
docker logs api-dev --tail 100

# 如果看到类似错误：
# "relation 'users' does not exist"
# "table users does not exist"

# 解决：重启后端，等待自动建表
docker compose restart api-dev

# 或手动触发建表
docker exec api-dev python -c "from yuxi.storage.postgres.manager import pg_manager; pg_manager.initialize(); import asyncio; asyncio.run(pg_manager.create_tables())"
```

#### 1.2 PostgreSQL 未启动

**症状**：后端日志显示连接失败

**检查方法**：
```bash
# 检查 PostgreSQL 状态
docker ps | grep postgres

# 如果没有运行
docker compose up -d postgres

# 查看日志
docker logs postgres --tail 50
```

#### 1.3 环境变量配置错误

**症状**：数据库连接字符串错误

**检查方法**：
```bash
# 查看 .env 文件
cat .env | grep POSTGRES

# 确保有正确的配置：
# POSTGRES_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/greenhouse
```

#### 1.4 依赖包缺失

**症状**：ImportError 或 ModuleNotFoundError

**解决方法**：
```bash
# 进入容器安装依赖
docker exec api-dev pip install -r requirements.txt

# 或重新构建
docker compose build --no-cache api-dev
docker compose up -d
```

---

## 2. MQTT 连接失败

### 错误现象
```
ESP32: [Errno 113] ECONNABORTED
Backend: MQTT connection failed
```

### 可能原因

#### 2.1 Mosquitto 未启动

**检查方法**：
```bash
docker ps | grep mosquitto

# 如果没有运行
docker compose up -d mosquitto
```

#### 2.2 Windows 防火墙阻止

**解决方法**：
1. 打开 Windows 设置 → 网络和 Internet → 网络属性
2. 将网络设置为「专用网络」
3. 或者添加防火墙规则允许 1883端口

#### 2.3 MQTT 配置错误

**检查 `.env`**：
```bash
MQTT_ENABLED=true
MQTT_BROKER_URL=mosquitto  # 不是 localhost
MQTT_BROKER_PORT=1883
```

---

## 3. 502 Bad Gateway

### 错误现象
```
GET http://localhost:5173/detect-api/... 502 (Bad Gateway)
```

### 可能原因

#### 3.1 检测服务未启动

**说明**：Docker 容器无法访问电脑摄像头，需要本地运行检测服务

**解决方法**：
```bash
# 本地启动检测服务
python scripts/run_detect_local.py

# 确保监听 8081端口
netstat -an | findstr 8081
```

#### 3.2 Vite 代理配置错误

**检查 `web/vite.config.js`**：
```javascript
'/detect-api': {
  target: 'http://localhost:8081',  // 本地检测服务
  changeOrigin: true,
  rewrite: (path) => path.replace(/^\/detect-api/, '/api/detect')
}
```

---

## 4. Token 认证失败

### 错误现象
```
401 Unauthorized
JWT token has expired
```

### 可能原因

#### 4.1 Token 过期

**解决方法**：重新登录

#### 4.2 JWT_SECRET_KEY 不一致

**说明**：如果重新部署，JWT 密钥变化会导致旧 token 失效

**解决方法**：清除浏览器 localStorage，重新登录

#### 4.3 Token Key 不匹配

**检查代码**：确保使用 `user_token` 而不是 `token`
```javascript
// 正确
localStorage.getItem('user_token')

// 错误
localStorage.getItem('token')
```

---

## 5. YOLO 检测失败

### 错误现象
```
ModuleNotFoundError: No module named 'ultralytics'
检测结果不准确
```

### 可能原因

#### 5.1 ultralytics 未安装

**解决方法**：
```bash
docker exec api-dev pip install ultralytics pyzbar "qrcode[pil]"
```

#### 5.2 分类映射错误

**检查 `detect_service.py`**：
```python
# 正确映射
# class_id: 0=Unripe, 1=Half-ripe, 2=Ripe
unripe = sum(1 for d in detections if d.class_id == 0)
half = sum(1 for d in detections if d.class_id == 1)
ripe = sum(1 for d in detections if d.class_id == 2)
```

---

## 6. 前端资源加载失败

### 错误现象
```
404 Not Found: /images/Tomato/xxx.png
```

### 可能原因

#### 6.1 图片文件缺失

**检查方法**：
```bash
ls -la web/public/images/Tomato/
```

#### 6.2 路径大小写

**说明**：Linux 系统区分大小写

**解决方法**：确保代码中的路径与实际文件名大小写一致

---

## 7. Docker 相关问题

### 7.1 容器无法启动

**检查方法**：
```bash
# 查看所有容器状态
docker ps -a

# 查看特定容器日志
docker logs <container_name> --tail 100

# 检查端口占用
netstat -ano | findstr :5173
netstat -ano | findstr :8000
```

### 7.2 磁盘空间不足

**解决方法**：
```bash
# 清理未使用的镜像和容器
docker system prune -a

# 查看磁盘空间
docker system df
```

### 7.3 内存不足

**症状**：容器频繁重启

**解决方法**：
1. 增加 Docker Desktop 内存限制（建议 4GB+）
2. 关闭不必要的服务

---

## 8. 快速诊断脚本

创建 `check_env.sh` 或 `check_env.ps1`：

```bash
#!/bin/bash
echo "=== 环境检查 ==="

echo "1. 检查 Docker..."
docker --version

echo "2. 检查容器状态..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "3. 检查后端日志..."
docker logs api-dev --tail 20 2>&1 | grep -i "error\|fail\|exception"

echo "4. 检查数据库连接..."
docker exec api-dev python -c "from yuxi.storage.postgres.manager import pg_manager; pg_manager.initialize(); print('DB OK' if pg_manager._initialized else 'DB FAIL')"

echo "5. 检查 MQTT..."
docker logs mosquitto --tail 10

echo "=== 检查完成 ==="
```

---

## 9. 获取帮助

如果以上方法都无法解决问题：

1. **查看完整日志**：
   ```bash
   docker compose logs --tail 500 > logs.txt
   ```

2. **检查环境信息**：
   ```bash
   docker --version
   docker compose version
   node --version
   python --version
   ```

3. **提交 Issue**：附上日志和环境信息
