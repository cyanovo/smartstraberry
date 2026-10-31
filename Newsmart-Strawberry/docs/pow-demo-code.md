# 区块链工作量证明 - 比赛演示代码

## 代码位置

`backend/package/yuxi/traceability/blockchain.py` **第 34-58 行**

---

## 完整代码 (13行)

```python
def _hash(record: Dict[str, Any]) -> str:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def proof_of_work(block_data: Dict[str, Any], difficulty: int = 4) -> tuple:
    """工作量证明：前 difficulty 位为 0"""
    prefix = "0" * difficulty
    nonce = 0
    while True:
        block_data["nonce"] = nonce
        h = _hash(block_data)
        if h.startswith(prefix):
            return h, nonce
        nonce += 1
```

---

## 逐行代码解释

### 第1-3行：哈希计算函数

```python
def _hash(record: Dict[str, Any]) -> str:                    # 定义函数，接收字典，返回字符串
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False)  # 将字典转为JSON字符串，sort_keys保证顺序一致
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()    # 计算SHA-256哈希，返回64位十六进制字符串
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 1 | `def _hash(record: Dict[str, Any]) -> str:` | 定义函数，接收字典类型参数，返回字符串 |
| 2 | `raw = json.dumps(record, sort_keys=True, ensure_ascii=False)` | 将字典序列化为JSON字符串，`sort_keys=True`保证相同数据总是生成相同字符串 |
| 3 | `return hashlib.sha256(raw.encode("utf-8")).hexdigest()` | 计算SHA-256哈希值，返回64位十六进制字符串 |

### 第5-13行：工作量证明函数

```python
def proof_of_work(block_data: Dict[str, Any], difficulty: int = 4) -> tuple:  # 接收区块数据和难度系数
    """工作量证明：前 difficulty 位为 0"""
    prefix = "0" * difficulty                                # 生成目标前缀，如difficulty=4 → "0000"
    nonce = 0                                                # 初始化nonce为0
    while True:                                              # 无限循环，直到找到符合条件的哈希
        block_data["nonce"] = nonce                          # 将nonce写入区块数据
        h = _hash(block_data)                                # 计算当前区块的哈希值
        if h.startswith(prefix):                             # 检查哈希是否以"0000"开头
            return h, nonce                                  # 找到！返回哈希值和nonce
        nonce += 1                                           # 没找到，nonce加1，继续尝试
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 5 | `def proof_of_work(block_data: Dict[str, Any], difficulty: int = 4) -> tuple:` | 定义函数，返回元组(哈希值, nonce) |
| 7 | `prefix = "0" * difficulty` | 生成目标前缀，difficulty=4时为"0000" |
| 8 | `nonce = 0` | 初始化nonce计数器 |
| 9 | `while True:` | 无限循环，直到找到有效哈希 |
| 10 | `block_data["nonce"] = nonce` | 将当前nonce写入区块数据 |
| 11 | `h = _hash(block_data)` | 计算包含当前nonce的区块哈希 |
| 12 | `if h.startswith(prefix):` | 检查哈希是否满足难度要求 |
| 13 | `return h, nonce` | 满足条件，返回哈希值和对应的nonce |
| 14 | `nonce += 1` | 不满足条件，nonce加1继续尝试 |

---

## 核心概念

| 概念 | 说明 | 示例 |
|------|------|------|
| **SHA-256** | 哈希算法，输出64位十六进制字符串 | `"a1b2c3d4e5f6..."` |
| **nonce** | 随机数，用于挖矿 | `0, 1, 2, 3, ...` |
| **difficulty** | 难度系数，决定前缀0的个数 | `4` → 前缀 `"0000"` |
| **挖矿** | 不断尝试nonce直到找到符合条件的哈希 | 循环计算 |

---

## 代码逻辑图解

```
┌─────────────────────────────────────────────────────────────┐
│                    工作量证明流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  输入: block_data = {                                       │
│      "index": 1,                                            │
│      "timestamp": 1690000000,                               │
│      "data": {"event": "创建批次"},                          │
│      "previous_hash": "0000abc123...",                       │
│      "nonce": 0  ← 这个值会不断变化                          │
│  }                                                          │
│                                                             │
│  目标: 找到一个nonce，使得hash以"0000"开头                    │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 尝试 nonce=0                                          │ │
│  │ hash(block_data) = "a1b2c3d4e5f6..." ✗ 不以0000开头   │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ 尝试 nonce=1                                          │ │
│  │ hash(block_data) = "f7e8d9c0b1a2..." ✗ 不以0000开头   │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ 尝试 nonce=2                                          │ │
│  │ hash(block_data) = "c3b4a5968778..." ✗ 不以0000开头   │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ ...                                                   │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ 尝试 nonce=12345                                      │ │
│  │ hash(block_data) = "0000a1b2c3d4..." ✓ 以0000开头！   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  输出: ("0000a1b2c3d4...", 12345)                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 为什么能防篡改？

```
假设攻击者想篡改区块1的数据：

原始链: 区块0 → 区块1 → 区块2 → 区块3
              ↓
        修改区块1的数据

修改后: 区块0 → 区块1' → 区块2 → 区块3
                ↓
          哈希值变化！

问题: 区块2存储的是区块1的旧哈希
      现在区块1的哈希变了，区块2的previous_hash对不上了！

解决: 必须重新计算区块1的工作量证明
      然后重新计算区块2的工作量证明
      然后重新计算区块3的工作量证明
      ...

结论: 攻击者需要掌握超过全网50%的算力才能成功篡改
      这在实际中几乎是不可能的
```

---

## 演示话术

### 介绍哈希函数 (第1-3行)

> "这是SHA-256哈希函数，将任意长度的数据转换为64位固定长度的字符串。特点是：输入微小变化会导致输出完全不同，且无法反推原始数据。"

### 介绍工作量证明 (第5-13行)

> "这是区块链的核心——工作量证明。我们不断尝试nonce值，计算区块哈希，直到找到以4个0开头的哈希。这个过程就像'挖矿'，需要消耗计算资源，从而保证数据难以被篡改。如果有人想修改历史区块，必须重新计算该区块之后所有区块的工作量证明，这在计算上是不可行的。"

---

## 技术亮点总结

1. **SHA-256 哈希算法**：密码学安全，不可逆
2. **工作量证明 (PoW)**：通过计算难度保证数据难以篡改
3. **链式结构**：每个区块包含前一个区块的哈希，形成链式依赖
4. **防篡改机制**：修改任意区块需要重新计算后续所有区块

---

## 相关代码

| 函数 | 文件位置 | 说明 |
|------|----------|------|
| `_hash` | `blockchain.py:34-36` | SHA-256哈希计算 |
| `calculate_hash` | `blockchain.py:39-46` | 区块哈希计算 |
| `proof_of_work` | `blockchain.py:49-58` | 工作量证明 |
| `add_block` | `blockchain.py:75-96` | 添加新区块 |
| `verify_chain` | `blockchain.py:117-148` | 验证链完整性 |

---

**文档版本**：v1.0
**最后更新**：2026-07-28
