"""Index-first content storage for the LearningSite editor."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

HEADING = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
IMAGE = re.compile(r"!\[[^]]*]\(([^ )]+)")
LINK = re.compile(r"(?<!!)\[[^]]+]\(([^ )#]+)(?:#[^)]+)?\)")


class ContentRepository:
    """Keeps page identity and display order exclusively in content-index.json."""
    def __init__(self, project: Path) -> None:
        self.project = project.resolve(); self.public = self.project / "public"
        self.content = self.public / "content"; self.images = self.public / "assets" / "images"
        self.index_path = self.public / "content-index.json"; self.trash = self.public / ".trash"
        self.content.mkdir(parents=True, exist_ok=True); self.images.mkdir(parents=True, exist_ok=True); self.trash.mkdir(parents=True, exist_ok=True)

    def read_index(self) -> list[dict]:
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            if isinstance(data, dict): data = data.get("pages", [])
            return [item for item in data if isinstance(item, dict) and isinstance(item.get("path"), str)] if isinstance(data, list) else []
        except (OSError, ValueError): return []

    @staticmethod
    def title_from_markdown(text: str, fallback: str) -> str:
        found = HEADING.search(text)
        return re.sub(r"[*_`]", "", found.group(1)).strip() if found else fallback.replace("-", " ").replace("_", " ")

    def markdown_files(self) -> list[Path]:
        found = {file.relative_to(self.content).as_posix(): file for file in self.content.rglob("*.md")}
        ordered = [found.pop(item["path"]) for item in self.read_index() if item["path"] in found]
        return [*ordered, *(found[path] for path in sorted(found, key=str.casefold))]

    def build_index(self, preferred_paths: list[str] | None = None, include_paths: list[str] | None = None, page_overrides: dict[str, dict] | None = None) -> list[dict]:
        files = {file.relative_to(self.content).as_posix(): file for file in self.content.rglob("*.md")}
        previous = {item["path"]: item for item in self.read_index()}
        paths = [path for path in (preferred_paths if preferred_paths is not None else [item["path"] for item in self.read_index()]) if path in files]
        paths.extend(path for path in (include_paths or []) if path in files and path not in paths)
        pages = []
        for order, path in enumerate(paths, 1):
            file, old = files[path], {**previous.get(path, {}), **(page_overrides or {}).get(path, {})}
            parts = path.removesuffix(".md").split("/")
            pages.append({
                "title": str(old.get("title") or self.title_from_markdown(file.read_text(encoding="utf-8"), file.stem)),
                "slug": "/".join(parts),
                "folder": " / ".join(parts[:-1]) or "כללי",
                "path": path, "file": f"content/{path}", "order": order,
                "show_toc": bool(old.get("show_toc", True)),
            })
        self.atomic_json(self.index_path, pages)
        self.atomic_json(self.public / "search-index.json", [
            {"slug": page["slug"], "title": page["title"], "content": files[page["path"]].read_text(encoding="utf-8")[:12000]}
            for page in pages
        ])
        return pages

    @staticmethod
    def atomic_json(path: Path, data: object) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp"); temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); temporary.replace(path)

    def references_for_image(self, image: Path) -> list[str]:
        target = "/assets/images/" + image.relative_to(self.images).as_posix()
        return [file.relative_to(self.content).as_posix() for file in self.markdown_files() if target in unquote(file.read_text(encoding="utf-8"))]

    def validate(self) -> dict[str, list[str]]:
        result = {"errors": [], "warnings": [], "info": []}; seen_slugs = set(); indexed = {item["path"] for item in self.read_index()}
        for file in self.markdown_files():
            path = file.relative_to(self.content).as_posix(); text = file.read_text(encoding="utf-8")
            entry = next((item for item in self.read_index() if item["path"] == path), None)
            if not entry: result["warnings"].append(f"{path}: לא נמצא באינדקס") ; continue
            if entry["slug"] in seen_slugs: result["errors"].append(f"{path}: slug כפול ({entry['slug']})")
            seen_slugs.add(entry["slug"])
            for match in IMAGE.finditer(text):
                url = unquote(match.group(1))
                if url.startswith("/assets/images/") and not (self.public / url.lstrip("/")).exists(): result["errors"].append(f"{path}: תמונה חסרה {url}")
            for match in LINK.finditer(text):
                if match.group(1).startswith("javascript:"): result["errors"].append(f"{path}: קישור לא בטוח")
        for image in self.images.rglob("*"):
            if image.is_file() and image.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"} and not self.references_for_image(image): result["warnings"].append(f"תמונה ללא שימוש: {image.relative_to(self.images).as_posix()}")
        result["info"].append(f"נסרקו {len(indexed)} עמודים באינדקס.")
        return result
