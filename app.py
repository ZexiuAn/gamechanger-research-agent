import asyncio
import os
import threading
import tomllib
import uuid
import webbrowser
import json
from datetime import datetime
from functools import partial
from json import dumps
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Task(BaseModel):
    id: str
    prompt: str
    created_at: datetime
    status: str
    steps: list = []

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["created_at"] = self.created_at.isoformat()
        return data


class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.queues = {}

    def create_task(self, prompt: str) -> Task:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id, prompt=prompt, created_at=datetime.now(), status="pending"
        )
        self.tasks[task_id] = task
        self.queues[task_id] = asyncio.Queue()
        return task

    async def update_task_step(
        self, task_id: str, step: int, result: str, step_type: str = "step"
    ):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.steps.append({"step": step, "result": result, "type": step_type})
            await self.queues[task_id].put(
                {"type": step_type, "step": step, "result": result}
            )
            await self.queues[task_id].put(
                {"type": "status", "status": task.status, "steps": task.steps}
            )

    async def complete_task(self, task_id: str, result: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "completed"
            await self.queues[task_id].put(
                {"type": "status", "status": task.status, "steps": task.steps}
            )
            await self.queues[task_id].put({"type": "complete", "result": result})

    async def fail_task(self, task_id: str, error: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = f"failed: {error}"
            await self.queues[task_id].put({"type": "error", "message": error})


task_manager = TaskManager()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/download")
async def download_file(file_path: str):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=os.path.basename(file_path))


@app.post("/tasks")
async def create_task(prompt: str = Body(..., embed=True)):
    task = task_manager.create_task(prompt)
    asyncio.create_task(run_task(task.id, prompt))
    return {"task_id": task.id}


from app.agent.manus import Manus


def _collect_deliverable_snippets(raw_result: str, max_chars: int = 4500) -> tuple[str, list[str]]:
    """收集本次可能产出的 workspace 文稿片段，供最终用户结论生成。"""
    import re
    from pathlib import Path

    ws = Path(__file__).resolve().parent / "workspace"
    paths = re.findall(r"workspace/[\w./-]+\.(?:md|txt|html)", raw_result or "")
    # 也从常见 create/编辑日志样式里抓文件名
    paths += re.findall(r"(?:创建|写入|保存|saved?)\s*[「`']?(workspace/[\w./-]+\.(?:md|txt))", raw_result or "", re.I)
    recent = []
    try:
        recent = sorted(
            [
                p
                for p in ws.glob("*")
                if p.is_file() and p.suffix.lower() in {".md", ".txt"}
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:5]
    except Exception:
        recent = []

    ordered: list[Path] = []
    for rel in paths:
        p = Path(__file__).resolve().parent / rel
        if p.exists() and p not in ordered:
            ordered.append(p)
    for p in recent:
        if p not in ordered:
            ordered.append(p)

    chunks: list[str] = []
    rels: list[str] = []
    used = 0
    for p in ordered[:3]:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            continue
        if not text:
            continue
        rel = f"workspace/{p.name}"
        rels.append(rel)
        # 优先多取「关键发现 / 对比总结」段，便于归纳结论
        piece = text
        for marker in ("## 关键发现", "## 竞品对比", "## 对比总结", "## 结论"):
            idx = text.find(marker)
            if idx >= 0:
                piece = text[idx:]
                break
        piece = piece[:2200]
        chunks.append(f"### 文件 {rel}\n{piece}")
        used += len(piece)
        if used >= max_chars:
            break
    return "\n\n".join(chunks), rels


def _collect_assistant_notes(agent) -> str:
    notes: list[str] = []
    memory = getattr(agent, "memory", None)
    messages = getattr(memory, "messages", None) or []
    for msg in messages:
        role = getattr(msg, "role", None)
        content = getattr(msg, "content", None)
        role_val = getattr(role, "value", role)
        if role_val != "assistant" or not content:
            continue
        text = str(content).strip()
        if len(text) < 20:
            continue
        if any(
            bad in text
            for bad in (
                "Observed output of cmd",
                "Executing step",
                "Tool arguments:",
                "下一步：",
                "调用 `terminate`",
                "调用 terminate",
                "任务目标已达成",
                "我将终止",
                "终止交互",
                "现在任务已完成",
            )
        ):
            continue
        notes.append(text)
    return "\n---\n".join(notes[-3:])


async def _compose_user_facing_reply(agent, user_prompt: str, raw_result: str) -> str:
    """任务结束后再用 LLM 生成面向用户的调研结论（不是内部思考）。"""
    from app.llm import LLM
    from app.schema import Message

    deliverable, rels = _collect_deliverable_snippets(raw_result)
    notes = _collect_assistant_notes(agent)
    path_hint = "、".join(f"`{r}`" for r in rels[:3]) if rels else "`workspace/`"

    from app.branding import PRODUCT_NAME

    system = (
        f"You are the executive summarization engine of '{PRODUCT_NAME}'. "
        "Your role: Synthesize a concise, professional, user-facing research summary based strictly on the persisted deliverables in workspace/. "
        "Do not output internal thoughts, tool names, 'terminate', task lists, or self-checks. "
        "Tone: Objective, executive, professional."
    )
    ask = (
        f"User Research Query:\n{user_prompt}\n\n"
        f"Agent Internal Notes (reference only):\n{notes or '(None)'}\n\n"
        f"Persisted Deliverable Extracts:\n{deliverable or '(No file text available)'}\n\n"
        "Please provide the final user-facing response with:\n"
        "1) Executive Conclusion: Directly answer the core research question, compare key entities/competitors, and provide strategic takeaway.\n"
        "2) Key Highlights: Up to 5 bullet points on critical discoveries or items needing verification.\n"
        f"3) Final line indicating file delivery path (e.g. 'Detailed briefing written to {path_hint}').\n"
        "4) No process jargon like 'next step', 'calling tool', or 'terminating'."
    )

    try:
        llm = LLM()
        reply = await llm.ask(
            messages=[Message.user_message(ask)],
            system_msgs=[Message.system_message(system)],
            stream=False,
            temperature=0.3,
        )
        reply = (reply or "").strip()
        if reply:
            return reply
    except Exception as e:
        from app.logger import logger

        logger.warning(f"user-facing summary failed: {e}")

    if rels:
        return (
            f"已完成调研整理，核心结论与对比细节见交付简报。"
            f"\n\n详细内容已写入：{'、'.join(f'`{r}`' for r in rels[:3])}。"
        )
    return "任务已完成。请查看上方工具轨迹，以及 workspace/ 中的交付文件。"


async def run_task(task_id: str, prompt: str):
    agent = None
    hwnd = None
    try:
        task_manager.tasks[task_id].status = "running"

        from app.branding import AGENT_DESCRIPTION, AGENT_NAME

        agent = await Manus.create(
            name=AGENT_NAME,
            description=AGENT_DESCRIPTION,
        )

        from app.logger import logger

        class SSELogHandler:
            def __init__(self, task_id):
                self.task_id = task_id

            async def __call__(self, message):
                import re

                cleaned_message = re.sub(r"^.*? - ", "", message)

                event_type = "log"
                if "thoughts:" in cleaned_message:
                    event_type = "think"
                elif "selected" in cleaned_message and "tools" in cleaned_message:
                    event_type = "tool"
                elif "Tool '" in cleaned_message and "completed" in cleaned_message:
                    event_type = "act"
                elif "Oops!" in cleaned_message:
                    event_type = "error"
                elif "Special tool" in cleaned_message:
                    # terminate 日志只做轨迹展示；真正的 complete 在 LLM 结论生成之后发出
                    event_type = "act"
                elif "Activating tool" in cleaned_message:
                    event_type = "tool"
                elif "Executing step" in cleaned_message:
                    event_type = "log"

                await task_manager.update_task_step(
                    self.task_id, 0, cleaned_message, event_type
                )

        sse_handler = SSELogHandler(task_id)
        hwnd = logger.add(sse_handler)

        result = await agent.run(prompt)
        logger.remove(hwnd)
        hwnd = None

        await task_manager.update_task_step(
            task_id, 0, "正在根据调研材料生成面向用户的结论…", "log"
        )
        final_text = await _compose_user_facing_reply(agent, prompt, result)
        await task_manager.update_task_step(task_id, 1, final_text, "result")
        await asyncio.sleep(0.2)
        await task_manager.complete_task(task_id, final_text)
    except Exception as e:
        await task_manager.fail_task(task_id, str(e))
    finally:
        if hwnd is not None:
            try:
                from app.logger import logger

                logger.remove(hwnd)
            except Exception:
                pass
        if agent is not None:
            try:
                await agent.cleanup()
            except Exception:
                pass


@app.get("/api/demo-tasks")
async def demo_tasks():
    from app.branding import ORG_LINE, PRODUCT_NAME

    return {
        "product": PRODUCT_NAME,
        "org": ORG_LINE,
        "tasks": [
            {
                "id": "research",
                "title": "Competitor & Tech Research Briefing",
                "prompt": (
                    "Please draft a structured competitor & tech research briefing.\n"
                    "Topic: AI assistant capabilities in sports analytics & team management platforms (e.g. Hudl, MaxPreps, GameChanger).\n"
                    "Requirements: 1) Use research_kb to check benchmark competitors; 2) web_search & fetch_url key sources; "
                    "3) Synthesize 5-8 insights with comparison matrix; 4) Save to workspace/research_brief_sports_ai.md with citations; 5) terminate."
                ),
            },
            {
                "id": "docs",
                "title": "Internal Memo & Task Digest",
                "prompt": (
                    "Use research_kb template=docs to align structure, read workspace/internal_memo_rd_tasks.txt, "
                    "digest action items by priority into workspace/task_digest_rd.md, then terminate."
                ),
            },
        ],
    }


@app.get("/api/health")
async def api_health():
    """给 UI 显示模型是否已配置（不暴露密钥）。"""
    try:
        from app.config import config

        llm = config.llm["default"]
        key = (llm.api_key or "").strip()
        ok = bool(key)
        return {
            "ok": ok,
            "model": llm.model if ok else None,
            "provider": "DashScope" if ok else None,
            "message": "已连接" if ok else "未配置 API Key",
        }
    except Exception as e:
        return {"ok": False, "model": None, "provider": None, "message": str(e)}


@app.get("/api/capabilities")
async def api_capabilities():
    """展示当前打开的能力面（工具 / MCP / 浏览器开关）。"""
    try:
        from app.agent.manus import Manus, _BROWSER_AVAILABLE
        from app.config import config

        # 不 create()，避免每次刷新都拉起 MCP 子进程
        tool_names = [t.name for t in Manus().available_tools.tools]
        mcp_ids = list((config.mcp_config.servers or {}).keys())
        features = [
            {"id": "react", "label": "多步 Tool Calling", "on": True},
            {"id": "web_search", "label": "联网搜索", "on": "web_search" in tool_names},
            {"id": "fetch_url", "label": "网页精读", "on": "fetch_url" in tool_names},
            {"id": "research_kb", "label": "调研知识库", "on": "research_kb" in tool_names},
            {"id": "files", "label": "文件落盘", "on": "str_replace_editor" in tool_names},
            {"id": "python", "label": "代码执行", "on": "python_execute" in tool_names},
            {"id": "mcp", "label": f"MCP({','.join(mcp_ids) or '未配置'})", "on": bool(mcp_ids)},
            {
                "id": "browser",
                "label": "浏览器自动化",
                "on": _BROWSER_AVAILABLE and "browser_use" in tool_names,
            },
        ]
        return {
            "tools": tool_names,
            "mcp_servers": mcp_ids,
            "browser_enabled": _BROWSER_AVAILABLE,
            "features": features,
        }
    except Exception as e:
        return {
            "tools": [],
            "mcp_servers": [],
            "browser_enabled": False,
            "features": [],
            "error": str(e),
        }


@app.get("/tasks/{task_id}/events")
async def task_events(task_id: str):
    async def event_generator():
        if task_id not in task_manager.queues:
            yield f"event: error\ndata: {dumps({'message': 'Task not found'})}\n\n"
            return

        queue = task_manager.queues[task_id]

        task = task_manager.tasks.get(task_id)
        if task:
            yield f"event: status\ndata: {dumps({'type': 'status', 'status': task.status, 'steps': task.steps})}\n\n"

        while True:
            try:
                event = await queue.get()
                formatted_event = dumps(event)

                yield ": heartbeat\n\n"

                if event["type"] == "complete":
                    yield f"event: complete\ndata: {formatted_event}\n\n"
                    break
                elif event["type"] == "error":
                    yield f"event: error\ndata: {formatted_event}\n\n"
                    break
                elif event["type"] == "step":
                    task = task_manager.tasks.get(task_id)
                    if task:
                        yield f"event: status\ndata: {dumps({'type': 'status', 'status': task.status, 'steps': task.steps})}\n\n"
                    yield f"event: {event['type']}\ndata: {formatted_event}\n\n"
                elif event["type"] in ["think", "tool", "act", "run"]:
                    yield f"event: {event['type']}\ndata: {formatted_event}\n\n"
                else:
                    yield f"event: {event['type']}\ndata: {formatted_event}\n\n"

            except asyncio.CancelledError:
                print(f"Client disconnected for task {task_id}")
                break
            except Exception as e:
                print(f"Error in event stream: {str(e)}")
                yield f"event: error\ndata: {dumps({'message': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/tasks")
async def get_tasks():
    sorted_tasks = sorted(
        task_manager.tasks.values(), key=lambda task: task.created_at, reverse=True
    )
    return JSONResponse(
        content=[task.model_dump() for task in sorted_tasks],
        headers={"Content-Type": "application/json"},
    )


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in task_manager.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_manager.tasks[task_id]


@app.get("/config/status")
async def check_config_status():
    config_path = Path(__file__).parent / "config" / "config.toml"
    example_config_path = Path(__file__).parent / "config" / "config.example.toml"

    if config_path.exists():
        return {"status": "exists"}
    elif example_config_path.exists():
        try:
            with open(example_config_path, "rb") as f:
                example_config = tomllib.load(f)
            return {"status": "missing", "example_config": example_config}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        return {"status": "no_example"}


@app.post("/config/save")
async def save_config(config_data: dict = Body(...)):
    try:
        config_dir = Path(__file__).parent / "config"
        config_dir.mkdir(exist_ok=True)

        config_path = config_dir / "config.toml"

        toml_content = ""

        if "llm" in config_data:
            toml_content += "# Global LLM configuration\n[llm]\n"
            llm_config = config_data["llm"]
            for key, value in llm_config.items():
                if key != "vision":
                    if isinstance(value, str):
                        toml_content += f'{key} = "{value}"\n'
                    else:
                        toml_content += f"{key} = {value}\n"

        if "server" in config_data:
            toml_content += "\n# Server configuration\n[server]\n"
            server_config = config_data["server"]
            for key, value in server_config.items():
                if isinstance(value, str):
                    toml_content += f'{key} = "{value}"\n'
                else:
                    toml_content += f"{key} = {value}\n"

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(toml_content)

        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"message": f"Server error: {str(exc)}"}
    )


def open_local_browser(config):
    webbrowser.open_new_tab(f"http://{config['host']}:{config['port']}")


def load_config():
    try:
        config_path = Path(__file__).parent / "config" / "config.toml"

        if not config_path.exists():
            return {"host": "localhost", "port": 5172}

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        return {"host": config["server"]["host"], "port": config["server"]["port"]}
    except FileNotFoundError:
        return {"host": "localhost", "port": 5172}
    except KeyError as e:
        print(
            f"The configuration file is missing necessary fields: {str(e)}, use default configuration"
        )
        return {"host": "localhost", "port": 5172}


if __name__ == "__main__":
    import uvicorn

    config = load_config()
    open_with_config = partial(open_local_browser, config)
    threading.Timer(3, open_with_config).start()
    uvicorn.run(app, host=config["host"], port=config["port"])
