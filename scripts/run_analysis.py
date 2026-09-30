"""Run locally on authorized CSVs; write one aggregate JSON to a NEW output path."""
from pathlib import Path
import argparse
import json
import sys
import os

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
sys.path.insert(0,str(ROOT/'src'))
from segmentation import load_inputs,build_analysis
from insights import build_summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['transactions','rates','fees','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists():
        parser.error('Output already exists; choose a new path to preserve previous results')
    frames=load_inputs(args.transactions,args.rates,args.fees)
    nonzero,analysis,extreme=build_analysis(*frames)
    summary=build_summary(frames[0],nonzero,analysis,extreme)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:
        json.dump(summary,f,ensure_ascii=False,indent=2,allow_nan=False)
    print('PASS: aggregate analysis complete. No observation rows exported.')


if __name__=='__main__':
    main()
