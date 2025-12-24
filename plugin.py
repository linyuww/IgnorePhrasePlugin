import re
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set
from src.plugin_system import (
    BasePlugin,
    register_plugin,
    BaseCommand,
    BaseEventHandler,
    EventType,
    MaiMessages,
    ComponentInfo,
    ConfigField
)
from src.common.logger import get_logger

logger = get_logger("ignore_phrase_plugin")

# --- Manager ---
class IgnorePhraseManager:
    _instance = None
    phrases: List[str] = []
    file_path: Optional[Path] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(IgnorePhraseManager, cls).__new__(cls)
        return cls._instance

    def load(self, plugin_dir: str):
        self.file_path = Path(plugin_dir) / "ignore_phrases.json"
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.phrases = json.load(f)
                logger.info(f"Loaded {len(self.phrases)} ignore phrases.")
            else:
                self.phrases = []
                self.save()
                logger.info("Created new ignore_phrases.json")
        except Exception as e:
            logger.error(f"Failed to load ignore phrases: {e}")
            self.phrases = []

    def save(self):
        if not self.file_path:
            return
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.phrases, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Failed to save ignore phrases: {e}")

    def add(self, pattern: str) -> bool:
        if pattern not in self.phrases:
            self.phrases.append(pattern)
            self.save()
            return True
        return False

    def delete(self, pattern: str) -> bool:
        if pattern in self.phrases:
            self.phrases.remove(pattern)
            self.save()
            return True
        return False

    def get_all(self) -> List[str]:
        return self.phrases

manager = IgnorePhraseManager()

# --- Commands ---

class AddIgnorePhraseCommand(BaseCommand):
    command_name = "ignore_add"
    command_description = "添加忽略短语（支持正则）。格式：.ignore add <regex>"
    command_pattern = r"^\.ignore\s+add\s+(?P<pattern>.+)$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        pattern = self.matched_groups.get("pattern", "").strip()
        if not pattern:
            return False, "请输入要忽略的正则表达式", 2
        
        # Validate regex
        try:
            re.compile(pattern)
        except re.error:
            return False, "无效的正则表达式", 2

        if manager.add(pattern):
            return True, f"✅ 已添加忽略规则：{pattern}", 2
        else:
            return False, f"⚠️ 规则已存在：{pattern}", 2

class DeleteIgnorePhraseCommand(BaseCommand):
    command_name = "ignore_del"
    command_description = "删除忽略短语。格式：.ignore del <regex>"
    command_pattern = r"^\.ignore\s+del\s+(?P<pattern>.+)$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        pattern = self.matched_groups.get("pattern", "").strip()
        if not pattern:
            return False, "请输入要删除的正则表达式", 2

        if manager.delete(pattern):
            return True, f"✅ 已删除忽略规则：{pattern}", 2
        else:
            return False, f"⚠️ 规则不存在：{pattern}", 2

class ListIgnorePhrasesCommand(BaseCommand):
    command_name = "ignore_list"
    command_description = "列出所有忽略短语"
    command_pattern = r"^\.ignore\s+list$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        phrases = manager.get_all()
        if not phrases:
            return True, "📭 当前没有忽略规则", 2
        
        msg = "📋 忽略规则列表：\n" + "\n".join([f"- {p}" for p in phrases])
        return True, msg, 2

# --- Event Handler ---

class IgnorePhraseEventHandler(BaseEventHandler):
    handler_name = "ignore_phrase_handler"
    handler_description = "检查消息是否匹配忽略规则，匹配则拦截"
    event_type = EventType.ON_MESSAGE
    weight = 9000 # High priority, but maybe lower than silent mode? Silent mode is 10000.
    intercept_message = True

    async def execute(self, message: MaiMessages) -> Tuple[bool, bool, Optional[str], None, None]:
        text = getattr(message, "plain_text", "") or getattr(message, "text", "") or ""
        if not text:
             return True, True, None, None, None

        for pattern in manager.get_all():
            try:
                if re.search(pattern, text):
                    logger.info(f"[IgnorePhrasePlugin] Message ignored by pattern: {pattern}")
                    # Return False to stop propagation
                    return True, False, "Ignored by pattern", None, None
            except re.error:
                continue
        
        return True, True, None, None, None

# --- Plugin Registration ---

@register_plugin
class IgnorePhrasePlugin(BasePlugin):
    plugin_name = "ignore_phrase_plugin"
    enable_plugin = True
    config_file_name = "config.toml"
    
    config_schema = {
        "plugin": {
            "name": ConfigField(type=str, default="ignore_phrase_plugin", description="插件名称"),
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        manager.load(self.plugin_dir)

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        return [
            (AddIgnorePhraseCommand.get_command_info(), AddIgnorePhraseCommand),
            (DeleteIgnorePhraseCommand.get_command_info(), DeleteIgnorePhraseCommand),
            (ListIgnorePhrasesCommand.get_command_info(), ListIgnorePhrasesCommand),
            (IgnorePhraseEventHandler.get_handler_info(), IgnorePhraseEventHandler),
        ]
