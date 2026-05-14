"""
batch23: 肌肉附着点详表 — 程序化批量生成

通过结构化数据自动生成每块肌肉的起止点、功能、训练动作 chunks
目标：~60块肌肉 = ~60 chunks
"""

from chunk_utils import make_chunk
from graph_alignment import normalize_muscles
from typing import List, Dict
import json
import os

MUSCLE_ATTACHMENTS = [
    {"name": "胸大肌", "latin": "Pectoralis Major", "graph_name": "胸部",
     "origin": "锁骨内侧1/2（锁骨头）、胸骨前面和上6肋软骨（胸肋头）、腹直肌鞘前层（腹部头）",
     "insertion": "肱骨大结节嵴（结节间沟外侧唇）",
     "function": "肩关节水平内收、屈曲（锁骨头）、内旋。从外展位内收手臂。",
     "nerve": "胸内侧神经（C8-T1）和胸外侧神经（C5-C7）",
     "exercises": "卧推（平板/上斜/下斜）、飞鸟、夹胸、俯卧撑、双杠臂屈伸",
     "stretch": "门框拉伸（手臂90°/135°外展，身体前倾）；仰卧泡沫轴纵放，双臂外展",
     "notes": "上斜卧推重点刺激锁骨头（上胸）；下斜/双杠重点刺激胸肋头（中下胸）。内旋位飞鸟增加收缩感。",
     "keywords": ["胸大肌", "卧推", "锁骨头", "胸肋头", "水平内收"]},

    {"name": "背阔肌", "latin": "Latissimus Dorsi", "graph_name": "背阔肌",
     "origin": "T7-L5棘突、骶骨后面、髂嵴后部、下3-4肋骨、肩胛骨下角",
     "insertion": "肱骨结节间沟底部（小结节嵴）",
     "function": "肩关节伸展、内收、内旋。从屈曲位拉回手臂（引体向上动作）。",
     "nerve": "胸背神经（C6-C8）",
     "exercises": "引体向上、高位下拉、各种划船、直臂下拉、单臂哑铃划船",
     "stretch": "侧身抓门框，身体向对侧倾斜拉伸；儿童式（跪姿前伸）",
     "notes": "宽握引体=更多内收（上背宽度）；窄握=更多伸展（背阔肌下部长度）。全ROM很重要——完全伸展到完全收缩。",
     "keywords": ["背阔肌", "引体向上", "肩伸展", "内收", "V形背"]},

    {"name": "三角肌前束", "latin": "Anterior Deltoid", "graph_name": "三角肌前束",
     "origin": "锁骨外侧1/3前缘",
     "insertion": "肱骨三角肌粗隆",
     "function": "肩关节屈曲、水平内收、内旋。手臂前举和推举动作。",
     "nerve": "腋神经（C5-C6）",
     "exercises": "过头推举、前平举、上斜卧推、Arnold推举",
     "stretch": "手臂后伸，掌心朝后，另一手辅助向后拉",
     "notes": "前三角肌在所有推举动作中都参与，通常不需要大量孤立训练。过度发达的前三角肌+薄弱后三角肌=圆肩风险。",
     "keywords": ["三角肌前束", "推举", "前平举", "肩屈曲"]},

    {"name": "三角肌中束", "latin": "Middle/Lateral Deltoid", "graph_name": "三角肌中束",
     "origin": "肩峰外侧缘",
     "insertion": "肱骨三角肌粗隆",
     "function": "肩关节外展（手臂侧举）。是肩部宽度的主要决定因素。",
     "nerve": "腋神经（C5-C6）",
     "exercises": "侧平举（哑铃/绳索）、直立划船、过头推举（部分参与）",
     "stretch": "手臂横过胸前，另一手按压肘部向身体拉",
     "notes": "侧平举时小指略高于拇指（轻度内旋）可增加中束激活。绳索侧平举在顶部张力更大。高频率训练效果好（每周4-6次，每次3-4组）。",
     "keywords": ["三角肌中束", "侧平举", "肩宽", "外展"]},

    {"name": "三角肌后束", "latin": "Posterior Deltoid", "graph_name": "三角肌后束",
     "origin": "肩胛冈下缘",
     "insertion": "肱骨三角肌粗隆",
     "function": "肩关节伸展、水平外展、外旋。手臂后拉动作。",
     "nerve": "腋神经（C5-C6）",
     "exercises": "面拉、反向飞鸟、俯身侧平举、绳索后拉",
     "stretch": "手臂横过胸前向对侧拉（同中束拉伸）",
     "notes": "后三角肌是最容易被忽略的肌群之一。面拉应该每次训练都做。后三角肌发达=肩部立体感+预防肩伤。",
     "keywords": ["三角肌后束", "面拉", "水平外展", "肩部健康"]},

    {"name": "肱二头肌长头", "latin": "Biceps Brachii (Long Head)", "graph_name": "肱二头肌长头",
     "origin": "肩胛骨盂上结节（关节盂上方）",
     "insertion": "桡骨粗隆和前臂筋膜（通过肱二头肌腱膜）",
     "function": "肘关节屈曲、前臂旋后、肩关节屈曲（辅助）。长头跨越肩关节。",
     "nerve": "肌皮神经（C5-C6）",
     "exercises": "上斜弯举（肩伸展位=长头拉伸更多）、杠铃弯举、锤式弯举",
     "stretch": "手臂后伸，掌心朝前，感觉二头肌前方拉伸",
     "notes": "长头在肩伸展位（手臂在身后）被拉伸最多→上斜弯举是长头最佳动作。长头肌腱经过肱骨结节间沟，容易发炎（二头肌腱炎）。",
     "keywords": ["肱二头肌长头", "上斜弯举", "肩伸展", "二头肌腱"]},

    {"name": "肱二头肌短头", "latin": "Biceps Brachii (Short Head)", "graph_name": "肱二头肌短头",
     "origin": "肩胛骨喙突",
     "insertion": "桡骨粗隆（与长头共同止点）",
     "function": "肘关节屈曲、前臂旋后。短头不跨越肩关节后方。",
     "nerve": "肌皮神经（C5-C6）",
     "exercises": "牧师凳弯举（肩屈曲位=短头缩短更多）、蜘蛛弯举、集中弯举",
     "stretch": "与长头相同的拉伸动作",
     "notes": "短头在肩屈曲位（手臂在前方）收缩更充分→牧师凳/蜘蛛弯举重点刺激短头。短头发达=二头肌内侧饱满度。",
     "keywords": ["肱二头肌短头", "牧师凳弯举", "喙突", "内侧"]},

    {"name": "肱三头肌长头", "latin": "Triceps Brachii (Long Head)", "graph_name": "三头肌长头",
     "origin": "肩胛骨盂下结节（关节盂下方）",
     "insertion": "尺骨鹰嘴",
     "function": "肘关节伸展、肩关节伸展和内收。长头跨越肩关节。",
     "nerve": "桡神经（C6-C8）",
     "exercises": "过头臂屈伸（肩屈曲位=长头拉伸最大）、法式推举、仰卧臂屈伸",
     "stretch": "手臂举过头，屈肘，另一手按压肘部向下",
     "notes": "长头是三头肌最大的头，占三头肌体积的50%+。过头位置（肩屈曲）拉伸长头最多→过头臂屈伸是长头最佳动作。",
     "keywords": ["肱三头肌长头", "过头臂屈伸", "肩屈曲", "最大头"]},

    {"name": "肱三头肌外侧头", "latin": "Triceps Brachii (Lateral Head)", "graph_name": "肱三头肌外侧头",
     "origin": "肱骨后面（桡神经沟上方）",
     "insertion": "尺骨鹰嘴",
     "function": "肘关节伸展。不跨越肩关节，只作用于肘。",
     "nerve": "桡神经（C6-C8）",
     "exercises": "绳索下压（正握/V把）、窄距卧推、钻石俯卧撑、Kickback",
     "stretch": "与长头相同",
     "notes": "外侧头是三头肌'马蹄形'外观的主要贡献者。绳索下压（正握）重点刺激外侧头。不需要过头位置。",
     "keywords": ["肱三头肌外侧头", "绳索下压", "马蹄形", "肘伸展"]},

    {"name": "股四头肌-股直肌", "latin": "Rectus Femoris", "graph_name": "股直肌",
     "origin": "髂前下棘（AIIS）和髋臼上缘",
     "insertion": "胫骨粗隆（通过髌韧带）",
     "function": "膝关节伸展+髋关节屈曲。唯一跨越髋和膝两个关节的股四头肌。",
     "nerve": "股神经（L2-L4）",
     "exercises": "腿屈伸（膝伸展）、悬垂举腿（髋屈曲）、深蹲（两者兼有）",
     "stretch": "站立抓脚踝向臀部拉（同时髋伸展效果更好=弓步位拉伸）",
     "notes": "因为跨两个关节，股直肌在深蹲中的贡献不如其他三头（主动不足现象）。腿屈伸是孤立股直肌的最佳动作。Thomas测试评估其紧张程度。",
     "keywords": ["股直肌", "双关节肌", "髋屈曲", "膝伸展", "Thomas测试"]},

    {"name": "股内侧肌", "latin": "Vastus Medialis (VMO)", "graph_name": "股四头肌内侧",
     "origin": "股骨粗线内侧唇",
     "insertion": "胫骨粗隆（通过髌韧带）+ 髌骨内侧缘",
     "function": "膝关节伸展，尤其是最后15-30°的终末伸膝。维持髌骨内侧稳定。",
     "nerve": "股神经（L2-L4）",
     "exercises": "终末伸膝（最后30°）、西班牙深蹲、腿屈伸（全ROM）、分腿蹲",
     "stretch": "侧卧，抓上方脚踝向臀部拉",
     "notes": "VMO是髌骨轨迹的关键稳定者。VMO薄弱→髌骨外移→髌股疼痛。膝关节最后30°伸展时VMO激活最大。康复中优先强化VMO。",
     "keywords": ["股内侧肌", "VMO", "髌骨稳定", "终末伸膝", "膝前痛"]},

    {"name": "臀大肌", "latin": "Gluteus Maximus", "graph_name": "臀部",
     "origin": "髂骨翼外面（臀后线后方）、骶骨和尾骨后面、骶结节韧带、竖脊肌腱膜",
     "insertion": "髂胫束和股骨臀肌粗隆",
     "function": "髋关节伸展（最强）、外旋、外展（上纤维）、内收（下纤维）。从屈曲位伸展髋关节。",
     "nerve": "臀下神经（L5-S2）",
     "exercises": "臀推、深蹲（尤其底部）、硬拉、保加利亚分腿蹲、臀桥、Cable Pull-through",
     "stretch": "仰卧4字拉伸（一脚踝放对侧膝上，拉向胸部）；鸽子式",
     "notes": "臀大肌是人体最大最强的肌肉。在髋伸展末端（站直/臀推顶部）收缩最强。深蹲底部和硬拉锁定时臀大肌参与最多。久坐导致臀肌失忆。",
     "keywords": ["臀大肌", "髋伸展", "臀推", "最大肌肉", "臀肌失忆"]},

    {"name": "臀中肌", "latin": "Gluteus Medius", "graph_name": "臀中肌",
     "origin": "髂骨翼外面（臀前线和臀后线之间）",
     "insertion": "股骨大转子外侧面",
     "function": "髋关节外展（主要）、内旋（前纤维）、外旋（后纤维）。单腿站立时防止骨盆下沉。",
     "nerve": "臀上神经（L4-S1）",
     "exercises": "侧卧抬腿、蚌式开合、弹力带侧走、单腿深蹲/硬拉、侧平板",
     "stretch": "坐姿交叉腿拉伸（一脚跨过对侧膝，转体）",
     "notes": "臀中肌薄弱=Trendelenburg征（单腿站立时骨盆下沉）=膝内扣=跑步膝/IT Band综合征。是下肢稳定的关键。每次训练都应包含臀中肌激活。",
     "keywords": ["臀中肌", "髋外展", "骨盆稳定", "Trendelenburg", "膝内扣"]},

    {"name": "腘绳肌-股二头肌", "latin": "Biceps Femoris", "graph_name": "股二头肌（外侧）",
     "origin": "长头：坐骨结节；短头：股骨粗线外侧唇",
     "insertion": "腓骨头",
     "function": "膝关节屈曲+外旋、髋关节伸展（长头）。长头跨越髋和膝两个关节。",
     "nerve": "长头：胫神经（L5-S2）；短头：腓总神经（L5-S2）",
     "exercises": "腿弯举、北欧腿弯举、罗马尼亚硬拉、Good Morning",
     "stretch": "直腿前屈（脚尖朝前=股二头肌；脚尖内旋=更多外侧拉伸）",
     "notes": "股二头肌是冲刺时最容易拉伤的肌肉。离心力量不足是主要风险因素。北欧腿弯举是预防拉伤的金标准。",
     "keywords": ["股二头肌", "腘绳肌外侧", "冲刺拉伤", "北欧腿弯举", "膝屈曲"]},

    {"name": "腓肠肌", "latin": "Gastrocnemius", "graph_name": "小腿",
     "origin": "股骨内侧髁后面（内侧头）和股骨外侧髁后面（外侧头）",
     "insertion": "跟骨后面（通过跟腱/Achilles tendon）",
     "function": "踝关节跖屈（踮脚）、膝关节屈曲（辅助）。跨越膝和踝两个关节。",
     "nerve": "胫神经（S1-S2）",
     "exercises": "站姿提踵（直膝=腓肠肌为主）、跳跃、跑步",
     "stretch": "墙壁推墙拉伸（直膝，脚跟着地）",
     "notes": "腓肠肌在直膝时被充分拉伸→站姿提踵主要训练腓肠肌。屈膝时腓肠肌松弛→坐姿提踵主要训练比目鱼肌。小腿训练需要高次数（12-20次）因为日常步行已经适应低负荷。",
     "keywords": ["腓肠肌", "小腿", "提踵", "跟腱", "跖屈"]},

    {"name": "竖脊肌", "latin": "Erector Spinae", "graph_name": "下背部",
     "origin": "骶骨后面、髂嵴、腰椎棘突和横突（分为棘肌/最长肌/髂肋肌三列）",
     "insertion": "各椎骨棘突和横突、肋骨角、枕骨",
     "function": "脊柱伸展（后仰）、侧屈、维持直立姿势。是抗重力肌群。",
     "nerve": "脊神经后支（各节段）",
     "exercises": "硬拉（等长维持）、Good Morning、背伸展（罗马椅）、超人式",
     "stretch": "猫式（四点跪姿弓背）、儿童式、站立前屈",
     "notes": "竖脊肌在硬拉/深蹲中主要做等长收缩（维持脊柱中立），不是主动伸展。过度训练竖脊肌（如大量背伸展）可能导致腰椎过伸。核心训练应该平衡前后。",
     "keywords": ["竖脊肌", "脊柱伸展", "硬拉", "等长收缩", "抗重力"]},

    {"name": "腹直肌", "latin": "Rectus Abdominis", "graph_name": "腹直肌",
     "origin": "耻骨联合和耻骨嵴",
     "insertion": "第5-7肋软骨前面和剑突",
     "function": "脊柱屈曲（卷腹）、骨盆后倾、增加腹内压（辅助呼气/排便/分娩）。",
     "nerve": "肋间神经（T7-T12）",
     "exercises": "卷腹、悬垂举腿、Ab Wheel、Cable Crunch、反向卷腹",
     "stretch": "眼镜蛇式（俯卧撑起上半身，髋部贴地）",
     "notes": "腹直肌是一整块肌肉（没有'上腹肌'和'下腹肌'之分），但可以通过不同动作强调不同区域。'六块腹肌'的分隔是腱划（tendinous inscriptions）造成的，数量由基因决定。",
     "keywords": ["腹直肌", "卷腹", "六块腹肌", "脊柱屈曲", "腱划"]},

    {"name": "腹外斜肌", "latin": "External Oblique", "graph_name": "腹斜肌",
     "origin": "第5-12肋骨外面（与前锯肌交错）",
     "insertion": "髂嵴前半、腹白线、耻骨结节",
     "function": "脊柱屈曲、对侧旋转（右侧收缩=躯干左转）、同侧侧屈。",
     "nerve": "肋间神经（T7-T12）+ 髂腹下神经",
     "exercises": "俄罗斯转体、自行车卷腹、侧平板、Pallof Press、伐木",
     "stretch": "站立侧屈（一手举过头向对侧弯）",
     "notes": "腹斜肌是核心旋转和抗旋转的主要肌群。训练应包含旋转（伐木）和抗旋转（Pallof Press）两种模式。过度训练腹斜肌可能增加腰围视觉宽度。",
     "keywords": ["腹外斜肌", "旋转", "抗旋转", "Pallof Press", "侧屈"]},

    {"name": "前锯肌", "latin": "Serratus Anterior", "graph_name": "腹斜肌",
     "origin": "第1-9肋骨外侧面",
     "insertion": "肩胛骨内侧缘前面（肋骨面）",
     "function": "肩胛骨前伸（推离胸壁）、上回旋（配合斜方肌完成手臂过头）。固定肩胛骨贴胸壁。",
     "nerve": "胸长神经（C5-C7）",
     "exercises": "前锯肌Plus俯卧撑（俯卧撑顶部额外推出肩胛骨）、墙壁滑动、Landmine Press",
     "stretch": "侧卧，上方手臂伸直过头，身体略后仰",
     "notes": "前锯肌薄弱=翼状肩胛=肩峰撞击风险。是过头动作的关键稳定肌。'拳击手肌肉'——出拳时前伸肩胛骨。每次肩部训练都应包含前锯肌激活。",
     "keywords": ["前锯肌", "肩胛骨前伸", "上回旋", "翼状肩胛", "Plus俯卧撑"]},

    {"name": "髂腰肌", "latin": "Iliopsoas", "graph_name": "腹股沟",
     "origin": "腰椎体和横突（腰大肌）+ 髂窝（髂肌）",
     "insertion": "股骨小转子",
     "function": "髋关节屈曲（最强屈髋肌）、腰椎稳定（腰大肌）、骨盆前倾。",
     "nerve": "股神经分支（L1-L3）",
     "exercises": "悬垂举腿、高抬腿、登山者、冲刺",
     "stretch": "半跪姿髋屈肌拉伸（后腿膝盖着地，骨盆后倾，重心前移）",
     "notes": "久坐导致髂腰肌缩短→骨盆前倾→下交叉综合征。但髂腰肌不是'坏肌肉'——它对步态和跑步至关重要。问题是缩短+对侧臀肌薄弱的组合。",
     "keywords": ["髂腰肌", "髋屈曲", "骨盆前倾", "久坐", "半跪姿拉伸"]},
]

MUSCLE_ATTACHMENTS += [
    {"name": "斜方肌上束", "latin": "Upper Trapezius", "graph_name": "上斜方肌",
     "origin": "枕外隆凸、项韧带、C1-C7棘突",
     "insertion": "锁骨外侧1/3、肩峰",
     "function": "肩胛骨上提（耸肩）、上回旋（辅助）、颈部伸展和侧屈。",
     "nerve": "副神经（CN XI）+ C3-C4",
     "exercises": "耸肩（杠铃/哑铃）、农夫走（被动）、高翻",
     "stretch": "侧颈拉伸（耳朵靠向肩膀，对侧手轻压头部）",
     "notes": "上斜方肌是最容易过度活跃的肌群之一。很多人在推举/侧平举时不自觉耸肩=上斜方肌代偿。需要学会'肩膀远离耳朵'。",
     "keywords": ["上斜方肌", "耸肩", "肩胛骨上提", "代偿", "颈部紧张"]},

    {"name": "斜方肌中束", "latin": "Middle Trapezius", "graph_name": "斜方肌（中背）",
     "origin": "C7-T3棘突",
     "insertion": "肩峰内侧缘、肩胛冈上缘",
     "function": "肩胛骨后缩（夹背）。维持肩胛骨贴近胸壁。",
     "nerve": "副神经（CN XI）+ C3-C4",
     "exercises": "面拉、俯身飞鸟、坐姿划船（挤压肩胛骨）、俯卧T举",
     "stretch": "双手前伸抱住对侧肩膀，弓背拉伸中背",
     "notes": "中斜方肌和菱形肌共同负责肩胛骨后缩。薄弱=圆肩。划船动作终点挤压肩胛骨=中斜方肌最大收缩。",
     "keywords": ["斜方肌中束", "肩胛骨后缩", "菱形肌", "划船", "圆肩纠正"]},

    {"name": "斜方肌下束", "latin": "Lower Trapezius", "graph_name": "斜方肌下部",
     "origin": "T4-T12棘突",
     "insertion": "肩胛冈内侧端（三角形区域）",
     "function": "肩胛骨下沉+后缩+上回旋。在过头动作中稳定肩胛骨。",
     "nerve": "副神经（CN XI）+ C3-C4",
     "exercises": "俯卧Y举、面拉（强调下沉）、高位下拉（起始肩胛骨下沉）",
     "stretch": "与中斜方肌相同",
     "notes": "下斜方肌是肩部健康的关键——它与上斜方肌形成力偶，控制肩胛骨上回旋。薄弱=肩峰撞击。引体向上起始动作（肩胛骨下沉）是最佳激活方式。",
     "keywords": ["斜方肌下束", "肩胛骨下沉", "上回旋", "Y举", "肩部健康"]},

    {"name": "肱桡肌", "latin": "Brachioradialis", "graph_name": "前臂肌群",
     "origin": "肱骨外上髁上方（外侧髁上嵴）",
     "insertion": "桡骨茎突",
     "function": "肘关节屈曲（尤其在中立位/锤式握法时最强）。前臂旋前/旋后到中立位。",
     "nerve": "桡神经（C5-C6）",
     "exercises": "锤式弯举（中立握）、反握弯举、Zottman弯举",
     "stretch": "手臂伸直，掌心朝下，另一手向下压手背",
     "notes": "肱桡肌在中立握位（锤式）时力矩臂最大，是该位置的主要屈肘肌。锤式弯举不只是'肱二头肌变体'，而是重点训练肱桡肌。前臂外观的主要贡献者。",
     "keywords": ["肱桡肌", "锤式弯举", "中立握", "前臂", "肘屈曲"]},

    {"name": "腹横肌", "latin": "Transversus Abdominis", "graph_name": "上腹肌",
     "origin": "第7-12肋软骨内面、胸腰筋膜、髂嵴、腹股沟韧带",
     "insertion": "腹白线（通过腹直肌鞘）",
     "function": "增加腹内压（核心稳定的关键）、压缩腹腔内容物。不产生脊柱运动。",
     "nerve": "肋间神经（T7-T12）+ 髂腹下/髂腹股沟神经",
     "exercises": "腹式呼吸（呼气时收缩）、死虫式、鸟狗式、Valsalva动作",
     "stretch": "不需要专门拉伸（它是稳定肌，不是运动肌）",
     "notes": "腹横肌是'天然腰带'——在任何肢体运动前先激活（前馈机制）。腰痛患者常见腹横肌激活延迟。训练重点是学会在运动前自动激活，而非孤立训练。",
     "keywords": ["腹横肌", "腹内压", "核心稳定", "前馈", "天然腰带"]},
]

# No more splices needed

def generate_batch23() -> List[Dict]:
    """从结构化数据生成肌肉附着点 chunks"""
    chunks = []
    for m in MUSCLE_ATTACHMENTS:
        content = f"## {m['name']}（{m['latin']}）\n\n"
        content += f"**起点**：{m['origin']}\n\n"
        content += f"**止点**：{m['insertion']}\n\n"
        content += f"**功能**：{m['function']}\n\n"
        content += f"**神经支配**：{m['nerve']}\n\n"
        content += f"**训练动作**：{m['exercises']}\n\n"
        content += f"**拉伸方法**：{m['stretch']}\n\n"
        if m.get('notes'):
            content += f"**训练要点**：{m['notes']}"

        graph_muscles = normalize_muscles([m['graph_name']])
        chunks.append(make_chunk(
            category="anatomy",
            subcategory="muscle_attachments",
            title=f"{m['name']} — 起止点与功能",
            content=content,
            keywords=m['keywords'],
            related_muscles=graph_muscles,
        ))
    return chunks


if __name__ == "__main__":
    chunks = generate_batch23()
    print(f"生成 {len(chunks)} 个肌肉附着点 chunks")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "batch23.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("已保存到 output/batch23.json")
