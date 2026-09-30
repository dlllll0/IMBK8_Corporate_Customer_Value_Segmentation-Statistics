"""Notebook-derived segmentation. Reads local inputs; never exports observation rows.

The income proxy preserves the original notebook formulas. It is not audited profit.
See docs/methodology.md for corrections and source-cell mapping.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler


def load_inputs(transactions, rates, fees):
    paths = [Path(p).resolve() for p in (transactions, rates, fees)]
    if not all(p.is_file() for p in paths):
        raise FileNotFoundError('Three authorized local CSV inputs are required')
    df = pd.read_csv(paths[0], encoding='cp949')
    schema = json.loads((Path(__file__).resolve().parents[1] / 'docs/input-schema.json').read_text(encoding='utf-8'))
    required = schema['files']['corporate_transactions.csv']['required_columns']
    if set(required) != set(df.columns):
        raise ValueError('Unexpected transaction schema; review before analysis')
    # Location missing values are handled by the original notebook rules.
    if df.drop(columns=['사업장_시도', '사업장_시군구']).isna().any().any():
        raise ValueError('Unexpected missing input; do not silently impute')
    return df, pd.read_csv(paths[1], encoding='utf-8-sig'), pd.read_csv(paths[2], encoding='utf-8-sig')


def build_analysis(df, df_b, fee_df):
    """Return nonzero-balance, regular and extreme cohorts in memory only."""
    df, df_b, fee_df = df.copy(), df_b.copy(), fee_df.copy()
    # 원본 가설 노트북 셀 5
    count_mapping = {'0건': 0, '1건': 1, '2건': 2, '2건초과 5건이하': 3.5, '5건초과 10건이하': 7.5, '10건초과 20건이하': 15, '20건초과 30건이하': 25, '30건초과 40건이하': 35, '40건초과 50건이하': 45, '50건 초과': 55}
    channel_count_cols = ['인터넷뱅킹거래건수', '스마트뱅킹거래건수', '폰뱅킹거래건수', '자동이체거래건수', '창구거래건수', 'ATM거래건수', '외환_수출실적거래건수', '외환_수입실적거래건수']
    for col in channel_count_cols:
        if col in df.columns:
            unknown = set(df[col].dropna().unique()) - set(count_mapping)
            if unknown:
                raise ValueError('Unmapped transaction count category')
            df[col] = df[col].map(count_mapping)
    account_mapping = {'0개': 0, '1개': 1, '2개': 2, '2개초과 5개이하': 4, '5개초과 10개이하': 8, '10개초과 20개이하': 15.5, '20개초과 30개이하': 25.5, '30개초과 40개이하': 35.5, '40개초과 50개이하': 45.5, '50개 초과': 55}
    account_count_cols = ['요구불예금좌수', '거치식예금좌수', '적립식예금좌수', '수익증권좌수', '신탁좌수', '퇴직연금좌수', '여신_운전자금대출좌수', '여신_시설자금대출좌수', '신용카드개수']
    for col in account_count_cols:
        if col in df.columns:
            unknown = set(df[col].dropna().unique()) - set(account_mapping)
            if unknown:
                raise ValueError('Unmapped account count category')
            df[col] = df[col].map(account_mapping)

    # 원본 가설 노트북 셀 6
    deposit_bal_cols = ['요구불예금잔액', '거치식예금잔액', '적립식예금잔액']
    product_bal_cols = ['수익증권잔액', '신탁잔액']
    deposit_cnt_cols = ['요구불예금좌수', '거치식예금좌수', '적립식예금좌수']
    product_cnt_cols = ['수익증권좌수', '신탁좌수', '퇴직연금좌수']
    flow_cols = ['요구불입금금액', '요구불출금금액']
    loan_bal_cols = ['여신_운전자금대출잔액', '여신_시설자금대출잔액']
    loan_cnt_cols = ['여신_운전자금대출좌수', '여신_시설자금대출좌수']
    rjfo_total = ['인터넷뱅킹거래금액', '폰뱅킹거래금액', '스마트뱅킹거래금액', '창구거래금액', 'ATM거래금액']
    rjfo_digital = ['인터넷뱅킹거래금액', '폰뱅킹거래금액', '스마트뱅킹거래금액']
    rjfo_offline = ['창구거래금액', 'ATM거래금액']
    rjfo_card_total = ['신용카드사용금액', '체크카드사용금액']
    channel_cnt_cols = ['창구거래건수', '인터넷뱅킹거래건수', '스마트뱅킹거래건수', '폰뱅킹거래건수', 'ATM거래건수']
    dhlghks = ['외환_수출실적금액', '외환_수입실적금액']

    # 원본 가설 노트북 셀 7
    df['총예금잔액'] = df[deposit_bal_cols].sum(axis=1)
    df['자산관리잔액'] = df[product_bal_cols].sum(axis=1)
    df['총대출잔액'] = df[loan_bal_cols].sum(axis=1)
    df['총예금좌수'] = df[deposit_cnt_cols].sum(axis=1)
    df['총대출좌수'] = df[loan_cnt_cols].sum(axis=1)
    df['자산관리좌수'] = df[product_cnt_cols].sum(axis=1)
    df['총요구불입출금'] = df[flow_cols].sum(axis=1)
    df['전체거래액'] = df[rjfo_total].sum(axis=1)
    df['총디지털거래액'] = df[rjfo_digital].sum(axis=1)
    df['총오프라인거래액'] = df[rjfo_offline].sum(axis=1)
    df['총카드소비'] = df[rjfo_card_total].sum(axis=1)
    df['총외환실적'] = df[dhlghks].sum(axis=1)

    # 원본 가설 노트북 셀 8
    cols_to_use = ['기준년월', '평균대출금리(%)', '평균예금금리(%)', '예대마진(%)']
    df_b_subset = df_b[cols_to_use]
    df2 = pd.merge(df, df_b_subset, on='기준년월', how='left', validate='many_to_one')

    # 원본 가설 노트북 셀 9
    fee_df = fee_df.dropna(how='all').copy()
    fee_df.columns = fee_df.columns.str.strip()
    target_fee_cols = ['신탁보수율(trust)', '카드수수료율(card)', '수익증권/연금(fund)', '외환/기타(fx)', '채널건당(channel)', '연도(year)']
    df2 = df2.drop(columns=[c for c in target_fee_cols if c in df2.columns])
    try:
        df2['연도_join'] = df2['기준년월'].astype(int) // 100
    except:
        df2['연도_join'] = df2['기준년월'].astype(str).str[:4].astype(int)
    df2 = pd.merge(df2, fee_df, left_on='연도_join', right_on='연도(year)', how='left', validate='many_to_one')
    if df2[['신탁보수율(trust)', '카드수수료율(card)', '수익증권/연금(fund)', '외환/기타(fx)']].isna().any().any():
        raise ValueError('Missing fee rate for observation year')
    df2['수익증권수익'] = df2['수익증권잔액'] * df2['수익증권/연금(fund)']
    df2['신탁수익'] = df2['신탁잔액'] * df2['신탁보수율(trust)']
    df2['외환수익'] = (df2['외환_수출실적금액'] + df2['외환_수입실적금액']) * df2['외환/기타(fx)']
    df2['카드수익'] = (df2['신용카드사용금액'] + df2['체크카드사용금액']) * df2['카드수수료율(card)']
    df2['추정_비이자수익'] = df2['수익증권수익'].fillna(0) + df2['신탁수익'].fillna(0) + df2['외환수익'].fillna(0) + df2['카드수익'].fillna(0)
    df2 = df2.drop(columns=['연도_join', '연도(year)'])

    # 원본 가설 노트북 셀 10
    if df2[['평균대출금리(%)', '평균예금금리(%)']].isna().any().any():
        raise ValueError('Missing monthly interest rate')
    df2['총자산'] = df2['총예금잔액'] + df2['총대출잔액'] + df2['자산관리잔액']
    df2['예금이자'] = df2['총예금잔액'] * df2['평균예금금리(%)'] * 0.01
    df2['대출이자'] = df2['총대출잔액'] * df2['평균대출금리(%)'] * 0.01
    df2['예대마진'] = df2['대출이자'] - df2['예금이자']
    df2['예대마진수익률(%)'] = (df2['대출이자'] - df2['예금이자']) / df2['총자산'] * 100
    df2['이자+비이자수익'] = df2['예대마진'] + df2['추정_비이자수익']
    df2['자산대비수익률(%)'] = df2['이자+비이자수익'] / df2['총자산'] * 100

    # 원본 가설 노트북 셀 11
    df2.loc[df2['사업장_시도'] == '세종특별자치시', '사업장_시군구'] = '세종시'
    df2['사업장_시도'] = df2['사업장_시도'].fillna('미상')
    df2['사업장_시군구'] = df2['사업장_시군구'].fillna('미상')
    sejong_check = df2[df2['사업장_시도'] == '세종특별자치시']['사업장_시군구'].unique()

    # 원본 가설 노트북 셀 12
    df2 = df2.rename(columns={'평균대출금리(%)': '월평균대출금리(%)', '평균예금금리(%)': '월평균예금금리(%)', '예대마진(%)': '기준예대마진(%)', '이자+비이자수익': '총수익', '예금이자': '기준예금이자', '대출이자': '기준대출이자'})

    # 원본 가설 노트북 셀 15
    df2 = df2[df2['총자산'] != 0].copy()

    # 원본 가설 노트북 셀 19
    df2['총채널거래금액'] = df2['전체거래액']
    df2['총채널거래건수'] = df2[channel_cnt_cols].sum(axis=1)
    df2['총거래건수'] = df2['총채널거래건수'] + df2[['외환_수출실적거래건수', '외환_수입실적거래건수']].sum(axis=1)
    df2['총디지털거래건수'] = df2[['인터넷뱅킹거래건수', '스마트뱅킹거래건수', '폰뱅킹거래건수']].sum(axis=1)
    df2['디지털거래건수비중'] = np.where(df2['총거래건수'] > 0, df2['총디지털거래건수'] / df2['총거래건수'], 0)
    df2['총외환금액'] = df2['총외환실적']
    df2['총외환거래건수'] = df2[['외환_수출실적거래건수', '외환_수입실적거래건수']].sum(axis=1)
    df2['총카드사용금액'] = df2['총카드소비']
    df2['예금이용'] = (df2['총예금잔액'] > 0).astype(int)
    df2['대출이용'] = (df2['총대출잔액'] > 0).astype(int)
    df2['카드이용'] = (df2['총카드사용금액'] > 0).astype(int)
    df2['외환이용'] = (df2['총외환금액'] > 0).astype(int)
    df2['상품다양성개수'] = df2[['예금이용', '대출이용', '카드이용', '외환이용']].sum(axis=1)
    df2['다양성점수'] = df2['상품다양성개수'] / 4

    # 원본 가설 노트북 셀 27
    key_vars = ['총자산', '여신한도금액', '전체거래액', '총수익']

    # 원본 가설 노트북 셀 28
    is_vvvip_condition = pd.Series(False, index=df2.index)
    for var in key_vars:
        Q1 = df2[var].quantile(0.25)
        Q3 = df2[var].quantile(0.75)
        IQR = Q3 - Q1
        upper_whisker = Q3 + 3.0 * IQR
        lower_whisker = Q1 - 3.0 * IQR
        is_vvvip_condition = is_vvvip_condition | (df2[var] > upper_whisker) | (df2[var] < lower_whisker)
    vvvip_df2 = df2[is_vvvip_condition].copy()
    analysis_df2 = df2[~is_vvvip_condition].copy()

    # 원본 가설 노트북 셀 46
    def _get_scaler(scaler_type='minmax'):
        if scaler_type == 'minmax':
            return MinMaxScaler()
        if scaler_type == 'standard':
            return StandardScaler()
        raise ValueError("scaler_type은 'minmax' 또는 'standard'만 지원합니다.")

    def _scale_series(series, scaler_type='minmax', log_transform=True):
        values = pd.to_numeric(series, errors='coerce').astype(float)
        if log_transform:
            finite_values = values[np.isfinite(values)]
            if not finite_values.empty:
                min_val = finite_values.min()
                if min_val < 0:
                    values = np.log1p(values - min_val)
                else:
                    values = np.log1p(values)
        scaler = _get_scaler(scaler_type)
        scaled = scaler.fit_transform(values.to_frame()).reshape(-1)
        return pd.Series(scaled, index=series.index)

    # 원본 가설 노트북 셀 47
    size_vars = ['총예금잔액', '총대출잔액', '총채널거래금액', '총외환금액', '총카드사용금액']
    freq_vars = ['총채널거래건수', '총외환거래건수']
    diversity_vars = ['다양성점수']
    contrib_vars = ['예대마진', '추정_비이자수익']
    eff_vars = ['자산대비수익률(%)']

    # 원본 가설 노트북 셀 48
    for col in size_vars + freq_vars:
        analysis_df2[f'{col}_score'] = _scale_series(analysis_df2[col], scaler_type='minmax', log_transform=True)
    for col in contrib_vars:
        analysis_df2[f'{col}_score'] = _scale_series(analysis_df2[col], scaler_type='minmax', log_transform=True)
    for col in eff_vars + diversity_vars:
        col_name = '다양성점수' if col == '다양성점수' else col
        analysis_df2[f'{col_name}_score'] = _scale_series(analysis_df2[col], scaler_type='minmax', log_transform=False)
    analysis_df2['규모점수'] = analysis_df2[[f'{c}_score' for c in size_vars]].mean(axis=1)
    analysis_df2['빈도점수'] = analysis_df2[[f'{c}_score' for c in freq_vars]].mean(axis=1)
    analysis_df2['FAI'] = (analysis_df2['규모점수'] + analysis_df2['빈도점수'] + analysis_df2['다양성점수_score']) / 3
    analysis_df2['수익기여점수'] = analysis_df2[[f'{c}_score' for c in contrib_vars]].mean(axis=1)
    analysis_df2['수익효율점수'] = analysis_df2[[f'{c}_score' for c in eff_vars]].mean(axis=1)
    analysis_df2['FPI'] = (analysis_df2['수익기여점수'] + analysis_df2['수익효율점수']) / 2

    # 원본 가설 노트북 셀 52
    fai_cutoff = analysis_df2['FAI'].median()
    fpi_cutoff = analysis_df2['FPI'].median()

    def get_segment(row):
        if row['FAI'] >= fai_cutoff and row['FPI'] >= fpi_cutoff:
            return '스타(Star)'
        elif row['FAI'] < fai_cutoff and row['FPI'] >= fpi_cutoff:
            return '알짜(Cash Cow)'
        elif row['FAI'] >= fai_cutoff and row['FPI'] < fpi_cutoff:
            return '잠재(Potential)'
        else:
            return '일반(Standard)'
    analysis_df2['등급'] = analysis_df2.apply(get_segment, axis=1)
    if not np.isfinite(analysis_df2[['FAI', 'FPI', '총수익']]).all().all():
        raise ValueError('Nonfinite final indicators')
    return df2, analysis_df2, vvvip_df2
