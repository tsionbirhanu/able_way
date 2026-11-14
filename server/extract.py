"""Turn the frozen Savanna pages into searchable chunks of course content.

Run from anywhere:

    python server/extract.py

It reads pages/*.html and writes server/data/chunks.json. Every chunk keeps the page and
heading it came from, which is what the tutor shows as a citation.

Standard library only, so it runs on a machine with no internet and nothing installed.
"""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
OUT = Path(__file__).resolve().parent / "data" / "chunks.json"

MAX_CHARS = 1400  # a chunk longer than this is split at line boundaries
MIN_CHARS = 40  # anything shorter carries no content worth citing

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BLOCK = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "figure", "footer", "form",
    "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
    "table", "tr", "ul", "a", "button",
}
INLINE_FORMAT = {"b", "i", "em", "strong", "u", "mark", "sub", "sup", "code", "small"}
SKIP = {"script", "style", "svg", "noscript"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# Page chrome that is not course content: the authoring help modal and the "well done" modal.
SKIP_IDS = {"markdown-guide-modal", "curriculum-validation-congrats-modal"}


# ------------------------------------------------------------------ a very small DOM


class Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: "Node | None"):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Node | str] = []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def find(self, pred) -> "Node | None":
        return next((n for n in self.walk() if pred(n)), None)

    def find_all(self, pred) -> "list[Node]":
        return [n for n in self.walk() if pred(n)]

    def by_id(self, id_: str) -> "Node | None":
        return self.find(lambda n: n.attrs.get("id") == id_)


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, {k: (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        node = self.cur
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.cur = node.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(path: Path) -> Node:
    builder = _Builder()
    builder.feed(path.read_text(encoding="utf-8"))
    return builder.root


def clean(text: str) -> str:
    text = re.sub(r"[ \t\r\f\v ]+", " ", text)
    text = re.sub(r" +([,.;:!?%)])", r"\1", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def tokens(node: Node, into_templates: bool = False):
    """Yield ("h", level, title, anchor) for headings and ("t", text) for everything else,
    in document order. Templates hold content for other weeks/modules and are skipped
    unless the caller starts from one."""
    for child in node.children:
        if isinstance(child, str):
            yield ("t", child)
            continue
        if child.tag in SKIP or child.attrs.get("id") in SKIP_IDS:
            continue
        if child.tag == "template" and not into_templates:
            continue
        if child.tag in HEADINGS:
            title = clean("".join(t[1] for t in tokens(child) if t[0] == "t")).replace("\n", " ")
            anchor = child.attrs.get("id") or next(
                (n.attrs["id"] for n in child.walk() if n.attrs.get("id")), ""
            )
            yield ("h", int(child.tag[1]), title, anchor)
            continue
        if child.tag == "img" and child.attrs.get("alt"):
            # Alt text is content too, but file-name alts ("VA-Content-Banner") are not.
            alt = child.attrs["alt"]
            if " " in alt.strip() and "static frame" not in alt:
                yield ("t", f" [Image: {alt}] ")
            continue
        # Block elements end a line. Other containers (span, td, label) get a space so that
        # neighbouring cells do not run together; pure text formatting gets nothing.
        gap = "\n" if child.tag in BLOCK else "" if child.tag in INLINE_FORMAT else " "
        yield ("t", gap)
        yield from tokens(child)
        yield ("t", gap)


def text_of(node: Node, into_templates: bool = False) -> str:
    parts = []
    for tok in tokens(node, into_templates):
        parts.append(tok[1] if tok[0] == "t" else f"\n{tok[2]}\n")
    return clean("".join(parts))


# ------------------------------------------------------------------ chunking


def split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    pieces, current = [], ""
    for line in text.split("\n"):
        if current and len(current) + len(line) + 1 > MAX_CHARS:
            pieces.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    if current:
        pieces.append(current)
    return pieces


def sections(node: Node, split_level: int, into_templates: bool = False):
    """Cut a subtree into (heading, anchor, text) at headings of split_level or higher.
    Lower headings stay inside the text as their own line."""
    heading, anchor, buf = "", "", []
    for tok in tokens(node, into_templates):
        if tok[0] == "h" and tok[1] <= split_level and tok[2]:
            if clean("".join(buf)):
                yield heading, anchor, clean("".join(buf))
            heading, anchor, buf = tok[2], tok[3], []
        elif tok[0] == "h":
            buf.append(f"\n{tok[2]}\n")
        else:
            buf.append(tok[1])
    if clean("".join(buf)):
        yield heading, anchor, clean("".join(buf))


def grouped(parts, limit: int = MAX_CHARS):
    """Merge neighbouring sections until a group is about one chunk long, so that a page made
    of many small headed blocks does not become dozens of two-line chunks. The group is named
    after its first heading."""
    title, anchor, buf = "", "", ""
    for heading, anc, text in parts:
        piece = f"{heading}\n{text}" if heading else text
        if buf and len(buf) + len(piece) > limit:
            yield title, anchor, buf
            title, anchor, buf = "", "", ""
        if not buf:
            title, anchor = heading, anc
        buf = f"{buf}\n{piece}" if buf else piece
    if buf:
        yield title, anchor, buf


class Chunks:
    def __init__(self):
        self.items: list[dict] = []
        self._seen: set[str] = set()

    def add(self, *, page: str, course: str, title: str, text: str, anchor: str = "", kind: str = "lesson"):
        for i, piece in enumerate(split_long(text)):
            if len(piece) < MIN_CHARS:
                continue
            digest = hashlib.sha1(piece.encode("utf-8")).hexdigest()[:12]
            if digest in self._seen:  # the same panel is often rendered for several weeks
                continue
            self._seen.add(digest)
            self.items.append(
                {
                    "id": f"c{len(self.items) + 1:03d}",
                    "corpus": "course",
                    "kind": kind,
                    "lang": "en",
                    "course": course,
                    "title": title if i == 0 else f"{title} (part {i + 1})",
                    "page": page,
                    "url": f"pages/{page}" + (f"#{anchor}" if anchor else ""),
                    "text": piece,
                }
            )


# ------------------------------------------------------------------ the three pages


def concept_page(chunks: Chunks):
    page = "concept-with-navigation.html"
    course = "VA-1: VA Foundations & Professional Identity"
    root = parse(PAGES / page)
    content = root.by_id("curriculum_navigation_content")
    lesson = "The Future of the VA Industry"
    for heading, anchor, text in sections(content, split_level=4):
        if heading in ("", lesson):
            title = f"{lesson} — Introduction"
        else:
            title = f"{lesson} — {heading}"
        chunks.add(page=page, course=course, title=title, text=text, anchor=anchor)

    # The curriculum panel beside the lesson: which items the module contains.
    main = root.find(lambda n: n.tag == "main")
    outline = []
    for tok in tokens(main):
        if tok[0] == "h" and tok[2] == lesson:
            break
        outline.append(tok[1] if tok[0] == "t" else f"\n{tok[2]}\n")
    chunks.add(
        page=page,
        course=course,
        title="Module outline: What is a VA",
        text="Items in this module, in order:\n" + clean("".join(outline)),
        kind="outline",
    )


def self_paced_home(chunks: Chunks):
    page = "homepage-v1-self-paced.html"
    course = "VA-1: VA Foundations & Professional Identity"
    root = parse(PAGES / page)
    main = root.find(lambda n: n.tag == "main")
    chunks.add(
        page=page,
        course=course,
        title="Learner dashboard (self-paced): progress, pacing and events",
        text=text_of(main),
        kind="dashboard",
    )
    for tpl in root.find_all(lambda n: n.tag == "template" and "data-section-panel" in n.attrs):
        number = int(tpl.attrs["data-section-panel"] or 0) + 1
        chunks.add(
            page=page,
            course=course,
            title=f"Module {number} activities",
            text=f"Activities in module {number} of VA-1:\n" + text_of(tpl, into_templates=True),
            kind="dashboard",
        )
    modal = root.by_id("program-structure-modal")
    if modal is not None:
        chunks.add(
            page=page,
            course=course,
            title="Programme structure: courses and modules",
            text=text_of(modal, into_templates=True),
            kind="outline",
        )


def paced_home(chunks: Chunks):
    page = "homepage-v1-paced.html"
    course = "WR 100: Fundamentals of Effective Communication"
    root = parse(PAGES / page)
    main = root.find(lambda n: n.tag == "main")

    labels = {}  # track id -> "Week 10" or "Course Overview"
    for node in root.find_all(lambda n: "data-track-id" in n.attrs):
        label = text_of(node).replace("\n", " ").strip()
        match = re.search(r"Week \d+", label)
        labels[node.attrs["data-track-id"]] = match.group(0) if match else (label or "Course overview")

    # What the learner sees on load: the current week and the overall score.
    chunks.add(
        page=page,
        course=course,
        title="Learner dashboard (paced): current week, deliverables and events",
        text=text_of(main),
        kind="dashboard",
    )

    # Every week was pre-rendered into a <template>. Each one holds that week's lesson
    # content as well as its deliverables, so it is cut at its own headings.
    for tpl in root.find_all(lambda n: n.tag == "template" and "data-track-panel" in n.attrs):
        label = labels.get(tpl.attrs["data-track-panel"], "Course overview")
        for heading, _, text in grouped(sections(tpl, split_level=6, into_templates=True)):
            chunks.add(
                page=page,
                course=course,
                title=f"{label}: {heading}" if heading else label,
                text=f"From {label} of WR 100.\n{text}",
                kind="lesson",
            )

    # The score table is rendered once per week with the same rows; one copy is enough.
    for tpl in root.find_all(lambda n: n.tag == "template" and "data-track-modals" in n.attrs):
        body = text_of(tpl, into_templates=True)
        if len(body) > 200:
            chunks.add(
                page=page,
                course=course,
                title="Score details: grade for each assignment",
                text="Score details for WR 100.\n" + body,
                kind="dashboard",
            )
            break


def build() -> list[dict]:
    chunks = Chunks()
    concept_page(chunks)
    self_paced_home(chunks)
    paced_home(chunks)
    return chunks.items


if __name__ == "__main__":
    items = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    by_page: dict[str, int] = {}
    for item in items:
        by_page[item["page"]] = by_page.get(item["page"], 0) + 1
    print(f"Wrote {len(items)} chunks to {OUT.relative_to(ROOT)}")
    for page, count in by_page.items():
        print(f"  {count:3d}  {page}")
