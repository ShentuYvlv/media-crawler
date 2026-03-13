# API 参数说明文档

## 一、通用参数（所有API都需要）

这些参数会自动添加到每个请求中：

### 基础标识参数

| 参数名 | 示例值 | 说明 |
|--------|--------|------|
| `os_type` | `web` | 操作系统类型，web表示网页版 |
| `app` | `heybox` | 应用标识，heybox是小黑盒的应用名称 |
| `client_type` | `web` | 客户端类型，标识是网页客户端 |
| `version` | `999.0.4` | 应用版本号 |
| `web_version` | `2.5` | 网页版本号 |
| `x_client_type` | `web` | 扩展的客户端类型标识 |
| `x_app` | `heybox_website` | 扩展的应用标识，表示小黑盒网站 |

### 设备信息参数

| 参数名 | 示例值 | 说明 |
|--------|--------|------|
| `x_os_type` | `Windows` | 操作系统类型（Windows/Mac/Linux） |
| `device_info` | `Chrome` | 设备信息，通常是浏览器类型 |
| `device_id` | `2c2fef8385ccef915e3b3caf94e3aa06` | 设备唯一标识，用于识别设备 |
| `heybox_id` | `` | 用户ID，未登录时为空 |

### 安全验证参数

| 参数名 | 示例值 | 说明 |
|--------|--------|------|
| `hkey` | `UVD0D97` | **签名密钥**，由算法自动生成，用于验证请求合法性 |
| `_time` | `1770356391` | **时间戳**（秒），自动生成，用于防止重放攻击 |
| `nonce` | `C8B6CB8884949DDE30311CC2281A9642` | **随机数**，自动生成的MD5字符串，用于防止重放攻击 |

---

## 二、API特定参数

不同的API需要不同的特定参数，以下是各个API的参数说明：

### 1. 动态流 (feeds)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `pull` | string | 拉取方式：0=下拉刷新，1=上拉加载 | `0` |
| `offset` | string | 偏移量，用于分页加载 | `0` |
| `dw` | string | 设备宽度（像素） | `844` |

**使用示例：**
```bash
node generate.js feeds offset=20 dw=1920
```

### 2. 用户资料 (user_profile)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `userid` | string | **必填** - 要查询的用户ID | `12345678` |

**使用示例：**
```bash
node generate.js user_profile userid=12345678
```

### 3. 帖子详情 (link_tree)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `link_id` | string | **必填** - 帖子ID | `87654321` |

**使用示例：**
```bash
node generate.js link_tree link_id=87654321
```

### 4. 评论列表 (comment_list)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `link_id` | string | **必填** - 帖子ID | `87654321` |
| `offset` | string | 偏移量，用于分页 | `0` |
| `limit` | string | 每页数量 | `30` |

**使用示例：**
```bash
node generate.js comment_list link_id=87654321 offset=0 limit=50
```

### 5. 新闻列表 (news_list)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `offset` | string | 偏移量，用于分页 | `0` |
| `limit` | string | 每页数量 | `20` |

**使用示例：**
```bash
node generate.js news_list offset=0 limit=30
```

### 6. 推荐用户 (recommend_user)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `offset` | string | 偏移量，用于分页 | `0` |
| `limit` | string | 每页数量 | `20` |

**使用示例：**
```bash
node generate.js recommend_user limit=50
```

### 7. 热门话题 (hot_topics)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `offset` | string | 偏移量，用于分页 | `0` |
| `limit` | string | 每页数量 | `20` |

**使用示例：**
```bash
node generate.js hot_topics offset=0 limit=30
```

### 8. 游戏列表 (game_list)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `offset` | string | 偏移量，用于分页 | `0` |
| `limit` | string | 每页数量 | `30` |

**使用示例：**
```bash
node generate.js game_list limit=50
```

### 9. 用户帖子 (user_posts)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `userid` | string | **必填** - 用户ID | `12345678` |
| `offset` | string | 偏移量，用于分页 | `0` |
| `limit` | string | 每页数量 | `20` |

**使用示例：**
```bash
node generate.js user_posts userid=12345678 offset=0 limit=30
```

### 10. 通知消息 (notifications)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `notice_type` | string | 通知类型：0=全部，1=评论，2=点赞，3=关注 | `0` |

**使用示例：**
```bash
node generate.js notifications notice_type=1
```

### 11. 搜索发现 (search_found)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `force_refresh` | string | 是否强制刷新：true/false | `false` |

**使用示例：**
```bash
node generate.js search_found force_refresh=true
```

### 12. 数据上报 (data_report)

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `type` | string | 上报类型：104=页面访问 | `104` |
| `time_` | string | 时间戳（自动生成） | `1770356391` |

**使用示例：**
```bash
node generate.js data_report type=104
```

### 13. 其他API

以下API不需要额外参数，直接调用即可：

- **emojis_list** - 表情列表
- **topic_categories** - 话题分类
- **search_welcome** - 搜索欢迎页

**使用示例：**
```bash
node generate.js emojis_list
node generate.js topic_categories
```

---

## 三、参数说明总结

### 🔐 安全验证机制

小黑盒API使用三重验证机制来确保请求的安全性：

1. **hkey（签名密钥）** - 通过复杂的算法计算得出，包含了路径、时间戳、nonce的混淆信息
2. **_time（时间戳）** - 防止请求过期，服务器会验证时间戳的有效性
3. **nonce（随机数）** - 防止重放攻击，每次请求都应该使用不同的nonce

这三个参数由脚本自动生成，无需手动填写。

### 📊 分页参数

大多数列表类API都支持分页参数：

- **offset** - 偏移量，表示从第几条数据开始获取（从0开始）
- **limit** - 每页数量，表示一次获取多少条数据

**分页示例：**
```bash
# 获取第1页（前20条）
node generate.js feeds offset=0 limit=20

# 获取第2页（21-40条）
node generate.js feeds offset=20 limit=20

# 获取第3页（41-60条）
node generate.js feeds offset=40 limit=20
```

### 🎯 必填参数

某些API需要必填参数，否则无法正常工作：

- **user_profile** - 必须提供 `userid`
- **link_tree** - 必须提供 `link_id`
- **comment_list** - 必须提供 `link_id`
- **user_posts** - 必须提供 `userid`

**错误示例：**
```bash
# ❌ 错误：缺少必填参数
node generate.js user_profile

# ✅ 正确：提供了userid
node generate.js user_profile userid=12345678
```

### 🔧 自定义参数

你可以在命令行中覆盖或添加任何参数：

```bash
# 覆盖默认参数
node generate.js feeds offset=100 limit=50 dw=1920

# 添加额外参数
node generate.js emojis_list custom_param=value
```

---

## 四、常见问题

### Q1: hkey是什么？为什么需要它？

**A:** hkey是小黑盒API的签名密钥，用于验证请求的合法性。它通过复杂的算法计算得出，包含了请求路径、时间戳和随机数的混淆信息。没有正确的hkey，服务器会拒绝请求。

### Q2: 为什么每次生成的URL都不一样？

**A:** 因为每次请求都会生成新的时间戳（`_time`）和随机数（`nonce`），这两个参数会影响hkey的计算结果，所以每次生成的完整URL都是唯一的。

### Q3: 生成的URL有效期是多久？

**A:** 通常API会验证时间戳的有效性，建议在生成URL后立即使用。如果时间戳过期（通常是几分钟到几小时），服务器可能会拒绝请求。

### Q4: 如何获取用户ID或帖子ID？

**A:** 这些ID通常可以从小黑盒网站的URL中获取，例如：
- 用户主页：`https://api.xiaoheihe.cn/v3/bbs/app/profile/user/12345678` → userid是12345678
- 帖子详情：`https://api.xiaoheihe.cn/bbs/app/link/87654321` → link_id是87654321

### Q5: 可以用这个工具做什么？

**A:** 这个工具主要用于：
- 学习和研究小黑盒API的工作原理
- 开发小黑盒相关的自动化工具
- 测试API接口
- 数据分析和爬虫开发（请遵守网站的使用条款）

---

## 五、最佳实践

1. **合理使用分页** - 不要一次请求过多数据，使用合理的limit值
2. **尊重API限制** - 不要频繁请求，避免给服务器造成压力
3. **保护隐私** - 不要滥用用户数据，遵守隐私保护法规
4. **错误处理** - 在实际应用中要处理API可能返回的错误
5. **遵守规则** - 遵守小黑盒的使用条款和服务协议


