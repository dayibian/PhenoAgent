import os
import json
import pandas as pd
import glob
import argparse
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix

LABEL_MAP = {
    "positive": "Positive", "yes": "Positive", "1": "Positive", "case": "Positive",
    "negative": "Negative", "no": "Negative", "0": "Negative", "control": "Negative",
    "indeterminate": "Indeterminate", "uncertain": "Indeterminate", "unknown": "Indeterminate", "pmh": "Indeterminate",
    "excluded": "Excluded", "exclusion": "Excluded",
}

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
    parser = argparse.ArgumentParser(description="Generate PhenoAgent Evaluation & Summary Report")
    parser.add_argument("--res_dir", type=str, default="results/stuttering_parallel/json_results", help="Directory containing JSON results")
    parser.add_argument("--out_file", type=str, default="results/stuttering_parallel/summary/evaluation_report.md", help="Path to output markdown report")
    parser.add_argument("--gt_path", type=str, default=None, help="Optional path to ground truth Excel or CSV file")
    parser.add_argument("--phenotype", type=str, default="Stuttering", help="Phenotype name (default: Stuttering)")
    args = parser.parse_args()

    out_dir = os.path.dirname(args.out_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    json_files = glob.glob(os.path.join(args.res_dir, "*.json"))
    if not json_files:
        print(f"No JSON result files found in {args.res_dir}")
        return

    results = []
    for jf in json_files:
        with open(jf, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
            grid = data.get("grid")
            diagnosis = data.get("diagnosis", "Unknown")
            confidence = data.get("confidence", 0.0)
            reasoning = data.get("reasoning", "")
            decision_path = data.get("decision_path", "")
            evidence = data.get("evidence", [])
            evidence_str = "; ".join(evidence[:5]) if isinstance(evidence, list) else str(evidence)
            results.append({
                "Patient ID": str(grid).strip() if grid else "",
                "Agent_Label": diagnosis,
                "Confidence": confidence,
                "Reasoning": reasoning,
                "Decision_Path": decision_path,
                "Evidence": evidence_str,
            })

    df_res = pd.DataFrame(results)
    if len(df_res) == 0:
        print(f"No valid JSON records parsed in {args.res_dir}")
        return

    df_res["Patient ID"] = df_res["Patient ID"].astype(str).str.strip()
    df_res["Agent_Label"] = df_res["Agent_Label"].str.strip()

    # Check if ground truth is provided and exists
    has_gt = False
    df_gt = None
    if args.gt_path and os.path.exists(args.gt_path):
        has_gt = True
        if args.gt_path.endswith((".xlsx", ".xls")):
            import openpyxl
            wb = openpyxl.load_workbook(args.gt_path, data_only=True)
            sheet = wb.active
            data = []
            for row in sheet.iter_rows(min_row=2, values_only=True):
                data.append({
                    "Patient ID": str(row[0]).strip() if row[0] is not None else "",
                    "Diagnosis": str(row[1]).strip() if row[1] is not None else "",
                    "Comment": str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
                })
            df_gt = pd.DataFrame(data)
        else:
            raw_gt = pd.read_csv(args.gt_path)
            id_col = next((c for c in raw_gt.columns if any(k in c.lower() for k in ["patient", "grid", "id"])), raw_gt.columns[0])
            diag_col = next((c for c in raw_gt.columns if any(k in c.lower() for k in ["diag", "label", "pheno", "status"])), raw_gt.columns[1])
            df_gt = pd.DataFrame({
                "Patient ID": raw_gt[id_col].astype(str).str.strip(),
                "Diagnosis": raw_gt[diag_col].astype(str).str.strip(),
                "Comment": raw_gt.get("Comment", "")
            })

        df_gt["GT_Label"] = df_gt["Diagnosis"].str.strip().str.lower().map(LABEL_MAP).fillna("Unknown")

    md_content = f"# PhenoAgent {args.phenotype} Phenotyping Report\n\n"
    md_content += f"**Total evaluated patients:** {len(df_res)}\n\n"

    # 1. Phenotype Cohort Distribution
    dist = df_res["Agent_Label"].value_counts().reset_index()
    dist.columns = ["Phenotype", "Count"]
    dist["Percentage"] = (dist["Count"] / len(df_res) * 100).round(1).astype(str) + "%"
    
    # Add mean confidence per class
    conf_series = df_res.groupby("Agent_Label")["Confidence"].mean().round(2).to_dict()
    dist["Mean Confidence"] = dist["Phenotype"].map(conf_series).fillna(0.0)

    md_content += "## Phenotype Distribution\n\n"
    md_content += df_to_markdown(dist.set_index("Phenotype")) + "\n\n"

    # Plot Phenotype Distribution Bar Chart
    plt.figure(figsize=(7, 4.5))
    colors = ["#2b5c8f", "#5b92e5", "#8fc29b", "#d95f02"]
    bar_colors = [colors[i % len(colors)] for i in range(len(dist))]
    plt.bar(dist["Phenotype"], dist["Count"], color=bar_colors, edgecolor="black", alpha=0.85)
    plt.title(f"{args.phenotype} Phenotype Distribution (N={len(df_res)})", fontsize=14)
    plt.xlabel("Phenotype", fontsize=12)
    plt.ylabel("Patient Count", fontsize=12)
    for i, v in enumerate(dist["Count"]):
        plt.text(i, v + max(1, max(dist["Count"]) * 0.01), f"{v} ({dist['Percentage'].iloc[i]})", ha="center", fontsize=10)
    plt.tight_layout()
    dist_plot_path = os.path.join(out_dir, "phenotype_distribution.png")
    plt.savefig(dist_plot_path, dpi=150)
    plt.close()

    # 2. Ground Truth Comparison (if available)
    if has_gt and df_gt is not None:
        df_merged = pd.merge(df_res, df_gt, on="Patient ID", how="inner")
        md_content += f"**Total matched with Ground Truth:** {len(df_merged)}\n\n"
        if len(df_merged) > 0:
            labels = ["Positive", "Negative", "Indeterminate", "Excluded"]
            cm_labels = [l for l in labels if l in df_merged["GT_Label"].unique() or l in df_merged["Agent_Label"].unique()]
            
            cm_df = pd.crosstab(df_merged["GT_Label"], df_merged["Agent_Label"], dropna=False)
            cm_df = cm_df.reindex(index=cm_labels, columns=cm_labels, fill_value=0)
            
            md_content += "## Confusion Matrix\n\n"
            md_content += df_to_markdown(cm_df) + "\n\n"

            # Plot Confusion Matrix
            plt.figure(figsize=(6, 5))
            cm_values = cm_df.values
            plt.imshow(cm_values, cmap='Blues', interpolation='nearest')
            plt.title(f'{args.phenotype} Confusion Matrix', fontsize=14)
            plt.colorbar()
            tick_marks = range(len(cm_df.columns))
            plt.xticks(tick_marks, cm_df.columns, fontsize=11, rotation=20)
            plt.yticks(tick_marks, cm_df.index, fontsize=11)
            for i in range(len(cm_df.index)):
                for j in range(len(cm_df.columns)):
                    val = cm_values[i, j]
                    max_val = cm_values.max()
                    color = "white" if max_val > 0 and val > max_val / 2 else "black"
                    plt.text(j, i, str(val), ha="center", va="center", color=color, fontsize=12)
            plt.ylabel('Ground Truth Label', fontsize=12)
            plt.xlabel('Agent Label', fontsize=12)
            plt.tight_layout()
            cm_plot_path = os.path.join(out_dir, "confusion_matrix.png")
            plt.savefig(cm_plot_path, dpi=150)
            plt.close()

            # Classification Report
            report = classification_report(
                df_merged["GT_Label"],
                df_merged["Agent_Label"],
                labels=cm_labels,
                zero_division=0,
                output_dict=True,
            )
            report_df = pd.DataFrame(report).transpose().round(3)
            md_content += "### Classification Metrics\n\n"
            md_content += df_to_markdown(report_df) + "\n\n"

    # 3. Sample Case Findings & Reasoning
    md_content += "## Sample Clinical Phenotyping Decisions\n\n"
    for cat in ["Positive", "Excluded", "Indeterminate", "Negative"]:
        cat_samples = df_res[df_res["Agent_Label"] == cat].head(3)
        if not cat_samples.empty:
            md_content += f"### {cat} Cases\n\n"
            for _, row in cat_samples.iterrows():
                md_content += f"- **Patient:** `{row['Patient ID']}` (Confidence: {row['Confidence']})  \n"
                if row["Reasoning"]:
                    md_content += f"  - **Reasoning:** {row['Reasoning']}  \n"
                if row["Evidence"]:
                    md_content += f"  - **Evidence:** *\"{row['Evidence'][:200]}\"*  \n"
                if row["Decision_Path"]:
                    md_content += f"  - **Path:** {row['Decision_Path']}  \n"
                md_content += "\n"

    with open(args.out_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Report successfully saved to {args.out_file}")

if __name__ == '__main__':
    main()

