"""
IgnorePhrasePlugin - 忽略短语插件

用于在消息处理流程中拦截和忽略特定的消息。
支持精确短语匹配和正则表达式匹配两种方式。
"""

import re
import logging
from pathlib import Path
from typing import List, Tuple, Type, Dict, Optional

try:
    import tomli
    import tomli_w
except ImportError:
    import tomllib as tomli
    tomli_w = None

from src.plugin_system import (
    BasePlugin,
    register_plugin,
    ComponentInfo,
    ConfigField,
    BaseEventHandler,
    BaseCommand,
    EventType,
    MaiMessages,
)

logger = logging.getLogger(__name__)


# ===== 配置管理器 =====

class ConfigManager:
    """
    负责直接读写 config.toml 文件。
    命令添加的屏蔽词会直接写入 config.toml，与 webui 完全互通。
    """
    _instance = None
    config_path: Optional[Path] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def load(self, plugin_dir: str):
        """设置配置文件路径"""
        self.config_path = Path(plugin_dir) / "config.toml"
        logger.info(f"配置文件路径: {self.config_path}")
        if tomli_w is None:
            logger.warning("tomli_w 未安装，命令添加/删除功能将不可用")

    def _read_config(self) -> Dict:
        """读取配置文件"""
        if not self.config_path or not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return {}
        try:
            with open(self.config_path, "rb") as f:
                config = tomli.load(f)
                logger.debug(f"读取配置成功: {list(config.keys())}")
                return config
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            return {}

    def _write_config(self, config: Dict) -> bool:
        """写入配置文件，返回是否成功"""
        if not self.config_path:
            logger.error("配置文件路径未设置")
            return False
        if tomli_w is None:
            logger.error("tomli_w 未安装，无法写入配置。请安装: pip install tomli_w")
            return False
        try:
            with open(self.config_path, "wb") as f:
                tomli_w.dump(config, f)
            logger.info(f"配置已保存到: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"写入配置文件失败: {e}", exc_info=True)
            return False

    def get_phrases(self) -> List[str]:
        """获取屏蔽词列表"""
        config = self._read_config()
        return config.get("phrases", {}).get("list", [])

    def get_patterns(self) -> List[str]:
        """获取正则表达式列表"""
        config = self._read_config()
        return config.get("regex", {}).get("patterns", [])

    def add_phrase(self, phrase: str) -> bool:
        """添加屏蔽词"""
        config = self._read_config()
        if "phrases" not in config:
            config["phrases"] = {}
        phrases = list(config["phrases"].get("list", []))
        if phrase in phrases:
            return False
        phrases.append(phrase)
        config["phrases"]["list"] = phrases
        return self._write_config(config)

    def add_pattern(self, pattern: str) -> bool:
        """添加正则表达式"""
        config = self._read_config()
        if "regex" not in config:
            config["regex"] = {}
        patterns = list(config["regex"].get("patterns", []))
        if pattern in patterns:
            return False
        patterns.append(pattern)
        config["regex"]["patterns"] = patterns
        return self._write_config(config)

    def del_phrase(self, phrase: str) -> bool:
        """删除屏蔽词"""
        config = self._read_config()
        phrases = list(config.get("phrases", {}).get("list", []))
        if phrase not in phrases:
            return False
        phrases.remove(phrase)
        if "phrases" not in config:
            config["phrases"] = {}
        config["phrases"]["list"] = phrases
        return self._write_config(config)

    def del_pattern(self, pattern: str) -> bool:
        """删除正则表达式"""
        config = self._read_config()
        patterns = list(config.get("regex", {}).get("patterns", []))
        if pattern not in patterns:
            return False
        patterns.remove(pattern)
        if "regex" not in config:
            config["regex"] = {}
        config["regex"]["patterns"] = patterns
        return self._write_config(config)


# 全局配置管理器实例
config_manager = ConfigManager()


# ===== 权限检查工具函数 =====

def check_permission(user_id: str, config: Optional[Dict]) -> bool:
    """
    检查用户是否有权限执行命令
    """
    if not user_id or not config:
        return False

    user_control = config.get("user_control", {})
    list_type = user_control.get("list_type", "whitelist")
    user_list_raw = user_control.get("list", [])
    user_list = {str(u) for u in user_list_raw} if user_list_raw else set()

    if list_type == "whitelist":
        return user_id in user_list
    elif list_type == "blacklist":
        return user_id not in user_list
    return False


class PermissionMixin:
    """权限检查混入类"""

    async def check_user_permission(self) -> bool:
        try:
            user_id = str(self.message.message_info.user_info.user_id)
            return check_permission(user_id, self.plugin_config)
        except Exception:
            return False

    async def send_no_permission(self) -> Tuple[bool, str, bool]:
        await self.send_text("❌ 你没有权限执行此命令")
        return False, "权限不足", True


# ===== 命令组件 =====

class IgnoreCommand(BaseCommand):
    """
    忽略词管理命令
    
    /ignore - 显示帮助
    /ignore list - 列出所有屏蔽词和正则
    /ignore add <词> - 添加屏蔽词
    /ignore add regex <正则> - 添加正则表达式
    /ignore del <词> - 删除屏蔽词
    /ignore del regex <正则> - 删除正则表达式
    """

    command_name = "ignore"
    command_description = "管理忽略词列表"
    command_pattern = r"^/ignore\s*$"  # 只匹配 /ignore

    async def execute(self) -> Tuple[bool, str, bool]:
        """执行命令 - 显示帮助"""
        return await self._show_help()

    async def _show_help(self) -> Tuple[bool, str, bool]:
        """显示帮助信息"""
        help_text = """📋 忽略词管理命令

/ignore list - 列出所有屏蔽词
/ignore add <词> - 添加屏蔽词
/ignore addr <正则> - 添加正则表达式
/ignore del <词> - 删除屏蔽词
/ignore delr <正则> - 删除正则表达式

示例:
/ignore add 广告
/ignore addr ^/spam.*
/ignore del 推广"""
        await self.send_text(help_text)
        return True, "显示帮助", True


class IgnoreListCommand(BaseCommand):
    """列出屏蔽词命令"""

    command_name = "ignore_list"
    command_description = "列出所有屏蔽词"
    command_pattern = r"^/ignore\s+list\s*$"

    async def execute(self) -> Tuple[bool, str, bool]:
        # 直接从 config.toml 文件读取最新数据
        phrase_list = config_manager.get_phrases()
        regex_patterns = config_manager.get_patterns()
        match_mode = self.get_config("phrases.match_mode", "contains")

        lines = ["📋 当前屏蔽词列表\n"]

        lines.append(f"【短语匹配】模式: {match_mode}")
        if phrase_list:
            for i, phrase in enumerate(phrase_list, 1):
                lines.append(f"  {i}. {phrase}")
        else:
            lines.append("  (空)")

        lines.append("")

        lines.append("【正则表达式】")
        if regex_patterns:
            for i, pattern in enumerate(regex_patterns, 1):
                lines.append(f"  {i}. {pattern}")
        else:
            lines.append("  (空)")

        await self.send_text("\n".join(lines))
        return True, "列出屏蔽词", True


class IgnoreAddCommand(PermissionMixin, BaseCommand):
    """添加屏蔽词命令"""

    command_name = "ignore_add"
    command_description = "添加屏蔽词"
    command_pattern = r"^/ignore\s+add\s+(?P<phrase>.+)$"

    async def execute(self) -> Tuple[bool, str, bool]:
        if not await self.check_user_permission():
            return await self.send_no_permission()

        phrase = self.matched_groups.get("phrase", "").strip() if self.matched_groups else ""

        if not phrase:
            await self.send_text("❌ 请指定要添加的屏蔽词\n用法: /ignore add <词>")
            return False, "参数缺失", True

        if config_manager.add_phrase(phrase):
            await self.send_text(f"✅ 已添加屏蔽词: {phrase}")
            return True, f"添加屏蔽词: {phrase}", True
        else:
            await self.send_text(f"⚠️ 屏蔽词已存在: {phrase}")
            return False, "已存在", True


class IgnoreAddRegexCommand(PermissionMixin, BaseCommand):
    """添加正则表达式命令"""

    command_name = "ignore_addr"
    command_description = "添加正则表达式"
    command_pattern = r"^/ignore\s+addr\s+(?P<pattern>.+)$"

    async def execute(self) -> Tuple[bool, str, bool]:
        if not await self.check_user_permission():
            return await self.send_no_permission()

        pattern = self.matched_groups.get("pattern", "").strip() if self.matched_groups else ""

        if not pattern:
            await self.send_text("❌ 请指定正则表达式\n用法: /ignore addr <正则>")
            return False, "参数缺失", True

        # 验证正则表达式
        try:
            re.compile(pattern)
        except re.error as e:
            await self.send_text(f"❌ 无效的正则表达式: {e}")
            return False, "正则无效", True

        if config_manager.add_pattern(pattern):
            await self.send_text(f"✅ 已添加正则表达式: {pattern}")
            return True, f"添加正则: {pattern}", True
        else:
            await self.send_text(f"⚠️ 正则表达式已存在: {pattern}")
            return False, "已存在", True


class IgnoreDelCommand(PermissionMixin, BaseCommand):
    """删除屏蔽词命令"""

    command_name = "ignore_del"
    command_description = "删除屏蔽词"
    command_pattern = r"^/ignore\s+del\s+(?P<phrase>.+)$"

    async def execute(self) -> Tuple[bool, str, bool]:
        if not await self.check_user_permission():
            return await self.send_no_permission()

        phrase = self.matched_groups.get("phrase", "").strip() if self.matched_groups else ""

        if not phrase:
            await self.send_text("❌ 请指定要删除的屏蔽词\n用法: /ignore del <词>")
            return False, "参数缺失", True

        if config_manager.del_phrase(phrase):
            await self.send_text(f"✅ 已删除屏蔽词: {phrase}")
            return True, f"删除屏蔽词: {phrase}", True
        else:
            await self.send_text(f"⚠️ 屏蔽词不存在: {phrase}")
            return False, "不存在", True


class IgnoreDelRegexCommand(PermissionMixin, BaseCommand):
    """删除正则表达式命令"""

    command_name = "ignore_delr"
    command_description = "删除正则表达式"
    command_pattern = r"^/ignore\s+delr\s+(?P<pattern>.+)$"

    async def execute(self) -> Tuple[bool, str, bool]:
        if not await self.check_user_permission():
            return await self.send_no_permission()

        pattern = self.matched_groups.get("pattern", "").strip() if self.matched_groups else ""

        if not pattern:
            await self.send_text("❌ 请指定正则表达式\n用法: /ignore delr <正则>")
            return False, "参数缺失", True

        if config_manager.del_pattern(pattern):
            await self.send_text(f"✅ 已删除正则表达式: {pattern}")
            return True, f"删除正则: {pattern}", True
        else:
            await self.send_text(f"⚠️ 正则表达式不存在: {pattern}")
            return False, "不存在", True


class IgnoreMessageHandler(BaseEventHandler):
    """
    消息忽略事件处理器
    
    监听 ON_MESSAGE 事件，在消息到达其他处理器之前进行过滤检查。
    支持短语匹配和正则表达式匹配两种方式。
    """

    event_type = EventType.ON_MESSAGE
    handler_name = "ignore_message_handler"
    handler_description = "拦截匹配配置短语或正则表达式的消息"
    intercept_message = True  # 启用拦截能力

    def _check_phrase_match(self, text: str, phrases: List[str], match_mode: str, case_sensitive: bool) -> bool:
        """
        检查文本是否匹配短语列表
        
        Args:
            text: 要检查的文本
            phrases: 短语列表
            match_mode: 匹配模式 (contains, exact, startswith, endswith)
            case_sensitive: 是否区分大小写
            
        Returns:
            bool: 是否匹配
        """
        if not text or not phrases:
            return False
            
        check_text = text if case_sensitive else text.lower()
        
        for phrase in phrases:
            if not phrase:  # 跳过空短语
                continue
            check_phrase = phrase if case_sensitive else phrase.lower()
            
            if match_mode == "exact":
                if check_text == check_phrase:
                    return True
            elif match_mode == "startswith":
                if check_text.startswith(check_phrase):
                    return True
            elif match_mode == "endswith":
                if check_text.endswith(check_phrase):
                    return True
            else:  # contains (default)
                if check_phrase in check_text:
                    return True
        
        return False

    def _check_regex_match(self, text: str, patterns: List[str], case_sensitive: bool) -> bool:
        """
        检查文本是否匹配正则表达式模式列表
        
        Args:
            text: 要检查的文本
            patterns: 正则表达式模式列表
            case_sensitive: 是否区分大小写
            
        Returns:
            bool: 是否匹配
        """
        if not text or not patterns:
            return False
            
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for pattern in patterns:
            if not pattern:  # 跳过空模式
                continue
            try:
                if re.search(pattern, text, flags):
                    return True
            except re.error as e:
                # 无效的正则表达式，记录警告并跳过
                debug_enabled = self.get_config("logging.debug", False)
                if debug_enabled:
                    logger.warning(f"无效的正则表达式 '{pattern}': {e}")
                continue
        
        return False

    async def execute(self, message: MaiMessages | None) -> Tuple[bool, bool, str | None, None, None]:
        """
        执行消息过滤检查
        
        Args:
            message: 消息对象
            
        Returns:
            Tuple[bool, bool, str | None, None, None]:
                - success: 是否执行成功
                - continue_processing: 是否继续处理消息 (False = 拦截)
                - reason: 处理原因说明
                - None: 保留参数
                - None: 保留参数
        """
        # 检查插件是否启用
        plugin_enabled = self.get_config("plugin.enabled", True)
        if not plugin_enabled:
            return True, True, None, None, None
        
        # 获取消息文本
        if not message or not message.plain_text:
            return True, True, None, None, None
        
        text = message.plain_text
        debug_enabled = self.get_config("logging.debug", False)
        log_ignored = self.get_config("logging.log_ignored", True)
        
        if debug_enabled:
            logger.debug(f"检查消息: {text[:50]}...")
        
        # 检查短语匹配
        phrases_enabled = self.get_config("phrases.enabled", True)
        if phrases_enabled:
            # 直接从 config.toml 获取数据
            phrase_list = self.get_config("phrases.list", [])
            match_mode = self.get_config("phrases.match_mode", "contains")
            case_sensitive = self.get_config("phrases.case_sensitive", False)
            
            if self._check_phrase_match(text, phrase_list, match_mode, case_sensitive):
                if log_ignored:
                    logger.info(f"[IgnorePhrasePlugin] 短语匹配拦截消息: {text[:50]}...")
                return True, False, "短语匹配拦截", None, None
        
        # 检查正则匹配
        regex_enabled = self.get_config("regex.enabled", True)
        if regex_enabled:
            # 直接从 config.toml 获取数据
            patterns = self.get_config("regex.patterns", [])
            regex_case_sensitive = self.get_config("regex.case_sensitive", False)
            
            if self._check_regex_match(text, patterns, regex_case_sensitive):
                if log_ignored:
                    logger.info(f"[IgnorePhrasePlugin] 正则匹配拦截消息: {text[:50]}...")
                return True, False, "正则匹配拦截", None, None
        
        # 消息未匹配，继续处理
        return True, True, None, None, None


@register_plugin
class IgnorePhrasePlugin(BasePlugin):
    """
    忽略短语插件
    
    用于过滤和拦截特定消息，支持短语匹配和正则表达式匹配。
    配置通过 config_schema 自动生成 config.toml 文件，支持 webui 可视化编辑。
    """

    # 插件基本信息
    plugin_name: str = "ignore_phrase_plugin"
    enable_plugin: bool = True
    dependencies: List[str] = []
    python_dependencies: List[str] = ["tomli", "tomli_w"]
    config_file_name: str = "config.toml"

    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本设置",
        "phrases": "短语匹配配置",
        "regex": "正则表达式配置",
        "logging": "日志配置",
        "user_control": "权限控制",
    }

    # 配置 Schema 定义
    config_schema: dict = {
        "plugin": {
            "config_version": ConfigField(
                type=str, default="1.0.0", description="配置文件版本", disabled=True
            ),
            "enabled": ConfigField(
                type=bool, default=True, description="是否启用插件", label="启用插件"
            ),
        },
        "phrases": {
            "enabled": ConfigField(
                type=bool, default=True, description="是否启用短语匹配", label="启用短语匹配"
            ),
            "list": ConfigField(
                type=list,
                default=[],
                description="要忽略的短语列表",
                label="屏蔽词列表",
                input_type="list",
            ),
            "match_mode": ConfigField(
                type=str,
                default="contains",
                description="匹配模式",
                choices=["contains", "exact", "startswith", "endswith"],
                label="匹配模式",
            ),
            "case_sensitive": ConfigField(
                type=bool, default=False, description="是否区分大小写", label="区分大小写"
            ),
        },
        "regex": {
            "enabled": ConfigField(
                type=bool, default=True, description="是否启用正则匹配", label="启用正则匹配"
            ),
            "patterns": ConfigField(
                type=list,
                default=[],
                description="正则表达式模式列表",
                label="正则表达式列表",
                input_type="list",
            ),
            "case_sensitive": ConfigField(
                type=bool, default=False, description="正则匹配是否区分大小写", label="区分大小写"
            ),
        },
        "logging": {
            "log_ignored": ConfigField(
                type=bool, default=True, description="是否记录被忽略的消息", label="记录拦截日志"
            ),
            "debug": ConfigField(
                type=bool, default=False, description="是否启用调试日志", label="调试模式"
            ),
        },
        "user_control": {
            "list_type": ConfigField(
                type=str,
                default="whitelist",
                description="权限列表类型: whitelist(白名单-仅允许列表中用户), blacklist(黑名单-禁止列表中用户)",
                choices=["whitelist", "blacklist"],
                label="名单类型",
            ),
            "list": ConfigField(
                type=list,
                default=[],
                description="有权限使用命令的用户ID列表(QQ号)",
                label="用户列表",
                input_type="list",
            ),
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化配置管理器
        config_manager.load(self.plugin_dir)
        logger.info(f"IgnorePhrasePlugin v{self.get_config('plugin.config_version', '1.0.0')} 初始化完成")

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件组件列表"""
        return [
            (IgnoreMessageHandler.get_handler_info(), IgnoreMessageHandler),
            (IgnoreCommand.get_command_info(), IgnoreCommand),
            (IgnoreListCommand.get_command_info(), IgnoreListCommand),
            (IgnoreAddCommand.get_command_info(), IgnoreAddCommand),
            (IgnoreAddRegexCommand.get_command_info(), IgnoreAddRegexCommand),
            (IgnoreDelCommand.get_command_info(), IgnoreDelCommand),
            (IgnoreDelRegexCommand.get_command_info(), IgnoreDelRegexCommand),
        ]
