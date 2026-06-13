# App-Level QA & Client Data Replacement Report

The purpose of this report is documenting the verification results of the Streamlit application after replacing the demo data with CGI's actual spreadsheet data.

## 1. Data Replacement and Pipeline Execution

The opportunity preprocessing pipeline was rigorously verified to ensure smooth client handoff, addressing both default and custom CLI behaviors.

### 1.1 Default Demo Preprocessing Workflow
We confirmed that the pipeline remains fully backward-compatible. Running the script without any arguments defaults to processing the original demo files safely:
```bash
python -m src.opportunity_cleaner
```

### 1.2 CLI-Provided Safe Test Files Workflow
To accommodate CGI's custom environments, we explicitly tested the script using CLI-provided paths to safe test spreadsheets. The pipeline correctly accepts configurable paths, sheet names, and output directories without hardcoded dependencies:
```bash
python -m src.opportunity_cleaner \
    --opps1-path data/csv_files/anonymized_opps_1.xlsx \
    --opps2-path data/csv_files/anonymized_opps_2.xlsx \
    --sheet-name Data \
    --output-dir data/processed
```

### 1.3 Processed Data Loading Validation
After generating the outputs, we verified the data loading precedence within the Streamlit application (`app/app.py`). 
- **Verification:** The dashboard successfully prioritized loading the `data/processed/cleaned_opportunity_df.csv` file over raw `opportunity_df.csv` or any prebuilt mock data.
- **Evidence:** The UI correctly reflected the computed capacities from the newly generated CSVs without any backend terminal errors.

## 2. Dashboard Rendering and Stability

The Director Capacity Dashboard demonstrated excellent stability with the newly loaded CGI data. 

![Director Capacity Dashboard Screenshot](image/screencapture-%20dashboard.png)

When navigating to the dashboard via the sidebar, the page loaded successfully without crashing. All core charts, including the Relative Load chart, and the owner-level summary table rendered correctly with the new data points properly aligned. Furthermore, the UI text and disclaimers remained appropriately conservative, successfully retaining the "processed / computed CRM-derived data" phrasing without introducing any overclaims like "Live Data".

## 3. RFP Assignment Workflow

The RFP Assignment Tool was also smoke-tested and performed as expected. 

![RFP Assignment Tool Screenshot](image/screencapture-RFP.png)

The initial page loaded normally upon navigation. After copying and pasting a sample RFP text into the tool, the entire analysis pipeline executed smoothly and successfully returned recommended directors. The results page accurately displayed the current retrieval mode (e.g., `azure_chroma` or `local_fallback`), and the generated Risk Flags reasonably reflected the constraints and context of the new data.

## 4. Resilience and Failure-State Testing

To satisfy robust error-handling requirements, multiple targeted failure-state checks were conducted to verify application resilience:

**4.1 Missing Processed Data Fallback**

- **Test Condition** 

The `data/processed` folder was temporarily renamed to simulate missing data pipeline outputs.

- **Observed Behavior** 

The dashboard avoided a complete crash, successfully routing to a lower-priority source (prebuilt/mock fallback data).

- **UI Warning Verified** 

The UI clearly displayed the specific `st.warning` banner: `"Data loading fell back to a lower-priority source. Details: ..."` 

**4.2 Empty RFP Input Protection**

- **Test Condition** 

Attempting to execute the RFP Assignment analysis without pasting any text or uploading a file.
- **Observed Behavior** 

The frontend intercepted the empty submission before making backend API calls.

- **UI Warning Verified:** 

The UI successfully caught the error and displayed: `"Please paste RFP text before running the analysis."`

**4.3 Retrieval Engine Degradation**

- **Test Condition** 

We verified the system's defined behavior when the primary Azure/Chroma retrieval engine encounters an issue or lacks sufficient semantic evidence.

- **Observed Behavior** 

The application correctly degrades to the local retrieval strategy, surfacing the `local_fallback` state flag to the user to ensure complete transparency of the data source being utilized.

These verified behaviors confirm the robustness of the application's error-handling logic across both data loading and user interaction scenarios.

## 5. Next Steps for CGI User Handoff

Users from CGI can now independently run the pipeline using their actual CRM spreadsheets. 
1. Place your specific actual spreadsheets into the `data/csv_files/` directory. 
2. Run the pipeline using the full CLI command, explicitly pointing to your specific filenames.

**Example Command for CGI Execution:**
```bash
# change <actual_cgi_opps1>.xlsx to your real spreadsheet filename
python -m src.opportunity_cleaner \
    --opps1-path data/csv_files/<actual_cgi_opps1>.xlsx \
    --opps2-path data/csv_files/<actual_cgi_opps2>.xlsx \
    --sheet-name Data \
    --output-dir data/processed
```
