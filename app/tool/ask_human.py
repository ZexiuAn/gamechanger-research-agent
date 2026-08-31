import os

from app.tool import BaseTool


class AskHuman(BaseTool):
    """向人类寻求帮助。Web/无 TTY 环境下不会阻塞，避免卡死事件循环。"""

    name: str = "ask_human"
    description: str = "使用此工具向人类寻求帮助。"
    parameters: dict = {
        "type": "object",
        "properties": {
            "inquire": {
                "type": "string",
                "description": "你想问人类的问题。",
            }
        },
        "required": ["inquire"],
    }

    async def execute(self, inquire: str) -> str:
        # CLI 且确有交互终端时才阻塞询问；否则直接回退，防止 Web UI 卡死
        if os.getenv("ALLOW_ASK_HUMAN", "0") == "1" and os.isatty(0):
            try:
                return input(f"""Bot: {inquire}\n\nYou: """).strip()
            except EOFError:
                pass
        return (
            "（当前为非交互环境，无法人工作答。）"
            f"请基于已有公开信息继续完成任务，不要再次调用 ask_human。问题原为：{inquire}"
        )
