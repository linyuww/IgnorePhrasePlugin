# 忽略短语插件 (IgnorePhrasePlugin)

这是一个用于自动忽略特定消息的插件。当用户输入的消息匹配预设的正则表达式时，机器人将自动忽略该消息，不进行任何回复或思考。

## 功能

- **自动忽略**：当用户输入匹配特定正则表达式的消息时，机器人将自动忽略该消息，不进行任何回复或思考。
- **动态管理**：支持通过聊天命令动态添加、删除和查看忽略规则。
- **正则支持**：完全支持 Python 正则表达式语法。

![插件演示截图](https://via.placeholder.com/800x400?text=Plugin+Screenshot+Placeholder)

## 安装

1. 将本插件文件夹 `ignore_phrase_plugin` 放入 MaiBot 的 `plugins` 目录中。
2. 重启 MaiBot。
3. 在控制台或日志中确认插件加载成功。

## 使用方法

### 添加规则
发送命令：
```
.ignore add <正则表达式>
```
例如：
- 忽略包含 "测试" 的消息：`.ignore add 测试`
- 忽略以 "DEBUG" 开头的消息：`.ignore add ^DEBUG`

### 删除规则
发送命令：
```
.ignore del <正则表达式>
```
例如：`.ignore del 测试`

### 查看列表
发送命令：
```
.ignore list
```

## 注意事项

- 规则使用 Python 的 `re` 模块进行匹配。
- 匹配是部分匹配（`re.search`），如果需要全匹配请使用 `^` 和 `$`。
