from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import engine, Base
from app.contestants import router as contestants_router
from app.events import router as events_router
from app.registrations import router as registrations_router
from app.judges import router as judges_router
from app.scoring import router as scoring_router
from app.results import router as results_router
from app.dashboard import router as dashboard_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="世界胡子锦标赛选手档案与赛事评分管理系统",
    description="""
## 系统简介

国际胡子与髭须造型比赛的选手报名、赛事管理与评审打分系统。

### 核心模块

- **选手档案** - 参赛者信息录入、照片上传、历史参赛记录与获奖情况
- **赛事管理** - 创建比赛届次、举办城市与日期、开放报名起止时间
- **选手报名** - 在线报名、管理员审核、分组名单与出场顺序生成
- **评委管理** - 评委信息维护
- **评审打分** - 多评委五维度打分、自动去极值加权计分、组别排名与晋级名单
- **赛事结果** - 各组别前三名、最佳新人奖、全场总冠军、积分自动更新
- **数据看板** - 各国参赛统计、组别历年冠军分布、积分排行、赛事城市地图

### 参赛组别

| 代码 | 组别名称 |
|------|---------|
| natural_goatee | 自然山羊胡 |
| natural_moustache | 自然八字胡 |
| caribbean_pirate | 加勒比海盗胡 |
| imperial | 帝国胡 |
| dali | 达利胡 |
| freestyle | 自由造型 |
| full_beard | 全胡 |

### 评分维度与权重

| 维度 | 权重 |
|------|------|
| 造型创意 creativity | 25% |
| 对称性 symmetry | 20% |
| 维护水平 maintenance | 20% |
| 舞台表现 stage_presence | 15% |
| 总体印象 overall_impression | 20% |

### 计分规则

1. 每位评委对每位选手按五维度打分（0-100）
2. 计算每位评委的加权总分
3. 若评委数≥3，去掉最高分与最低分后取平均
4. 若评委数<3，直接取所有评委加权总分平均
5. 按组别排名生成晋级名单

### 奖项积分

| 奖项 | 积分 |
|------|------|
| 金奖 gold | 10 |
| 银奖 silver | 7 |
| 铜奖 bronze | 5 |
| 最佳新人 best_newcomer | 8 |
| 全场总冠军 overall_champion | 15 |
    """,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(contestants_router)
app.include_router(events_router)
app.include_router(registrations_router)
app.include_router(judges_router)
app.include_router(scoring_router)
app.include_router(results_router)
app.include_router(dashboard_router)


@app.get("/", tags=["系统"])
def root():
    return {
        "system": "世界胡子锦标赛选手档案与赛事评分管理系统",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["系统"])
def health_check():
    return {"status": "healthy"}
