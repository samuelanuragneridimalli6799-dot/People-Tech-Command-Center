# People Tech Command Centre

A small working demo of how one project manager can keep People Technology and People Analytics delivery visible. It is built around five jobs: run delivery governance, own vendor and contract management, keep one current roadmap and a weekly review, turn stakeholder pain points into a ranked automation pipeline, and plan an HRIS implementation.

All data is synthetic and the company ("Northwind Mobility") is fictional. Nothing comes from a real employer.

## Pages

1. **Roadmap and WBR**: cross-project Gantt, editable status table, dependency checks, and a rule-based Weekly Business Review. Every sentence in the review maps to a row in the data.
2. **Vendor Register**: renewal and notice deadlines, 30/60/90 day flags, spend by category, and a dated review plan counted back from the notice deadline.
3. **Automation Pipeline**: intake form that writes a scoped brief, score of hours saved per effort day, effort versus impact chart, capacity line, and a count of recurring requests that could be self-served.
4. **HRIS Implementation Plan**: illustrative workstream plan, governance, RAID log with heat map, data migration mapping and cutover checklist. Based on general implementation practice, not on any specific product.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Push to GitHub and deploy on Streamlit Community Cloud with `app.py` as the entry point.

## Design decisions

- **Rule-based review, no AI call.** It runs without API keys and can be audited line by line.
- **Simple scoring.** Hours saved per year divided by effort in person-days. Effort assumptions are editable so the ranking can be challenged.
- **Edits stay in the session.** A production version would write to a database or integrate with Jira and Confluence.
- **Built with AI assistance.** The structure, rules and content decisions are the author's.

## Data

Edit the CSV files in `data/` to change the scenario. The as-of date in the sidebar drives all flags and deadlines.
