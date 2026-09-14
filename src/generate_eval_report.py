import os
import json
import pandas as pd
import glob
import argparse
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix

def df_to_markdown(df):
    headers = [str(c) for c in df.columns]
    has_index = True
    if has_index:
        headers = [str(df.index.name or "")] + headers
        rows = [[str(idx)] + [str(v) for v in row] for idx, row in df.iterrows()]
    else:
        rows = [[str(v) for v in row] for _, row in df.iterrows()]
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))
    header_str = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_str = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
    row_strs = ["| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |" for row in rows]
    return "\n".join([header_str, sep_str] + row_strs)

def main():
    parser = argparse.ArgumentParser(description="Generate Evaluation Report")
    parser.add_argument("--res_dir", type=str, default="results/celiac_agent", help="Directory containing JSON results")
    parser.add_argument("--out_file", type=str, default="results/evaluation_report.md", help="Path to output markdown report")
    parser.add_argument("--gt_path", type=str, default="/home/biand/Projects/Celiac_BioVU/data/Celiac Diagnosis by Manual Review.xlsx", help="Path to ground truth Excel file")
    args = parser.parse_args()

    gt_path = args.gt_path
    if not os.path.exists(gt_path):
        if os.path.exists("data/Celiac Diagnosis by Manual Review.xlsx"):
            gt_path = "data/Celiac Diagnosis by Manual Review.xlsx"
    import openpyxl
    wb = openpyxl.load_workbook(gt_path, data_only=True)
    sheet = wb.active
    data = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        data.append({
            "Patient ID": str(row[0]).strip() if row[0] is not None else "",
            "Diagnosis": str(row[1]).strip() if row[1] is not None else "",
            "Comment": str(row[2]).strip() if row[2] is not None else ""
        })
    df_gt = pd.DataFrame(data)

    def map_gt(label):
        if label in ["Yes", "PMH"]:
            return "Positive"
        elif label == "No":
            return "Negative"
        else:
            return "Unknown"
            
    df_gt["GT_Label"] = df_gt["Diagnosis"].apply(map_gt)
    
    json_files = glob.glob(os.path.join(args.res_dir, "*.json"))
    
    results = []
    for jf in json_files:
        with open(jf, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
            grid = data.get("grid")
            diagnosis = data.get("diagnosis", "Unknown")
            reasoning = data.get("reasoning", "")
            results.append({
                "Patient ID": grid,
                "Agent_Label": diagnosis,
                "Reasoning": reasoning
            })
            
    df_res = pd.DataFrame(results)
    if len(df_res) == 0:
        print(f"No valid JSON results found in {args.res_dir}")
        return

    df_res["Patient ID"] = df_res["Patient ID"].astype(str).str.strip()
    
    df_merged = pd.merge(df_res, df_gt, on="Patient ID", how="inner")
    
    out_dir = os.path.dirname(args.out_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    
    md_content = "# Celiac Agent Evaluation Report\n\n"
    md_content += f"**Total evaluated files:** {len(df_res)}\n"
    md_content += f"**Total merged with Ground Truth:** {len(df_merged)}\n\n"
    
    if len(df_merged) == 0:
        md_content += "No matches found.\n"
        with open(args.out_file, "w") as f:
            f.write(md_content)
        return
        
    gt_labels = ["Positive", "Negative", "Unknown"]
    agent_labels = ["Positive", "Negative", "Indeterminate"]
    cm_df = pd.crosstab(df_merged["GT_Label"], df_merged["Agent_Label"], dropna=False)
    for gl in gt_labels:
        if gl not in cm_df.index:
            cm_df.loc[gl] = 0
    for al in agent_labels:
        if al not in cm_df.columns:
            cm_df[al] = 0
    cm_df = cm_df.reindex(index=gt_labels, columns=agent_labels, fill_value=0)
    
    md_content += "## Confusion Matrix (All Categories)\n\n"
    md_content += df_to_markdown(cm_df) + "\n\n"
    
    # Generate Positive/Negative Only confusion matrix
    cm_plot_df = cm_df.loc[["Positive", "Negative"], ["Positive", "Negative"]]
    md_content += "## Confusion Matrix (Positive/Negative Only)\n\n"
    md_content += df_to_markdown(cm_plot_df) + "\n\n"
    
    # Generate and save confusion matrix plot (keeping only Positive and Negative labels)
    plt.figure(figsize=(6, 5))
    im = plt.imshow(cm_plot_df.values, cmap='Blues', interpolation='nearest')
    plt.title('Confusion Matrix', fontsize=16)
    plt.colorbar(im)
    tick_marks = range(len(cm_plot_df.columns))
    plt.xticks(tick_marks, cm_plot_df.columns, fontsize=12)
    plt.yticks(tick_marks, cm_plot_df.index, fontsize=12)
    for i in range(len(cm_plot_df.index)):
        for j in range(len(cm_plot_df.columns)):
            val = cm_plot_df.values[i, j]
            max_val = cm_plot_df.values.max()
            color = "white" if max_val > 0 and val > max_val / 2 else "black"
            plt.text(j, i, str(val), ha="center", va="center", color=color, fontsize=14)
    plt.ylabel('Ground Truth Label', fontsize=12)
    plt.xlabel('Agent Label', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "confusion_matrix.png"))
    plt.close()
    
    df_eval = df_merged[df_merged["GT_Label"].isin(["Positive", "Negative"])].copy()
    md_content += f"## Evaluating on {len(df_eval)} samples with known Ground Truth (Positive/Negative)\n\n"
    
    report = classification_report(df_eval["GT_Label"], df_eval["Agent_Label"], labels=["Positive", "Negative", "Indeterminate"], zero_division=0, output_dict=True)
    report_df = pd.DataFrame(report).transpose()
    md_content += "### Classification Report\n\n"
    md_content += df_to_markdown(report_df) + "\n\n"
    
    md_content += "## Error Analysis\n\n"
    
    fp = df_eval[(df_eval["GT_Label"] == "Negative") & (df_eval["Agent_Label"] == "Positive")]
    md_content += f"### False Positives ({len(fp)})\n\n"
    for _, row in fp.iterrows():
        md_content += f"**Patient:** {row['Patient ID']}  \n"
        md_content += f"**GT:** {row['GT_Label']} | **Agent:** {row['Agent_Label']} | **Original GT:** {row['Diagnosis']}  \n"
        md_content += f"**Comment:** {row['Comment']}  \n"
        md_content += f"**Agent Reasoning:** {row['Reasoning']}  \n\n"
        
    fn = df_eval[(df_eval["GT_Label"] == "Positive") & (df_eval["Agent_Label"] == "Negative")]
    md_content += f"### False Negatives ({len(fn)})\n\n"
    for _, row in fn.iterrows():
        md_content += f"**Patient:** {row['Patient ID']}  \n"
        md_content += f"**GT:** {row['GT_Label']} | **Agent:** {row['Agent_Label']} | **Original GT:** {row['Diagnosis']}  \n"
        md_content += f"**Comment:** {row['Comment']}  \n"
        md_content += f"**Agent Reasoning:** {row['Reasoning']}  \n\n"
        
    ind = df_eval[df_eval["Agent_Label"] == "Indeterminate"]
    md_content += f"### Indeterminate on Known GT ({len(ind)})\n\n"
    for _, row in ind.iterrows():
        md_content += f"**Patient:** {row['Patient ID']}  \n"
        md_content += f"**GT:** {row['GT_Label']} | **Agent:** {row['Agent_Label']} | **Original GT:** {row['Diagnosis']}  \n"
        md_content += f"**Comment:** {row['Comment']}  \n"
        md_content += f"**Agent Reasoning:** {row['Reasoning']}  \n\n"

    with open(args.out_file, "w") as f:
        f.write(md_content)
        
if __name__ == '__main__':
    main()
