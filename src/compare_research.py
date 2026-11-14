"""Build a source-attributed related-work comparison without changing experiment results."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json


def markdown_table(headers, rows):
    def safe(value):
        return str(value).replace('|', '/')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',
                      *['| '+' | '.join(safe(value) for value in row)+' |' for row in rows]])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--papers-dir',type=Path)
    args=parser.parse_args()
    project=args.project.resolve()
    output=project/'results/literature_comparison'
    output.mkdir(parents=True,exist_ok=True)
    with (project/'results/final_test/test_metrics.csv').open(newline='') as handle:
        own={row['model']:row for row in csv.DictReader(handle)}
    paper_2017=dict(
        id='10.1109/TEL-NET.2017.8343582',year=2017,
        title='Bank loan analysis using customer usage data: A big data approach using Hadoop',
        doi='10.1109/TEL-NET.2017.8343582',
        file='Bank_loan_analysis_using_customer_usage_data_A_big_data_approach_using_Hadoop.pdf',
        evidence='PDF pp. 3–7, dataset, results and conclusion',
        focus='Historical, descriptive Lending Club loan analysis using Hadoop/HDFS/Hive/HiveQL.',
        findings=[
            'The paper reports debt consolidation as 58.88% of loan purposes (p. 4).',
            'Reported mean interest rates: 11.21% for 36-month loans, 15.32% for 60-month loans, and 12.18% overall (pp. 4, 7).',
            'The paper presents loan-issuance, status and grade-based summaries. It does not report trained-model accuracy, recall, F1 or ROC-AUC for its own analysis.',
        ])
    paper_2025=dict(
        id='10.1109/CISCON66933.2025.11337606',year=2025,
        title='Assessing Fairness and Transparency in Credit Scoring Using Explainable AI',
        doi='10.1109/CISCON66933.2025.11337606',
        file='Assessing_Fairness_and_Transparency_in_Credit_Scoring_Using_Explainable_AI.pdf',
        evidence='PDF p. 3, Section III; pp. 5–6, Section IV and Table V',
        focus='Lending Club classification using Random Forest, LightGBM and XGBoost; SHAP-based interpretation is described.',
        findings=[
            'Table V reports the highest model scores for XGBoost: accuracy 0.8285, recall 0.7425, F1 0.8123 and AUC 0.8988.',
            'LightGBM is close behind in Table V: accuracy 0.8284, recall 0.7412, F1 0.8111 and AUC 0.8981.',
            'The supplied paper describes undersampling and qualitative SHAP feature interpretations. It does not provide numeric home-ownership FPR/recall gaps or a controlled Hive storage/materialization benchmark.',
        ])
    scores=[]
    for name,f1,accuracy,recall,auc in [
        ('Random Forest',.8010,.8180,.7318,.8883),
        ('LightGBM',.8111,.8284,.7412,.8981),
        ('XGBoost',.8123,.8285,.7425,.8988),
    ]:
        scores.append(dict(source='Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606)',model=name,accuracy=accuracy,recall=recall,f1=f1,roc_auc=auc,
                           threshold=None,evidence='Table V, PDF p. 6',provenance='Author-reported; not rerun'))
    for name in ['Logistic Regression','LightGBM']:
        row=own[name]
        scores.append(dict(source='Our project',model=name,accuracy=float(row['accuracy']),recall=float(row['chargeoff_recall']),
                           f1=float(row['f1']),roc_auc=float(row['roc_auc']),threshold=float(row['threshold']),
                           evidence='results/final_test/test_metrics.csv',provenance='Frozen held-out test; 90,615 loans'))
    capabilities=[
        dict(aspect='Main outcome',paper_2017='Historical loan/purpose/grade/status summaries.',paper_2025='Predictive model scores and qualitative SHAP interpretation.',ours='Equivalent-data Hive export benchmark, predictive baselines and group error audit.'),
        dict(aspect='Dataset/cohort',paper_2017='Approximately 1 GB of Lending Club data, Jan 2012–Dec 2016.',paper_2025='Lending Club; exact cohort and split protocol insufficiently specified for a matched rerun.',ours='306,462 resolved 36-month loans, 2012–2014; 90,615-loan test split.'),
        dict(aspect='Predictive models',paper_2017='No trained predictive model evaluated in the reported analysis.',paper_2025='Random Forest, LightGBM and XGBoost.',ours='Dummy baseline, Logistic Regression and LightGBM.'),
        dict(aspect='Class balance / decision rule',paper_2017='Not a predictive classification evaluation.',paper_2025='States undersampling for class balance; discusses NearMiss/Tomek Links. Threshold and split details not fully specified.',ours='Original selected-cohort imbalance retained; validation maximum-F1 rule selects 0.15 for both trained models.'),
        dict(aspect='Input features',paper_2017='Dataset section reports 74 retained attributes for descriptive analysis.',paper_2025='Table II lists 26 predictors plus target; includes interest rate, grade, subgrade and term.',ours='19 model inputs; uses FICO midpoint and credit-history months; does not use interest rate or grades.'),
        dict(aspect='Hive pipeline benchmark',paper_2017='Uses Hive/HiveQL, but no matched CSV/raw-ORC/prepared-ORC timing benchmark is reported.',paper_2025='No Hive storage/materialization benchmark reported.',ours='Five measured exports per pipeline; median 34.96 s (CSV), 30.14 s (raw ORC), 3.35 s (prepared ORC).'),
        dict(aspect='Storage / preparation cost',paper_2017='Dataset size is described; no comparable pipeline cost breakdown reported.',paper_2025='No comparable pipeline storage/preparation experiment reported.',ours='Raw CSV 50.17 MB; raw ORC 5.99 MB; prepared ORC 7.65 MB. Estimated two-stage preparation 37.39 s.'),
        dict(aspect='Quantitative group audit',paper_2017='No group error-rate disparity metrics reported.',paper_2025='Fairness/SHAP discussion, but no numeric group FPR/recall gaps in the supplied paper.',ours='MORTGAGE/RENT/OWN audit: LightGBM FPR gap 23.32 pp and recall gap 25.37 pp. Substantial disparities remain.'),
        dict(aspect='Explainability',paper_2017='Descriptive charts, not individual model explanations.',paper_2025='Describes SHAP-based local/global interpretation and discusses DTI, interest rate and income.',ours='No SHAP or causal feature explanation implemented; this is a limitation relative to the paper’s stated scope.'),
        dict(aspect='Uncertainty / reproducibility',paper_2017='No paired predictive intervals or comparable frozen-model replay reported.',paper_2025='No paired confidence intervals or matched reproducibility package in the supplied paper.',ours='1,000 paired row-bootstrap samples; frozen file fingerprints; equivalent-feature replay and exact metric replay with original row order.'),
        dict(aspect='Execution setting',paper_2017='Cloudera QuickStart 5.8, Hadoop/HDFS and Hive.',paper_2025='Google Colab, 16 GB RAM, Python 3.12.',ours='Single-host WSL2/Docker, Hive 4.2.1, HDFS/YARN/Tez; Python model training outside Hive.'),
    ]
    cautions=[
        'These are side-by-side reported results, not a controlled head-to-head benchmark. We did not reproduce either paper’s full experimental setup.',
        'Cohort, predictor set, target mapping, sampling and split definitions differ or are insufficiently specified. The 2025 paper states undersampling; our test cohort retains its selected natural imbalance (14.13% charged off).',
        'Threshold-dependent accuracy, recall and F1 also depend on decision rules. AUC is threshold-independent; its difference cannot be explained by the 0.15 threshold or imbalance alone.',
        'The 2025 paper’s displayed confusion-matrix totals differ across models: 97,622 for RF/XGBoost and 65,082 for LightGBM (Figures 2–4). Table V is reproduced as author-reported, without silently reconciling those totals or recalculating its metrics.',
        'No claim is made that our model is more accurate than the 2025 models, that our pipeline is 10.44 times faster than either paper, or that our group audit proves fairness.',
    ]
    contribution='Our added work is the controlled equivalent-feature Hive pipeline benchmark, explicit preparation/storage measurements, quantitative home-ownership error audit and reproducibility evidence. Our reported predictive scores are lower than the 2025 paper’s scores, and SHAP is not implemented here.'
    data=dict(papers=[paper_2017,paper_2025],scores=scores,capabilities=capabilities,cautions=cautions,
              contribution=contribution,dataset_reference='wordsforthewise/Lending Club on Kaggle is the data source, not a third research paper with performance results.',
              generated_at_utc=datetime.now(timezone.utc).isoformat(),paper_file_sha256={})
    if args.papers_dir:
        for paper in data['papers']:
            path=args.papers_dir/paper['file']
            if path.is_file():
                data['paper_file_sha256'][paper['file']]=hashlib.sha256(path.read_bytes()).hexdigest()
    (output/'comparison.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    for filename,rows in [('reported_model_scores.csv',scores),('study_comparison.csv',capabilities)]:
        with (output/filename).open('w',newline='',encoding='utf-8') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    score_rows=[[r['source'],r['model'],f"{r['accuracy']:.4f}",f"{r['recall']:.4f}",f"{r['f1']:.4f}",f"{r['roc_auc']:.4f}"] for r in scores]
    section='''### Comparison of the reference papers and our outcomes

The following is a comparison of published findings and our recorded outcomes, not a matched replication. The 2017 study, the 2025 study and our project address different parts of the problem. Kaggle supplies the dataset and is not a third research paper with its own model scores.

#### What the 2017 paper reports

**Bank loan analysis using customer usage data: A big data approach using Hadoop** (paper ID / DOI: 10.1109/TEL-NET.2017.8343582) uses Hadoop/HDFS/Hive to summarize Lending Club data from January 2012 through December 2016 (approximately 1 GB). Their results include loan issuance, purposes, grade-based summaries and loan statuses. For example, they report debt consolidation at 58.88% of purposes and mean interest rates of 11.21% for 36-month loans, 15.32% for 60-month loans and 12.18% overall (PDF pp. 4 and 7). These are descriptive findings, not predictive accuracy. No accuracy, F1, recall or ROC-AUC is reported for a trained model in their own analysis, and no directly comparable pipeline latency is reported. Our project does not reproduce those descriptive statistics on an identical cohort, so no numeric improvement over those statistics is claimed.

#### What the 2025 paper reports, alongside our model results

**Assessing Fairness and Transparency in Credit Scoring Using Explainable AI** (paper ID / DOI: 10.1109/CISCON66933.2025.11337606) reports the following in Table V (PDF p. 6). Our rows come from the frozen test evaluation. All values in this table are fractions, not percentages.

'''+markdown_table(['Study','Model','Accuracy','Recall','F1','ROC-AUC'],score_rows)+'''

The published XGBoost row has the highest reported AUC (0.8988); the paper’s LightGBM AUC is 0.8981. Our LightGBM AUC is 0.6644. Therefore, we do not claim a predictive-score improvement over that paper. Our main comparison is between our own pipelines under shared controls, not a claim that our classifier beats the published models.

#### Differences in scope and implemented evidence

'''+markdown_table(['Aspect','Bank loan analysis using customer usage data: A big data approach using Hadoop (2017; DOI: 10.1109/TEL-NET.2017.8343582)','Assessing Fairness and Transparency in Credit Scoring Using Explainable AI (2025; DOI: 10.1109/CISCON66933.2025.11337606)','Our project'],[[r['aspect'],r['paper_2017'],r['paper_2025'],r['ours']] for r in capabilities])+'''

#### Why these scores cannot establish a fair head-to-head ranking

'''+ '\n\n'.join('- '+note for note in cautions)+'''

The 2025 methods section (PDF p. 3) describes undersampling, NearMiss and Tomek Links, but the exact application order, cohort/split details and final decision thresholds are insufficient for a matched reproduction. Table II also includes predictors such as interest rate, grade, subgrade and term that are not in our 19-feature model. These differences are not proof of an error or leakage in that paper. Our own retrospective issue-date split has a label-availability limitation and must also be stated openly.

**What our project adds:** '''+contribution+'''

Sources: *Bank loan analysis using customer usage data: A big data approach using Hadoop*, DOI 10.1109/TEL-NET.2017.8343582, PDF pp. 3–7; *Assessing Fairness and Transparency in Credit Scoring Using Explainable AI*, DOI 10.1109/CISCON66933.2025.11337606, PDF p. 3 and pp. 5–6/Table V; our `results/final_test/test_metrics.csv` and `results/pipeline_benchmark` files. “Not reported” means no corresponding result was found in the supplied paper; it does not mean a measured value of zero.
'''
    (output/'research_comparison.md').write_text('# Reference paper and project comparison\n\n'+section,encoding='utf-8')
    start='<!-- BEGIN RESEARCH COMPARISON -->'
    end='<!-- END RESEARCH COMPARISON -->'
    report=project/'results/report/project_results.md'
    text=report.read_text(encoding='utf-8')
    block=start+'\n'+section+'\n'+end+'\n\n'
    if start in text:
        text=text[:text.index(start)]+block+text[text.index(end)+len(end):].lstrip('\r\n')
    else:
        text=text.replace('## 3. Dataset, target and cohort',block+'## 3. Dataset, target and cohort',1)
    report.write_text(text,encoding='utf-8')
    # Keep the existing report assembler aware of the new evidence.
    builder=project/'src/build_results_report.py'
    code=builder.read_text(encoding='utf-8')
    hook='''    # Include the source-attributed literature comparison when it is available.
    literature = project / 'results/literature_comparison/research_comparison.md'
    if literature.exists():
        comparison_section = literature.read_text(encoding='utf-8').split('\\n', 2)[-1]
        report = report.replace('## 3. Dataset, target and cohort', comparison_section + '\\n\\n## 3. Dataset, target and cohort', 1)
'''
    if '# Include the source-attributed literature comparison' not in code:
        code=code.replace("    (output / 'project_results.md').write_text(report, encoding='utf-8')",hook+"    (output / 'project_results.md').write_text(report, encoding='utf-8')")
        builder.write_text(code,encoding='utf-8')
    print('Comparison saved:',output)
    print('Report source updated. Frozen models and evaluation files were not changed.')


if __name__=='__main__':
    main()
