"""Aggregate-only statistics and business extensions to the original notebook."""
import numpy as np
import pandas as pd
from scipy import stats
import scikit_posthocs as sp
from statsmodels.stats.outliers_influence import variance_inflation_factor


def target_mask(frame):
    return (frame['등급'] == '알짜(Cash Cow)') & (frame['법인_고객등급'] == '일반')


def build_summary(raw, nonzero, analysis, extreme):
    """Return aggregates only; no client identifiers, rows or location cross-tabs."""
    cc = analysis[analysis['등급'] == '알짜(Cash Cow)']
    general = analysis[target_mask(analysis)]
    latest_month = int(analysis['기준년월'].max())
    latest = analysis[analysis['기준년월'] == latest_month]
    target = latest[target_mask(latest)]
    nonusers = target[target['총디지털거래건수'] == 0]
    card_candidate = target[(target['대출이용'] == 1) & (target['카드이용'] == 0)]
    reactivation = card_candidate[card_candidate['신용카드개수'] > 0]
    latest_nonzero = nonzero[nonzero['기준년월'] == latest_month]
    def test_groups(frame, group, value, fn):
        return fn(*[x[value].to_numpy() for _, x in frame.groupby(group)])
    def result(test):
        return {'statistic': float(test.statistic), 'p_value': float(test.pvalue)}
    dunn = sp.posthoc_dunn(cc, val_col='FPI', group_col='법인_고객등급', p_adjust='bonferroni')
    user = general.loc[general['총디지털거래건수'] > 0, 'FPI']
    nonuser = general.loc[general['총디지털거래건수'] == 0, 'FPI']
    digital_test = stats.mannwhitneyu(user, nonuser, alternative='two-sided')
    general_fpi, excellent_fpi = cc.loc[cc['법인_고객등급']=='일반','FPI'], cc.loc[cc['법인_고객등급']=='우수','FPI']
    pair = stats.mannwhitneyu(general_fpi, excellent_fpi, alternative='two-sided')
    tests = {
        'alpha': .05,
        'old_grade_FPI_kruskal': result(test_groups(analysis,'법인_고객등급','FPI',stats.kruskal)),
        'new_grade_FPI_kruskal': result(test_groups(analysis,'등급','FPI',stats.kruskal)),
        'new_grade_FAI_kruskal_corrected': result(test_groups(analysis,'등급','FAI',stats.kruskal)),
        'old_grade_margin_levene': result(test_groups(analysis,'법인_고객등급','예대마진',stats.levene)),
        'cashcow_FPI_levene': result(test_groups(cc,'법인_고객등급','FPI',stats.levene)),
        'cashcow_FPI_kruskal': result(test_groups(cc,'법인_고객등급','FPI',stats.kruskal)),
        'cashcow_FPI_dunn_bonferroni': dunn.to_dict(),
        'cashcow_general_excellent_rank_biserial_added': float(2*pair.statistic/(len(general_fpi)*len(excellent_fpi))-1),
        'digital_FPI_mannwhitney': result(digital_test),
        'digital_rank_biserial_added': float(2*digital_test.statistic/(len(user)*len(nonuser))-1),
    }
    for label in ['일반(Standard)', '잠재(Potential)']:
        tests['cashcow_margin_greater_than_'+label] = result(stats.mannwhitneyu(cc['예대마진'],analysis.loc[analysis['등급']==label,'예대마진'],alternative='greater'))
    vif_cols=['총예금잔액','총대출잔액','총채널거래금액','총외환금액','총카드사용금액','총채널거래건수','총외환거래건수','다양성점수']
    vif = {col:float(variance_inflation_factor(analysis[vif_cols].to_numpy(),i)) for i,col in enumerate(vif_cols)}
    def cohort(x):
        return {'rows':len(x),'income_proxy_million_krw':float(x['총수익'].sum()),'margin_proxy_million_krw':float(x['예대마진'].sum()),'fee_proxy_million_krw':float(x['추정_비이자수익'].sum()),'income_proxy_median_million_krw':float(x['총수익'].median())}
    n_branch=int((nonusers['창구거래건수']>0).sum())
    # Suppress a small cohort in public summaries; private audit retains its source evidence.
    branch_display=str(n_branch) if n_branch>=10 else '<10'
    current = {
        'month':latest_month,'raw_rows':int((raw['기준년월']==latest_month).sum()),
        'regular':cohort(latest),'nonzero_including_extreme':cohort(latest_nonzero),'target':cohort(target),
        'target_row_share_regular':len(target)/len(latest),
        'target_proxy_share_regular':float(target['총수익'].sum()/latest['총수익'].sum()),
        'target_proxy_share_nonzero':float(target['총수익'].sum()/latest_nonzero['총수익'].sum()),
        'target_digital_nonuser_rows':len(nonusers),'target_zero_channel_rows':int((target['총채널거래건수']==0).sum()),
        'nonuser_with_branch_activity_rows_display':branch_display,
        'target_dedicated_manager_rows':int((target['전담고객여부']=='Y').sum()),
        'target_loan_use_rows':int(target['대출이용'].sum()),'target_card_use_rows':int(target['카드이용'].sum()),
        'loan_and_no_card_use_candidate_rows':len(card_candidate),
        'candidate_dedicated_manager_rows':int((card_candidate['전담고객여부']=='Y').sum()),
        'candidate_credit_card_zero_count_rows':int((card_candidate['신용카드개수']==0).sum()),
        'candidate_credit_card_positive_count_rows':int((card_candidate['신용카드개수']>0).sum()),
        'reactivation_dedicated_manager_rows':int((reactivation['전담고객여부']=='Y').sum()),
        'segments':{name:cohort(x) for name,x in latest.groupby('등급')},
    }
    # Sensitivity only: same retrospective fitted feature scales, change the FPI weight.
    base=set(target.index); sensitivity=[]
    for weight in [.4,.5,.6]:
        fpi=weight*analysis['수익기여점수']+(1-weight)*analysis['수익효율점수']
        selected=analysis[(analysis['FAI']<analysis['FAI'].median())&(fpi>=fpi.median())&(analysis['법인_고객등급']=='일반')&(analysis['기준년월']==latest_month)]
        ids=set(selected.index)
        sensitivity.append({'contribution_weight':weight,'efficiency_weight':1-weight,'latest_target_rows':len(ids),'baseline_overlap_rows':len(ids&base),'jaccard':len(ids&base)/len(ids|base)})
    # Illustrative one-month economics: assumptions, NOT estimates from this dataset.
    n=len(reactivation); unit_gain=30000; contact_cost=1000
    scenarios=[{'incremental_conversion_assumption':r,'candidate_rows_used_as_contact_slots_assumption':n,'expected_incremental_activations':n*r,'one_month_net_gain_assumption_krw':n*r*unit_gain-n*contact_cost} for r in [.02,.05,.10]]
    summary={
        'basis':'Notebook-derived recomputation; new business extensions explicitly separated',
        'data':{'rows':len(raw),'variables':len(raw.columns),'first_month':int(raw['기준년월'].min()),'last_month':latest_month,'months':int(raw['기준년월'].nunique()),'exact_duplicate_rows_retained':int(raw.duplicated().sum()),'has_stable_customer_id':False,'nonzero_balance_rows':len(nonzero),'extreme_rows':len(extreme),'analysis_rows':len(analysis)},
        'segments':analysis['등급'].value_counts().to_dict(),
        'cutoffs':{'FAI':float(analysis.FAI.median()),'FPI':float(analysis.FPI.median())},
        'cashcow_grade_FPI_median':cc.groupby('법인_고객등급').FPI.median().to_dict(),
        'historical_target':{'rows':len(general),'digital_nonuser_rows':len(nonuser)},
        'tests':tests,'VIF_activity_no_intercept_original':vif,'latest':current,'sensitivity':sensitivity,
        'scenario':{'horizon':'one month','status':'illustrative assumptions, not observed profit or bank estimates','incremental_contribution_per_activation_krw_assumption':unit_gain,'contact_cost_per_slot_krw_assumption':contact_cost,'break_even_incremental_conversion_assumption':contact_cost/unit_gain,'cases':scenarios},
    }
    # Independent arithmetic controls against cohort membership.
    assert len(nonzero)==len(analysis)+len(extreme)
    assert sum(x['rows'] for x in current['segments'].values())==len(latest)
    assert np.isclose(sum(x['income_proxy_million_krw'] for x in current['segments'].values()),latest['총수익'].sum())
    assert current['candidate_credit_card_zero_count_rows']+current['candidate_credit_card_positive_count_rows']==len(card_candidate)
    return summary
