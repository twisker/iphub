#!/usr/bin/env python3
"""Generate README.md + HTML landing pages from registry data.

Usage: python scripts/generate_pages.py [--changed-only]

Reads: registry/, index.yaml, templates/
Writes: docs/
"""

import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry"
TEMPLATES = ROOT / "templates"
PAGES = ROOT / "docs"
INDEX_FILE = ROOT / "index.yaml"
LANGUAGES = ["en", "zh-cn"]


def load_i18n(lang: str) -> dict:
    path = TEMPLATES / "i18n" / f"{lang}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_index() -> dict:
    if INDEX_FILE.exists():
        return yaml.safe_load(INDEX_FILE.read_text(encoding="utf-8")) or {}
    return {}


def get_skill_info(skill_name: str, index: dict) -> dict:
    skills = index.get("skills", {})
    info = skills.get(skill_name, {})
    return {
        "name": skill_name,
        "description": info.get("description", ""),
        "installs": info.get("installs", 0),
    }


def process_package(owner_dir: Path, pkg_dir: Path, index: dict, env: Environment):
    meta_file = pkg_dir / "meta.yaml"
    if not meta_file.exists():
        return

    meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
    pkg_name = meta.get("name", pkg_dir.name)
    owner = owner_dir.name

    # Load version files
    versions = []
    for vf in sorted(pkg_dir.glob("*.yaml"), reverse=True):
        if vf.name == "meta.yaml":
            continue
        vdata = yaml.safe_load(vf.read_text(encoding="utf-8")) or {}
        versions.append(vdata)

    # Get skill info from index
    skills = []
    if versions:
        for s in versions[0].get("skills", []):
            skills.append(get_skill_info(s.get("name", ""), index))

    # Check for custom.md override
    custom_md = pkg_dir / "custom.md"

    pkg_data = {
        "name": pkg_name,
        "description": meta.get("description", ""),
        "summary": meta.get("summary", ""),
        "tags": meta.get("tags", []),
        "links": meta.get("links", []),
        "icon": meta.get("icon", ""),
        "author": meta.get("author", owner),
        "homepage": meta.get("homepage", ""),
        "repository": meta.get("repository", ""),
    }

    out_dir = PAGES / owner / pkg_name

    # Generate README.md (single language, from custom.md or template)
    readme_template = env.get_template("ip-readme.md.j2")
    if custom_md.exists():
        readme_content = custom_md.read_text(encoding="utf-8")
    else:
        t = load_i18n("en")
        readme_content = readme_template.render(pkg=pkg_data, skills=skills, versions=versions, t=t)
    readme_dir = out_dir
    readme_dir.mkdir(parents=True, exist_ok=True)
    (readme_dir / "README.md").write_text(readme_content, encoding="utf-8")

    # Generate HTML per language
    html_template = env.get_template("ip-landing.html.j2")
    for lang in LANGUAGES:
        t = load_i18n(lang)
        other_langs = {l: f"../{l}/" for l in LANGUAGES if l != lang}
        html = html_template.render(
            pkg=pkg_data, skills=skills, versions=versions, t=t,
            lang=lang, other_langs=other_langs,
        )
        lang_dir = out_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        (lang_dir / "index.html").write_text(html, encoding="utf-8")

    # Root index.html — English default with language switcher
    t = load_i18n("en")
    root_html = html_template.render(
        pkg=pkg_data, skills=skills, versions=versions, t=t,
        lang="en", other_langs={"zh-cn": "zh-cn/"},
    )
    (out_dir / "index.html").write_text(root_html, encoding="utf-8")

    print(f"  Generated pages for {owner}/{pkg_name}")


def main():
    index = load_index()
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=False,
        keep_trailing_newline=True,
    )

    PAGES.mkdir(exist_ok=True)

    if not REGISTRY.exists():
        print("No registry directory found.")
        return

    count = 0
    for owner_dir in sorted(REGISTRY.iterdir()):
        if not owner_dir.is_dir():
            continue
        for item in sorted(owner_dir.iterdir()):
            if item.is_dir():
                process_package(owner_dir, item, index, env)
                count += 1

    print(f"Generated pages for {count} packages.")

    generate_homepage(index, env)
    generate_tag_pages(index, env)
    generate_author_pages(index, env)


def generate_homepage(index: dict, env: Environment):
    """Generate IpHub homepage."""
    template = env.get_template("index-page.html.j2")
    trending = index.get("trending", {})
    tags = index.get("tags", {})

    # Collect all entries for listing
    all_skills = [{"name": n, **info} for n, info in index.get("skills", {}).items()]
    all_packages = [{"name": n, **info} for n, info in index.get("packages", {}).items()]

    # Collect unique authors
    authors = set()
    for section in ("skills", "packages"):
        for name, info in index.get(section, {}).items():
            owner = info.get("owner", "")
            if owner:
                authors.add(owner)
    authors = sorted(authors)

    for lang in LANGUAGES:
        t = load_i18n(lang)
        html = template.render(
            trending=trending, all_skills=all_skills, all_packages=all_packages,
            tags=tags, authors=authors, t=t, lang=lang,
        )
        lang_dir = PAGES / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        (lang_dir / "index.html").write_text(html, encoding="utf-8")

    # Root index.html — English default
    t = load_i18n("en")
    html = template.render(
        trending=trending, all_skills=all_skills, all_packages=all_packages,
        tags=tags, authors=authors, t=t, lang="en",
    )
    (PAGES / "index.html").write_text(html, encoding="utf-8")
    print("  Generated homepage")


def generate_tag_pages(index: dict, env: Environment):
    """Generate per-tag browse pages."""
    template = env.get_template("tag-page.html.j2")
    tags_data = index.get("tags", {})

    for tag_name, tag_info in tags_data.items():
        # Collect entries for this tag
        entries = []
        for section in ("skills", "packages"):
            for name, info in index.get(section, {}).items():
                if tag_name in info.get("tags", []):
                    entries.append({"name": name, "type": info.get("type", section), **info})

        for lang in LANGUAGES:
            t = load_i18n(lang)
            html = template.render(tag_name=tag_name, entries=entries, t=t, lang=lang)
            tag_dir = PAGES / "tags" / tag_name / lang
            tag_dir.mkdir(parents=True, exist_ok=True)
            (tag_dir / "index.html").write_text(html, encoding="utf-8")

        # Root for this tag — English default
        t = load_i18n("en")
        html = template.render(tag_name=tag_name, entries=entries, t=t, lang="en")
        tag_root = PAGES / "tags" / tag_name
        tag_root.mkdir(parents=True, exist_ok=True)
        (tag_root / "index.html").write_text(html, encoding="utf-8")

    print(f"  Generated {len(tags_data)} tag pages")


def generate_author_pages(index: dict, env: Environment):
    """Generate per-author profile pages."""
    template = env.get_template("author-page.html.j2")

    # Aggregate by owner
    authors = {}
    for section in ("skills", "packages"):
        for name, info in index.get(section, {}).items():
            owner = info.get("owner", "unknown")
            if owner not in authors:
                authors[owner] = {"skills": [], "packages": [], "total_installs": 0}
            entry = {"name": name, **info}
            if section == "skills":
                authors[owner]["skills"].append(entry)
            else:
                authors[owner]["packages"].append(entry)
            authors[owner]["total_installs"] += info.get("installs", 0)

    for author, data in authors.items():
        for lang in LANGUAGES:
            t = load_i18n(lang)
            html = template.render(
                author=author, skills=data["skills"], packages=data["packages"],
                total_installs=data["total_installs"], t=t, lang=lang,
            )
            author_dir = PAGES / author / lang
            author_dir.mkdir(parents=True, exist_ok=True)
            (author_dir / "index.html").write_text(html, encoding="utf-8")

        # Root — English default
        t = load_i18n("en")
        html = template.render(
            author=author, skills=data["skills"], packages=data["packages"],
            total_installs=data["total_installs"], t=t, lang="en",
        )
        author_root = PAGES / author
        author_root.mkdir(parents=True, exist_ok=True)
        (author_root / "index.html").write_text(html, encoding="utf-8")

    print(f"  Generated {len(authors)} author pages")


if __name__ == "__main__":
    main()
