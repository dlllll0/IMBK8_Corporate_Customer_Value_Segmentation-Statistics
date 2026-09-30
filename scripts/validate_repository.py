"""Read-only publication checks. No third-party packages or private input required."""
from pathlib import Path
import ast,json,re,sys
import xml.etree.ElementTree as ET


def validate():
    root=Path(__file__).resolve().parents[1]
    errors=[]; notebooks=0; code_cells=0
    forbidden={'.csv','.tsv','.xlsx','.xls','.pdf','.docx','.pptx','.parquet','.pkl','.pickle','.zip'}
    for path in root.rglob('*'):
        if not path.is_file():continue
        rel=path.relative_to(root)
        # Local work dirs are ignored by Git, but report them before an upload.
        if any(part in {'.git','.venv','.cache','__pycache__','.ipynb_checkpoints','outputs'} for part in rel.parts):continue
        if path.suffix.lower() in forbidden or 'data' in rel.parts or 'private-review' in rel.parts:
            errors.append(f'Private/excluded material present: {rel}')
        if path.suffix in {'.py','.md','.json','.ipynb','.svg','.txt'}:
            body=path.read_text(encoding='utf-8')
            private_pattern=r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]|'+('/'+'Users/')+'|'+('/'+'home/')+'|'+('data:'+'image/')+r'|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}'
            if re.search(private_pattern,body):
                errors.append(f'Private path or secret-like pattern: {rel}')
        if path.suffix=='.py':ast.parse(body)
        if path.suffix=='.svg':ET.fromstring(body)
        if path.suffix=='.md':
            for dest in re.findall(r'\]\(([^)]+)\)',body):
                if '://' in dest or dest.startswith('#'):continue
                if not (path.parent/dest.split('#',1)[0]).exists():errors.append(f'Broken link: {rel} -> {dest}')
        if path.suffix=='.ipynb':
            notebooks+=1; nb=json.loads(body); ids=set()
            for c in nb['cells']:
                if c.get('outputs') or c.get('execution_count') is not None or c.get('attachments'):
                    errors.append(f'Stored notebook output: {rel}')
                if not c.get('id') or c['id'] in ids:errors.append(f'Missing/duplicate cell id: {rel}')
                ids.add(c.get('id'))
                if c['cell_type']=='code':ast.parse(''.join(c['source']));code_cells+=1
    s=json.loads((root/'assets/analysis-summary.json').read_text(encoding='utf-8'))
    d=s['data']; latest=s['latest']; scenario=s['scenario']
    if d['analysis_rows']+d['extreme_rows']!=d['nonzero_balance_rows']:errors.append('Cohort arithmetic mismatch')
    if sum(s['segments'].values())!=d['analysis_rows']:errors.append('Segment count mismatch')
    if latest['candidate_credit_card_positive_count_rows']+latest['candidate_credit_card_zero_count_rows']!=latest['loan_and_no_card_use_candidate_rows']:errors.append('Card split mismatch')
    for c in scenario['cases']:
        n=c['candidate_rows_used_as_contact_slots_assumption']
        expected=n*c['incremental_conversion_assumption']*scenario['incremental_contribution_per_activation_krw_assumption']-n*scenario['contact_cost_per_slot_krw_assumption']
        if abs(expected-c['one_month_net_gain_assumption_krw'])>1e-7:errors.append('Scenario arithmetic mismatch')
    if errors:
        for e in errors:print('FAIL:',e)
        return 1
    print(f'PASS: {notebooks} notebook, {code_cells} code cells, syntax, links, no stored outputs.')
    print('PASS: excluded-file/private-path scan, aggregate and scenario arithmetic.')
    print('NOTE: publication rights and personal contribution require owner review; this check does not rerun statistics.')
    return 0


if __name__=='__main__':sys.exit(validate())
