# App-Level QA & Client Data Replacement Report

The purpose of this report is documenting the verification results of the Streamlit application after replacing the demo data with CGI's actual spreadsheet data.

## 1. Data Replacement and Pipeline Execution

The opportunity preprocessing pipeline was verified against both default and custom CLI arguments.

**Default Workflow:**
Running the script without arguments successfully processes the default demo files:
```bash
python -m src.opportunity_cleaner
```

**CLI-Provided Safe Test Files Workflow:**
The script correctly accepts custom paths to specific safe test spreadsheets, configurable sheet names, and output directories:
```bash
python -m src.opportunity_cleaner \
    --opps1-path data/csv_files/anonymized_opps_1.xlsx \
    --opps2-path data/csv_files/anonymized_opps_2.xlsx \
    --sheet-name Data \
    --output-dir data/processed
```
Both workflows ran successfully and generated the expected output `.csv` files. Upon launching the application (`streamlit run app/app.py`), we explicitly verified that the dashboard prioritized loading `data/processed/cleaned_opportunity_df.csv` over fallback sources or raw `opportunity_df.csv`.

## 2. Dashboard Rendering and Stability

The Director Capacity Dashboard demonstrated excellent stability with the newly loaded CGI data. 

![Director Capacity Dashboard Screenshot](image/screencapture-%20dashboard.png)

When navigating to the dashboard via the sidebar, the page loaded successfully without crashing. All core charts, including the Relative Load chart, and the owner-level summary table rendered correctly with the new data points properly aligned. Furthermore, the UI text and disclaimers remained appropriately conservative, successfully retaining the "processed / computed CRM-derived data" phrasing without introducing any overclaims like "Live Data".

## 3. RFP Assignment Workflow

The RFP Assignment Tool was also smoke-tested and performed as expected. 

![RFP Assignment Tool Screenshot](image/screencapture-RFP.png)

The initial page loaded normally upon navigation. After copying and pasting a sample RFP text into the tool, the entire analysis pipeline executed smoothly and successfully returned recommended directors. The results page accurately displayed the current retrieval mode (e.g., `azure_chroma` or `local_fallback`), and the generated Risk Flags reasonably reflected the constraints and context of the new data.

## 4. Resilience Testing

A failure-state check was conducted to test the application's resilience. When the `data/processed` folder was temporarily renamed to simulate missing processed data, the dashboard gracefully fell back to a lower-priority source (prebuilt/mock data) and displayed the exact expected warning: `Data loading fell back to a lower-priority source.` rather than experiencing a complete crash. This confirms the robustness of the application's fallback and error-handling logic.

## 5. Next Steps for CGI
Users from CGI can now place their specific actual spreadsheets into the `data/csv_files/` directory. They can then run the pipeline independently using the full CLI command, explicitly pointing to their specific filenames. For example:
```bash
python -m src.opportunity_cleaner \
    --opps1-path data/csv_files/<actual_cgi_opps1>.xlsx \
    --opps2-path data/csv_files/<actual_cgi_opps2>.xlsx
```
