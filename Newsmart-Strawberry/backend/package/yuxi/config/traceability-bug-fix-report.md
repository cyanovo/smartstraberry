## 🔍 日志分析

### 关键错误日志

```log
2026-08-05 16:55:01 - ERROR - manager.py:495 - PostgreSQL async operation failed: 400: 批次编号 4852485283625863 已存在
2026-08-05 16:55:01 - ERROR - manager.py:495 - PostgreSQL async operation failed: 'NoneType' object is not subscriptable
2026-08-05 16:55:39 - ERROR - manager.py:495 - PostgreSQL async operation failed: 'NoneType' object is not subscriptable
2026-08-05 16:57:36 - ERROR - manager.py:495 - PostgreSQL async operation failed: 'NoneType' object is not subscriptable
2026-08-05 16:57:37 - ERROR - manager.py:495 - PostgreSQL async operation failed: 'NoneType' object is not subscriptable
2026-08-05 16:58:38 - ERROR - manager.py:495 - PostgreSQL async operation failed: 'NoneType' object is not subscriptable
```

### 错误模式识别

1. **批次编号重复错误**：批次编号 `4852485283625863` 已存在
2. **空值访问错误**：`'NoneType' object is not subscriptable` - 尝试对 None 值进行下标操作

## 🐛 Bug 根源分析

### 问题位置

#### 1. 数据库层 (`yuxi/traceability/db.py`)

**函数**: `get_package(pid: str)` (第 891-901 行)

```python
def get_package(pid: str) -> Optional[Package]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM packages WHERE id = ?", (pid,)).fetchone()
    if not row:
        conn.close()
        return None
    tc_row = conn.execute("SELECT code FROM trace_codes WHERE package_id = ?", (pid,)).fetchone()
    conn.close()
    d = dict(row)
    d["trace_code"] = tc_row["code"] if tc_row else None  # ✅ 已正确处理
    return Package(**d)
```

**函数**: `list_packages(batch_id: str)` (第 903-913 行)

```python
def list_packages(batch_id: str) -> List[Package]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM packages WHERE batch_id = ? ORDER BY package_date", (batch_id,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        tc_row = conn.execute("SELECT code FROM trace_codes WHERE package_id = ?", (r["id"],)).fetchone()
        d["trace_code"] = tc_row["code"] if tc_row else None  # ⚠️ 需要注意空列表情况
        result.append(Package(**d))
    conn.close()
    return result
```

#### 2. API 路由层 (`server/routers/trace_router.py`)

**函数**: `trace_by_batch_code(batch_code: str)` (第 260-306 行)

```python
@trace.get("/query/batch/{batch_code}")
async def trace_by_batch_code(batch_code: str):
    batch = db.get_batch_by_code(batch_code)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    # ...

    report = {
        # ...
        "harvest_date": batch.harvests[-1].get("harvest_date") if batch.harvests else None,
        "harvest_grade": batch.harvests[-1].get("grade") if batch.harvests else None,
        "harvest_yield_kg": batch.harvests[-1].get("yield_kg") if batch.harvests else None,
        # ...
        "package_info": {
            "package_date": batch.packages[-1].get("package_date"),
            "weight_kg": batch.packages[-1].get("weight_kg"),
            "lot_number": batch.packages[-1].get("lot_number"),
        } if batch.packages else None,  # ⚠️ 问题在这里！
    }
```

### 问题详解

**问题 1：空列表访问**
- 当批次存在但还没有包装记录时，`batch.packages` 是空列表 `[]`
- 虽然有 `if batch.packages` 检查，但在某些数据不一致的情况下可能失效
- 使用 `batch.packages[-1]` 会抛出 `IndexError` 或导致 `NoneType` 错误

**问题 2：并发访问问题**
- SQLite 数据库在多 worker 并发时可能出现锁竞争
- 包装记录和溯源码生成之间存在时间窗口，可能导致数据不一致

**问题 3：数据完整性**
- 创建批次时返回成功，但查询时数据不完整
- 可能是数据库迁移或数据清理导致的数据丢失

## ✅ 修复方案

### 修复 1：增强空列表检查

**文件**: `server/routers/trace_router.py`

**修改前**:
```python
"package_info": {
    "package_date": batch.packages[-1].get("package_date"),
    "weight_kg": batch.packages[-1].get("weight_kg"),
    "lot_number": batch.packages[-1].get("lot_number"),
} if batch.packages else None,
```

**修改后**:
```python
"package_info": {
    "package_date": batch.packages[-1].get("package_date"),
    "weight_kg": batch.packages[-1].get("weight_kg"),
    "lot_number": batch.packages[-1].get("lot_number"),
} if batch.packages and len(batch.packages) > 0 else None,
```

### 修复 2：添加错误处理和日志

**文件**: `package/yuxi/traceability/db.py`

在关键函数中添加异常处理和日志记录：

```python
def get_package(pid: str) -> Optional[Package]:
    try:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM packages WHERE id = ?", (pid,)).fetchone()
        if not row:
            conn.close()
            return None
        tc_row = conn.execute("SELECT code FROM trace_codes WHERE package_id = ?", (pid,)).fetchone()
        conn.close()
        d = dict(row)
        d["trace_code"] = tc_row["code"] if tc_row else None
        return Package(**d)
    except Exception as e:
        logger.error(f"Error getting package {pid}: {e}")
        return None

def list_packages(batch_id: str) -> List[Package]:
    try:
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM packages WHERE batch_id = ? ORDER BY package_date", (batch_id,)).fetchall()
        result = []
        for r in rows:
            try:
                d = dict(r)
                tc_row = conn.execute("SELECT code FROM trace_codes WHERE package_id = ?", (r["id"],)).fetchone()
                d["trace_code"] = tc_row["code"] if tc_row else None
                result.append(Package(**d))
            except Exception as e:
                logger.error(f"Error processing package {r['id']}: {e}")
                continue
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error listing packages for batch {batch_id}: {e}")
        return []
```

### 修复 3：优化查询函数

**文件**: `server/routers/trace_router.py`

在 `trace_by_batch_code` 函数中添加更安全的数据访问：

```python
# 获取最近的采摘记录
harvest_date = None
harvest_grade = None
harvest_yield_kg = None
if batch.harvests and len(batch.harvests) > 0:
    try:
        last_harvest = batch.harvests[-1]
        harvest_date = last_harvest.get("harvest_date")
        harvest_grade = last_harvest.get("grade")
        harvest_yield_kg = last_harvest.get("yield_kg")
    except (IndexError, KeyError) as e:
        logger.error(f"Error accessing harvest data: {e}")

# 获取包装信息
package_info = None
if batch.packages and len(batch.packages) > 0:
    try:
        last_package = batch.packages[-1]
        package_info = {
            "package_date": last_package.get("package_date"),
            "weight_kg": last_package.get("weight_kg"),
            "lot_number": last_package.get("lot_number"),
        }
    except (IndexError, KeyError) as e:
        logger.error(f"Error accessing package data: {e}")
```

## 🧪 测试建议

1. **创建测试批次**：验证批次创建流程
2. **添加包装记录**：确保包装记录正确生成溯源码
3. **查询溯源码**：验证溯源码查询功能
4. **查询批次编号**：验证批次编号查询功能
5. **并发测试**：多用户同时创建和查询
6. **边界测试**：测试空数据、无效数据等情况

## 📊 监控建议

1. **添加详细日志**：在关键操作点记录日志
2. **数据库监控**：监控 SQLite 锁等待和死锁
3. **性能监控**：监控查询响应时间
4. **错误告警**：设置错误率告警阈值

## 🔄 部署步骤

1. 备份当前数据库
2. 应用代码修复
3. 重启应用服务
4. 验证修复效果
5. 监控系统日志

## 📝 后续改进建议

1. **迁移到 PostgreSQL**：对于高并发场景，考虑使用 PostgreSQL
2. **添加缓存层**：使用 Redis 缓存热点数据
3. **实现数据库连接池**：优化数据库连接管理
4. **添加数据校验**：在写入前验证数据完整性
5. **实现事务管理**：确保相关操作的原子性

---

**文档生成时间**: 2026-08-05
**分析工具**: Claude Code
**状态**: 待验证修复
