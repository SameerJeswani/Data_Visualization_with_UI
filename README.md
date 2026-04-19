# Data_Visualization_with_UI

📊 DataLens — CSV Data Analyzer
A lightweight CSV analysis tool built in Python that cleans data, generates statistics, and visualizes insights in an interactive browser dashboard.

🚀 Overview
DataLens allows users to upload a CSV file and instantly:

Clean messy data
Generate statistical summaries
Visualize insights using charts
View results in a modern dark-themed UI
Runs completely locally — no server required.

🧰 Tech Stack
Python
Pandas — data loading and processing
NumPy — statistical calculations
Chart.js — browser-based visualizations
Built-in modules: json, webbrowser, tempfile, os
⚙️ Workflow
Step 1 — Load CSV
Upload CSV file via UI
Displays:
Total rows and columns
Missing values
Duplicate rows
Preview of data
Step 2 — Data Cleaning
Removes duplicate rows
Strips extra spaces from text columns
Handles missing values:
Numeric → filled with median
Text → filled with mode
Step 3 — Statistical Analysis
Uses df.describe() for summary
Calculates:
Mean
Standard Deviation
Minimum
Maximum
Step 4 — Dashboard Visualization
Interactive browser dashboard includes:

Metric Cards — Mean of first 4 numeric columns
Histogram — Distribution with mean & median
Pie Chart — Categorical distribution or numeric share
Correlation Heatmap — Relationship between columns
🎨 UI Features
Dark theme interface
Clean and responsive layout
Drag & Drop CSV upload
Interactive charts (Chart.js)
Automatic file name display
No clutter — focused dashboard
▶️ How to Run
pip install pandas numpy
python Data_Visualization_with_UI.py
