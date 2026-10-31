# 新嵌入式设备 MQTT v1.1 与设备控制功能升级说明

本文档用于把老项目升级到新的番茄嵌入式设备协议，使网页和后端可以直接控制新 ESP32 设备。

## 1. 升级目标

老项目通常还在使用旧 MQTT 主题：

```text
/air/post
/soil/post
```

新嵌入式设备改为统一根主题：

```text
tomato_hnsw0001
```

并使用以下主题通信：

| 主题 | 方向 | 作用 |
| --- | --- | --- |
| `tomato_hnsw0001/set` | 后端 -> ESP32 | 下发控制命令 |
| `tomato_hnsw0001/result` | ESP32 -> 后端 | 返回命令执行结果 |
| `tomato_hnsw0001/state` | ESP32 -> 后端 | 返回设备当前状态 |
| `tomato_hnsw0001/telemetry` | ESP32 -> 后端 | 上报传感器数据 |
| `tomato_hnsw0001/availability` | ESP32 -> 后端 | 上报在线/离线状态 |

## 2. 需要同步的文件

如果是从老项目手动升级，优先替换或对照修改这些文件：

```text
.env
docker-compose.yml
README.md
esp32/main.py
backend/package/yuxi/iot/schemas.py
backend/package/yuxi/iot/mqtt_client.py
backend/package/yuxi/iot/__init__.py
backend/package/yuxi/services/iot_service.py
backend/server/utils/lifespan.py
backend/server/routers/iot_router.py
backend/package/yuxi/agents/toolkits/iot/tools.py
backend/scripts/mqtt_monitor.py
backend/test/unit/test_mqtt_client.py
web/src/apis/iot_api.js
web/src/views/IndustrialIotView.vue
web/src/views/TomatoDashboardView.vue
docs/develop-guides/changelog.md
```

其中最核心的是：

```text
backend/package/yuxi/iot/mqtt_client.py
backend/package/yuxi/services/iot_service.py
backend/server/routers/iot_router.py
web/src/apis/iot_api.js
web/src/views/IndustrialIotView.vue
esp32/main.py
.env
docker-compose.yml
```

## 3. 环境配置

`.env` 中需要增加或确认：

```env
MQTT_ENABLED=true
MQTT_BROKER_URL=broker.emqx.io
MQTT_BROKER_PORT=1883
MQTT_BROKER_USERNAME=admin
MQTT_BROKER_PASSWORD=admin123
MQTT_TOPIC_ROOT=tomato_hnsw0001
```

`docker-compose.yml` 的 `api` 服务中需要传入：

```yaml
MQTT_BROKER_URL: ${MQTT_BROKER_URL:-broker.emqx.io}
MQTT_BROKER_PORT: ${MQTT_BROKER_PORT:-1883}
MQTT_BROKER_USERNAME: ${MQTT_BROKER_USERNAME:-admin}
MQTT_BROKER_PASSWORD: ${MQTT_BROKER_PASSWORD:-admin123}
MQTT_TOPIC_ROOT: ${MQTT_TOPIC_ROOT:-tomato_hnsw0001}
```

Mosquitto 服务需要暴露 1883 端口：

```yaml
mosquitto:
  ports:
    - "1883:1883"
    - "9002:9001"
```

开发环境的 Mosquitto 可使用匿名连接：

```conf
listener 1883
allow_anonymous true
```

## 4. ESP32 设备连接哪个 MQTT 服务

新嵌入式代码里默认 MQTT Server 是：

```text
broker.emqx.io
```

当前新版设备控制方案按公网 MQTT Broker 对接，后端和 ESP32 都连接：

```text
broker.emqx.io:1883
```

因此 ESP32 配网页面建议填写：

```text
MQTT Server: broker.emqx.io
MQTT User: admin
MQTT Password: admin123
```

后端 `.env` 也必须保持一致：

```env
MQTT_BROKER_URL=broker.emqx.io
MQTT_BROKER_PORT=1883
MQTT_BROKER_USERNAME=admin
MQTT_BROKER_PASSWORD=admin123
MQTT_TOPIC_ROOT=tomato_hnsw0001
```

如果后端连本地 `mosquitto`，而 ESP32 连公网 `broker.emqx.io`，页面就收不到设备数据，也无法控制设备。

本地 Mosquitto 仍然可以保留给离线调试使用：

```text
mosquitto:1883
```

如果希望完全走局域网离线调试，需要同时修改两边：

```text
后端 MQTT_BROKER_URL=mosquitto
ESP32 MQTT Server=电脑局域网IP
```

注意：`mosquitto` 这个名字只给 Docker 容器内部使用，ESP32 不能填写 `mosquitto`。

默认推荐直接使用公网 `broker.emqx.io`，这样设备不需要和电脑处在同一个 WiFi 下。

## 5. ESP32 配网流程

1. 确保电脑已经启动 Docker 项目。
2. 确保电脑和 ESP32 将要连接同一个 WiFi。
3. 打开 ESP32 电源。
4. 连接 ESP32 热点：

```text
WiFi: A-tomato
Password: 12345678
```

5. 浏览器打开：

```text
http://192.168.4.1
```

6. 填写 WiFi 名称、WiFi 密码。
7. MQTT Server 填：

```text
broker.emqx.io
```

8. MQTT User 填 `admin`，MQTT Password 填 `admin123`。
9. 保存配置并重启 ESP32。

## 6. 新控制命令

所有控制命令都由后端发布到：

```text
tomato_hnsw0001/set
```

Payload 格式：

```json
{
  "request_id": "server-001",
  "cmd": "03",
  "data": {
    "value": 1
  }
}
```

支持的命令：

| cmd | 功能 | data 示例 |
| --- | --- | --- |
| `01` | 红光亮度 | `{"value":80}` |
| `02` | 蓝光亮度 | `{"value":60}` |
| `03` | 水泵开关 | `{"value":1}` 或 `{"value":0}` |
| `04` | 补光灯总开关 | `{"value":1}` 或 `{"value":0}` |
| `05` | 补光模式 | `{"value":2}` |
| `06` | 水泵间隔分钟 | `{"value":30}` |
| `07` | 水泵持续秒数 | `{"value":10}` |
| `08` | 手动/AI 模式 | `{"value":"manual"}` 或 `{"value":"ai"}` |
| `09` | 休眠时间段 | `{"start_hour":22,"start_minute":0,"end_hour":6,"end_minute":0}` |

## 7. 后端接口

升级后，前端或接口可以调用：

```text
POST /api/iot/actuator/irrigation?state=true
POST /api/iot/actuator/pump?state=true
POST /api/iot/mode?mode=manual
POST /api/iot/mode?mode=ai
POST /api/iot/light/red?value=80
POST /api/iot/light/blue?value=60
POST /api/iot/light/mode?value=2
POST /api/iot/pump/interval?value=30
POST /api/iot/pump/duration?value=10
POST /api/iot/rest-schedule
```

`/api/iot/rest-schedule` 请求体示例：

```json
{
  "start_hour": 22,
  "start_minute": 0,
  "end_hour": 6,
  "end_minute": 0
}
```

旧接口兼容说明：

| 老功能 | 新处理方式 |
| --- | --- |
| `/air/post` | 后端仍保留订阅，过渡期兼容 |
| `/soil/post` | 后端仍保留订阅，过渡期兼容 |
| `irrigation` | 映射为新协议水泵命令 `cmd=03` |
| `auto` | 兼容映射为 `manual` |
| `mist` | 新协议没有对应命令，不再实际控制 |
| `ventilation` | 新协议没有对应命令，不再实际控制 |

## 8. 启动项目

Windows PowerShell：

```powershell
docker compose up -d
```

如果后端和依赖已经启动，只需要单独启动前端：

```powershell
docker compose up -d --no-deps web
```

访问页面：

```text
http://localhost:5173
```

后端健康检查：

```text
http://localhost:5050/api/system/health
```

## 9. 验证 MQTT 是否连通

查看后端日志：

```powershell
docker logs api-dev --tail 100
```

正常情况下应看到后端连接到 MQTT，并订阅这些主题：

```text
tomato_hnsw0001/result
tomato_hnsw0001/state
tomato_hnsw0001/telemetry
tomato_hnsw0001/availability
/air/post
/soil/post
```

在本机监听设备消息：

```powershell
docker exec mosquitto mosquitto_sub -h localhost -p 1883 -t "tomato_hnsw0001/#" -v
```

在另一个终端模拟下发水泵开启：

```powershell
docker exec mosquitto mosquitto_pub -h localhost -p 1883 -t "tomato_hnsw0001/set" -m "{\"request_id\":\"test-001\",\"cmd\":\"03\",\"data\":{\"value\":1}}"
```

如果 ESP32 已连接，监听窗口应看到 `state`、`result` 或 `telemetry` 相关消息。

## 10. 常见问题

### 页面能打开，但控制不了设备

优先检查后端和 ESP32 是否连的是同一个 MQTT Broker。当前推荐二者都使用：

```text
broker.emqx.io:1883
```

如果后端 `.env` 是 `mosquitto`，而 ESP32 是 `broker.emqx.io`，就会出现页面无数据、无法控制设备。

### 使用局域网 Mosquitto 时连不上

如果选择离线局域网模式，才需要检查 Windows 防火墙是否允许局域网设备访问 TCP `1883` 端口。

也要确认电脑和 ESP32 在同一个 WiFi 或同一个局域网，并通过以下命令查电脑 WiFi IPv4 地址：

```powershell
ipconfig
```

找当前 WiFi 网卡下面的 IPv4 地址。不要使用 Docker、WSL、虚拟网卡的地址。

### 后端能启动，但没有收到数据

检查这些项：

```text
MQTT_TOPIC_ROOT 是否为 tomato_hnsw0001
ESP32 是否发布到 tomato_hnsw0001/telemetry
ESP32 是否订阅 tomato_hnsw0001/set
后端和 ESP32 是否连接同一个 MQTT Broker
```

## 11. 推荐验收标准

升级完成后，至少确认以下结果：

```text
docker compose ps 中 api-dev、mosquitto、web-dev 正常运行
http://localhost:5050/api/system/health 返回 status=ok
http://localhost:5173 可以打开页面
ESP32 配置 MQTT Server 为 broker.emqx.io
mosquitto_sub 能监听到 tomato_hnsw0001/telemetry 或 availability
页面点击水泵控制后，ESP32 能收到 tomato_hnsw0001/set 命令
```
