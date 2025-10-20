# 🔧 Baseline Adjustment Tool for NIR Instruments

This Streamlit app guides the user through a **5-step process to correct and regenerate NIR baseline files** (.ref or .csv).  
It is designed for **instrument calibration and cross-lamp standardization** workflows, typically used in quality control and analytical laboratories.

---

## 🚀 Features

✅ Step-by-step assistant for NIR baseline correction  
✅ Interactive upload and visualization of `.tsv`, `.ref`, and `.csv` files  
✅ Sample selection with checkboxes for correction and validation  
✅ Calculation of mean spectral difference between lamps  
✅ Baseline validation and correction preview  
✅ Export of corrected baselines (`.ref`, `.csv`) and detailed comparison tables  
✅ Automatic generation of a full **HTML report** with client info and results  
✅ Optional utilities to convert `.ref` ↔ `.csv`

---

## 🧭 Workflow Summary

| Step | Description |
|------|--------------|
| **0** | Enter client and instrument information |
| **1** | Diagnostic with White Standard (WSTD) |
| **2** | Measure Standard Kit and match samples |
| **3** | Calculate correction between reference and new lamp |
| **4** | Upload baseline of new lamp |
| **5** | Apply correction, export results and generate report |

---

## 🖥️ Usage

### Local execution
1. Install Python ≥ 3.10  
2. Clone this repository and install dependencies:
   ```bash
   pip install -r requirements.txt
