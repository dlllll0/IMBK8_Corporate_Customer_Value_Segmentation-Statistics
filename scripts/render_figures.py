"""Render only reviewed aggregates. Requires a new destination directory."""
from pathlib import Path
import argparse
import json
import os
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager


def render(summary, destination):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    fonts={f.name for f in font_manager.fontManager.ttflist}
    font=next((name for name in ['Malgun Gothic','Noto Sans CJK KR','NanumGothic'] if name in fonts),None)
    if font is None:
        raise RuntimeError('Install a Korean font before rendering figures')
    plt.rcParams.update({'font.family':font,'axes.unicode_minus':False,'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#ffffff','axes.titleweight':'bold'})
    current=summary['latest']
    period=f"{current['month']//100}.{current['month']%100:02d}"
    fig,ax=plt.subplots(figsize=(9,4.6),layout='constrained')
    values=[100*current['target_row_share_regular'],100*current['target_proxy_share_regular']]
    bars=ax.barh(['관측 행 비중','추정 수익 기여 비중'],values,color=['#718096','#087f8c'],height=.48)
    ax.invert_yaxis();ax.set_xlim(0,max(values)*1.25);ax.set_xlabel('정규 분석군 내 비중 (%)')
    ax.set_title('일반 등급 알짜: 관측 비중과 추정 기여 비중',loc='left',pad=18)
    for bar,val in zip(bars,values):ax.text(val+.15,bar.get_y()+bar.get_height()/2,f'{val:.2f}%',va='center',fontweight='bold')
    fig.supxlabel(f"{period} · 정규 분석군 {current['regular']['rows']:,}행 기준 · 노트북 산식상 추정치, 실제 순이익 아님",fontsize=9)
    fig.savefig(destination/'contribution-share.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5.4),layout='constrained')
    labels=['일반 등급 알짜','대출 이용','대출 이용 + 당월 카드 미이용','위 후보 중 신용카드 보유']
    values=[current['target']['rows'],current['target_loan_use_rows'],current['loan_and_no_card_use_candidate_rows'],current['candidate_credit_card_positive_count_rows']]
    bars=ax.barh(labels,values,color=['#b8c6d1','#879dae','#48788f','#087f8c'],height=.58)
    ax.invert_yaxis();ax.set_xlim(0,max(values)*1.16);ax.set_xlabel('관측 행 수')
    ax.set_title('상품 연계 후보를 구체적인 이용 재개 대상으로 좁히기',loc='left',pad=18)
    for bar,val in zip(bars,values):ax.text(val+6,bar.get_y()+bar.get_height()/2,f'{val:,}',va='center',fontweight='bold')
    fig.supxlabel(f'{period} · 원노트북 오류 수정 후 · 고유 고객 수·접촉 가능 여부는 별도 확인 필요',fontsize=9)
    fig.savefig(destination/'action-candidates.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    cases=summary['scenario']['cases'];values=[x['one_month_net_gain_assumption_krw']/10000 for x in cases]
    labels=[f"{100*x['incremental_conversion_assumption']:.0f}%p" for x in cases]
    bars=ax.bar(labels,values,color=['#c06b5a','#718096','#087f8c'],width=.5)
    ax.axhline(0,color='#334155',linewidth=.8)
    ax.set_ylabel('1개월 순증 이익 가정 (만원)');ax.set_xlabel('대조군 대비 추가 활성률 가정')
    ax.set_ylim(min(values)-7,max(values)+10)
    ax.set_title('실제 성과가 아닌, 실행 판단을 위한 손익 시나리오',loc='left',pad=18)
    for bar,val in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,val+(1 if val>=0 else -1),f'{val:,.2f}',ha='center',va='bottom' if val>=0 else 'top',fontweight='bold')
    scenario=summary['scenario']
    ax.text(.03,.94,f"손익분기 추가 활성률 {100*scenario['break_even_incremental_conversion_assumption']:.2f}%p",transform=ax.transAxes,color='#334155')
    contacts=cases[0]['candidate_rows_used_as_contact_slots_assumption']
    cost=scenario['contact_cost_per_slot_krw_assumption']/1000
    gain=scenario['incremental_contribution_per_activation_krw_assumption']/10000
    fig.supxlabel(f'예시 가정: {contacts}개 접촉 · 접촉당 {cost:g}천 원 · 추가 활성당 월 순기여 {gain:g}만 원 · 추가 고정비 0원',fontsize=9)
    fig.savefig(destination/'break-even-scenarios.png',dpi=180);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    render(json.loads(args.summary.read_text(encoding='utf-8')),args.output_dir)
    print('PASS: three aggregate-only figures generated')
