"""Research helper for candidate shadow tracking and 2+2 rotation.

This is a research-only script. It parses exported JoinQuant structured logs,
builds a WATCH_POOL from unbought daily candidates, and, when running inside
JoinQuant research, fetches daily prices to test trend-confirmation rules and a
simplified 2+2 satellite rotation model.

It never calls trading order APIs and should not be copied as strategy code.
"""

import argparse
import csv
import math
import re
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

try:
    from jqdata import get_price, get_trade_days  # type: ignore

    JQDATA_AVAILABLE = True
except Exception:
    # Some JoinQuant research notebooks expose get_price/get_trade_days only in
    # the interactive namespace. Run this script with "%run -i" after
    # "from jqdata import *" so those functions are visible here.
    _existing_get_price = globals().get('get_price')
    _existing_get_trade_days = globals().get('get_trade_days')
    if callable(_existing_get_price) and callable(_existing_get_trade_days):
        get_price = _existing_get_price
        get_trade_days = _existing_get_trade_days
        JQDATA_AVAILABLE = True
    else:
        get_price = None
        get_trade_days = None
        JQDATA_AVAILABLE = False


EVENT_NAMES = (
    'AUCTION_PREFILTER_TOP',
    'BIGMEAT_POOL_TOP',
    'ADD_CANDIDATE_SNAPSHOT',
    'BIGMEAT_BUY',
    'TRADE_CLOSE',
    'TRADE_ANALYTICS',
    'HOLD_SNAPSHOT',
    'DAILY_SUMMARY',
)

CONFIRMED_SIGNAL_COLUMNS = [
    'rule', 'signal_date', 'confirm_date', 'days_after_signal',
    'stock', 'name', 'signal_source', 'signal_entry_type',
    'signal_rank', 'signal_score', 'signal_price', 'confirm_price',
    'ret_from_signal', 'day_ret',
    'volume_ratio_vs_prev', 'money_ratio_vs_prev', 'ma5',
    'ma5_distance', 'close_to_day_high', 'is_limit_up_if_available',
    'paused',
]

TRADE_SIM_EXTRA_COLUMNS = [
    'exit_date_3d', 'exit_price_3d', 'return_3d',
    'exit_date_5d', 'exit_price_5d', 'return_5d',
    'trade_close_available', 'trade_close_date',
    'trade_close_ret_actual', 'return_to_trade_close_if_available',
    'exit_reason_if_available',
]

RULES = {
    'rule_A_ret5_day5_vol_gt1': {
        'ret_from_signal_min': 5.0,
        'day_ret_min': 5.0,
        'volume_ratio_min': 1.0,
        'volume_ratio_max': None,
        'ma5_distance_max': None,
        'close_to_day_high_min': None,
    },
    'rule_B_ret5_day5_vol_1_2': {
        'ret_from_signal_min': 5.0,
        'day_ret_min': 5.0,
        'volume_ratio_min': 1.0,
        'volume_ratio_max': 2.0,
        'ma5_distance_max': None,
        'close_to_day_high_min': None,
    },
    'rule_C_ruleB_ma5_12': {
        'ret_from_signal_min': 5.0,
        'day_ret_min': 5.0,
        'volume_ratio_min': 1.0,
        'volume_ratio_max': 2.0,
        'ma5_distance_max': 12.0,
        'close_to_day_high_min': None,
    },
    'rule_D_ruleB_ma5_10_close_high_097': {
        'ret_from_signal_min': 5.0,
        'day_ret_min': 5.0,
        'volume_ratio_min': 1.0,
        'volume_ratio_max': 2.0,
        'ma5_distance_max': 10.0,
        'close_to_day_high_min': 0.97,
    },
}

OUTPUT_FILES = {
    'candidates': 'shadow_rotation_candidate_pool.csv',
    'watch': 'shadow_rotation_watch_signals.csv',
    'confirmed': 'shadow_rotation_confirmed_signals.csv',
    'rules': 'shadow_rotation_rule_summary.csv',
    'refined_rules': 'shadow_rotation_rule_refined_summary.csv',
    'trades': 'shadow_rotation_trade_sim_detail.csv',
    'portfolio': 'shadow_rotation_portfolio_sim_summary.csv',
    'full_compound': 'shadow_rotation_portfolio_full_compound_summary.csv',
    'report': 'v1.4.0_影子轮动精细化_满仓复利研究报告.md',
    'excel': 'shadow_rotation_research_outputs.xlsx',
}

REFINED_RULES = (
    'rule_D_all',
    'rule_D_deep_water',
    'rule_D_trend_core',
    'rule_D_deep_water_day1',
    'rule_D_deep_water_day2_3',
    'rule_B_deep_water',
    'rule_B_trend_core',
)

FULL_COMPOUND_RULES = (
    'rule_A_ret5_day5_vol_gt1',
    'rule_B_ret5_day5_vol_1_2',
    'rule_C_ruleB_ma5_12',
    'rule_D_ruleB_ma5_10_close_high_097',
    'rule_D_deep_water',
    'rule_D_deep_water_day2_3',
    'rule_B_deep_water',
)

PORTFOLIO_MODES = (
    {
        'portfolio_mode': 'conservative_75',
        'core_exposure': 0.60,
        'satellite_slots': 2,
        'satellite_ratio': 0.10,
        'max_total_position_ratio': 0.75,
        'is_full_compound_mode': 0,
    },
    {
        'portfolio_mode': 'full_A_80_10',
        'core_exposure': 0.80,
        'satellite_slots': 2,
        'satellite_ratio': 0.10,
        'max_total_position_ratio': 1.00,
        'is_full_compound_mode': 1,
    },
    {
        'portfolio_mode': 'full_B_70_15',
        'core_exposure': 0.70,
        'satellite_slots': 2,
        'satellite_ratio': 0.15,
        'max_total_position_ratio': 1.00,
        'is_full_compound_mode': 1,
    },
    {
        'portfolio_mode': 'full_C_60_20',
        'core_exposure': 0.60,
        'satellite_slots': 2,
        'satellite_ratio': 0.20,
        'max_total_position_ratio': 1.00,
        'is_full_compound_mode': 1,
    },
)

FULL_COMPOUND_COLUMNS = [
    'portfolio_mode', 'rule', 'exit_horizon', 'core_exposure',
    'satellite_slots', 'requested_satellite_position_ratio',
    'effective_satellite_position_ratio', 'max_total_position_ratio',
    'gross_exposure', 'effective_total_exposure',
    'is_full_compound_mode', 'final_nav_proxy', 'total_return_proxy',
    'max_drawdown_proxy', 'trade_count', 'turnover',
    'avg_holding_days', 'satellite_profit', 'replacement_count',
    'replaced_profit_after_sell', 'new_position_profit_after_buy',
]


def _coerce_value(value):
    text = str(value).strip()
    if text in ('', 'NA', 'None', 'null', 'nan', 'NaN'):
        return None
    numeric_text = text[:-1] if text.endswith('%') else text
    numeric_text = numeric_text.replace(',', '')
    try:
        return float(numeric_text)
    except ValueError:
        return text


def _parse_timestamp(line):
    try:
        return datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


def parse_key_value_log(line):
    pattern = r'(' + '|'.join(EVENT_NAMES) + r')\|'
    match = re.search(pattern, line)
    if not match:
        return None
    dt = _parse_timestamp(line)
    event = match.group(1)
    payload = line[match.end():].strip()
    record = {
        'event': event,
        'log_dt': dt,
        'log_date': dt.date().isoformat() if dt else None,
        '_raw': line.rstrip('\n'),
    }
    for token in payload.split('|'):
        if '=' not in token:
            continue
        key, value = token.split('=', 1)
        record[key.strip()] = _coerce_value(value)
    if 'date' not in record or record.get('date') is None:
        record['date'] = record.get('log_date')
    return record


def read_text_file(path):
    path = Path(path)
    if path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path, 'r') as handle:
            members = [name for name in handle.namelist() if not name.endswith('/')]
            if len(members) != 1:
                raise RuntimeError('zip log must contain exactly one file')
            data = handle.read(members[0])
        for encoding in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk'):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode('gb18030', errors='replace')

    for encoding in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk'):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding='gb18030', errors='replace')


def load_records(log_path):
    text = read_text_file(log_path)
    records = []
    for line_number, line in enumerate(text.splitlines(), 1):
        record = parse_key_value_log(line)
        if record is None:
            continue
        record['_line_number'] = line_number
        records.append(record)
    return records


def event_frame(records, event):
    rows = [record for record in records if record.get('event') == event]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    if 'date' in frame.columns:
        frame['date'] = frame['date'].astype(str)
    return frame


def normalize_candidate_rows(records):
    rows = []
    for record in records:
        event = record.get('event')
        if event not in ('AUCTION_PREFILTER_TOP', 'BIGMEAT_POOL_TOP'):
            continue
        if event == 'AUCTION_PREFILTER_TOP':
            score = record.get('prefilter_score')
            entry_type = 'auction_prefilter'
            source = 'AUCTION_PREFILTER_TOP'
        else:
            score = record.get('score')
            entry_type = record.get('tpl')
            source = 'BIGMEAT_POOL_TOP'
        rows.append({
            'date': record.get('date'),
            'stock': record.get('stock'),
            'name': record.get('name'),
            'candidate_rank': record.get('rank'),
            'candidate_score': score,
            'source': source,
            'entry_type': entry_type,
            'whether_bought': 0,
            'whether_already_holding': 0,
            'open_ratio': record.get('open_ratio'),
            'close_to_high': record.get('close_to_high'),
            'auc_ratio': record.get('auc_ratio'),
            'prefilter_score': record.get('prefilter_score'),
            'avg_money_5': record.get('avg_money_5'),
            'avg_money_10': record.get('avg_money_10'),
            'ret_5': record.get('ret_5'),
            'ret_10': record.get('ret_10'),
            'close_to_20d_high': record.get('close_to_20d_high'),
            'range_10': record.get('range_10'),
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    for col in ('candidate_rank', 'candidate_score'):
        frame[col] = pd.to_numeric(frame[col], errors='coerce')
    frame['date'] = frame['date'].astype(str)
    return frame.sort_values(['date', 'source', 'candidate_rank', 'stock'])


def mark_bought_and_holding(candidate_df, buy_df, hold_df):
    if candidate_df.empty:
        return candidate_df
    result = candidate_df.copy()
    bought_pairs = set()
    if not buy_df.empty and {'date', 'stock'}.issubset(buy_df.columns):
        bought_pairs = set(zip(buy_df['date'].astype(str), buy_df['stock']))
    holding_pairs = set()
    if not hold_df.empty and {'date', 'stock'}.issubset(hold_df.columns):
        holding_pairs = set(zip(hold_df['date'].astype(str), hold_df['stock']))
    result['whether_bought'] = [
        int((date, stock) in bought_pairs)
        for date, stock in zip(result['date'], result['stock'])
    ]
    result['whether_already_holding'] = [
        int((date, stock) in holding_pairs)
        for date, stock in zip(result['date'], result['stock'])
    ]
    return result


def build_watch_pool(candidate_df, source='BIGMEAT_POOL_TOP', expire_days=3):
    columns = [
        'signal_date', 'stock', 'name', 'signal_rank', 'signal_score',
        'signal_source', 'signal_entry_type', 'signal_price', 'expire_days',
        'watch_reason',
    ]
    if candidate_df.empty:
        return pd.DataFrame(columns=columns)
    base = candidate_df[
        (candidate_df['source'] == source)
        & (candidate_df['whether_bought'] == 0)
        & (candidate_df['whether_already_holding'] == 0)
    ].copy()
    if base.empty:
        return pd.DataFrame(columns=columns)
    base = base.rename(columns={
        'date': 'signal_date',
        'candidate_rank': 'signal_rank',
        'candidate_score': 'signal_score',
        'source': 'signal_source',
        'entry_type': 'signal_entry_type',
    })
    base['signal_price'] = math.nan
    base['expire_days'] = expire_days
    base['watch_reason'] = 'candidate_not_bought_not_holding'
    return base[columns].sort_values(['signal_date', 'signal_rank', 'stock'])


def auto_find_log(workdir):
    candidates = [
        workdir / 'v1.2.1A.log',
        workdir / 'jq_v121A.log',
        workdir / 'jq_v121A_20250701_20260614.log',
        workdir / 'jq_v130A_20260101_20260614.log.txt',
        Path.home() / 'Downloads' / 'log (8).zip',
    ]
    for path in candidates:
        if path.exists():
            return path
    zips = sorted(workdir.glob('*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
    if zips:
        return zips[0]
    logs = sorted(workdir.glob('*.log*'), key=lambda p: p.stat().st_mtime, reverse=True)
    if logs:
        return logs[0]
    raise FileNotFoundError('No log file found. Pass --log explicitly.')


def ensure_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)[:10]


def get_research_trade_days(start_date, end_date, fallback_dates=None):
    if JQDATA_AVAILABLE:
        days = get_trade_days(start_date=start_date, end_date=end_date)
        return [ensure_date(day) for day in days]
    if fallback_dates:
        return sorted(set(str(day)[:10] for day in fallback_dates if str(day) != 'nan'))
    return []


def fetch_price_data(stocks, start_date, end_date, include_high_limit=False):
    base_fields = ['open', 'close', 'high', 'low', 'volume', 'money', 'pre_close', 'paused']
    fields = list(base_fields)
    price_meta = {
        'include_high_limit_requested': int(bool(include_high_limit)),
        'high_limit_available': 0,
        'high_limit_non_null_count': 0,
        'limit_up_price_row_count': 0,
        'high_limit_error': '',
    }
    if include_high_limit:
        fields.append('high_limit')
    if not JQDATA_AVAILABLE:
        return pd.DataFrame(columns=['date', 'stock'] + fields), price_meta
    frames = []
    stock_list = sorted(set(stocks))
    for start in range(0, len(stock_list), 200):
        batch = stock_list[start:start + 200]
        try:
            data = get_price(
                batch,
                start_date=start_date,
                end_date=end_date,
                frequency='daily',
                fields=fields,
                skip_paused=False,
                fq='pre',
                panel=False,
            )
        except Exception as exc:
            if not include_high_limit:
                raise
            price_meta['high_limit_error'] = str(exc)[:200]
            fields = list(base_fields)
            data = get_price(
                batch,
                start_date=start_date,
                end_date=end_date,
                frequency='daily',
                fields=fields,
                skip_paused=False,
                fq='pre',
                panel=False,
            )
        if data is None or len(data) == 0:
            continue
        frame = data.reset_index()
        if 'code' not in frame.columns:
            for col in ('major', 'level_0'):
                if col in frame.columns:
                    frame = frame.rename(columns={col: 'code'})
                    break
        if 'time' not in frame.columns:
            for col in ('minor', 'index', 'level_1'):
                if col in frame.columns:
                    frame = frame.rename(columns={col: 'time'})
                    break
        if 'code' in frame.columns:
            frame = frame.rename(columns={'code': 'stock'})
        if 'time' in frame.columns:
            frame['date'] = pd.to_datetime(frame['time']).dt.date.astype(str)
        elif 'date' in frame.columns:
            frame['date'] = pd.to_datetime(frame['date']).dt.date.astype(str)
        else:
            raise RuntimeError('get_price result has no date/time column')
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=['date', 'stock'] + fields), price_meta
    price_df = pd.concat(frames, ignore_index=True)
    price_df = price_df.sort_values(['stock', 'date'])
    for col in fields:
        if col in price_df.columns:
            price_df[col] = pd.to_numeric(price_df[col], errors='coerce')
    price_df['prev_volume'] = price_df.groupby('stock')['volume'].shift(1)
    price_df['prev_money'] = price_df.groupby('stock')['money'].shift(1)
    price_df['ma5'] = (
        price_df.groupby('stock')['close']
        .rolling(5, min_periods=5)
        .mean()
        .reset_index(level=0, drop=True)
    )
    if 'high_limit' in price_df.columns:
        high_limit = pd.to_numeric(price_df['high_limit'], errors='coerce')
        price_meta['high_limit_non_null_count'] = int(high_limit.notna().sum())
        price_meta['high_limit_available'] = int(price_meta['high_limit_non_null_count'] > 0)
        close = pd.to_numeric(price_df['close'], errors='coerce')
        price_meta['limit_up_price_row_count'] = int((close >= high_limit * 0.999).fillna(False).sum())
    return price_df, price_meta


def enrich_watch_prices(watch_df, price_df):
    if watch_df.empty or price_df.empty:
        return watch_df
    price_map = price_df.set_index(['date', 'stock'])['close'].to_dict()
    result = watch_df.copy()
    result['signal_price'] = [
        price_map.get((row.signal_date, row.stock), math.nan)
        for row in result.itertuples(index=False)
    ]
    return result


def ensure_signal_metadata(frame, watch_df):
    if frame.empty:
        return frame
    result = frame.copy()
    needs_merge = False
    for col in ('signal_source', 'signal_entry_type', 'signal_rank', 'signal_score'):
        if col not in result.columns:
            result[col] = math.nan
            needs_merge = True
        elif result[col].isna().any():
            needs_merge = True
    if not needs_merge or watch_df.empty:
        return result
    meta_cols = [
        'signal_date', 'stock', 'signal_source', 'signal_entry_type',
        'signal_rank', 'signal_score',
    ]
    available = [col for col in meta_cols if col in watch_df.columns]
    merged = result.merge(
        watch_df[available].drop_duplicates(['signal_date', 'stock']),
        on=['signal_date', 'stock'],
        how='left',
        suffixes=('', '_watch'),
    )
    for col in ('signal_source', 'signal_entry_type', 'signal_rank', 'signal_score'):
        watch_col = col + '_watch'
        if watch_col in merged.columns:
            merged[col] = merged[col].where(merged[col].notna(), merged[watch_col])
            merged = merged.drop(columns=[watch_col])
    return merged


def rule_passes(row, rule, ignore_limit=False):
    if pd.isna(row.get('ret_from_signal')) or pd.isna(row.get('day_ret')):
        return False
    if row['ret_from_signal'] < rule['ret_from_signal_min']:
        return False
    if row['day_ret'] < rule['day_ret_min']:
        return False
    vol = row.get('volume_ratio_vs_prev')
    if pd.isna(vol) or vol <= rule['volume_ratio_min']:
        return False
    if rule['volume_ratio_max'] is not None and vol > rule['volume_ratio_max']:
        return False
    ma5_distance_max = rule['ma5_distance_max']
    if ma5_distance_max is not None:
        ma5_distance = row.get('ma5_distance')
        if pd.isna(ma5_distance) or ma5_distance > ma5_distance_max:
            return False
    close_to_day_high_min = rule['close_to_day_high_min']
    if close_to_day_high_min is not None:
        close_to_day_high = row.get('close_to_day_high')
        if pd.isna(close_to_day_high) or close_to_day_high < close_to_day_high_min:
            return False
    if row.get('paused') == 1:
        return False
    if not ignore_limit and row.get('is_limit_up_if_available') == 1:
        return False
    return True


def build_confirmed_signals(watch_df, price_df, trade_days):
    columns = CONFIRMED_SIGNAL_COLUMNS
    if watch_df.empty or price_df.empty or not trade_days:
        return pd.DataFrame(columns=columns), {'limit_up_filtered_count': 0}

    price_lookup = {
        (row.date, row.stock): row
        for row in price_df.itertuples(index=False)
    }
    day_index = {day: i for i, day in enumerate(trade_days)}
    rows = []
    meta = {'limit_up_filtered_count': 0}
    for signal in watch_df.itertuples(index=False):
        start_idx = day_index.get(signal.signal_date)
        if start_idx is None or pd.isna(signal.signal_price) or signal.signal_price <= 0:
            continue
        seen_rule = set()
        for offset in range(1, int(signal.expire_days) + 1):
            if start_idx + offset >= len(trade_days):
                break
            check_date = trade_days[start_idx + offset]
            price = price_lookup.get((check_date, signal.stock))
            if price is None:
                continue
            close = getattr(price, 'close', math.nan)
            high = getattr(price, 'high', math.nan)
            pre_close = getattr(price, 'pre_close', math.nan)
            if pd.isna(pre_close) or pre_close <= 0:
                pre_close = signal.signal_price
            prev_volume = getattr(price, 'prev_volume', math.nan)
            prev_money = getattr(price, 'prev_money', math.nan)
            ma5 = getattr(price, 'ma5', math.nan)
            row = {
                'signal_date': signal.signal_date,
                'confirm_date': check_date,
                'days_after_signal': offset,
                'stock': signal.stock,
                'name': signal.name,
                'signal_source': signal.signal_source,
                'signal_entry_type': signal.signal_entry_type,
                'signal_rank': signal.signal_rank,
                'signal_score': signal.signal_score,
                'signal_price': signal.signal_price,
                'confirm_price': close,
                'ret_from_signal': (close / signal.signal_price - 1.0) * 100.0,
                'day_ret': (close / pre_close - 1.0) * 100.0,
                'volume_ratio_vs_prev': getattr(price, 'volume', math.nan) / prev_volume
                if prev_volume and not pd.isna(prev_volume) else math.nan,
                'money_ratio_vs_prev': getattr(price, 'money', math.nan) / prev_money
                if prev_money and not pd.isna(prev_money) else math.nan,
                'ma5': ma5,
                'ma5_distance': (close / ma5 - 1.0) * 100.0
                if ma5 and not pd.isna(ma5) else math.nan,
                'close_to_day_high': close / high if high and not pd.isna(high) else math.nan,
                'is_limit_up_if_available': math.nan,
                'paused': getattr(price, 'paused', math.nan),
            }
            if hasattr(price, 'high_limit'):
                high_limit = getattr(price, 'high_limit')
                if high_limit and not pd.isna(high_limit):
                    row['is_limit_up_if_available'] = int(close >= high_limit * 0.999)
            for rule_name, rule in RULES.items():
                if rule_name in seen_rule:
                    continue
                if row.get('is_limit_up_if_available') == 1 and rule_passes(row, rule, ignore_limit=True):
                    meta['limit_up_filtered_count'] += 1
                    seen_rule.add(rule_name)
                    continue
                if rule_passes(row, rule):
                    out = {'rule': rule_name}
                    out.update(row)
                    rows.append(out)
                    seen_rule.add(rule_name)
    return pd.DataFrame(rows, columns=columns), meta


def build_trade_close_map(trade_close_df):
    if trade_close_df.empty:
        return defaultdict(list)
    result = defaultdict(list)
    for row in trade_close_df.sort_values(['date', '_line_number']).itertuples(index=False):
        result[row.stock].append(row)
    return result


def attach_returns(confirmed_df, price_df, trade_close_df, trade_days):
    columns = CONFIRMED_SIGNAL_COLUMNS + TRADE_SIM_EXTRA_COLUMNS
    if confirmed_df.empty:
        return pd.DataFrame(columns=columns)
    price_lookup = {
        (row.date, row.stock): row
        for row in price_df.itertuples(index=False)
    }
    day_index = {day: i for i, day in enumerate(trade_days)}
    trade_map = build_trade_close_map(trade_close_df)
    rows = []
    for signal in confirmed_df.itertuples(index=False):
        item = signal._asdict()
        confirm_idx = day_index.get(signal.confirm_date)
        for horizon in (3, 5):
            exit_date = None
            exit_price = math.nan
            ret = math.nan
            if confirm_idx is not None:
                exit_idx = min(confirm_idx + horizon, len(trade_days) - 1)
                if exit_idx > confirm_idx:
                    exit_date = trade_days[exit_idx]
                    price = price_lookup.get((exit_date, signal.stock))
                    if price is not None:
                        exit_price = getattr(price, 'close', math.nan)
                        ret = (exit_price / signal.confirm_price - 1.0) * 100.0
            item[f'exit_date_{horizon}d'] = exit_date
            item[f'exit_price_{horizon}d'] = exit_price
            item[f'return_{horizon}d'] = ret

        close_record = None
        for close in trade_map.get(signal.stock, []):
            close_date = str(getattr(close, 'date'))
            if close_date >= signal.confirm_date:
                close_record = close
                break
        item['trade_close_available'] = 1 if close_record is not None else 0
        item['trade_close_date'] = getattr(close_record, 'date', None) if close_record else None
        item['trade_close_ret_actual'] = getattr(close_record, 'trade_ret', math.nan) if close_record else math.nan
        item['exit_reason_if_available'] = getattr(close_record, 'exit_reason', None) if close_record else None
        ret_to_close = math.nan
        if close_record is not None:
            price = price_lookup.get((str(getattr(close_record, 'date')), signal.stock))
            if price is not None:
                exit_price = getattr(price, 'close', math.nan)
                ret_to_close = (exit_price / signal.confirm_price - 1.0) * 100.0
        item['return_to_trade_close_if_available'] = ret_to_close
        rows.append(item)
    return pd.DataFrame(rows, columns=columns)


def summarize_rules(trade_df):
    columns = [
        'rule', 'sample_count', 'win_count', 'loss_count', 'win_rate',
        'avg_return_3d', 'median_return_3d', 'avg_return_5d',
        'median_return_5d', 'max_gain', 'max_loss', 'avg_ret_from_signal',
        'avg_day_ret', 'avg_volume_ratio', 'avg_ma5_distance',
        'top_gain_contribution_ratio', 'sample_stocks',
    ]
    if trade_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for rule, group in trade_df.groupby('rule'):
        returns = pd.to_numeric(group['return_5d'], errors='coerce').dropna()
        gains = returns[returns > 0].sort_values(ascending=False)
        positive_sum = gains.sum()
        top_gain_ratio = gains.iloc[0] / positive_sum if positive_sum > 0 else math.nan
        rows.append({
            'rule': rule,
            'sample_count': len(group),
            'win_count': int((returns > 0).sum()),
            'loss_count': int((returns <= 0).sum()),
            'win_rate': (returns > 0).mean() if len(returns) else math.nan,
            'avg_return_3d': pd.to_numeric(group['return_3d'], errors='coerce').mean(),
            'median_return_3d': pd.to_numeric(group['return_3d'], errors='coerce').median(),
            'avg_return_5d': returns.mean(),
            'median_return_5d': returns.median(),
            'max_gain': returns.max() if len(returns) else math.nan,
            'max_loss': returns.min() if len(returns) else math.nan,
            'avg_ret_from_signal': pd.to_numeric(group['ret_from_signal'], errors='coerce').mean(),
            'avg_day_ret': pd.to_numeric(group['day_ret'], errors='coerce').mean(),
            'avg_volume_ratio': pd.to_numeric(group['volume_ratio_vs_prev'], errors='coerce').mean(),
            'avg_ma5_distance': pd.to_numeric(group['ma5_distance'], errors='coerce').mean(),
            'top_gain_contribution_ratio': top_gain_ratio,
            'sample_stocks': ','.join(
                group[['stock', 'name']]
                .drop_duplicates()
                .apply(lambda row: '{}:{}'.format(row['stock'], row['name']), axis=1)
                .tolist()[:20]
            ),
        })
    return pd.DataFrame(rows, columns=columns)


def _refined_filter(trade_df, rule_name):
    if trade_df.empty:
        return trade_df.copy()
    entry_type = trade_df.get('signal_entry_type')
    days_after = pd.to_numeric(trade_df.get('days_after_signal'), errors='coerce')
    if rule_name == 'rule_D_all':
        mask = trade_df['rule'] == 'rule_D_ruleB_ma5_10_close_high_097'
    elif rule_name == 'rule_D_deep_water':
        mask = (
            (trade_df['rule'] == 'rule_D_ruleB_ma5_10_close_high_097')
            & (entry_type == 'deep_water')
        )
    elif rule_name == 'rule_D_trend_core':
        mask = (
            (trade_df['rule'] == 'rule_D_ruleB_ma5_10_close_high_097')
            & (entry_type == 'trend_core')
        )
    elif rule_name == 'rule_D_deep_water_day1':
        mask = (
            (trade_df['rule'] == 'rule_D_ruleB_ma5_10_close_high_097')
            & (entry_type == 'deep_water')
            & (days_after == 1)
        )
    elif rule_name == 'rule_D_deep_water_day2_3':
        mask = (
            (trade_df['rule'] == 'rule_D_ruleB_ma5_10_close_high_097')
            & (entry_type == 'deep_water')
            & (days_after.isin([2, 3]))
        )
    elif rule_name == 'rule_B_deep_water':
        mask = (
            (trade_df['rule'] == 'rule_B_ret5_day5_vol_1_2')
            & (entry_type == 'deep_water')
        )
    elif rule_name == 'rule_B_trend_core':
        mask = (
            (trade_df['rule'] == 'rule_B_ret5_day5_vol_1_2')
            & (entry_type == 'trend_core')
        )
    else:
        mask = pd.Series([False] * len(trade_df), index=trade_df.index)
    result = trade_df[mask].copy()
    if not result.empty:
        result['rule'] = rule_name
    return result


def build_refined_trade_frame(trade_df):
    if trade_df.empty:
        return pd.DataFrame(columns=trade_df.columns)
    frames = []
    for rule_name in REFINED_RULES:
        refined = _refined_filter(trade_df, rule_name)
        if not refined.empty:
            frames.append(refined)
    if not frames:
        return pd.DataFrame(columns=trade_df.columns)
    return pd.concat(frames, ignore_index=True)


def build_refined_rule_summary(trade_df):
    refined = build_refined_trade_frame(trade_df)
    summary = summarize_rules(refined)
    if summary.empty:
        return summary
    summary['rule'] = pd.Categorical(summary['rule'], categories=list(REFINED_RULES), ordered=True)
    return summary.sort_values('rule').reset_index(drop=True)


def active_position_score(position, current_row, entry_idx, current_idx):
    if current_row is None:
        return -999.0
    close = getattr(current_row, 'close', math.nan)
    ma5 = getattr(current_row, 'ma5', math.nan)
    if pd.isna(close) or close <= 0:
        return -999.0
    pnl = (close / position['entry_price'] - 1.0) * 100.0
    hold_days = max(0, current_idx - entry_idx)
    below_ma5_penalty = 5.0 if (ma5 and not pd.isna(ma5) and close < ma5) else 0.0
    stale_penalty = 3.0 if hold_days > 3 and pnl <= 0 else 0.0
    return pnl - below_ma5_penalty - stale_penalty


def simulate_portfolio(trade_df, price_df, trade_days, rule_name, horizon, satellite_ratio,
                       core_exposure=0.60, max_total_position_ratio=0.75):
    columns = [
        'rule', 'exit_horizon', 'requested_satellite_position_ratio',
        'effective_satellite_position_ratio', 'final_nav_proxy',
        'total_return_proxy', 'max_drawdown_proxy', 'trade_count',
        'turnover', 'avg_holding_days', 'core_profit', 'satellite_profit',
        'replacement_count', 'replaced_profit_after_sell',
        'new_position_profit_after_buy',
    ]
    if trade_df.empty:
        return pd.DataFrame(columns=columns)

    candidates = trade_df[trade_df['rule'] == rule_name].copy()
    if candidates.empty:
        return pd.DataFrame(columns=columns)
    max_satellite_total = max(0.0, max_total_position_ratio - core_exposure)
    effective_ratio = min(satellite_ratio, max_satellite_total / 2.0)
    if effective_ratio <= 0:
        return pd.DataFrame(columns=columns)

    price_lookup = {
        (row.date, row.stock): row
        for row in price_df.itertuples(index=False)
    }
    day_index = {day: i for i, day in enumerate(trade_days)}
    active = []
    realized_profit = 0.0
    replaced_profit = 0.0
    new_position_profit = 0.0
    replacement_count = 0
    trade_count = 0
    holding_days = []
    nav_series = []

    candidates = candidates.sort_values(['confirm_date', 'signal_score'], ascending=[True, False])
    candidates_by_date = defaultdict(list)
    for row in candidates.itertuples(index=False):
        candidates_by_date[row.confirm_date].append(row)

    for day in trade_days:
        idx = day_index[day]
        still_active = []
        for pos in active:
            if pos['exit_date'] <= day:
                exit_price = getattr(price_lookup.get((pos['exit_date'], pos['stock'])), 'close', math.nan)
                if not pd.isna(exit_price):
                    pnl = (exit_price / pos['entry_price'] - 1.0) * effective_ratio
                    realized_profit += pnl
                    new_position_profit += pnl
                holding_days.append(max(1, day_index.get(pos['exit_date'], idx) - pos['entry_idx']))
            else:
                still_active.append(pos)
        active = still_active

        for signal in candidates_by_date.get(day, []):
            if any(pos['stock'] == signal.stock for pos in active):
                continue
            exit_date = getattr(signal, f'exit_date_{horizon}d')
            if not exit_date or pd.isna(signal.confirm_price):
                continue
            new_strength = (
                float(signal.ret_from_signal)
                + float(signal.day_ret)
                + float(signal.volume_ratio_vs_prev) * 2.0
                + float(signal.signal_score or 0.0) * 10.0
            )
            new_pos = {
                'stock': signal.stock,
                'entry_date': signal.confirm_date,
                'entry_idx': idx,
                'entry_price': signal.confirm_price,
                'exit_date': exit_date,
                'strength': new_strength,
            }
            if len(active) < 2:
                active.append(new_pos)
                trade_count += 1
                continue

            scored = []
            for pos in active:
                entry_idx = pos['entry_idx']
                current_row = price_lookup.get((day, pos['stock']))
                score = active_position_score(pos, current_row, entry_idx, idx)
                scored.append((score, pos))
            weakest_score, weakest = sorted(scored, key=lambda x: x[0])[0]
            if weakest_score < 0 or new_strength > weakest_score + 5.0:
                current_row = price_lookup.get((day, weakest['stock']))
                if current_row is not None:
                    close = getattr(current_row, 'close', math.nan)
                    if not pd.isna(close):
                        pnl = (close / weakest['entry_price'] - 1.0) * effective_ratio
                        realized_profit += pnl
                        replaced_profit += pnl
                        holding_days.append(max(1, idx - weakest['entry_idx']))
                active = [pos for pos in active if pos is not weakest]
                active.append(new_pos)
                trade_count += 1
                replacement_count += 1

        mtm = realized_profit
        for pos in active:
            price_row = price_lookup.get((day, pos['stock']))
            if price_row is None:
                continue
            close = getattr(price_row, 'close', math.nan)
            if not pd.isna(close):
                mtm += (close / pos['entry_price'] - 1.0) * effective_ratio
        nav_series.append(1.0 + mtm)

    satellite_profit = (nav_series[-1] - 1.0) if nav_series else 0.0
    peak = -math.inf
    max_dd = 0.0
    for nav in nav_series:
        peak = max(peak, nav)
        if peak > 0:
            max_dd = min(max_dd, nav / peak - 1.0)
    return pd.DataFrame([{
        'rule': rule_name,
        'exit_horizon': '{}d'.format(horizon),
        'requested_satellite_position_ratio': satellite_ratio,
        'effective_satellite_position_ratio': effective_ratio,
        'final_nav_proxy': nav_series[-1] if nav_series else 1.0,
        'total_return_proxy': satellite_profit,
        'max_drawdown_proxy': max_dd,
        'trade_count': trade_count,
        'turnover': trade_count * effective_ratio,
        'avg_holding_days': statistics.mean(holding_days) if holding_days else math.nan,
        'core_profit': math.nan,
        'satellite_profit': satellite_profit,
        'replacement_count': replacement_count,
        'replaced_profit_after_sell': replaced_profit,
        'new_position_profit_after_buy': new_position_profit,
    }], columns=columns)


def build_portfolio_summary(trade_df, price_df, trade_days):
    rows = []
    if trade_df.empty or price_df.empty or not trade_days:
        return pd.DataFrame(columns=[
            'rule', 'exit_horizon', 'requested_satellite_position_ratio',
            'effective_satellite_position_ratio', 'final_nav_proxy',
            'total_return_proxy', 'max_drawdown_proxy', 'trade_count',
            'turnover', 'avg_holding_days', 'core_profit', 'satellite_profit',
            'replacement_count', 'replaced_profit_after_sell',
            'new_position_profit_after_buy',
        ])
    for rule_name in RULES:
        for horizon in (3, 5):
            for ratio in (0.10, 0.125):
                rows.append(simulate_portfolio(
                    trade_df, price_df, trade_days, rule_name, horizon, ratio
                ))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _empty_full_compound_summary():
    return pd.DataFrame(columns=FULL_COMPOUND_COLUMNS)


def _nav_drawdown(nav_series):
    peak = -math.inf
    max_dd = 0.0
    for nav in nav_series:
        peak = max(peak, nav)
        if peak > 0:
            max_dd = min(max_dd, nav / peak - 1.0)
    return max_dd


def _position_mtm_value(position, price_row):
    if price_row is None:
        return position['allocation']
    close = getattr(price_row, 'close', math.nan)
    if pd.isna(close) or close <= 0:
        return position['allocation']
    return position['allocation'] * close / position['entry_price']


def simulate_portfolio_compound(trade_df, price_df, trade_days, rule_name, horizon, mode,
                                risk_off_dates=None, risk_off_target_exposure=None):
    if trade_df.empty or price_df.empty or not trade_days:
        return _empty_full_compound_summary()
    candidates = trade_df[trade_df['rule'] == rule_name].copy()
    if candidates.empty:
        return _empty_full_compound_summary()

    risk_off_dates = risk_off_dates or set()
    core_exposure = float(mode['core_exposure'])
    satellite_slots = int(mode['satellite_slots'])
    requested_ratio = float(mode['satellite_ratio'])
    max_total = float(mode['max_total_position_ratio'])
    max_satellite_total = max(0.0, max_total - core_exposure)
    effective_ratio = min(requested_ratio, max_satellite_total / float(max(1, satellite_slots)))
    gross_exposure = core_exposure + requested_ratio * satellite_slots
    effective_total_exposure = core_exposure + effective_ratio * satellite_slots
    if effective_ratio <= 0:
        return _empty_full_compound_summary()

    price_lookup = {
        (row.date, row.stock): row
        for row in price_df.itertuples(index=False)
    }
    day_index = {day: i for i, day in enumerate(trade_days)}
    candidates = candidates.sort_values(['confirm_date', 'signal_score'], ascending=[True, False])
    candidates_by_date = defaultdict(list)
    for row in candidates.itertuples(index=False):
        candidates_by_date[row.confirm_date].append(row)

    cash = 1.0
    active = []
    nav_series = []
    trade_count = 0
    turnover = 0.0
    replacement_count = 0
    holding_days = []
    replaced_profit_after_sell = 0.0
    new_position_profit_after_buy = 0.0

    for day in trade_days:
        idx = day_index[day]
        still_active = []
        for pos in active:
            if pos['exit_date'] <= day:
                price_row = price_lookup.get((pos['exit_date'], pos['stock']))
                exit_value = _position_mtm_value(pos, price_row)
                cash += exit_value
                new_position_profit_after_buy += exit_value - pos['allocation']
                holding_days.append(max(1, day_index.get(pos['exit_date'], idx) - pos['entry_idx']))
            else:
                still_active.append(pos)
        active = still_active

        nav_before_entries = cash
        for pos in active:
            nav_before_entries += _position_mtm_value(pos, price_lookup.get((day, pos['stock'])))

        risk_off_today = day in risk_off_dates
        if risk_off_today:
            # Research proxy only: do not open new satellite positions during
            # risk-off. Existing satellite positions expire by their horizon.
            nav_series.append(nav_before_entries)
            continue

        for signal in candidates_by_date.get(day, []):
            if any(pos['stock'] == signal.stock for pos in active):
                continue
            exit_date = getattr(signal, 'exit_date_{}d'.format(horizon))
            if not exit_date or pd.isna(signal.confirm_price):
                continue
            current_nav = cash
            for pos in active:
                current_nav += _position_mtm_value(pos, price_lookup.get((day, pos['stock'])))
            allocation = current_nav * effective_ratio
            if allocation <= 0:
                continue
            new_strength = (
                float(signal.ret_from_signal)
                + float(signal.day_ret)
                + float(signal.volume_ratio_vs_prev) * 2.0
                + float(signal.signal_score or 0.0) * 10.0
            )
            new_pos = {
                'stock': signal.stock,
                'entry_date': signal.confirm_date,
                'entry_idx': idx,
                'entry_price': signal.confirm_price,
                'exit_date': exit_date,
                'allocation': allocation,
                'strength': new_strength,
            }
            if len(active) < satellite_slots and cash >= allocation:
                cash -= allocation
                active.append(new_pos)
                trade_count += 1
                turnover += allocation
                continue

            if len(active) < satellite_slots:
                continue

            scored = []
            for pos in active:
                entry_idx = pos['entry_idx']
                current_row = price_lookup.get((day, pos['stock']))
                score = active_position_score(pos, current_row, entry_idx, idx)
                scored.append((score, pos))
            weakest_score, weakest = sorted(scored, key=lambda x: x[0])[0]
            if weakest_score < 0 or new_strength > weakest_score + 5.0:
                current_row = price_lookup.get((day, weakest['stock']))
                exit_value = _position_mtm_value(weakest, current_row)
                cash += exit_value
                replaced_profit_after_sell += exit_value - weakest['allocation']
                holding_days.append(max(1, idx - weakest['entry_idx']))
                active = [pos for pos in active if pos is not weakest]
                current_nav = cash
                for pos in active:
                    current_nav += _position_mtm_value(pos, price_lookup.get((day, pos['stock'])))
                allocation = current_nav * effective_ratio
                if cash >= allocation:
                    cash -= allocation
                    new_pos['allocation'] = allocation
                    active.append(new_pos)
                    trade_count += 1
                    turnover += allocation
                    replacement_count += 1

        nav = cash
        for pos in active:
            nav += _position_mtm_value(pos, price_lookup.get((day, pos['stock'])))
        nav_series.append(nav)

    final_nav = nav_series[-1] if nav_series else 1.0
    satellite_profit = final_nav - 1.0
    return pd.DataFrame([{
        'portfolio_mode': mode['portfolio_mode'],
        'rule': rule_name,
        'exit_horizon': '{}d'.format(horizon),
        'core_exposure': core_exposure,
        'satellite_slots': satellite_slots,
        'requested_satellite_position_ratio': requested_ratio,
        'effective_satellite_position_ratio': effective_ratio,
        'max_total_position_ratio': max_total,
        'gross_exposure': gross_exposure,
        'effective_total_exposure': effective_total_exposure,
        'is_full_compound_mode': mode.get('is_full_compound_mode', 0),
        'final_nav_proxy': final_nav,
        'total_return_proxy': satellite_profit,
        'max_drawdown_proxy': _nav_drawdown(nav_series),
        'trade_count': trade_count,
        'turnover': turnover,
        'avg_holding_days': statistics.mean(holding_days) if holding_days else math.nan,
        'satellite_profit': satellite_profit,
        'replacement_count': replacement_count,
        'replaced_profit_after_sell': replaced_profit_after_sell,
        'new_position_profit_after_buy': new_position_profit_after_buy,
    }], columns=FULL_COMPOUND_COLUMNS)


def build_market_state(records):
    keys = (
        'regime', 'reg2', 'trend', 'market_state', 'prev_regime',
        'prev_trend', 'market_score', 'breadth_score',
    )
    rows = []
    for record in records:
        row = {'date': record.get('date')}
        has_market_field = False
        for key in keys:
            value = record.get(key)
            row[key] = value
            if value is not None:
                has_market_field = True
        if has_market_field and row['date'] is not None:
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=['date'] + list(keys)), set()
    market_df = pd.DataFrame(rows).drop_duplicates('date', keep='last')
    risk_off_dates = set()
    for row in market_df.itertuples(index=False):
        regime = str(getattr(row, 'regime', '') or getattr(row, 'prev_regime', '') or '').lower()
        trend = str(getattr(row, 'trend', '') or getattr(row, 'prev_trend', '') or '').lower()
        if regime in ('bear', 'panic', 'extreme') or (trend == 'down' and regime != 'bull'):
            risk_off_dates.add(str(row.date))
    return market_df, risk_off_dates


def build_full_compound_summary(trade_df, price_df, trade_days, records):
    refined_trade_df = build_refined_trade_frame(trade_df)
    compound_source = pd.concat([trade_df, refined_trade_df], ignore_index=True) if not refined_trade_df.empty else trade_df
    if compound_source.empty or price_df.empty or not trade_days:
        return _empty_full_compound_summary(), {
            'risk_off_available': 0,
            'risk_off_dates_count': 0,
        }
    market_df, risk_off_dates = build_market_state(records)
    risk_meta = {
        'risk_off_available': int(not market_df.empty),
        'risk_off_dates_count': len(risk_off_dates),
    }
    rows = []
    for mode in PORTFOLIO_MODES:
        for rule_name in FULL_COMPOUND_RULES:
            for horizon in (3, 5):
                rows.append(simulate_portfolio_compound(
                    compound_source, price_df, trade_days, rule_name, horizon, mode
                ))
    if risk_meta['risk_off_available']:
        risk_mode = {
            'portfolio_mode': 'risk_off_full_B',
            'core_exposure': 0.70,
            'satellite_slots': 2,
            'satellite_ratio': 0.15,
            'max_total_position_ratio': 1.00,
            'is_full_compound_mode': 1,
        }
        for rule_name in FULL_COMPOUND_RULES:
            for horizon in (3, 5):
                rows.append(simulate_portfolio_compound(
                    compound_source, price_df, trade_days, rule_name, horizon,
                    risk_mode, risk_off_dates=risk_off_dates,
                    risk_off_target_exposure=0.60,
                ))
    summary = pd.concat(rows, ignore_index=True) if rows else _empty_full_compound_summary()
    return summary, risk_meta


def _fmt(value, pct=False):
    if value is None or pd.isna(value):
        return 'NA'
    try:
        number = float(value)
    except Exception:
        return str(value)
    if pct:
        return '{:.2%}'.format(number)
    return '{:.4f}'.format(number)


def _markdown_table(frame, columns, max_rows=20):
    if frame is None or frame.empty:
        return '无数据'
    data = frame[columns].head(max_rows).copy()
    lines = []
    lines.append('| ' + ' | '.join(columns) + ' |')
    lines.append('| ' + ' | '.join(['---'] * len(columns)) + ' |')
    for _, row in data.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                values.append(_fmt(value))
            else:
                values.append(str(value))
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def _best_by(frame, column):
    if frame is None or frame.empty or column not in frame.columns:
        return None
    numeric = pd.to_numeric(frame[column], errors='coerce')
    if numeric.dropna().empty:
        return None
    return frame.loc[numeric.idxmax()]


def build_diagnostics_df(run_meta, risk_meta, high_limit_meta, excel_meta):
    rows = []
    for source, data in (
        ('run', run_meta),
        ('risk_off', risk_meta),
        ('high_limit', high_limit_meta),
        ('excel', excel_meta),
    ):
        for key, value in sorted((data or {}).items()):
            rows.append({
                'section': source,
                'key': key,
                'value': value,
            })
    return pd.DataFrame(rows, columns=['section', 'key', 'value'])


def write_markdown_report(output_dir, run_meta, rule_summary_df, refined_summary_df,
                          full_compound_df, risk_meta, high_limit_meta,
                          excel_meta=None):
    report_path = output_dir / OUTPUT_FILES['report']
    excel_meta = excel_meta or {}
    best_full = _best_by(full_compound_df, 'final_nav_proxy')
    best_sat = _best_by(full_compound_df, 'satellite_profit')
    high_limit_ok = bool(high_limit_meta.get('high_limit_available'))
    risk_ok = bool(risk_meta.get('risk_off_available'))
    recommendation = '暂不建议'
    if best_sat is not None:
        try:
            if float(best_sat.get('satellite_profit', 0)) > 0:
                recommendation = '可以进入独立实验版观察'
        except Exception:
            pass

    lines = [
        '# v1.4.0 候选池影子轮动研究报告',
        '',
        '## 1. full 运行状态',
        '',
        '- mode: full',
        '- jqdata_available: {}'.format(run_meta.get('jqdata_available')),
        '- log: {}'.format(run_meta.get('log_path')),
        '- candidates: {}'.format(run_meta.get('candidate_count')),
        '- watch: {}'.format(run_meta.get('watch_count')),
        '- confirmed: {}'.format(run_meta.get('confirmed_count')),
        '- sim_trades: {}'.format(run_meta.get('sim_trade_count')),
        '',
        '## 2. 原始 A/B/C/D 规则结果',
        '',
        _markdown_table(rule_summary_df, [
            'rule', 'sample_count', 'win_rate', 'avg_return_3d',
            'median_return_3d', 'avg_return_5d', 'median_return_5d',
            'max_loss', 'top_gain_contribution_ratio',
        ]),
        '',
        '## 3. deep_water vs trend_core 对比',
        '',
        _markdown_table(refined_summary_df[
            refined_summary_df['rule'].isin([
                'rule_D_deep_water', 'rule_D_trend_core',
                'rule_B_deep_water', 'rule_B_trend_core',
            ])
        ] if not refined_summary_df.empty else refined_summary_df, [
            'rule', 'sample_count', 'win_rate', 'avg_return_5d',
            'median_return_5d', 'max_loss', 'sample_stocks',
        ]),
        '',
        '## 4. days_after_signal 对比',
        '',
        _markdown_table(refined_summary_df[
            refined_summary_df['rule'].isin([
                'rule_D_deep_water_day1', 'rule_D_deep_water_day2_3',
            ])
        ] if not refined_summary_df.empty else refined_summary_df, [
            'rule', 'sample_count', 'win_rate', 'avg_return_5d',
            'median_return_5d', 'max_loss',
        ]),
        '',
        '## 5. Rule D 派生规则表现',
        '',
        _markdown_table(refined_summary_df[
            refined_summary_df['rule'].astype(str).str.startswith('rule_D')
        ] if not refined_summary_df.empty else refined_summary_df, [
            'rule', 'sample_count', 'win_rate', 'avg_return_3d',
            'median_return_3d', 'avg_return_5d', 'median_return_5d',
            'max_loss', 'top_gain_contribution_ratio',
        ]),
        '',
        '## 6. Conservative-75 与 Full-A/B/C 对比',
        '',
        _markdown_table(full_compound_df, [
            'portfolio_mode', 'rule', 'exit_horizon', 'final_nav_proxy',
            'total_return_proxy', 'max_drawdown_proxy', 'trade_count',
            'satellite_profit', 'replacement_count',
        ], max_rows=60),
        '',
        '## 7. 满仓后收益提升',
        '',
        '最佳 final_nav_proxy: {}'.format(
            '{} / {} / {}'.format(
                best_full.get('portfolio_mode'), best_full.get('rule'), best_full.get('exit_horizon')
            ) if best_full is not None else 'NA'
        ),
        '',
        '## 8. 满仓后最大回撤变化',
        '',
        '请重点比较 full_A/B/C 与 conservative_75 的 max_drawdown_proxy。脚本只做卫星仓代理，不包含真实核心仓收益曲线。',
        '',
        '## 9. 卫星仓正贡献是否保持',
        '',
        '最佳 satellite_profit: {}'.format(
            '{} / {} / {} / {}'.format(
                best_sat.get('portfolio_mode'), best_sat.get('rule'),
                best_sat.get('exit_horizon'), _fmt(best_sat.get('satellite_profit'))
            ) if best_sat is not None else 'NA'
        ),
        '',
        '## 10. 替换弱仓是否仍然有效',
        '',
        '看 replacement_count、replaced_profit_after_sell、new_position_profit_after_buy。若替换次数上升但 satellite_profit 不升，说明替换无效。',
        '',
        '## 11. 大盘极差缩仓代理是否有效',
        '',
        'risk_off_available: {}'.format(int(risk_ok)),
        'risk_off_dates_count: {}'.format(risk_meta.get('risk_off_dates_count')),
        '说明: {}'.format(
            '已生成 risk_off_full_B 对比。' if risk_ok else
            '日志缺少 regime/trend/market_state 等市场字段，无法完成 risk_off 缩仓代理。'
        ),
        '',
        '## 12. high_limit 涨停不可买过滤是否成功',
        '',
        '- include_high_limit_requested: {}'.format(high_limit_meta.get('include_high_limit_requested')),
        '- high_limit_available: {}'.format(high_limit_meta.get('high_limit_available')),
        '- high_limit_non_null_count: {}'.format(high_limit_meta.get('high_limit_non_null_count')),
        '- limit_up_filtered_count: {}'.format(high_limit_meta.get('limit_up_filtered_count')),
        '- 说明: {}'.format(
            '已启用涨停不可买过滤。' if high_limit_ok else
            'high_limit 不可用或全为空，未完成涨停不可买过滤。'
        ),
        '',
        '## Excel 汇总文件',
        '',
        '{}'.format(
            '- 已生成 shadow_rotation_research_outputs.xlsx\n'
            '- 所有主要 CSV 已汇总到一个 Excel 文件\n'
            '- 下载时优先下载这个 xlsx 即可'
            if excel_meta.get('excel_export_ok') else
            '- Excel 汇总文件未生成\n'
            '- 原有 CSV 已保留\n'
            '- 失败原因: {}'.format(excel_meta.get('excel_error', 'NA'))
        ),
        '',
        '## 13. 推荐进入 v1.4.0A 的规则和仓位结构',
        '',
        '候选建议: {}'.format(
            '{} / {} / {}'.format(
                best_sat.get('portfolio_mode'), best_sat.get('rule'), best_sat.get('exit_horizon')
            ) if best_sat is not None else 'NA'
        ),
        '',
        '## 14. 是否建议进入真实策略实验版',
        '',
        recommendation,
        '',
        '注: 本报告由研究脚本生成，不包含真实下单逻辑。',
    ]
    report_path.write_text('\n'.join(lines), encoding='utf-8-sig')
    return report_path


def write_csv(path, frame):
    frame.to_csv(path, index=False, encoding='utf-8-sig')


def write_excel_bundle(output_dir, tables_dict):
    """Write all research outputs into one Excel workbook.

    CSV outputs remain the canonical fallback. If the JoinQuant environment
    lacks openpyxl/xlsxwriter, this function returns a warning instead of
    failing the research run.
    """
    output_path = output_dir / OUTPUT_FILES['excel']
    try:
        engine = None
        try:
            import openpyxl  # noqa: F401

            engine = 'openpyxl'
        except Exception:
            try:
                import xlsxwriter  # noqa: F401

                engine = 'xlsxwriter'
            except Exception:
                engine = None
        if engine is None:
            raise RuntimeError('openpyxl/xlsxwriter unavailable')

        with pd.ExcelWriter(str(output_path), engine=engine) as writer:
            for sheet_name, frame in tables_dict.items():
                safe_sheet = str(sheet_name)[:31]
                if frame is None:
                    frame = pd.DataFrame()
                if not isinstance(frame, pd.DataFrame):
                    frame = pd.DataFrame(frame)
                frame.to_excel(writer, sheet_name=safe_sheet, index=False)
        print('SHADOW_ROTATION|excel_export={}'.format(OUTPUT_FILES['excel']))
        return {
            'excel_export_ok': 1,
            'excel_path': str(output_path),
            'excel_error': '',
        }
    except Exception as exc:
        reason = str(exc).replace('|', '/').replace('\n', ' ')[:300]
        print('SHADOW_ROTATION_WARN|excel_export_failed=1|reason={}'.format(reason))
        return {
            'excel_export_ok': 0,
            'excel_path': str(output_path),
            'excel_error': reason,
        }


def output_empty_files(output_dir, candidate_df, watch_df):
    write_csv(output_dir / OUTPUT_FILES['candidates'], candidate_df)
    write_csv(output_dir / OUTPUT_FILES['watch'], watch_df)
    write_csv(output_dir / OUTPUT_FILES['confirmed'], pd.DataFrame(columns=[
        *CONFIRMED_SIGNAL_COLUMNS,
    ]))
    write_csv(output_dir / OUTPUT_FILES['rules'], pd.DataFrame(columns=[
        'rule', 'sample_count', 'win_count', 'loss_count', 'win_rate',
        'avg_return_3d', 'median_return_3d', 'avg_return_5d',
        'median_return_5d', 'max_gain', 'max_loss', 'avg_ret_from_signal',
        'avg_day_ret', 'avg_volume_ratio', 'avg_ma5_distance',
        'top_gain_contribution_ratio', 'sample_stocks',
    ]))
    write_csv(output_dir / OUTPUT_FILES['refined_rules'], pd.DataFrame(columns=[
        'rule', 'sample_count', 'win_count', 'loss_count', 'win_rate',
        'avg_return_3d', 'median_return_3d', 'avg_return_5d',
        'median_return_5d', 'max_gain', 'max_loss', 'avg_ret_from_signal',
        'avg_day_ret', 'avg_volume_ratio', 'avg_ma5_distance',
        'top_gain_contribution_ratio', 'sample_stocks',
    ]))
    write_csv(output_dir / OUTPUT_FILES['trades'], pd.DataFrame(
        columns=CONFIRMED_SIGNAL_COLUMNS + TRADE_SIM_EXTRA_COLUMNS
    ))
    write_csv(output_dir / OUTPUT_FILES['portfolio'], pd.DataFrame(columns=[
        'rule', 'exit_horizon', 'requested_satellite_position_ratio',
        'effective_satellite_position_ratio', 'final_nav_proxy',
        'total_return_proxy', 'max_drawdown_proxy', 'trade_count',
        'turnover', 'avg_holding_days', 'core_profit', 'satellite_profit',
        'replacement_count', 'replaced_profit_after_sell',
        'new_position_profit_after_buy',
    ]))
    write_csv(output_dir / OUTPUT_FILES['full_compound'], _empty_full_compound_summary())


def run(args):
    workdir = Path(args.workdir).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else workdir
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log).resolve() if args.log else auto_find_log(workdir)

    records = load_records(log_path)
    buy_df = event_frame(records, 'BIGMEAT_BUY')
    hold_df = event_frame(records, 'HOLD_SNAPSHOT')
    trade_close_df = event_frame(records, 'TRADE_CLOSE')
    candidate_df = normalize_candidate_rows(records)
    candidate_df = mark_bought_and_holding(candidate_df, buy_df, hold_df)
    watch_df = build_watch_pool(candidate_df, source=args.watch_source, expire_days=args.expire_days)

    if args.full and not JQDATA_AVAILABLE:
        print('SHADOW_ROTATION_ERROR|market_api_unavailable=1|log={}|candidates={}|watch={}'.format(
            log_path, len(candidate_df), len(watch_df)
        ))
        return None

    if not args.full:
        output_empty_files(output_dir, candidate_df, watch_df)
        print('SHADOW_ROTATION|mode=dry_run|jqdata_available={}|log={}|candidates={}|watch={}'.format(
            int(JQDATA_AVAILABLE), log_path, len(candidate_df), len(watch_df)
        ))
        print('SHADOW_ROTATION|note=Run inside JoinQuant research with --full to fetch prices and complete signal/portfolio simulation.')
        return

    all_dates = sorted(set(candidate_df['date'].dropna().astype(str).tolist()))
    start_date = (datetime.strptime(min(all_dates), '%Y-%m-%d') - timedelta(days=40)).date().isoformat()
    end_date = (datetime.strptime(max(all_dates), '%Y-%m-%d') + timedelta(days=10)).date().isoformat()
    stocks = sorted(set(watch_df['stock'].dropna().astype(str).tolist()))
    trade_days = get_research_trade_days(start_date, end_date, fallback_dates=all_dates)
    price_df, high_limit_meta = fetch_price_data(
        stocks, start_date, end_date, include_high_limit=args.include_high_limit
    )
    watch_df = enrich_watch_prices(watch_df, price_df)
    confirmed_df, confirm_meta = build_confirmed_signals(watch_df, price_df, trade_days)
    confirmed_df = ensure_signal_metadata(confirmed_df, watch_df)
    trade_sim_df = attach_returns(confirmed_df, price_df, trade_close_df, trade_days)
    trade_sim_df = ensure_signal_metadata(trade_sim_df, watch_df)
    rule_summary_df = summarize_rules(trade_sim_df)
    refined_summary_df = build_refined_rule_summary(trade_sim_df)
    portfolio_summary_df = build_portfolio_summary(trade_sim_df, price_df, trade_days)
    full_compound_df, risk_meta = build_full_compound_summary(
        trade_sim_df, price_df, trade_days, records
    )
    high_limit_meta.update(confirm_meta)

    write_csv(output_dir / OUTPUT_FILES['candidates'], candidate_df)
    write_csv(output_dir / OUTPUT_FILES['watch'], watch_df)
    write_csv(output_dir / OUTPUT_FILES['confirmed'], confirmed_df)
    write_csv(output_dir / OUTPUT_FILES['rules'], rule_summary_df)
    write_csv(output_dir / OUTPUT_FILES['refined_rules'], refined_summary_df)
    write_csv(output_dir / OUTPUT_FILES['trades'], trade_sim_df)
    write_csv(output_dir / OUTPUT_FILES['portfolio'], portfolio_summary_df)
    write_csv(output_dir / OUTPUT_FILES['full_compound'], full_compound_df)
    run_meta = {
        'jqdata_available': 1,
        'log_path': str(log_path),
        'candidate_count': len(candidate_df),
        'watch_count': len(watch_df),
        'confirmed_count': len(confirmed_df),
        'sim_trade_count': len(trade_sim_df),
    }
    expected_excel_meta = {
        'excel_export_ok': 1,
        'excel_path': str(output_dir / OUTPUT_FILES['excel']),
        'excel_error': '',
    }
    diagnostics_df = build_diagnostics_df(
        run_meta, risk_meta, high_limit_meta, expected_excel_meta
    )
    excel_meta = write_excel_bundle(output_dir, {
        '1_rule_original': rule_summary_df,
        '2_rule_refined': refined_summary_df,
        '3_portfolio_original': portfolio_summary_df,
        '4_portfolio_full': full_compound_df,
        '5_trade_sim': trade_sim_df,
        '6_confirmed': confirmed_df,
        '7_watch': watch_df,
        '8_candidates': candidate_df,
        '9_diagnostics': diagnostics_df,
    })
    if not excel_meta.get('excel_export_ok'):
        diagnostics_df = build_diagnostics_df(run_meta, risk_meta, high_limit_meta, excel_meta)
    report_path = write_markdown_report(
        output_dir, run_meta, rule_summary_df, refined_summary_df,
        full_compound_df, risk_meta, high_limit_meta, excel_meta
    )
    print('SHADOW_ROTATION|mode=full|jqdata_available=1|log={}|candidates={}|watch={}|confirmed={}|sim_trades={}'.format(
        log_path, len(candidate_df), len(watch_df), len(confirmed_df), len(trade_sim_df)
    ))
    print('SHADOW_ROTATION_HIGH_LIMIT|requested={}|available={}|non_null={}|limit_up_filtered={}'.format(
        high_limit_meta.get('include_high_limit_requested'),
        high_limit_meta.get('high_limit_available'),
        high_limit_meta.get('high_limit_non_null_count'),
        high_limit_meta.get('limit_up_filtered_count'),
    ))
    print('SHADOW_ROTATION_RISK_OFF|available={}|risk_off_dates={}'.format(
        risk_meta.get('risk_off_available'), risk_meta.get('risk_off_dates_count')
    ))
    print('SHADOW_ROTATION_REPORT|path={}'.format(report_path))
    return {
        'candidate_df': candidate_df,
        'watch_df': watch_df,
        'confirmed_df': confirmed_df,
        'trade_sim_df': trade_sim_df,
        'rule_summary_df': rule_summary_df,
        'refined_summary_df': refined_summary_df,
        'portfolio_summary_df': portfolio_summary_df,
        'full_compound_df': full_compound_df,
        'diagnostics_df': diagnostics_df,
        'high_limit_meta': high_limit_meta,
        'excel_meta': excel_meta,
        'risk_meta': risk_meta,
        'report_path': report_path,
    }


def run_full(workdir='.', log_path='jq_v121A_20250701_20260614.log.txt',
             output_dir='.', include_high_limit=False):
    """Notebook-friendly full run wrapper.

    Equivalent to command-line full mode. In JoinQuant notebooks, run
    "from jqdata import *" first, then use "%run -i" or call run_full().
    """
    args = argparse.Namespace(
        workdir=workdir,
        log=log_path,
        output_dir=output_dir,
        watch_source='BIGMEAT_POOL_TOP',
        expire_days=3,
        full=True,
        include_high_limit=include_high_limit,
    )
    return run(args)


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description='Research-only WATCH_POOL and 2+2 satellite rotation analyzer.'
    )
    parser.add_argument('--workdir', default='.', help='Project directory.')
    parser.add_argument('--log', default=None, help='Exported JoinQuant log txt/zip path.')
    parser.add_argument('--output-dir', default=None, help='CSV output directory.')
    parser.add_argument('--watch-source', default='BIGMEAT_POOL_TOP',
                        choices=['BIGMEAT_POOL_TOP', 'AUCTION_PREFILTER_TOP'])
    parser.add_argument('--expire-days', type=int, default=3)
    parser.add_argument('--full', action='store_true',
                        help='Fetch JoinQuant prices and run full signal/portfolio simulation.')
    parser.add_argument('--include-high-limit', action='store_true',
                        help='Also request high_limit if the JoinQuant environment supports it.')
    return parser


if __name__ == '__main__':
    run(build_arg_parser().parse_args())
