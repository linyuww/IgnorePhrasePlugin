# IgnorePhrasePlugin - 忽略短语插件

一个用于 MaiBot 的消息过滤插件，可以自动忽略包含特定短语或匹配正则表达式的消息。

![MaiBot Plugin](https://img.shields.io/badge/MaiBot-Plugin-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ 功能特性

- 🔤 短语匹配过滤（支持 contains/exact/startswith/endswith 四种模式）
- 🔣 正则表达式匹配过滤
- 🔠 大小写敏感性配置
- 🖥️ WebUI 可视化配置
- 💬 聊天命令动态管理（与 WebUI 完全互通）
- 🔐 白名单/黑名单权限控制

## 📦 安装

将 `IgnorePhrasePlugin` 文件夹复制到 MaiBot 的 `plugins` 目录下，重启 MaiBot 即可。

### 依赖

插件需要以下 Python 依赖：
```bash
pip install tomli tomli_w
```

## ⚙️ 配置

插件首次运行会自动生成 `config.toml` 配置文件，可通过 WebUI 或直接编辑文件进行配置。

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `plugin.enabled` | 是否启用插件 | `true` |
| `phrases.enabled` | 是否启用短语匹配 | `true` |
| `phrases.list` | 屏蔽词列表 | `[]` |
| `phrases.match_mode` | 匹配模式 | `contains` |
| `phrases.case_sensitive` | 是否区分大小写 | `false` |
| `regex.enabled` | 是否启用正则匹配 | `true` |
| `regex.patterns` | 正则表达式列表 | `[]` |
| `regex.case_sensitive` | 正则是否区分大小写 | `false` |
| `user_control.list_type` | 权限模式 | `whitelist` |
| `user_control.list` | 有权限的用户QQ号列表 | `[]` |

### 匹配模式

| 模式 | 说明 |
|------|------|
| `contains` | 消息包含屏蔽词即拦截 |
| `exact` | 消息完全等于屏蔽词才拦截 |
| `startswith` | 消息以屏蔽词开头才拦截 |
| `endswith` | 消息以屏蔽词结尾才拦截 |

## 📝 命令

| 命令 | 说明 | 权限 |
|------|------|------|
| `/ignore` | 显示帮助信息 | 所有人 |
| `/ignore list` | 列出所有屏蔽词 | 所有人 |
| `/ignore add <词>` | 添加屏蔽词 | 需要权限 |
| `/ignore addr <正则>` | 添加正则表达式 | 需要权限 |
| `/ignore del <词>` | 删除屏蔽词 | 需要权限 |
| `/ignore delr <正则>` | 删除正则表达式 | 需要权限 |

## 💾 数据存储

WebUI 和聊天命令添加的屏蔽词都存储在 `config.toml` 文件中，两者完全互通。

## 🔐 权限控制

通过 `user_control` 配置控制谁可以使用添加/删除命令：

- `whitelist` 模式：只有列表中的用户可以操作
- `blacklist` 模式：列表中的用户不能操作

## 📋 配置示例

```toml
# config.toml 示例

[plugin]
enabled = true

[phrases]
enabled = true
list = ["广告", "推广", "加群"]
match_mode = "contains"
case_sensitive = false

[regex]
enabled = true
patterns = ["^/spam.*", "https?://.*\\.xyz"]
case_sensitive = false

[user_control]
list_type = "whitelist"
list = ["123456789"]
```

### 命令演示

![1.png](https://youke2.picui.cn/s1/2025/12/25/694d5802f255e.png)
![2.png](https://youke2.picui.cn/s1/2025/12/25/694d58031ae2b.png)

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证开源。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

- 仓库地址：https://github.com/linyuww/IgnorePhrasePlugin
- 作者：[linyuww](https://github.com/linyuww)
