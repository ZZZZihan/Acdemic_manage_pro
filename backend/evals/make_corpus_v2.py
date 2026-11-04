"""Build the harder p1-v2 set. p1-v1 files are left untouched.

Questions paraphrase the conclusion, distractors share the topic wording,
the annotated fact sits in a later section, and unanswerable questions reuse
corpus vocabulary on purpose.
"""
import hashlib
import json
import os

from app.rag.chunk import chunk_document
from app.rag.engine import tokenize

SET_VERSION = "p1-v2"
UPDATED_AT = "2026-02-01T00:00:00+00:00"

FAMILIES = [
    {
        "slug": "resist",
        "noun": "光刻胶",
        "place": "黄光区",
        "title": "光刻胶收纳判定",
        "key_phrase": "四摄氏度专用柜",
        "fact": "拆封后的正性光刻胶只能放进四摄氏度专用柜，禁止在黄光区过夜。",
        "distractors": [
            ("光刻胶台面临时放置", "拆封后的正性光刻胶放在二十二摄氏度黄光区台面，允许停留六小时。"),
            ("光刻胶回温后再涂", "光刻胶从冷柜取出后先在黄光区回温二十分钟，再开始涂布。"),
        ],
        "questions": [
            ("paraphrase", "感光涂层打开包装以后，能不能在曝光房间留到第二天？应该收进多冷的柜子？"),
            ("paraphrase", "正胶用过之后如果不能留在曝光间过夜，指定收纳的是哪一类柜子？"),
            ("multichunk", "判定一节对打开包装的感光材料怎么收？写的是哪一种柜子，而不是台面临时放。"),
        ],
    },
    {
        "slug": "boat",
        "noun": "石英舟",
        "place": "清洗槽",
        "title": "石英舟酸洗判定",
        "key_phrase": "百分之一氢氟酸浸泡两分钟",
        "fact": "石英舟清洗用百分之一氢氟酸浸泡两分钟，随后用超纯水冲到中性。",
        "distractors": [
            ("石英舟清水冲洗", "石英舟只用超纯水冲洗十分钟，整个流程不接触氢氟酸。"),
            ("石英舟硝酸过夜", "石英舟每月用百分之五硝酸浸泡一夜，再冲洗。"),
        ],
        "questions": [
            ("paraphrase", "透明晶片载具上的残留膜，短时间弱酸洗的配比和时长是多少？不是过夜那种。"),
            ("paraphrase", "洗晶舟时，稀的氢氟酸要泡多久才冲水？"),
            ("multichunk", "判定里晶舟酸洗是短泡还是泡一夜？短泡的配方写在最后一节。"),
        ],
    },
    {
        "slug": "pump",
        "noun": "真空泵油",
        "place": "前级泵",
        "title": "真空泵换油判定",
        "key_phrase": "视窗变成琥珀色就换油",
        "fact": "真空泵油视窗变成琥珀色就换油，不要按固定月数硬换。",
        "distractors": [
            ("真空泵按月换油", "真空泵油每三十天更换，视窗颜色只做记录，不作为更换条件。"),
            ("真空泵浑浊再观察", "真空泵油轻微浑浊先继续运行，等到完全发黑再换油。"),
        ],
        "questions": [
            ("paraphrase", "前级泵润滑油的观察窗发黄发棕时，要不要立刻更换，还是只记一笔？"),
            ("paraphrase", "泵油是看颜色变成那种深黄棕再换，还是攒满一个月必须换？"),
            ("multichunk", "判定要求换油看视窗颜色还是看日历？正确条件写在文末。"),
        ],
    },
    {
        "slug": "ln2",
        "noun": "液氮",
        "place": "杜瓦",
        "title": "液氮补液判定",
        "key_phrase": "先排空软管再开阀门",
        "fact": "液氮罐补液前必须先排空软管再开阀门，防止热气灌入。",
        "distractors": [
            ("液氮直接开阀", "液氮罐补液时直接打开主阀，软管留在罐口，不必预先放气。"),
            ("液氮先开主阀", "补液顺序是先开阀门再提起软管，让液体自己把空气顶出去。"),
        ],
        "questions": [
            ("paraphrase", "往杜瓦里加低温液体之前，连接管里的热气要先放掉吗？"),
            ("paraphrase", "灌低温冷媒时，是先把管子排空还是先拧开总阀？"),
            ("multichunk", "判定规定的补液顺序是什么？不要把先开阀的写法当成结论。"),
        ],
    },
    {
        "slug": "glove",
        "noun": "手套箱",
        "place": "传样窗",
        "title": "手套箱水氧判定",
        "key_phrase": "水氧都超过一 ppm 就锁传样",
        "fact": "手套箱水氧都超过一 ppm 就锁传样，只允许紧急取样。",
        "distractors": [
            ("手套箱十 ppm 才停", "手套箱水氧超过十 ppm 才报警，传样窗口在那之前照常打开。"),
            ("手套箱只记水氧", "手套箱水氧读数每小时抄录，传样窗不因读数上锁。"),
        ],
        "questions": [
            ("paraphrase", "惰性气氛箱里水分和氧气同时越界到大约百万分之一时，传递窗还让不让用？"),
            ("paraphrase", "箱体气氛刚过很严的那一档，是锁上传递口，还是继续传东西？"),
            ("multichunk", "判定对传递口上锁的门槛，是较严的那一档还是宽松十倍的那一档？"),
        ],
    },
    {
        "slug": "probe",
        "noun": "探针台",
        "place": "扎针间",
        "title": "探针台接地判定",
        "key_phrase": "接地电阻大于两欧姆就停机",
        "fact": "探针台接地线每周测量，接地电阻大于两欧姆就停机。",
        "distractors": [
            ("探针台二十欧姆才停", "探针台接地电阻大于二十欧姆才停机，两欧姆只写进点检表。"),
            ("探针台只记录阻值", "探针台接地电阻每周测量并归档，不设停机线。"),
        ],
        "questions": [
            ("paraphrase", "扎针设备的保护地线阻值高过大约两个欧姆时，还能不能继续扎？"),
            ("paraphrase", "地线每周量一次，读数刚超过二欧就要关机吗？"),
            ("multichunk", "判定里的停机线是大约二欧，还是二十欧那种宽松线？"),
        ],
    },
    {
        "slug": "incubator",
        "noun": "培养箱",
        "place": "细胞间",
        "title": "培养箱供气判定",
        "key_phrase": "钢瓶压力低于一兆帕就更换",
        "fact": "培养箱二氧化碳钢瓶压力低于一兆帕就更换，不要等到流量报警。",
        "distractors": [
            ("培养箱零点二兆帕再换", "培养箱二氧化碳钢瓶压力低于零点二兆帕再更换。"),
            ("培养箱等流量报警", "培养箱钢瓶一直用到流量报警才更换，压力表只做参考。"),
        ],
        "questions": [
            ("paraphrase", "细胞箱供气瓶的表压掉到大约一个兆帕时就要换瓶吗？"),
            ("paraphrase", "供气瓶是压力掉到一兆帕就换，还是非要等流量叫了再换？"),
            ("multichunk", "判定要求换瓶看表压的哪一档？不要采用等报警的写法。"),
        ],
    },
    {
        "slug": "hood",
        "noun": "超净台",
        "place": "洁净间",
        "title": "超净台滤芯判定",
        "key_phrase": "滤芯压差超过一百五十帕就换",
        "fact": "超净台风速滤芯压差超过一百五十帕就换，不要只看日历。",
        "distractors": [
            ("超净台半年一换", "超净台滤芯每半年更换，压差只做参考，不触发更换。"),
            ("超净台三百帕再换", "超净台滤芯压差超过三百帕才更换，一百五十帕继续使用。"),
        ],
        "questions": [
            ("paraphrase", "洁净工作台送风变弱、过滤层两侧阻力升过大约一百五十帕时，要不要马上换过滤部件？"),
            ("paraphrase", "过滤层的阻力门槛是一百五那一档就换，还是要更高才动？"),
            ("multichunk", "判定是按压差更换过滤层，还是按半年日历更换？"),
        ],
    },
    {
        "slug": "centrifuge",
        "noun": "离心机",
        "place": "转子柜",
        "title": "离心机转子判定",
        "key_phrase": "转子编号必须和腔体铭牌一致",
        "fact": "离心机转子编号必须和腔体铭牌一致，禁止混用相邻型号。",
        "distractors": [
            ("离心机可临时换转子", "离心机转子可以临时换到同转速的另一台，铭牌不一致也能转。"),
            ("离心机只核对转速", "离心机使用前只核对最高转速，转子编号不必对铭牌。"),
        ],
        "questions": [
            ("paraphrase", "转头上的号码和机身上的牌子对不上时，还能不能凑合转？"),
            ("paraphrase", "相邻型号的转头借到另一台同转速机器上，算不算违规？"),
            ("multichunk", "判定是否允许铭牌和转头号码不一致？结论在文末。"),
        ],
    },
    {
        "slug": "furnace",
        "noun": "退火炉",
        "place": "热处理间",
        "title": "退火炉升温判定",
        "key_phrase": "每分钟五度，禁止跳到目标温度",
        "fact": "退火炉升温斜率每分钟五度，禁止跳到目标温度。",
        "distractors": [
            ("退火炉直接设温", "退火炉允许直接设到目标温度，斜率不作要求。"),
            ("退火炉每分钟二十度", "退火炉升温斜率每分钟二十度，可以较快跳到目标温度附近。"),
        ],
        "questions": [
            ("paraphrase", "热处理炉能不能一下设到终点？记录要求的爬升是不是很慢的那一档？"),
            ("paraphrase", "升温是每分钟大约五度慢慢爬，还是允许直接打到终点？"),
            ("multichunk", "判定禁止的是跳温还是慢爬？正确斜率写在最后。"),
        ],
    },
    {
        "slug": "sputter",
        "noun": "溅射靶材",
        "place": "镀膜间",
        "title": "溅射换靶判定",
        "key_phrase": "更换要双人签字",
        "fact": "溅射靶材更换要双人签字，单人操作视为无效。",
        "distractors": [
            ("溅射一人换靶", "溅射靶材由当班一人更换，事后补一个签名即可。"),
            ("溅射换靶免签字", "溅射靶材更换只写进运行记录，不需要第二个人签名。"),
        ],
        "questions": [
            ("paraphrase", "镀膜机换金属源的时候，只留一个人签名算不算数？"),
            ("paraphrase", "换源是必须两个人当场一起签，还是事后补签也行？"),
            ("multichunk", "判定对换源签名的人数要求是什么？不要采用单人补签的说法。"),
        ],
    },
    {
        "slug": "water",
        "noun": "纯水机",
        "place": "制水间",
        "title": "纯水电阻率判定",
        "key_phrase": "电阻率低于十点零兆欧厘米就停用",
        "fact": "纯水机电阻率低于十点零兆欧厘米就停用出水。",
        "distractors": [
            ("纯水机一点零才停", "纯水机电阻率低于一点零兆欧厘米才停用，十点零仍可接水。"),
            ("纯水机只记录读数", "纯水机电阻率每班抄录，读数偏低也继续出水。"),
        ],
        "questions": [
            ("paraphrase", "去离子出水的电阻读数掉到大约十的时候，还允许接水吗？"),
            ("paraphrase", "水质掉到十兆欧这一档就要关出水，还是要更差才关？"),
            ("multichunk", "判定的停水线是十这一点，还是一点零那条更松的线？"),
        ],
    },
    {
        "slug": "ellips",
        "noun": "椭圆偏振仪",
        "place": "量测间",
        "title": "椭偏入射角判定",
        "key_phrase": "入射角固定七十度",
        "fact": "椭圆偏振仪入射角固定七十度，不准改成六十五。",
        "distractors": [
            ("椭偏用六十五度", "椭圆偏振仪入射角用六十五度，七十度只作备用角度。"),
            ("椭偏角度可改", "椭圆偏振仪入射角按样品临时修改，没有固定角度。"),
        ],
        "questions": [
            ("paraphrase", "测膜厚那台偏振光仪器，光束打到样品上的角度要锁死在哪一档？"),
            ("paraphrase", "量测时光的入射是固定在七十那一档，还是可以改小五度？"),
            ("multichunk", "判定是否允许把入射角改成备用的较小角度？"),
        ],
    },
    {
        "slug": "mask",
        "noun": "光罩盒",
        "place": "掩模柜",
        "title": "光罩存放判定",
        "key_phrase": "只能竖立存放，禁止叠放",
        "fact": "光罩盒只能竖立存放，禁止叠放。",
        "distractors": [
            ("光罩盒可以平叠", "光罩盒可以平放叠三层，竖立只在搬运时使用。"),
            ("光罩盒侧放两层", "光罩盒侧放不超过两层，竖立存放没有要求。"),
        ],
        "questions": [
            ("paraphrase", "掩模版的盒子在柜子里应该站着放，还是可以摞起来？"),
            ("paraphrase", "版盒是必须立着，还是允许摞到三层？"),
            ("multichunk", "判定允许叠放吗？正确姿势写在文末，不要看平放那一版。"),
        ],
    },
]

UNANSWERABLE = [
    "光刻胶这个月的采购含税金额是多少",
    "黄光区昨天访客的身份证号码是什么",
    "真空泵油供应商的银行账号是多少",
    "液氮罐去年全年的电费是多少",
    "手套箱值班员的家庭住址写在哪一页",
    "探针台维修合同的违约金是多少",
    "培养箱钢瓶的快递单号是什么",
    "超净台滤芯发票的代码是多少",
    "离心机转子出厂调试人员的手机号是多少",
    "退火炉的固定资产原值是多少",
    "溅射靶材这次投标的报价是多少",
    "纯水机耗材的报销单号是什么",
    "椭圆偏振仪校准员的护照号码是什么",
    "光罩盒所在仓库的月租金是多少",
    "石英舟清洗间的门禁密码是多少",
    "真空泵运输车辆的车牌号是什么",
    "液氮补液员的月工资是多少",
    "手套箱报警短信发到哪一个私人手机",
    "探针台夹具的专利许可费是多少",
    "培养箱相关论文的被引次数是多少",
    "超净台装修承包商的税号是多少",
    "离心机保险单的受益人是谁",
    "退火炉操作工的血型是什么",
    "溅射靶材供应商的报价单号是多少",
]


def _filler(noun, place):
    sentence = f"{noun}在{place}交接时核对批次、排风、温湿度、工单和签字栏。"
    return sentence * 18


def _document(doc_id, title, noun, place, fact):
    filler = _filler(noun, place)
    content = (
        f"# {title}\n\n"
        f"## 日常点检\n{filler}\n操作前确认{noun}批次与工单一致，异常先停手。\n\n"
        f"## 操作步骤\n{filler}\n按作业指导把{noun}送到{place}，做完写入运行记录。\n\n"
        f"## 判定\n{fact}\n"
    )
    return {
        "doc_id": doc_id,
        "title": title,
        "content": content,
        "source": "seed",
        "updated_at": UPDATED_AT,
        "access_scope": "lab",
        "source_url": f"https://example.com/seed/{doc_id}",
    }


def build():
    documents = []
    questions = []
    for index, family in enumerate(FAMILIES, start=1):
        gold_id = f"v2g{index:02d}"
        documents.append(_document(gold_id, family["title"], family["noun"], family["place"], family["fact"]))
        for offset, (title, fact) in enumerate(family["distractors"], start=1):
            documents.append(_document(
                f"v2d{index:02d}{chr(96 + offset)}",
                title,
                family["noun"],
                family["place"],
                fact,
            ))
        for q_index, (kind, text) in enumerate(family["questions"], start=1):
            questions.append({
                "id": f"v2-{family['slug']}-{q_index}",
                "question": text,
                "answerable": True,
                "doc_id": gold_id,
                "key_phrase": family["key_phrase"],
                "type": kind,
                "split": _split(f"{family['slug']}-{kind}-{q_index}"),
                "set_version": SET_VERSION,
            })
    for index, text in enumerate(UNANSWERABLE, start=1):
        questions.append({
            "id": f"v2-u{index:02d}",
            "question": text,
            "answerable": False,
            "doc_id": None,
            "key_phrase": None,
            "type": "unanswerable",
            "split": _split(f"unanswerable-{index}"),
            "set_version": SET_VERSION,
        })
    _validate(documents, questions)
    return documents, questions


def _split(key):
    bucket = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % 5
    return "dev" if bucket < 2 else "test"


def _validate(documents, questions):
    by_id = {row["doc_id"]: row["content"] for row in documents}
    corpus_tokens = set()
    for row in documents:
        corpus_tokens.update(tokenize(row["title"] + "\n" + row["content"]))
    if len(questions) < 60:
        raise SystemExit(f"expected at least 60 questions, got {len(questions)}")
    for item in questions:
        if not item["answerable"]:
            overlap = set(tokenize(item["question"])) & corpus_tokens
            if len(overlap) < 2:
                raise SystemExit(f"unanswerable question shares too little: {item['question']} {overlap}")
            continue
        if item["key_phrase"] in item["question"]:
            raise SystemExit(f"question copies the key phrase: {item['id']}")
        gold = by_id[item["doc_id"]]
        if gold.count(item["key_phrase"]) != 1:
            raise SystemExit(f"key phrase count != 1 in gold: {item['id']}")
        for doc_id, content in by_id.items():
            if doc_id != item["doc_id"] and item["key_phrase"] in content:
                raise SystemExit(f"key phrase leaked into {doc_id}: {item['key_phrase']}")
        chunks = chunk_document(gold, title="")
        if len(chunks) < 2:
            raise SystemExit(f"gold doc is a single chunk: {item['doc_id']} chunks={len(chunks)}")
        if item["key_phrase"] in chunks[0]["text"]:
            raise SystemExit(f"key phrase is in the first chunk: {item['doc_id']}")
        if not any(item["key_phrase"] in chunk["text"] for chunk in chunks):
            raise SystemExit(f"key phrase missing from chunks: {item['doc_id']}")


def main():
    root = os.path.dirname(__file__)
    documents, questions = build()
    _dump(os.path.join(root, "corpus_v2.jsonl"), documents)
    _dump(os.path.join(root, "questions_v2.jsonl"), questions)
    answerable = sum(1 for item in questions if item["answerable"])
    dev = sum(1 for item in questions if item["split"] == "dev")
    print(
        f"docs={len(documents)} questions={len(questions)} answerable={answerable} "
        f"dev={dev} test={len(questions) - dev} version={SET_VERSION}"
    )


def _dump(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
