#!/usr/bin/env python3
"""K-06: data/checklists.json からライフイベント・チェックリストページを生成する。

出力先: checklist/<slug>/index.html
チェック状態はlocalStorage(キー: enshu-checklist-<slug>)に保持し、進捗を表示する。
共通パーツ(header/footer/disclaimer/head-css)は他ページと同じマーカーで埋め込み、
scripts/inject_parts.py の対象になる。

使い方: python3 scripts/build_checklists.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKLISTS_PATH = os.path.join(ROOT, "data", "checklists.json")
PARTS_DIR = os.path.join(ROOT, "parts")
OUT_DIR = os.path.join(ROOT, "checklist")


def load_parts():
    parts = {}
    for name in ("head-css", "header", "disclaimer", "footer"):
        with open(os.path.join(PARTS_DIR, "%s.html" % name), encoding="utf-8") as f:
            parts[name] = f.read().strip()
    return parts


def part_markup(name, content):
    return "<!-- PART:%s:START -->%s<!-- PART:%s:END -->" % (name, content, name)


def build_page(checklist, parts):
    slug = checklist["slug"]
    title = checklist["title"]
    emoji = checklist["emoji"]
    lead = checklist["lead"]
    tasks = checklist["tasks"]
    storage_key = "enshu-checklist-%s" % slug

    items_html = "".join(
        '<li class="checklist-item" data-task-id="%s">'
        '<label class="checklist-label">'
        '<input type="checkbox" class="checklist-check" data-task-id="%s" data-track-click="checklist_check">'
        '<span class="checklist-text">%s</span>'
        "</label>"
        '<a class="checklist-link" href="%s">くわしく見る</a>'
        "</li>" % (t["id"], t["id"], t["label"], t["href"])
        for t in tasks
    )

    task_ids_json = json.dumps([t["id"] for t in tasks], ensure_ascii=False)

    script = (
        "<script>(function(){"
        "var KEY=%s;var ids=%s;"
        "var box=document.getElementById('checklist-box');if(!box){return;}"
        "var bar=document.getElementById('checklist-progress-bar');"
        "var label=document.getElementById('checklist-progress-label');"
        "function load(){try{return JSON.parse(localStorage.getItem(KEY)||'{}');}catch(e){return {};}}"
        "function save(state){try{localStorage.setItem(KEY,JSON.stringify(state));}catch(e){}}"
        "function render(){"
        "var state=load();var done=0;"
        "ids.forEach(function(id){"
        "var cb=box.querySelector('.checklist-check[data-task-id=\"'+id+'\"]');"
        "var li=box.querySelector('.checklist-item[data-task-id=\"'+id+'\"]');"
        "var checked=!!state[id];"
        "if(cb){cb.checked=checked;}"
        "if(li){li.classList.toggle('is-done',checked);}"
        "if(checked){done++;}"
        "});"
        "var pct=ids.length?Math.round(done/ids.length*100):0;"
        "if(bar){bar.style.width=pct+'%%';}"
        "if(label){label.textContent=done+' / '+ids.length+' 完了';}"
        "if(done===ids.length&&ids.length){box.classList.add('is-complete');}else{box.classList.remove('is-complete');}"
        "}"
        "box.addEventListener('change',function(e){"
        "var cb=e.target.closest('.checklist-check');if(!cb){return;}"
        "var state=load();state[cb.getAttribute('data-task-id')]=cb.checked;save(state);render();"
        "});"
        "render();"
        "})();</script>"
    ) % (json.dumps(storage_key, ensure_ascii=False), task_ids_json)

    html = (
        '<!doctype html><html lang="ja"><head>\n'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>%s | チェックリスト | 磐田ライフハック</title>\n"
        '<meta name="description" content="%s">\n'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
        "%s\n"
        "</head><body>\n"
        "%s\n"
        "%s\n"
        '<main id="main"><div class="wrap">\n'
        '<p class="breadcrumb"><a href="/">磐田ライフハック</a> ／ チェックリスト ／ %s</p>\n'
        '<section class="hero"><div class="hero-visual"><h1>%s %s</h1></div>'
        '<div class="hero-body"><p class="lead">%s</p></div></section>\n'
        '<div id="checklist-box" class="checklist-box">\n'
        '<div class="checklist-progress"><div class="checklist-progress-track">'
        '<div id="checklist-progress-bar" class="checklist-progress-bar"></div></div>'
        '<p id="checklist-progress-label" class="checklist-progress-label">0 / %d 完了</p></div>\n'
        '<ul class="checklist-list">%s</ul>\n'
        '<p class="checklist-note mini">チェックはこの端末のブラウザに保存されます。他の端末とは共有されません。手続きの詳細・最新情報は各リンク先ページ、または磐田市公式サイトで必ず確認してください。</p>\n'
        "</div>\n"
        "%s\n"
        "</div></main>\n"
        "%s\n"
        "</body></html>\n"
    ) % (
        title,
        lead,
        part_markup("head-css", parts["head-css"]),
        part_markup("header", parts["header"]),
        part_markup("disclaimer", parts["disclaimer"]),
        title,
        emoji,
        title,
        lead,
        len(tasks),
        items_html,
        script,
        part_markup("footer", parts["footer"]),
    )

    out_path = os.path.join(OUT_DIR, slug, "index.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(html)
    return out_path


def main():
    with open(CHECKLISTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    parts = load_parts()

    generated = []
    for checklist in data["checklists"]:
        path = build_page(checklist, parts)
        generated.append(os.path.relpath(path, ROOT))

    print("生成 %d ページ:" % len(generated))
    for p in generated:
        print("  " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
