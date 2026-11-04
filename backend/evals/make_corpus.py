"""Write the versioned Chinese eval corpus and questions.

The notes are synthetic lab records. Questions either quote a unique conclusion
or ask for a rare batch code that also appears in a pile of look-alike notes.
"""
import json
import os

from app.rag.engine import tokenize

SET_VERSION = "p1-v1"
UPDATED_AT = "2026-01-15T00:00:00+00:00"

PHRASES = [
    "石英舟用稀释氢氟酸浸泡",
    "真空规管烘烤上限一百二十度",
    "光刻胶开封后必须冷藏",
    "等离子清洗机腔体先抽空",
    "金线键合压力逐批记录",
    "椭圆偏振仪入射角固定七十度",
    "超声波清洗换水不超过三次",
    "手套箱水氧报警阈值写在门上",
    "溅射靶材更换要双人签字",
    "退火炉升温斜率每分钟五度",
    "探针台接地线每周测电阻",
    "光罩盒只能竖立存放",
    "离心机转子对号入座",
    "液氮罐补液前先排空软管",
    "培养箱二氧化碳瓶压力每天看",
    "超净台风速滤芯按月更换",
    "移液器外校证书贴在抽屉",
    "纯水机电阻率低于读数就停用",
    "真空泵油窗口变色即更换",
    "样品袋条码与工单号一致",
]

UNANSWERABLE = [
    "国际空间站年度预算折合多少美元",
    "周三食堂供应什么午餐",
    "贵州茅台今天的收盘价是多少",
    "个人护照延期要准备哪些材料",
    "世界杯决赛在哪座球场踢",
    "红烧排骨的配菜有哪几样",
    "地铁二号线末班车几点",
    "去年票房最高的电影叫什么",
    "北极航线冬季是否通航",
    "美元兑日元汇率现在是多少",
    "流感疫苗预约还开放吗",
    "钢琴考级曲目有哪些",
    "火星车太阳能板如何展开",
    "奥运会开幕式在哪天举行",
    "个人所得税专项扣除怎么填",
    "航空里程可以兑换什么机票",
    "咖啡豆烘焙曲线怎么看",
    "足球越位规则如何判定",
]


def build():
    documents = []
    questions = []
    for index, phrase in enumerate(PHRASES, start=1):
        doc_id = f"g{index:02d}"
        code = f"CODE-{1000 + index}"
        content = (
            f"# {phrase}\n\n"
            f"## 结论\n"
            f"编号 {code}。关键结论：{phrase}。校准周期按九十天执行。\n"
        )
        documents.append({
            "doc_id": doc_id,
            "title": phrase,
            "content": content,
            "source": "seed",
            "updated_at": UPDATED_AT,
            "access_scope": "lab",
            "source_url": f"https://example.com/seed/{doc_id}",
        })
        questions.append({
            "id": f"e{index:02d}",
            "question": f"{phrase}这一条记录的关键结论是什么",
            "answerable": True,
            "doc_id": doc_id,
            "key_phrase": phrase,
            "set_version": SET_VERSION,
        })
        if index <= 10:
            hard_question = f"编号 {code} 的校准周期是多少"
        else:
            hard_question = (
                f"请核对运行记录中的储存温度、负责岗位、校准周期和操作步骤，"
                f"只看编号 {code}。"
            )
        questions.append({
            "id": f"h{index:02d}",
            "question": hard_question,
            "answerable": True,
            "doc_id": doc_id,
            "key_phrase": phrase,
            "set_version": SET_VERSION,
        })
    boiler = (
        "本页汇总储存温度、负责岗位、校准周期和操作步骤。"
        "储存温度按室温记录，负责岗位由值班员填写，校准周期写入运行记录，"
        "操作步骤见附件清单。储存温度、负责岗位、校准周期、操作步骤需要双人复核。"
    )
    for index in range(1, 13):
        doc_id = f"d{index:02d}"
        documents.append({
            "doc_id": doc_id,
            "title": f"运行记录索引 {index}",
            "content": f"# 运行记录索引\n\n## 条目\n编号 DECOY-{index:02d}。{boiler}\n",
            "source": "seed",
            "updated_at": UPDATED_AT,
            "access_scope": "lab",
            "source_url": f"https://example.com/seed/{doc_id}",
        })
    corpus_tokens = set()
    for document in documents:
        corpus_tokens.update(tokenize(document["title"] + document["content"]))
    for index, question in enumerate(UNANSWERABLE, start=1):
        overlap = set(tokenize(question)) & corpus_tokens
        if overlap:
            raise SystemExit(f"unanswerable question overlaps corpus: {question} {overlap}")
        questions.append({
            "id": f"u{index:02d}",
            "question": question,
            "answerable": False,
            "doc_id": None,
            "key_phrase": None,
            "set_version": SET_VERSION,
        })
    return documents, questions


def main():
    root = os.path.dirname(__file__)
    documents, questions = build()
    _dump(os.path.join(root, "corpus.jsonl"), documents)
    _dump(os.path.join(root, "questions.jsonl"), questions)
    answerable = sum(1 for item in questions if item["answerable"])
    print(f"docs={len(documents)} questions={len(questions)} answerable={answerable} version={SET_VERSION}")


def _dump(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
