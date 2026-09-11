#!/usr/bin/env python3
"""
test_weights.py - 蜂巢大脑权重逻辑单元测试（M1 验收②）
覆盖：命中上调 / 复用上调 / 时间衰减 / 阈值流转 / backfill 幂等 / 读时惰性衰减

运行: python -m pytest tests/test_weights.py -v
"""

import sys
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# 把 .dsh-memory/scripts 加入 path（依赖 tier_manager / backfill_weights）
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SCRIPTS_DIR = REPO_ROOT / '.dsh-memory' / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

import tier_manager as tm
import backfill_weights as bf

# ---------- 工具：构造临时经验文件 ----------

@pytest.fixture()
def tmp_exp(tmp_path):
    """构造一个带 frontmatter 的经验文件在临时目录"""
    def _make(name='exp-test.md', meta=None, body='# 测试经验\n\n内容'):
        m = {
            'id': 'exp-test-001',
            'tier': 'sparse',
            'hit_count': 0,
            'reuse_success': False,
            'created_at': '2026-09-01T00:00:00Z',
            ** (meta or {}),
        }
        content = tm.write_frontmatter(m, body)
        f = tmp_path / name
        f.write_text(content, encoding='utf-8')
        return f
    return _make


# ---------- 命中/复用上调 ----------

def test_hit_bumps_weight(tmp_exp):
    f = tmp_exp()
    content = f.read_text(encoding='utf-8')
    meta, body = tm.parse_frontmatter(content)
    assert meta.get('weight', tm.WEIGHT_INIT) == tm.WEIGHT_INIT  # 0.5

    tm.bump_weight(meta, tm.WEIGHT_HIT_DELTA)
    assert meta['weight'] == pytest.approx(tm.WEIGHT_INIT + tm.WEIGHT_HIT_DELTA)
    assert 'weight_updated_at' in meta


def test_reuse_bumps_more(tmp_exp):
    f = tmp_exp()
    content = f.read_text(encoding='utf-8')
    meta, body = tm.parse_frontmatter(content)

    tm.bump_weight(meta, tm.WEIGHT_HIT_DELTA)
    tm.bump_weight(meta, tm.WEIGHT_REUSE_DELTA)
    expected = tm.WEIGHT_INIT + tm.WEIGHT_HIT_DELTA + tm.WEIGHT_REUSE_DELTA
    assert meta['weight'] == pytest.approx(expected)


def test_weight_capped_at_max(tmp_exp):
    f = tmp_exp(meta={'weight': 0.95, 'weight_updated_at': '2026-09-01T00:00:00Z'})
    content = f.read_text(encoding='utf-8')
    meta, body = tm.parse_frontmatter(content)
    tm.bump_weight(meta, tm.WEIGHT_REUSE_DELTA)
    assert meta['weight'] <= tm.WEIGHT_MAX


# ---------- 时间衰减 ----------

def test_decay_over_time():
    """权重随时间按 exp(-rate*dt) 衰减"""
    meta = {
        'weight': 1.0,
        'weight_updated_at': '2026-09-01T00:00:00Z',
        'decay_rate': 0.01,
        'knowledge_type': 'experience',
    }
    now = datetime(2026, 9, 11, tzinfo=timezone.utc)  # 10 天后
    w = tm.apply_decay(meta, now)
    expected = 1.0 * (2.718281828459045 ** (-0.01 * 10))
    assert w == pytest.approx(expected, abs=1e-6)


def test_decay_zero_for_fresh():
    """weight_updated_at 与 now 相同时不衰减"""
    now = datetime.now(timezone.utc)
    meta = {
        'weight': 0.5,
        'weight_updated_at': now.isoformat(),
        'decay_rate': 0.01,
    }
    w = tm.apply_decay(meta, now)
    assert w == pytest.approx(0.5)


def test_decay_rate_by_type():
    """不同类型默认衰减率不同（产品最慢，场景最快）"""
    assert tm.DECAY_RATE_BY_TYPE['product'] < tm.DECAY_RATE_BY_TYPE['experience'] < tm.DECAY_RATE_BY_TYPE['scene']


# ---------- 流转阈值 ----------

def test_promote_threshold_logic():
    """晋升条件：weight >= 0.7 且 hit_count>=3 且 reuse_success"""
    meta = {'weight': 0.72, 'hit_count': 3, 'reuse_success': True, 'tier': 'sparse'}
    assert meta['weight'] >= tm.WEIGHT_PROMOTE
    assert meta['hit_count'] >= tm.DEFAULT_PROMOTE_THRESHOLD
    assert meta['reuse_success']


def test_demote_threshold_logic():
    """降级条件：weight < 0.4"""
    assert 0.35 < tm.WEIGHT_DEMOTE


def test_expire_threshold_logic():
    """过期条件：weight < 0.15"""
    assert 0.1 < tm.WEIGHT_EXPIRE


# ---------- backfill 幂等 ----------

def test_backfill_idempotent(tmp_path, monkeypatch):
    """backfill：首次填充 weight，重复运行跳过（幂等）"""
    # 构造临时 experiences 目录结构
    exp_dir = tmp_path / 'knowledge' / 'experiences'
    for tier in ['refined', 'sparse', 'expired']:
        d = exp_dir / tier
        d.mkdir(parents=True)
        meta = {'id': f'x-{tier}', 'tier': tier, 'created_at': '2026-08-01T00:00:00Z'}
        (d / f'exp-{tier}.md').write_text(tm.write_frontmatter(meta, '# x\n'), encoding='utf-8')

    # 指向临时目录
    monkeypatch.setattr(bf, 'EXPERIENCES_DIR', exp_dir)

    # 第一次运行
    p1, s1 = 0, 0
    for tier in ['refined', 'sparse', 'expired']:
        p, s = bf.backfill(tier)
        p1 += p
        s1 += s
    assert p1 == 3  # 全部填充
    assert s1 == 0

    # refined 初始权重 = 0.7（已验证），sparse = 0.5，expired = 0.1
    refined_f = exp_dir / 'refined' / 'exp-refined.md'
    meta, _ = tm.parse_frontmatter(refined_f.read_text(encoding='utf-8'))
    assert meta['weight'] == bf.TIER_INIT_WEIGHT['refined'] == tm.WEIGHT_PROMOTE
    assert 'weight_updated_at' in meta

    # 第二次运行：全部跳过
    p2, s2 = 0, 0
    for tier in ['refined', 'sparse', 'expired']:
        p, s = bf.backfill(tier)
        p2 += p
        s2 += s
    assert p2 == 0
    assert s2 == 3


def test_backfill_benchmark_is_now_not_created():
    """N1：backfill 基准 = now，不取 created_at（老 refined 不因 backfill 立即降级）"""
    meta = {
        'weight': tm.WEIGHT_PROMOTE,          # 0.7
        'weight_updated_at': '2026-09-11T00:00:00Z',  # backfill 执行时刻（now）
        'decay_rate': 0.01,
    }
    now = datetime(2026, 9, 11, tzinfo=timezone.utc)
    w = tm.apply_decay(meta, now)
    # 若基准=now，则无衰减，仍 0.7，高于降级阈值 0.4
    assert w == pytest.approx(0.7)
    assert w > tm.WEIGHT_DEMOTE


# ---------- 读时惰性衰减（search N4） ----------

def test_lazy_decay_no_writeback(tmp_path):
    """读时惰性衰减：不写回文件（不修改传入 meta）"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    import importlib
    import search as sr

    meta = {
        'weight': 1.0,
        'weight_updated_at': '2026-08-01T00:00:00Z',
        'decay_rate': 0.01,
    }
    meta_before = dict(meta)  # 快照
    now = datetime(2026, 9, 11, tzinfo=timezone.utc)
    w = sr._effective_weight(meta, now)
    expected = 1.0 * (2.718281828459045 ** (-0.01 * 41))
    assert w == pytest.approx(expected, abs=1e-6)
    # meta 不应被修改（读时惰性衰减只计算，不写回 frontmatter）
    assert meta == meta_before


def test_score_uses_boost():
    import search as sr
    meta = {'weight': 0.5, 'weight_updated_at': '2026-09-11T00:00:00Z', 'decay_rate': 0.0}
    s_refined = sr._score(meta, 'refined')
    s_sparse = sr._score(meta, 'sparse')
    s_expired = sr._score(meta, 'expired')
    assert s_refined > s_sparse > s_expired
    assert s_sparse == pytest.approx(0.5)  # sparse boost=1.0
