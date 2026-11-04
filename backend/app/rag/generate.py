"""Grounded prompt. The model only sees retrieved chunks."""


def messages_for(query, hits):
    blocks = []
    for hit in hits:
        doc_id = hit.get("doc_id") or hit.get("id")
        span = hit.get("span")
        blocks.append(
            "\n".join([
                f"[doc_id={doc_id}] 标题={hit.get('title') or ''}",
                f"章节={hit.get('section') or ''}",
                f"span={span}",
                hit.get("quote") or hit.get("text") or "",
            ])
        )
    system = (
        "你是实验室知识库问答助手。只能根据下面的检索片段回答。\n"
        "不要使用片段以外的知识，不要编造数字、人员或结论。\n"
        "每个事实句末用 [doc_id] 标出来源。\n"
        "如果片段不足以回答，只输出“不知道”。\n\n"
        + "\n\n".join(blocks)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]
