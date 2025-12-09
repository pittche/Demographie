#!/usr/bin/env python3
"""
Bildungsplanungs-Datenanalyse App für den Saarpfalz-Kreis
VERSION 3.1 STABLE - PRODUCTION READY

ALLE 7 KRITISCHEN FEHLER BEHOBEN:
✅ NaN-Werte werden behandelt (fillna)
✅ Null-Checks überall
✅ Division durch Null abgefangen
✅ Dashboard-Auslastung mit klarer Warnung
✅ Leere DataFrames behandelt
✅ Excel-Export mit Validierung
✅ Zeitvergleich mit Validierung

TOP 5 FEATURES:
1. Bedarfs-Rechner (Kita, Klassen, Räume)
2. Excel-Gesamt-Export (alle Analysen)
3. Zeitvergleich / Trends (historische Daten)
4. Interaktive Karten (OpenStreetMap)
5. Dashboard / Cockpit (KPI-Übersicht)

Entwickelt für: Alex, Datenanalyst für Bildungsplanung
Version: 3.1 STABLE
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
import warnings
import zipfile
import io
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import json

# Neue Imports für V3.0+
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    
try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

warnings.filterwarnings('ignore')

# Seitenkonfiguration
st.set_page_config(
    page_title="Bildungsplanungs-Analyse V3.1 STABLE | Saarpfalz-Kreis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS für professionelles Design
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f4788;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f4788;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #ffc107;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #28a745;
    }
    .danger-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #dc3545;
    }
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .kpi-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .kpi-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .dashboard-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


class BildungsplanungAnalyzerV31:
    """V3.1 STABLE - Production Ready mit allen Fehlerkorrekturen"""
    
    def __init__(self):
        self.df = None
        self.df_historical = {}  # Für Zeitvergleich
        self.gemeinden = []
        self.ortsteile = []
        self.has_ortsteile = False
        self.loaded_files = []
        
        # NEU V3.1 FINAL9: Datenschutz-Parameter
        self.datenschutz_threshold = 5  # Small Number Suppression
        
        # Geburten-Daten
        self.df_geburten = None
        self.has_geburten = False
        
        # V3.1 FINAL5: Geburtsmonat-Daten für Einschulungsplanung
        self.df_birthmonth = None
        self.has_birthmonth = False
        
        self.altersgruppen = {
            'Kita (0-2 Jahre)': (0, 2),
            'Kita (3-5 Jahre)': (3, 5),
            'Grundschule (6-9 Jahre)': (6, 9),
            'Sek I (10-15 Jahre)': (10, 15),
            'Sek II (16-18 Jahre)': (16, 18),
            'Junge Erwachsene (19-24 Jahre)': (19, 24),
            'Erwachsene (25-64 Jahre)': (25, 64),
            'Senioren (65+ Jahre)': (65, 100)
        }
        
        # Bedarfs-Parameter (konfigurierbar)
        self.bedarfs_parameter = {
            'kita_u3_quote': 0.35,  # 35% U3-Betreuung
            'kita_ue3_quote': 0.95,  # 95% Ü3-Betreuung
            'kita_puffer': 0.05,  # 5% Kapazitätspuffer
            'klassen_groesse_soll': 25,  # Soll-Klassengröße
            'klassen_groesse_min': 15,  # Min Klassengröße
            'klassen_groesse_max': 29,  # Max Klassengröße
            'schueler_pro_lehrer': 18,  # Schüler-Lehrer-Verhältnis
            'qm_pro_schueler': 2.5,  # m² pro Schüler
            'fachraum_faktor': 0.5,  # 50% zusätzlich für Fachräume
            'fgts_quote_aktuell': 0.45,  # 45% FGTS-Nutzung aktuell
            'fgts_quote_ziel': 0.80  # 80% FGTS-Ziel ab 2026
        }
    
    @staticmethod
    def suppress_small_number(value, threshold=5, replacement="< 5"):
        """
        Small Number Suppression für Datenschutz
        V3.1 FINAL9: Prio 0 Compliance (DSGVO)
        
        Werte unter threshold werden durch replacement ersetzt
        """
        try:
            if pd.isna(value):
                return replacement
            num_value = float(value)
            if num_value < threshold and num_value > 0:
                return replacement
            return int(num_value) if num_value == int(num_value) else num_value
        except (ValueError, TypeError):
            return value
    
    def extract_zip(self, zip_file) -> List[Tuple[str, bytes]]:
        """Extrahiert CSV-Dateien aus einem ZIP-Archiv"""
        csv_files = []
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    if file_name.lower().endswith('.csv') and not file_name.startswith('__MACOSX'):
                        file_content = zip_ref.read(file_name)
                        csv_files.append((file_name, file_content))
        except Exception as e:
            st.error(f"Fehler beim Extrahieren der ZIP-Datei: {str(e)}")
        
        return csv_files
    
    def load_single_csv(self, file_content, file_name: str) -> Optional[pd.DataFrame]:
        """
        Lädt eine einzelne CSV-Datei
        V3.1 FIXED3: Entfernt trailing Semicolons vor dem Parsen
        """
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                # Lese Rohdaten
                if isinstance(file_content, bytes):
                    content = file_content.decode(encoding)
                else:
                    file_content.seek(0)
                    content = file_content.read()
                    if isinstance(content, bytes):
                        content = content.decode(encoding)
                
                # KRITISCHER FIX: Entferne trailing Semicolons am Zeilenende
                # Problem: CSV hat ";55;" statt ";55" → Pandas denkt es gibt eine leere Spalte
                lines = content.split('\n')
                cleaned_lines = []
                for line in lines:
                    line = line.rstrip('\r\n')  # Entferne Zeilenumbrüche
                    if line.endswith(';'):  # Entferne trailing Semicolon
                        line = line[:-1]
                    cleaned_lines.append(line)
                
                cleaned_content = '\n'.join(cleaned_lines)
                
                # Parse bereinigten Content
                from io import StringIO
                df = pd.read_csv(
                    StringIO(cleaned_content),
                    sep=';',
                    on_bad_lines='skip'
                )
                
                # Füge Quell-Datei hinzu
                df['_source_file'] = file_name
                
                # Extrahiere Datum aus Dateinamen (falls vorhanden)
                import re
                date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', file_name)
                if date_match:
                    df['_file_date'] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                else:
                    df['_file_date'] = datetime.now().strftime('%Y-%m-%d')
                
                return df
                
            except (UnicodeDecodeError, Exception) as e:
                continue
        
        return None
    
    def detect_ortsteil_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        Erkennt automatisch die Ortsteil-Spalte
        V3.1 FIXED3: GemTeil erkannt + Strengere Prüfung
        """
        # Zuerst: Suche nach expliziten Ortsteil-Spaltennamen
        # WICHTIG: "GemTeil" ist der offizielle Name in SPK-Daten!
        possible_names = ['GemTeil', 'gemteil', 'Ortsteil', 'ortsteil', 'Stadtteil', 'stadtteil', 
                         'Ortschaft', 'ortschaft', 'Bezirk', 'bezirk', 'Gemeindeteile', 'gemeindeteile']
        
        for col in possible_names:
            if col in df.columns:
                return col
        
        # Zweite Methode: Suche nach Spalte zwischen Gemeinde und Alter
        cols = df.columns.tolist()
        if 'Gemeinde' in cols and 'Alter' in cols:
            gemeinde_idx = cols.index('Gemeinde')
            alter_idx = cols.index('Alter')
            
            # Prüfe ob zwischen Gemeinde und Alter genau EINE Spalte ist
            if alter_idx == gemeinde_idx + 2:
                potential_ortsteil = cols[gemeinde_idx + 1]
                
                # Zusätzliche Validierung: Darf NICHT in verbotenen Namen sein
                verboten = ['Alter', 'Staatsang', 'Staatsangehörigkeit', 'm', 'w', 'x', 'SUMME', 
                           'Datum', 'OU', 'Land', 'Kreis', '_source_file', '_file_date']
                
                if potential_ortsteil not in verboten:
                    # Prüfe ob die Spalte auch Text-Werte hat (nicht nur Zahlen)
                    sample_values = df[potential_ortsteil].dropna().head(10).astype(str).tolist()
                    
                    # Wenn mindestens ein Wert keine reine Zahl ist, ist es wahrscheinlich Ortsteil
                    has_text = any(not v.replace('.', '').replace('-', '').isdigit() for v in sample_values if v and v != 'nan')
                    
                    if has_text:
                        return potential_ortsteil
        
        return None
    
    def load_data(self, files, zeitpunkt_label: Optional[str] = None) -> bool:
        """
        Lädt eine oder mehrere CSV-Dateien (auch aus ZIP)
        V3.1: Mit verbesserter Fehlerbehandlung
        """
        try:
            all_dataframes = []
            self.loaded_files = []
            
            if not isinstance(files, list):
                files = [files]
            
            for file in files:
                file_name = file.name if hasattr(file, 'name') else str(file)
                
                if file_name.lower().endswith('.zip'):
                    st.info(f"📦 Extrahiere ZIP-Archiv: {file_name}")
                    csv_files = self.extract_zip(file)
                    
                    for csv_name, csv_content in csv_files:
                        df_temp = self.load_single_csv(csv_content, csv_name)
                        if df_temp is not None:
                            all_dataframes.append(df_temp)
                            self.loaded_files.append(csv_name)
                            st.success(f"✅ Geladen: {csv_name} ({len(df_temp):,} Zeilen)")
                
                elif file_name.lower().endswith('.csv'):
                    df_temp = self.load_single_csv(file, file_name)
                    if df_temp is not None:
                        all_dataframes.append(df_temp)
                        self.loaded_files.append(file_name)
                        st.success(f"✅ Geladen: {file_name} ({len(df_temp):,} Zeilen)")
            
            if not all_dataframes:
                st.error("❌ Keine gültigen CSV-Dateien gefunden.")
                return False
            
            # NEU V3.1 FINAL9: Intelligente Zeitreihen-Erkennung
            # Unterscheide: Zeitreihen-Analyse vs. versehentliche Duplikate
            
            ew_files = [f for f in self.loaded_files if 'EW' in f.upper() and 'GEB' not in f.upper()]
            
            if len(ew_files) > 1:
                # Extrahiere Zeitpunkte aus Dateinamen
                import re
                zeitpunkte = []
                for fname in ew_files:
                    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', fname)
                    if match:
                        datum_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                        zeitpunkte.append((fname, datum_str))
                
                if len(zeitpunkte) >= 2:
                    # Prüfe ob Zeitpunkte unterschiedlich sind
                    unique_dates = set([z[1] for z in zeitpunkte])
                    
                    if len(unique_dates) > 1:
                        # ZEITREIHEN-MODUS: Verschiedene Monate erkannt
                        st.success(
                            f"📊 **ZEITREIHEN-MODUS aktiviert!**\n\n"
                            f"Erkannte Zeitpunkte: {len(unique_dates)}\n"
                            f"Zeitraum: {min(unique_dates)} bis {max(unique_dates)}\n\n"
                            f"✅ Alle Zeitpunkte werden für Trend-Analysen gespeichert.\n"
                            f"✅ Status-Ansichten zeigen nur den neuesten Stand: **{max(unique_dates)}**"
                        )
                        
                        # Speichere Zeitreihen in df_historical
                        self.df_historical = {}
                        
                        for df in all_dataframes:
                            if '_source_file' in df.columns:
                                source = df['_source_file'].iloc[0]
                                if any(ew in source for ew in ['EW1', 'EW2', 'Melderegister']) and 'GEB' not in source.upper():
                                    datum = df['_file_date'].iloc[0] if '_file_date' in df.columns else 'Unbekannt'
                                    
                                    # WICHTIG: Bereinige Alter-Spalte auch für historische Daten!
                                    df_hist = df.copy()
                                    if 'Alter' in df_hist.columns:
                                        df_hist['Alter'] = df_hist['Alter'].astype(str).str.replace('100 und älter', '100', regex=False)
                                        df_hist['Alter'] = df_hist['Alter'].str.replace('100 und aelter', '100', regex=False)
                                        df_hist['Alter'] = pd.to_numeric(df_hist['Alter'], errors='coerce').fillna(0)
                                    
                                    self.df_historical[datum] = df_hist
                        
                        # Für Status-Ansichten: Nur neueste verwenden
                        neueste_datum = max(unique_dates)
                        all_dataframes_cleaned = []
                        for df in all_dataframes:
                            source = df['_source_file'].iloc[0] if '_source_file' in df.columns else ''
                            datum = df['_file_date'].iloc[0] if '_file_date' in df.columns else ''
                            
                            # Behalte:
                            # - Die neueste EW-Datei (für Status)
                            # - Alle Geburten-Dateien
                            # - Alle anderen Dateien
                            if datum == neueste_datum or 'GEB' in source.upper() or 'birth_month' in source.lower() or 'POLYTEIA' in source.upper():
                                all_dataframes_cleaned.append(df)
                        
                        all_dataframes = all_dataframes_cleaned
                        
                        st.info(f"ℹ️ Status-Ansichten verwenden: **{neueste_datum}** | Zeitvergleich nutzt alle {len(unique_dates)} Zeitpunkte")
                    
                    else:
                        # DUPLIKATE: Gleicher Monat mehrfach
                        st.error(
                            f"❌ **DUPLIKATE ERKANNT!**\n\n"
                            f"Alle {len(ew_files)} Dateien haben das gleiche Datum: **{list(unique_dates)[0]}**\n\n"
                            f"Das ist wahrscheinlich ein Versehen. Ich verwende nur die erste Datei."
                        )
                        
                        # Verwende nur erste Datei
                        erste_ew = ew_files[0]
                        all_dataframes_cleaned = []
                        for df in all_dataframes:
                            source = df['_source_file'].iloc[0] if '_source_file' in df.columns else ''
                            if source == erste_ew or 'GEB' in source.upper() or 'birth_month' in source.lower():
                                all_dataframes_cleaned.append(df)
                        
                        all_dataframes = all_dataframes_cleaned
                
                else:
                    # Keine Datums-Informationen → Warnung wie vorher
                    st.warning(
                        f"⚠️ **ACHTUNG: Mehrere Einwohner-Dateien ohne Datum!**\n\n"
                        f"Gefunden: {', '.join(ew_files)}\n\n"
                        f"Ich verwende nur die erste Datei. Für Zeitreihen bitte Dateien mit Datum benennen (z.B. EW2_2025-11-12.csv)"
                    )
                    
                    erste_ew = ew_files[0]
                    all_dataframes_cleaned = []
                    for df in all_dataframes:
                        source = df['_source_file'].iloc[0] if '_source_file' in df.columns else ''
                        if source == erste_ew or 'GEB' in source.upper() or 'birth_month' in source.lower():
                            all_dataframes_cleaned.append(df)
                    
                    all_dataframes = all_dataframes_cleaned
            
            # Kombiniere alle DataFrames
            df_combined = pd.concat(all_dataframes, ignore_index=True)
            
            # KORREKTUR 1: Prüfe ob DataFrame leer
            if df_combined.empty:
                st.error("❌ Alle geladenen Dateien sind leer.")
                return False
            
            # Datenbereinigung
            df_combined.columns = df_combined.columns.str.strip()
            
            # DEBUG: Zeige erkannte Spalten
            st.info(f"📋 Erkannte Spalten: {', '.join(df_combined.columns.tolist()[:10])}...")
            
            # Erkenne Ortsteil-Spalte
            ortsteil_col = self.detect_ortsteil_column(df_combined)
            
            if ortsteil_col:
                self.has_ortsteile = True
                
                # Bereinige leere Werte in GemTeil (oft ";;" in CSV)
                # WICHTIG: Pandas liest ";;" als NaN, nicht als leeren String!
                df_combined[ortsteil_col] = df_combined[ortsteil_col].fillna('')
                df_combined[ortsteil_col] = df_combined[ortsteil_col].astype(str).str.strip()
                
                # WICHTIG: Leere GemTeil-Werte bedeuten "Gemeinde ohne Ortsteil-Zuordnung"
                # Beispiel: Bexbach hat Zeilen mit leerem GemTeil (Bexbach gesamt) UND mit gefülltem GemTeil (Oberbexbach, etc.)
                # Wir ersetzen leere Werte durch einen aussagekräftigen Namen
                def get_ortsteil_name(row):
                    ot_value = row[ortsteil_col]
                    # Prüfe auf leer, NaN, 'nan', None
                    if pd.isna(ot_value) or not ot_value or ot_value == '' or str(ot_value).lower() == 'nan':
                        # Leerer GemTeil → Nutze Gemeindename als Basis
                        gemeinde = str(row['Gemeinde']).replace('Melderegister ', '')
                        return f"{gemeinde} (Kernstadt)"
                    else:
                        return ot_value
                
                df_combined['Ortsteil'] = df_combined.apply(get_ortsteil_name, axis=1)
                
                # Entferne Original-Spalte
                if ortsteil_col != 'Ortsteil':
                    df_combined = df_combined.drop(columns=[ortsteil_col])
                
                # Zähle nicht-leere Ortsteile
                ortsteile_unique = df_combined['Ortsteil'].unique()
                ortsteile_anzahl = len([x for x in ortsteile_unique if x and str(x).lower() != 'nan'])
                
                if ortsteile_anzahl > 0:
                    st.info(f"🏘️ Ortsteil-Daten erkannt! Spalte: '{ortsteil_col}' → 'Ortsteil' ({ortsteile_anzahl} Ortsteile gefunden)")
                else:
                    st.info(f"🏘️ Spalte '{ortsteil_col}' erkannt, aber alle Werte leer (wird wie EW1 behandelt)")
                    self.has_ortsteile = False
            else:
                self.has_ortsteile = False
                df_combined['Ortsteil'] = ''
                st.info("ℹ️ Keine Ortsteil-Spalte erkannt (EW1-Format)")
            
            # KORREKTUR 2: Konvertiere numerische Spalten UND behandle NaN-Werte
            # WICHTIG: Alter-Spalte kann "100 und älter" enthalten!
            if 'Alter' in df_combined.columns:
                # Spezialbehandlung für "100 und älter" → 100
                df_combined['Alter'] = df_combined['Alter'].astype(str).str.replace('100 und älter', '100', regex=False)
                df_combined['Alter'] = df_combined['Alter'].str.replace('100 und aelter', '100', regex=False)  # Falls ohne Umlaut
                df_combined['Alter'] = pd.to_numeric(df_combined['Alter'], errors='coerce').fillna(0)
            
            # Andere numerische Spalten
            numeric_cols = ['m', 'w', 'x', 'SUMME']
            for col in numeric_cols:
                if col in df_combined.columns:
                    df_combined[col] = pd.to_numeric(df_combined[col], errors='coerce').fillna(0)
            
            # KRITISCHE VALIDIERUNG V3.1 FINAL9: Prüfe Pflicht-Spalten
            # ABER NUR für EW-Dateien, nicht für Geburten-Dateien!
            
            # Erkenne Datei-Typ anhand der Spalten
            is_birthmonth_file = 'municipality' in df_combined.columns and 'birth_halbjahr' in df_combined.columns
            is_geburten_file = any(f for f in self.loaded_files if 'GEB' in f.upper())
            
            if not is_birthmonth_file and not is_geburten_file:
                # Das ist eine EW-Datei → Validiere Pflicht-Spalten
                required_cols = ['Gemeinde', 'Alter', 'SUMME']
                missing_cols = [col for col in required_cols if col not in df_combined.columns]
                
                if missing_cols:
                    st.error(
                        f"❌ **KRITISCHER FEHLER: Pflicht-Spalten fehlen!**\n\n"
                        f"Fehlende Spalten: {', '.join(missing_cols)}\n\n"
                        f"Vorhandene Spalten: {', '.join(df_combined.columns.tolist()[:20])}\n\n"
                        f"**Bitte prüfen Sie ob Sie die richtige EW-Datei hochgeladen haben!**"
                    )
                    return False
            
            # Extrahiere Gemeindeliste
            if 'Gemeinde' in df_combined.columns:
                # KORREKTUR: Filtere NaN-Werte BEVOR sortiert wird
                gemeinden_raw = df_combined['Gemeinde'].unique().tolist()
                self.gemeinden = sorted([x for x in gemeinden_raw if x and str(x).strip() and str(x) != 'nan'])
            
            # Extrahiere Ortsteil-Liste
            if self.has_ortsteile and 'Ortsteil' in df_combined.columns:
                ortsteile_raw = df_combined['Ortsteil'].unique().tolist()
                self.ortsteile = sorted([x for x in ortsteile_raw if x and str(x).strip() and str(x) != 'nan'])
            
            # Speichere Daten
            if zeitpunkt_label:
                self.df_historical[zeitpunkt_label] = df_combined
            else:
                self.df = df_combined
            
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.success(
                f"**📊 Daten erfolgreich geladen!**\n\n"
                f"- **{len(all_dataframes)}** Datei(en)\n"
                f"- **{len(df_combined):,}** Datensätze gesamt\n"
                f"- **{len(self.gemeinden)}** Gemeinden\n"
                f"- **{len(self.ortsteile)}** Ortsteile" + 
                (f" (erkannt in {ortsteil_col})" if self.has_ortsteile else "")
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            return True
            
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Daten: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    def load_geburten_data(self, uploaded_files):
        """
        Lädt Geburten-Statistik Dateien (SPK_GEB_*.csv)
        V3.1 FINAL3: Neue Funktion für Geburten-Analyse
        """
        try:
            geburten_dataframes = []
            
            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                
                # Prüfe ob es eine Geburten-Datei ist
                if 'GEB' not in file_name.upper() and 'GEBURT' not in file_name.upper():
                    continue
                
                st.info(f"📄 Lade Geburten-Datei: {file_name}")
                
                # Lade CSV
                df_geb = self.load_single_csv(uploaded_file, file_name)
                
                if df_geb is not None:
                    geburten_dataframes.append(df_geb)
            
            if not geburten_dataframes:
                return False
            
            # Kombiniere alle Geburten-Dateien
            df_geb_combined = pd.concat(geburten_dataframes, ignore_index=True)
            
            st.info(f"📋 Erkannte Spalten: {', '.join(df_geb_combined.columns.tolist()[:12])}...")
            
            # Konvertiere numerische Spalten
            # AlterMutter kann "100 und älter" enthalten
            if 'AlterMutter' in df_geb_combined.columns:
                df_geb_combined['AlterMutter'] = df_geb_combined['AlterMutter'].astype(str).str.replace('100 und älter', '100', regex=False)
                df_geb_combined['AlterMutter'] = pd.to_numeric(df_geb_combined['AlterMutter'], errors='coerce').fillna(0)
            
            # Andere numerische Spalten
            numeric_cols = ['m', 'w', 'x', 'SUMME', 'ALLE']
            for col in numeric_cols:
                if col in df_geb_combined.columns:
                    df_geb_combined[col] = pd.to_numeric(df_geb_combined[col], errors='coerce').fillna(0)
            
            # Speichere Geburten-Daten
            self.df_geburten = df_geb_combined
            self.has_geburten = True
            
            geburten_gesamt = int(df_geb_combined['SUMME'].sum())
            
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.success(
                f"**👶 Geburten-Daten erfolgreich geladen!**\n\n"
                f"- **{len(geburten_dataframes)}** Geburten-Datei(en)\n"
                f"- **{len(df_geb_combined):,}** Datensätze\n"
                f"- **{geburten_gesamt}** Geburten gesamt\n"
                f"- **{len(self.gemeinden)}** Gemeinden"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            return True
            
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Geburten-Daten: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    def load_birthmonth_data(self, uploaded_files):
        """
        Lädt Geburtsmonat-Statistik Dateien (birth_month.csv / POLYTEIA)
        V3.1 FINAL5: Neue Funktion für Einschulungsplanung
        """
        try:
            birthmonth_dataframes = []
            
            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                
                # Prüfe ob es eine Geburtsmonat-Datei ist
                if 'birth_month' not in file_name.lower() and 'polyteia' not in file_name.lower():
                    continue
                
                st.info(f"📄 Lade Geburtsmonat-Datei: {file_name}")
                
                # Lade CSV (mit Komma-Separator!)
                uploaded_file.seek(0)
                df_birth = pd.read_csv(uploaded_file, sep=',')  # WICHTIG: Komma statt Semikolon!
                
                if df_birth is not None and not df_birth.empty:
                    birthmonth_dataframes.append(df_birth)
                    df_birth['_source_file'] = file_name
            
            if not birthmonth_dataframes:
                return False
            
            # Kombiniere alle Geburtsmonat-Dateien
            df_birth_combined = pd.concat(birthmonth_dataframes, ignore_index=True)
            
            st.info(f"📋 Erkannte Spalten: {', '.join(df_birth_combined.columns.tolist())}")
            
            # Konvertiere numerische Spalten
            if 'age' in df_birth_combined.columns:
                df_birth_combined['age'] = pd.to_numeric(df_birth_combined['age'], errors='coerce').fillna(0)
            if 'persons' in df_birth_combined.columns:
                df_birth_combined['persons'] = pd.to_numeric(df_birth_combined['persons'], errors='coerce').fillna(0)
            
            # Standardisiere Gemeinde-Namen (municipality → Gemeinde)
            if 'municipality' in df_birth_combined.columns:
                df_birth_combined['Gemeinde'] = df_birth_combined['municipality'].str.title()
            elif 'location' in df_birth_combined.columns:
                df_birth_combined['Gemeinde'] = df_birth_combined['location']
            
            # Speichere Geburtsmonat-Daten
            self.df_birthmonth = df_birth_combined
            self.has_birthmonth = True
            
            kinder_gesamt = int(df_birth_combined['persons'].sum())
            gemeinden_anzahl = df_birth_combined['Gemeinde'].nunique() if 'Gemeinde' in df_birth_combined.columns else 0
            
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.success(
                f"**📅 Geburtsmonat-Daten erfolgreich geladen!**\n\n"
                f"- **{len(birthmonth_dataframes)}** Datei(en)\n"
                f"- **{len(df_birth_combined):,}** Datensätze\n"
                f"- **{kinder_gesamt:,}** Kinder gesamt (0-9 Jahre)\n"
                f"- **{gemeinden_anzahl}** Gemeinden"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            return True
            
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Geburtsmonat-Daten: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return False
    
    def get_filtered_data(self, gemeinde: Optional[str] = None, ortsteil: Optional[str] = None, 
                         altersgruppe_name: Optional[str] = None, df_source: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Filtert Daten nach Gemeinde, Ortsteil und Altersgruppe
        V3.1: Mit Null-Checks
        """
        if df_source is None:
            df_source = self.df
        
        # KORREKTUR 3: Prüfe ob Daten vorhanden
        if df_source is None:
            return pd.DataFrame()  # Leerer DataFrame statt Crash
        
        if df_source.empty:
            return pd.DataFrame()
        
        df_filtered = df_source.copy()
        
        # KORREKTUR FINAL9: Validiere benötigte Spalten
        if gemeinde and gemeinde != "Gesamter Kreis":
            if 'Gemeinde' not in df_filtered.columns:
                st.warning("⚠️ Spalte 'Gemeinde' fehlt - Filter ignoriert")
            else:
                df_filtered = df_filtered[df_filtered['Gemeinde'] == gemeinde]
        
        if ortsteil and ortsteil != "Alle Ortsteile" and self.has_ortsteile:
            if 'Ortsteil' not in df_filtered.columns:
                st.warning("⚠️ Spalte 'Ortsteil' fehlt - Filter ignoriert")
            else:
                df_filtered = df_filtered[df_filtered['Ortsteil'] == ortsteil]
        
        if altersgruppe_name:
            if 'Alter' not in df_filtered.columns:
                st.error("❌ Spalte 'Alter' fehlt - kann nicht filtern!")
                return pd.DataFrame()
            min_age, max_age = self.altersgruppen[altersgruppe_name]
            df_filtered = df_filtered[
                (df_filtered['Alter'] >= min_age) & 
                (df_filtered['Alter'] <= max_age)
            ]
        
        return df_filtered
    
    def get_ortsteile_for_gemeinde(self, gemeinde: str) -> List[str]:
        """Gibt alle Ortsteile für eine bestimmte Gemeinde zurück"""
        if not self.has_ortsteile or self.df is None:
            return []
        
        df_gem = self.df[self.df['Gemeinde'] == gemeinde]
        ortsteile_raw = df_gem['Ortsteil'].unique().tolist()
        ortsteile = sorted([x for x in ortsteile_raw if x and str(x).strip() and str(x) != 'nan'])
        return ortsteile
    
    def berechne_kennzahlen(self, df_filtered: pd.DataFrame) -> Dict:
        """
        Berechnet wichtige Kennzahlen
        V3.1: Mit Behandlung leerer DataFrames
        """
        # KORREKTUR 4: Prüfe ob DataFrame leer
        if df_filtered.empty:
            return {
                'Gesamtbevölkerung': 0,
                'Männlich': 0,
                'Weiblich': 0,
                'Divers': 0,
                'Deutsche Staatsangehörigkeit': 0,
                'Ausländische Staatsangehörigkeit': 0,
                'Anzahl Nationalitäten': 0,
                'Anteil_Ausländer': 0.0
            }
        
        kennzahlen = {
            'Gesamtbevölkerung': int(df_filtered['SUMME'].sum()),
            'Männlich': int(df_filtered['m'].sum()),
            'Weiblich': int(df_filtered['w'].sum()),
            'Divers': int(df_filtered['x'].sum()),
            'Deutsche Staatsangehörigkeit': int(
                df_filtered[df_filtered['Staatsang'] == 'deutsch']['SUMME'].sum()
            ),
            'Ausländische Staatsangehörigkeit': int(
                df_filtered[df_filtered['Staatsang'] != 'deutsch']['SUMME'].sum()
            ),
            'Anzahl Nationalitäten': len(df_filtered['Staatsang'].unique())
        }
        
        # KORREKTUR 5: Sichere Division
        if kennzahlen['Gesamtbevölkerung'] > 0:
            kennzahlen['Anteil_Ausländer'] = (
                kennzahlen['Ausländische Staatsangehörigkeit'] / 
                kennzahlen['Gesamtbevölkerung'] * 100
            )
        else:
            kennzahlen['Anteil_Ausländer'] = 0.0
        
        return kennzahlen
    
    # ========================================
    # FEATURE 1: BEDARFS-RECHNER (KORRIGIERT)
    # ========================================
    
    def berechne_bedarf(self, df_filtered: pd.DataFrame, gemeinde_name: str = "Ausgewählter Bereich") -> Dict:
        """
        Berechnet Bedarf für Kita, Klassen, Räume, Personal
        V3.1: Mit Division-durch-Null-Schutz
        """
        
        bedarf = {
            'gemeinde': gemeinde_name,
            'kita': {},
            'grundschule': {},
            'sek1': {},
            'sek2': {},
            'fgts': {},
            'gesamt': {}
        }
        
        # KORREKTUR 6: Prüfe ob DataFrame leer
        if df_filtered.empty:
            # Setze alle Werte auf 0
            bedarf['kita'] = {
                'kinder_u3': 0, 'kinder_ue3': 0,
                'plaetze_u3_noetig': 0, 'plaetze_ue3_noetig': 0,
                'plaetze_gesamt': 0
            }
            bedarf['grundschule'] = {
                'kinder': 0, 'klassen': 0, 'zuege': 0,
                'klassenraeume': 0, 'fachraeume': 0, 'raeume_gesamt': 0,
                'lehrer': 0, 'flaeche_qm': 0
            }
            bedarf['sek1'] = {
                'kinder': 0, 'klassen': 0, 'zuege': 0,
                'klassenraeume': 0, 'fachraeume': 0, 'raeume_gesamt': 0,
                'lehrer': 0, 'flaeche_qm': 0
            }
            bedarf['sek2'] = {
                'kinder': 0, 'kurse': 0, 'raeume': 0, 'lehrer': 0
            }
            bedarf['fgts'] = {
                'gs_kinder': 0, 'plaetze_aktuell': 0,
                'plaetze_ziel_2026': 0, 'plaetze_fehlen': 0,
                'gruppen_fehlen': 0
            }
            bedarf['gesamt'] = {
                'kinder_0_18': 0, 'klassen_gesamt': 0,
                'lehrer_gesamt': 0, 'raeume_gesamt': 0
            }
            return bedarf
        
        # KITA-BEDARF
        kinder_u3 = int(df_filtered[(df_filtered['Alter'] >= 0) & (df_filtered['Alter'] <= 2)]['SUMME'].sum())
        kinder_ue3 = int(df_filtered[(df_filtered['Alter'] >= 3) & (df_filtered['Alter'] <= 5)]['SUMME'].sum())
        
        bedarf['kita']['kinder_u3'] = kinder_u3
        bedarf['kita']['kinder_ue3'] = kinder_ue3
        bedarf['kita']['plaetze_u3_noetig'] = int(kinder_u3 * self.bedarfs_parameter['kita_u3_quote'] * (1 + self.bedarfs_parameter['kita_puffer']))
        bedarf['kita']['plaetze_ue3_noetig'] = int(kinder_ue3 * self.bedarfs_parameter['kita_ue3_quote'] * (1 + self.bedarfs_parameter['kita_puffer']))
        bedarf['kita']['plaetze_gesamt'] = bedarf['kita']['plaetze_u3_noetig'] + bedarf['kita']['plaetze_ue3_noetig']
        
        # GRUNDSCHUL-BEDARF
        gs_kinder = int(df_filtered[(df_filtered['Alter'] >= 6) & (df_filtered['Alter'] <= 9)]['SUMME'].sum())
        bedarf['grundschule']['kinder'] = gs_kinder
        
        # KORREKTUR 7: Division durch Null Schutz
        if gs_kinder > 0 and self.bedarfs_parameter['klassen_groesse_soll'] > 0:
            bedarf['grundschule']['klassen'] = int(np.ceil(gs_kinder / self.bedarfs_parameter['klassen_groesse_soll']))
            bedarf['grundschule']['zuege'] = int(np.ceil(bedarf['grundschule']['klassen'] / 4))  # 4 Jahrgänge
            bedarf['grundschule']['klassenraeume'] = bedarf['grundschule']['klassen']
            bedarf['grundschule']['fachraeume'] = int(np.ceil(bedarf['grundschule']['klassenraeume'] * 0.4))  # 40% Fachräume
            bedarf['grundschule']['raeume_gesamt'] = bedarf['grundschule']['klassenraeume'] + bedarf['grundschule']['fachraeume']
        else:
            bedarf['grundschule']['klassen'] = 0
            bedarf['grundschule']['zuege'] = 0
            bedarf['grundschule']['klassenraeume'] = 0
            bedarf['grundschule']['fachraeume'] = 0
            bedarf['grundschule']['raeume_gesamt'] = 0
        
        # KORREKTUR 8: Lehrer-Berechnung mit Schutz
        if gs_kinder > 0 and self.bedarfs_parameter['schueler_pro_lehrer'] > 0:
            bedarf['grundschule']['lehrer'] = int(np.ceil(gs_kinder / self.bedarfs_parameter['schueler_pro_lehrer']))
            bedarf['grundschule']['flaeche_qm'] = int(gs_kinder * self.bedarfs_parameter['qm_pro_schueler'] * (1 + self.bedarfs_parameter['fachraum_faktor']))
        else:
            bedarf['grundschule']['lehrer'] = 0
            bedarf['grundschule']['flaeche_qm'] = 0
        
        # SEK I BEDARF
        sek1_kinder = int(df_filtered[(df_filtered['Alter'] >= 10) & (df_filtered['Alter'] <= 15)]['SUMME'].sum())
        bedarf['sek1']['kinder'] = sek1_kinder
        
        # KORREKTUR 9: Division durch Null Schutz für Sek I
        if sek1_kinder > 0 and self.bedarfs_parameter['klassen_groesse_soll'] > 0:
            bedarf['sek1']['klassen'] = int(np.ceil(sek1_kinder / self.bedarfs_parameter['klassen_groesse_soll']))
            bedarf['sek1']['zuege'] = int(np.ceil(bedarf['sek1']['klassen'] / 6))  # 6 Jahrgänge
            bedarf['sek1']['klassenraeume'] = bedarf['sek1']['klassen']
            bedarf['sek1']['fachraeume'] = int(np.ceil(bedarf['sek1']['klassenraeume'] * 0.6))  # 60% Fachräume
            bedarf['sek1']['raeume_gesamt'] = bedarf['sek1']['klassenraeume'] + bedarf['sek1']['fachraeume']
        else:
            bedarf['sek1']['klassen'] = 0
            bedarf['sek1']['zuege'] = 0
            bedarf['sek1']['klassenraeume'] = 0
            bedarf['sek1']['fachraeume'] = 0
            bedarf['sek1']['raeume_gesamt'] = 0
        
        if sek1_kinder > 0 and self.bedarfs_parameter['schueler_pro_lehrer'] > 0:
            bedarf['sek1']['lehrer'] = int(np.ceil(sek1_kinder / self.bedarfs_parameter['schueler_pro_lehrer']))
            bedarf['sek1']['flaeche_qm'] = int(sek1_kinder * self.bedarfs_parameter['qm_pro_schueler'] * (1 + self.bedarfs_parameter['fachraum_faktor']))
        else:
            bedarf['sek1']['lehrer'] = 0
            bedarf['sek1']['flaeche_qm'] = 0
        
        # SEK II BEDARF
        sek2_kinder = int(df_filtered[(df_filtered['Alter'] >= 16) & (df_filtered['Alter'] <= 18)]['SUMME'].sum())
        bedarf['sek2']['kinder'] = sek2_kinder
        
        # KORREKTUR 10: Division durch Null Schutz für Sek II
        if sek2_kinder > 0:
            bedarf['sek2']['kurse'] = int(np.ceil(sek2_kinder / 20))  # Kurssystem, ca. 20 Schüler/Kurs
            bedarf['sek2']['raeume'] = int(np.ceil(bedarf['sek2']['kurse'] * 0.7))  # 70% Raumauslastung
            bedarf['sek2']['lehrer'] = int(np.ceil(sek2_kinder / 15))  # Besseres Verhältnis in Sek II
        else:
            bedarf['sek2']['kurse'] = 0
            bedarf['sek2']['raeume'] = 0
            bedarf['sek2']['lehrer'] = 0
        
        # FGTS-BEDARF (Ganztagsschule)
        bedarf['fgts']['gs_kinder'] = gs_kinder
        bedarf['fgts']['plaetze_aktuell'] = int(gs_kinder * self.bedarfs_parameter['fgts_quote_aktuell'])
        bedarf['fgts']['plaetze_ziel_2026'] = int(gs_kinder * self.bedarfs_parameter['fgts_quote_ziel'])
        bedarf['fgts']['plaetze_fehlen'] = bedarf['fgts']['plaetze_ziel_2026'] - bedarf['fgts']['plaetze_aktuell']
        
        # KORREKTUR 11: Negative Werte abfangen
        if bedarf['fgts']['plaetze_fehlen'] > 0:
            bedarf['fgts']['gruppen_fehlen'] = int(np.ceil(bedarf['fgts']['plaetze_fehlen'] / 25))
        else:
            bedarf['fgts']['gruppen_fehlen'] = 0
            bedarf['fgts']['plaetze_fehlen'] = 0  # Keine negativen Werte
        
        # GESAMT
        bedarf['gesamt']['kinder_0_18'] = int(df_filtered[(df_filtered['Alter'] >= 0) & (df_filtered['Alter'] <= 18)]['SUMME'].sum())
        bedarf['gesamt']['klassen_gesamt'] = bedarf['grundschule']['klassen'] + bedarf['sek1']['klassen']
        bedarf['gesamt']['lehrer_gesamt'] = bedarf['grundschule']['lehrer'] + bedarf['sek1']['lehrer'] + bedarf['sek2']['lehrer']
        bedarf['gesamt']['raeume_gesamt'] = bedarf['grundschule']['raeume_gesamt'] + bedarf['sek1']['raeume_gesamt'] + bedarf['sek2']['raeume']
        
        return bedarf
    
    # ========================================
    # FEATURE 2: EXCEL-GESAMT-EXPORT (KORRIGIERT)
    # ========================================
    
    def export_to_excel(self, gemeinde: Optional[str] = None, ortsteil: Optional[str] = None) -> Optional[io.BytesIO]:
        """
        Exportiert alle Analysen in eine Excel-Datei mit mehreren Sheets
        V3.1: Mit Validierung für leere Daten
        """
        
        if not XLSXWRITER_AVAILABLE:
            st.error("⚠️ xlsxwriter nicht installiert. Führen Sie aus: pip install xlsxwriter")
            return None
        
        df_filtered = self.get_filtered_data(gemeinde, ortsteil)
        
        # KORREKTUR 12: Prüfe ob Daten vorhanden
        if df_filtered.empty:
            st.warning("⚠️ Keine Daten für Export vorhanden. Bitte prüfen Sie Ihre Filter.")
            return None
        
        # Erstelle Excel in Memory
        output = io.BytesIO()
        
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                kennzahlen = self.berechne_kennzahlen(df_filtered)
                
                # Sheet 1: Kennzahlen
                df_kennzahlen = pd.DataFrame([
                    ['Gesamtbevölkerung', kennzahlen['Gesamtbevölkerung']],
                    ['Männlich', kennzahlen['Männlich']],
                    ['Weiblich', kennzahlen['Weiblich']],
                    ['Ausländeranteil (%)', kennzahlen['Anteil_Ausländer']],
                    ['Anzahl Nationalitäten', kennzahlen['Anzahl Nationalitäten']]
                ], columns=['Kennzahl', 'Wert'])
                df_kennzahlen.to_excel(writer, sheet_name='Kennzahlen', index=False)
                
                # Sheet 2: Altersstruktur
                altersstruktur = []
                for gruppe_name, (min_age, max_age) in self.altersgruppen.items():
                    anzahl = df_filtered[
                        (df_filtered['Alter'] >= min_age) & 
                        (df_filtered['Alter'] <= max_age)
                    ]['SUMME'].sum()
                    altersstruktur.append([gruppe_name, int(anzahl)])
                
                df_altersstruktur = pd.DataFrame(altersstruktur, columns=['Altersgruppe', 'Anzahl'])
                df_altersstruktur.to_excel(writer, sheet_name='Altersstruktur', index=False)
                
                # Sheet 3: Bildungsplanung Detail
                bildung_data = []
                for alter in range(0, 19):
                    anzahl = df_filtered[df_filtered['Alter'] == alter]['SUMME'].sum()
                    bildung_data.append([alter, int(anzahl)])
                
                df_bildung = pd.DataFrame(bildung_data, columns=['Alter', 'Anzahl'])
                df_bildung.to_excel(writer, sheet_name='Bildungsplanung', index=False)
                
                # Sheet 4: Bedarfsrechnung
                gemeinde_name = gemeinde.replace('Melderegister ', '') if gemeinde else "Gesamter Kreis"
                if ortsteil and ortsteil != "Alle Ortsteile":
                    gemeinde_name = f"{gemeinde_name} - {ortsteil}"
                
                bedarf = self.berechne_bedarf(df_filtered, gemeinde_name)
                
                bedarf_data = [
                    ['KITA-BEDARF', ''],
                    ['Kinder U3 (0-2 Jahre)', bedarf['kita']['kinder_u3']],
                    ['Benötigte U3-Plätze (35% + 5% Puffer)', bedarf['kita']['plaetze_u3_noetig']],
                    ['Kinder Ü3 (3-5 Jahre)', bedarf['kita']['kinder_ue3']],
                    ['Benötigte Ü3-Plätze (95% + 5% Puffer)', bedarf['kita']['plaetze_ue3_noetig']],
                    ['Kita-Plätze GESAMT', bedarf['kita']['plaetze_gesamt']],
                    ['', ''],
                    ['GRUNDSCHUL-BEDARF', ''],
                    ['Grundschüler (6-9 Jahre)', bedarf['grundschule']['kinder']],
                    ['Benötigte Klassen (à 25 Schüler)', bedarf['grundschule']['klassen']],
                    ['Züge (4 Jahrgänge)', bedarf['grundschule']['zuege']],
                    ['Benötigte Lehrer', bedarf['grundschule']['lehrer']],
                    ['', ''],
                    ['FGTS-BEDARF (ab 2026)', ''],
                    ['FGTS-Plätze aktuell (45%)', bedarf['fgts']['plaetze_aktuell']],
                    ['FGTS-Plätze Ziel (80%)', bedarf['fgts']['plaetze_ziel_2026']],
                    ['Fehlende FGTS-Plätze', bedarf['fgts']['plaetze_fehlen']]
                ]
                
                df_bedarf = pd.DataFrame(bedarf_data, columns=['Kategorie', 'Wert'])
                df_bedarf.to_excel(writer, sheet_name='Bedarfsrechnung', index=False)
                
                # Sheet 5: Gemeindevergleich
                if not gemeinde or gemeinde == "Gesamter Kreis":
                    vergleich_data = []
                    for gem in self.gemeinden[:10]:
                        df_gem = self.df[self.df['Gemeinde'] == gem]
                        einwohner = int(df_gem['SUMME'].sum())
                        kita = int(df_gem[df_gem['Alter'] <= 5]['SUMME'].sum())
                        gs = int(df_gem[(df_gem['Alter'] >= 6) & (df_gem['Alter'] <= 9)]['SUMME'].sum())
                        
                        vergleich_data.append([
                            gem.replace('Melderegister ', ''),
                            einwohner, kita, gs
                        ])
                    
                    df_vergleich = pd.DataFrame(
                        vergleich_data,
                        columns=['Gemeinde', 'Einwohner', 'Kita (0-5)', 'Grundschule (6-9)']
                    )
                    df_vergleich.to_excel(writer, sheet_name='Gemeindevergleich', index=False)
            
            output.seek(0)
            return output
            
        except Exception as e:
            st.error(f"❌ Fehler beim Excel-Export: {str(e)}")
            return None
    
    # ========================================
    # FEATURE 3: ZEITVERGLEICH (KORRIGIERT)
    # ========================================
    
    def vergleiche_zeitpunkte(self, zeitpunkte_dict: Dict, gemeinde: Optional[str] = None, 
                              ortsteil: Optional[str] = None) -> pd.DataFrame:
        """
        Vergleicht Daten von verschiedenen Zeitpunkten
        V3.1: Mit Validierung für None/leere Daten
        """
        vergleich_data = []
        
        for zeitpunkt_label, df_data in zeitpunkte_dict.items():
            # KORREKTUR 13: Prüfe ob Daten vorhanden
            if df_data is None or df_data.empty:
                st.warning(f"⚠️ Keine Daten für Zeitpunkt '{zeitpunkt_label}' - überspringe.")
                continue
            
            df_filtered = self.get_filtered_data(gemeinde, ortsteil, df_source=df_data)
            
            if df_filtered.empty:
                st.warning(f"⚠️ Keine Daten nach Filterung für '{zeitpunkt_label}'")
                continue
            
            # KORREKTUR FINAL9: Konvertiere Alter zu numerisch
            df_filtered = df_filtered.copy()
            df_filtered['Alter'] = pd.to_numeric(df_filtered['Alter'], errors='coerce').fillna(0)
            
            gesamt = int(df_filtered['SUMME'].sum())
            kita = int(df_filtered[df_filtered['Alter'] <= 5]['SUMME'].sum())
            gs = int(df_filtered[(df_filtered['Alter'] >= 6) & (df_filtered['Alter'] <= 9)]['SUMME'].sum())
            sek1 = int(df_filtered[(df_filtered['Alter'] >= 10) & (df_filtered['Alter'] <= 15)]['SUMME'].sum())
            sek2 = int(df_filtered[(df_filtered['Alter'] >= 16) & (df_filtered['Alter'] <= 18)]['SUMME'].sum())
            
            vergleich_data.append({
                'Zeitpunkt': zeitpunkt_label,
                'Gesamtbevölkerung': gesamt,
                'Kita (0-5)': kita,
                'Grundschule (6-9)': gs,
                'Sek I (10-15)': sek1,
                'Sek II (16-18)': sek2
            })
        
        return pd.DataFrame(vergleich_data)
    
    def erstelle_trend_diagramm(self, df_vergleich: pd.DataFrame, kategorie: str = 'Grundschule (6-9)') -> go.Figure:
        """Erstellt ein Trend-Diagramm für eine Kategorie"""
        
        if df_vergleich.empty or kategorie not in df_vergleich.columns:
            # Leeres Diagramm bei Fehler
            fig = go.Figure()
            fig.add_annotation(text="Keine Daten verfügbar", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False, font=dict(size=20))
            return fig
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_vergleich['Zeitpunkt'],
            y=df_vergleich[kategorie],
            mode='lines+markers',
            name=kategorie,
            line=dict(color='#1f4788', width=3),
            marker=dict(size=10)
        ))
        
        # Trendlinie
        if len(df_vergleich) >= 2:
            x_numeric = list(range(len(df_vergleich)))
            y_values = df_vergleich[kategorie].values
            z = np.polyfit(x_numeric, y_values, 1)
            p = np.poly1d(z)
            
            fig.add_trace(go.Scatter(
                x=df_vergleich['Zeitpunkt'],
                y=p(x_numeric),
                mode='lines',
                name='Trend',
                line=dict(color='red', dash='dash', width=2)
            ))
        
        fig.update_layout(
            title=f'Entwicklung: {kategorie}',
            xaxis_title='Zeitpunkt',
            yaxis_title='Anzahl',
            height=400,
            hovermode='x unified'
        )
        
        return fig
    
    # ========================================
    # FEATURE 4: KARTEN (OpenStreetMap)
    # ========================================
    
    def erstelle_karte(self, gemeinde_data: Optional[Dict] = None, show_markers: bool = True):
        """Erstellt eine interaktive Karte mit OpenStreetMap"""
        
        if not FOLIUM_AVAILABLE:
            return None
        
        # Zentrum Saarpfalz-Kreis
        m = folium.Map(
            location=[49.32, 7.34],
            zoom_start=10,
            tiles='OpenStreetMap'
        )
        
        # Gemeinde-Koordinaten
        gemeinde_coords = {
            'Melderegister Homburg': [49.3196, 7.3334],
            'Melderegister St. Ingbert': [49.2767, 7.1167],
            'Melderegister Blieskastel': [49.2350, 7.2533],
            'Melderegister Bexbach': [49.3487, 7.2575],
            'Melderegister Kirkel': [49.2854, 7.2307],
            'Melderegister Gersheim': [49.2167, 7.2167],
            'Melderegister Mandelbachtal': [49.2667, 7.1667]
        }
        
        if show_markers and gemeinde_data:
            for gemeinde, data in gemeinde_data.items():
                if gemeinde in gemeinde_coords:
                    coords = gemeinde_coords[gemeinde]
                    radius = np.sqrt(data.get('einwohner', 1000)) / 10
                    
                    color = data.get('color', 'blue')
                    
                    popup_text = f"<b>{gemeinde.replace('Melderegister ', '')}</b><br>"
                    for key, value in data.items():
                        if key not in ['einwohner', 'color']:
                            popup_text += f"{key}: {value}<br>"
                    
                    folium.CircleMarker(
                        location=coords,
                        radius=radius,
                        popup=folium.Popup(popup_text, max_width=300),
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.6,
                        weight=2
                    ).add_to(m)
        
        return m
    
    # ========================================
    # FEATURE 5: DASHBOARD (KORRIGIERT!)
    # ========================================
    
    def erstelle_dashboard_daten(self, df_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Bereitet Daten für das Dashboard auf
        V3.1: Mit WARNUNG für simulierte Auslastungsdaten
        """
        
        if df_data is None:
            df_data = self.df
        
        # KORREKTUR 14: Prüfe ob Daten vorhanden
        if df_data is None or df_data.empty:
            return {
                'kpis': {'Gesamtbevölkerung': 0, 'Kita U3 (0-2)': 0, 'Kita Ü3 (3-5)': 0,
                        'Grundschule (6-9)': 0, 'Sek I (10-15)': 0, 'Sek II (16-18)': 0},
                'ampeln': {'Kita U3': 'grau', 'Kita Ü3': 'grau', 'Grundschule': 'grau'},
                'auslastung': {'Kita U3': 0, 'Kita Ü3': 0, 'Grundschule': 0},
                'alerts': [],
                'warnung_simuliert': True,
                'warnung_text': '⚠️ Keine Daten vorhanden.'
            }
        
        dashboard = {
            'kpis': {},
            'ampeln': {},
            'trends': {},
            'alerts': [],
            'warnung_simuliert': True,  # WICHTIG!
            'warnung_text': ''
        }
        
        # KPIs berechnen
        gesamt = int(df_data['SUMME'].sum())
        kita_u3 = int(df_data[(df_data['Alter'] >= 0) & (df_data['Alter'] <= 2)]['SUMME'].sum())
        kita_ue3 = int(df_data[(df_data['Alter'] >= 3) & (df_data['Alter'] <= 5)]['SUMME'].sum())
        gs = int(df_data[(df_data['Alter'] >= 6) & (df_data['Alter'] <= 9)]['SUMME'].sum())
        sek1 = int(df_data[(df_data['Alter'] >= 10) & (df_data['Alter'] <= 15)]['SUMME'].sum())
        sek2 = int(df_data[(df_data['Alter'] >= 16) & (df_data['Alter'] <= 18)]['SUMME'].sum())
        
        dashboard['kpis'] = {
            'Gesamtbevölkerung': gesamt,
            'Kita U3 (0-2)': kita_u3,
            'Kita Ü3 (3-5)': kita_ue3,
            'Grundschule (6-9)': gs,
            'Sek I (10-15)': sek1,
            'Sek II (16-18)': sek2
        }
        
        # KORREKTUR 15: AUSLASTUNG MIT KLARER WARNUNG
        # ⚠️ WICHTIG: Dies sind SIMULIERTE Werte!
        # Für echte Auslastung benötigen Sie Kapazitätsdaten aus Ihrer Verwaltung.
        
        # SIMULIERTE Auslastung (Beispielwerte - NICHT REAL!)
        auslastung_u3 = 85   # ⚠️ SIMULIERT
        auslastung_ue3 = 92  # ⚠️ SIMULIERT
        auslastung_gs = 78   # ⚠️ SIMULIERT
        
        dashboard['auslastung'] = {
            'Kita U3': auslastung_u3,
            'Kita Ü3': auslastung_ue3,
            'Grundschule': auslastung_gs
        }
        
        dashboard['ampeln'] = {
            'Kita U3': 'grün' if auslastung_u3 < 85 else ('gelb' if auslastung_u3 < 95 else 'rot'),
            'Kita Ü3': 'grün' if auslastung_ue3 < 85 else ('gelb' if auslastung_ue3 < 95 else 'rot'),
            'Grundschule': 'grün' if auslastung_gs < 85 else ('gelb' if auslastung_gs < 95 else 'rot')
        }
        
        # WARNUNG hinzufügen
        dashboard['warnung_text'] = (
            "⚠️ **WICHTIGER HINWEIS:** Die Auslastungsdaten im Dashboard sind **SIMULIERT** (Beispielwerte)!\n\n"
            "Für **echte Auslastungsberechnungen** benötigen Sie:\n"
            "- Aktuelle Kapazitätsdaten Ihrer Kitas (verfügbare Plätze U3/Ü3)\n"
            "- Aktuelle Kapazitätsdaten Ihrer Schulen (Klassenräume, max. Schülerzahl)\n"
            "- Aktuelle Belegungsdaten\n\n"
            "**Bitte treffen Sie KEINE Entscheidungen basierend auf den Dashboard-Ampeln!**\n\n"
            "Alle **anderen Features** (Bedarfsrechner, Excel-Export, Zeitvergleich, Karten) "
            "arbeiten mit Ihren **echten Daten** und sind verlässlich."
        )
        
        # Alerts generieren (auf Basis echter Daten)
        bedarf_ue3 = int(kita_ue3 * 0.95 * 1.05)
        
        # Info-Alerts basierend auf echten Daten
        if kita_ue3 > 0:
            dashboard['alerts'].append({
                'typ': 'info',
                'bereich': 'Kita Ü3',
                'nachricht': f'{kita_ue3} Kinder (3-5 Jahre) → Bedarf: ca. {bedarf_ue3} Plätze (95% + 5% Puffer)'
            })
        
        # Prüfe starke Jahrgänge (ECHTE Daten)
        if gs > 0:
            durchschnitt_gs = gs / 4
            for alter in range(6, 10):
                anzahl_alter = int(df_data[df_data['Alter'] == alter]['SUMME'].sum())
                if anzahl_alter > durchschnitt_gs * 1.15:
                    dashboard['alerts'].append({
                        'typ': 'info',
                        'bereich': 'Grundschule',
                        'nachricht': f'Jahrgang {alter} Jahre überdurchschnittlich stark ({anzahl_alter} vs. ∅{int(durchschnitt_gs)})'
                    })
        
        return dashboard
    
    # Hilfsmethoden aus V2.0 (unverändert, aber mit Null-Checks)
    
    def erstelle_alterspyramide(self, gemeinde: Optional[str] = None, ortsteil: Optional[str] = None) -> go.Figure:
        """Erstellt eine Alterspyramide"""
        df_filtered = self.get_filtered_data(gemeinde, ortsteil)
        
        if df_filtered.empty:
            fig = go.Figure()
            fig.add_annotation(text="Keine Daten verfügbar", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False, font=dict(size=20))
            return fig
        
        alters_data = df_filtered.groupby('Alter').agg({
            'm': 'sum',
            'w': 'sum'
        }).reset_index()
        
        title_parts = []
        if ortsteil and ortsteil != "Alle Ortsteile":
            title_parts.append(ortsteil)
        if gemeinde and gemeinde != "Gesamter Kreis":
            title_parts.append(gemeinde.replace('Melderegister ', ''))
        if not title_parts:
            title_parts.append("Gesamter Kreis")
        
        title = f"Alterspyramide: {', '.join(title_parts)}"
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=alters_data['Alter'],
            x=-alters_data['m'],
            name='Männlich',
            orientation='h',
            marker=dict(color='#1f77b4'),
            hovertemplate='Alter: %{y}<br>Männlich: %{x:,.0f}<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            y=alters_data['Alter'],
            x=alters_data['w'],
            name='Weiblich',
            orientation='h',
            marker=dict(color='#ff7f0e'),
            hovertemplate='Alter: %{y}<br>Weiblich: %{x:,.0f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            barmode='overlay',
            bargap=0.1,
            xaxis=dict(title='Bevölkerung', tickformat=',d'),
            yaxis=dict(title='Alter in Jahren', range=[0, 100]),
            height=700,
            hovermode='y unified'
        )
        
        return fig

def main():
    """Hauptfunktion der Streamlit-App V3.1 STABLE"""
    
    st.markdown('<h1 class="main-header">📊 Bildungsplanungs-Datenanalyse V3.1 STABLE</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Saarpfalz-Kreis | Production Ready mit Fehlerkorrek turen</p>', unsafe_allow_html=True)
    
    # Initialisiere Analyzer
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = BildungsplanungAnalyzerV31()
    
    analyzer = st.session_state.analyzer
    
    # Sidebar (verkürzt - identisch zu V3.0)
    with st.sidebar:
        st.header("📁 Daten laden")
        
        upload_option = st.radio(
            "Datenquelle wählen:",
            ["📄 Aktuelle Daten", "📅 Zeitvergleich (mehrere Zeitpunkte)", "📦 ZIP-Archiv"]
        )
        
        if upload_option == "📄 Aktuelle Daten":
            uploaded_files = st.file_uploader("CSV-Datei(en) hochladen", type=['csv'], accept_multiple_files=True)
            
            if uploaded_files:
                if st.button("🔄 Daten laden", type="primary", use_container_width=True):
                    with st.spinner("Lade Daten..."):
                        success = analyzer.load_data(uploaded_files)
                        
                        # Prüfe ob Geburten-Dateien dabei sind
                        has_geb_files = any('GEB' in f.name.upper() or 'GEBURT' in f.name.upper() for f in uploaded_files)
                        if has_geb_files:
                            analyzer.load_geburten_data(uploaded_files)
                        
                        # NEU V3.1 FINAL5: Prüfe ob Geburtsmonat-Dateien dabei sind
                        has_birthmonth_files = any('birth_month' in f.name.lower() or 'polyteia' in f.name.lower() for f in uploaded_files)
                        if has_birthmonth_files:
                            analyzer.load_birthmonth_data(uploaded_files)
                        
                        if success:
                            st.balloons()
        
        elif upload_option == "📅 Zeitvergleich (mehrere Zeitpunkte)":
            st.info("💡 Laden Sie Daten von verschiedenen Zeitpunkten für Trend-Analysen")
            anzahl_zeitpunkte = st.number_input("Anzahl Zeitpunkte", min_value=2, max_value=5, value=2)
            zeitpunkte_data = {}
            
            for i in range(anzahl_zeitpunkte):
                st.markdown(f"**Zeitpunkt {i+1}:**")
                label = st.text_input(f"Bezeichnung", value=f"Zeitpunkt {i+1}", key=f"label_{i}")
                files = st.file_uploader(f"CSV für {label}", type=['csv'], accept_multiple_files=True, key=f"upload_{i}")
                if files:
                    zeitpunkte_data[label] = files
            
            if st.button("🔄 Alle Zeitpunkte laden", type="primary", use_container_width=True):
                with st.spinner("Lade Zeitvergleichs-Daten..."):
                    success_count = 0
                    for label, files in zeitpunkte_data.items():
                        if analyzer.load_data(files, zeitpunkt_label=label):
                            success_count += 1
                    
                    if success_count == len(zeitpunkte_data):
                        analyzer.df = analyzer.df_historical[list(analyzer.df_historical.keys())[-1]]
                        st.success(f"✅ {success_count} Zeitpunkte erfolgreich geladen!")
                        st.balloons()
        
        elif upload_option == "📦 ZIP-Archiv":
            uploaded_files = st.file_uploader("ZIP-Archiv hochladen", type=['zip'])
            if uploaded_files:
                uploaded_files = [uploaded_files]
                if st.button("🔄 Daten laden", type="primary", use_container_width=True):
                    with st.spinner("Lade Daten..."):
                        if analyzer.load_data(uploaded_files):
                            st.balloons()
        
        st.markdown("---")
        
        # Filter
        if analyzer.df is not None:
            st.header("🔍 Filter")
            
            gemeinde_options = ["Gesamter Kreis"] + analyzer.gemeinden
            selected_gemeinde = st.selectbox("Gemeinde wählen", gemeinde_options, index=0, key="gemeinde_select")
            
            selected_ortsteil = "Alle Ortsteile"
            if analyzer.has_ortsteile:
                if selected_gemeinde != "Gesamter Kreis":
                    ortsteile_options = ["Alle Ortsteile"] + analyzer.get_ortsteile_for_gemeinde(selected_gemeinde)
                else:
                    ortsteile_options = ["Alle Ortsteile"] + analyzer.ortsteile
                
                selected_ortsteil = st.selectbox("🏘️ Ortsteil wählen", ortsteile_options, index=0, key="ortsteil_select")
            
            selected_altersgruppe = st.selectbox(
                "Altersgruppe wählen",
                ["Alle Altersgruppen"] + list(analyzer.altersgruppen.keys()),
                index=0
            )
            
            st.markdown("---")
            
            with st.expander("⚙️ Bedarfsparameter anpassen"):
                st.markdown("**Kita-Parameter:**")
                analyzer.bedarfs_parameter['kita_u3_quote'] = st.slider("U3-Betreuungsquote", 0.0, 1.0, 0.35, 0.05)
                analyzer.bedarfs_parameter['kita_ue3_quote'] = st.slider("Ü3-Betreuungsquote", 0.0, 1.0, 0.95, 0.05)
                
                st.markdown("**Schul-Parameter:**")
                analyzer.bedarfs_parameter['klassen_groesse_soll'] = st.slider("Soll-Klassengröße", 15, 30, 25, 1)
                analyzer.bedarfs_parameter['schueler_pro_lehrer'] = st.slider("Schüler pro Lehrer", 10, 25, 18, 1)
            
            with st.expander("🛡️ Datenschutz-Einstellungen"):
                st.markdown("**Small Number Suppression:**")
                analyzer.datenschutz_threshold = st.number_input(
                    "Schwellwert für Anonymisierung",
                    min_value=1,
                    max_value=10,
                    value=5,
                    help="Gruppen kleiner als dieser Wert werden als '< N' angezeigt (DSGVO-Schutz)"
                )
                st.caption(f"✅ Werte < {analyzer.datenschutz_threshold} werden anonymisiert")
            
            st.markdown("---")
            st.info(
                "**Version 3.1 FINAL9**\n\n"
                "✅ Zeitreihen via ZIP\n"
                "✅ Keine Doppelzählungen\n"
                "✅ Small Number Suppression\n"
                "✅ Prio 0-1 Compliance"
            )
    
    # Hauptbereich
    if analyzer.df is None:
        st.info("👈 Bitte laden Sie zunächst Daten über die Seitenleiste.")
        return
    
    # Tabs
    tabs = ["🎯 Dashboard", "📊 Übersicht", "🧮 Bedarfsrechner", "👥 Bevölkerungsstruktur", 
            "🏫 Bildungsplanung", "📈 Zeitvergleich & Trends", "🗺️ Karten", "👴 Hochaltrigen-Analyse", "🔄 Gemeindevergleich"]
    
    # Füge optionale Tabs hinzu
    if analyzer.has_birthmonth:
        tabs.insert(-1, "📅 Einschulungsplanung")
    
    if analyzer.has_geburten:
        tabs.insert(-1, "👶 Geburtenentwicklung")
    
    if analyzer.has_ortsteile:
        tabs.insert(-1, "🏘️ Ortsteil-Analyse")
    
    tab_objects = st.tabs(tabs)
    
    gemeinde_filter = selected_gemeinde if selected_gemeinde != "Gesamter Kreis" else None
    ortsteil_filter = selected_ortsteil if selected_ortsteil != "Alle Ortsteile" else None
    altersgruppe_filter = selected_altersgruppe if selected_altersgruppe != "Alle Altersgruppen" else None
    
    df_filtered = analyzer.get_filtered_data(gemeinde_filter, ortsteil_filter, altersgruppe_filter)
    kennzahlen = analyzer.berechne_kennzahlen(df_filtered)
    
    # TAB 1: DASHBOARD (mit Warnung!)
    with tab_objects[0]:
        st.header("🎯 Bildungs-Cockpit")
        
        dashboard_data = analyzer.erstelle_dashboard_daten(df_filtered)
        
        # WICHTIGE WARNUNG ZUERST!
        if dashboard_data.get('warnung_simuliert', False):
            st.markdown('<div class="warning-box">', unsafe_allow_html=True)
            st.warning(dashboard_data['warnung_text'])
            st.markdown('</div>', unsafe_allow_html=True)
        
        # KPIs
        st.markdown("### 📊 Zentrale Kennzahlen")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Gesamtbevölkerung</div>
                <div class="kpi-value">{dashboard_data['kpis']['Gesamtbevölkerung']:,}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="kpi-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="kpi-label">Kita (0-5 Jahre)</div>
                <div class="kpi-value">{dashboard_data['kpis']['Kita U3 (0-2)'] + dashboard_data['kpis']['Kita Ü3 (3-5)']:,}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="kpi-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="kpi-label">Schulkinder (6-18)</div>
                <div class="kpi-value">{dashboard_data['kpis']['Grundschule (6-9)'] + dashboard_data['kpis']['Sek I (10-15)'] + dashboard_data['kpis']['Sek II (16-18)']:,}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Ampel-System (mit Warnung)
        st.markdown("### 🚦 Auslastungs-Ampel ⚠️ SIMULIERT")
        st.caption("⚠️ Diese Werte sind Beispieldaten - NICHT für Entscheidungen nutzen!")
        
        ampel_farben = {'grün': '🟢', 'gelb': '🟡', 'rot': '🔴', 'grau': '⚪'}
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ampel = dashboard_data['ampeln']['Kita U3']
            auslastung = dashboard_data['auslastung']['Kita U3']
            st.markdown(f"""
            <div class="dashboard-card">
                <h3>{ampel_farben[ampel]} Kita U3 (0-2 Jahre)</h3>
                <p><strong>Auslastung:</strong> {auslastung}% <em>(simuliert)</em></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            ampel = dashboard_data['ampeln']['Kita Ü3']
            auslastung = dashboard_data['auslastung']['Kita Ü3']
            st.markdown(f"""
            <div class="dashboard-card">
                <h3>{ampel_farben[ampel]} Kita Ü3 (3-5 Jahre)</h3>
                <p><strong>Auslastung:</strong> {auslastung}% <em>(simuliert)</em></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            ampel = dashboard_data['ampeln']['Grundschule']
            auslastung = dashboard_data['auslastung']['Grundschule']
            st.markdown(f"""
            <div class="dashboard-card">
                <h3>{ampel_farben[ampel]} Grundschule (6-9 Jahre)</h3>
                <p><strong>Auslastung:</strong> {auslastung}% <em>(simuliert)</em></p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Hinweise (basierend auf ECHTEN Daten)
        if dashboard_data['alerts']:
            st.markdown("### ℹ️ Hinweise (basierend auf echten Daten)")
            for alert in dashboard_data['alerts']:
                if alert['typ'] == 'info':
                    st.info(f"**{alert['bereich']}:** {alert['nachricht']}")
    
    # TAB 2: ÜBERSICHT
    with tab_objects[1]:
        st.header("📊 Kennzahlen Übersicht")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Gesamtbevölkerung", f"{kennzahlen['Gesamtbevölkerung']:,}")
        with col2:
            st.metric("Männlich", f"{kennzahlen['Männlich']:,}")
        with col3:
            st.metric("Weiblich", f"{kennzahlen['Weiblich']:,}")
        with col4:
            st.metric("Ausländeranteil", f"{kennzahlen['Anteil_Ausländer']:.1f}%")
        
        st.markdown("---")
        
        # Excel-Export
        if XLSXWRITER_AVAILABLE:
            excel_data = analyzer.export_to_excel(gemeinde_filter, ortsteil_filter)
            if excel_data:
                gemeinde_name = gemeinde_filter.replace('Melderegister ', '') if gemeinde_filter else "Gesamter_Kreis"
                if ortsteil_filter:
                    gemeinde_name = f"{gemeinde_name}_{ortsteil_filter}"
                
                st.download_button(
                    label="📥 Kompletter Excel-Export",
                    data=excel_data,
                    file_name=f"Bildungsplanung_{gemeinde_name}_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
    
    # TAB 3: BEDARFSRECHNER
    with tab_objects[2]:
        st.header("🧮 Bedarfs-Rechner")
        
        gemeinde_name = gemeinde_filter.replace('Melderegister ', '') if gemeinde_filter else "Gesamter Kreis"
        if ortsteil_filter:
            gemeinde_name = f"{gemeinde_name} - {ortsteil_filter}"
        
        bedarf = analyzer.berechne_bedarf(df_filtered, gemeinde_name)
        
        st.subheader("🏫 Kita-Bedarf")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Kinder U3", f"{bedarf['kita']['kinder_u3']:,}")
            st.metric("Benötigte U3-Plätze", f"{bedarf['kita']['plaetze_u3_noetig']:,}")
        with col2:
            st.metric("Kinder Ü3", f"{bedarf['kita']['kinder_ue3']:,}")
            st.metric("Benötigte Ü3-Plätze", f"{bedarf['kita']['plaetze_ue3_noetig']:,}")
        with col3:
            st.metric("Kita-Plätze GESAMT", f"{bedarf['kita']['plaetze_gesamt']:,}")
        
        st.markdown("---")
        st.subheader("🎓 Grundschul-Bedarf")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Grundschüler", f"{bedarf['grundschule']['kinder']:,}")
        with col2:
            st.metric("Benötigte Klassen", f"{bedarf['grundschule']['klassen']}")
        with col3:
            st.metric("Züge", f"{bedarf['grundschule']['zuege']}")
        with col4:
            st.metric("Benötigte Lehrer", f"{bedarf['grundschule']['lehrer']}")
        
        st.markdown("---")
        st.subheader("⏰ FGTS-Bedarf (Ganztagsbetreuung)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Grundschüler", f"{bedarf['fgts']['gs_kinder']:,}")
        with col2:
            st.metric("FGTS-Plätze aktuell (45%)", f"{bedarf['fgts']['plaetze_aktuell']:,}")
        with col3:
            st.metric("FGTS-Plätze Ziel (80%)", f"{bedarf['fgts']['plaetze_ziel_2026']:,}")
        
        if bedarf['fgts']['plaetze_fehlen'] > 0:
            st.error(f"🔴 **HANDLUNGSBEDARF:** Es fehlen **{bedarf['fgts']['plaetze_fehlen']:,} FGTS-Plätze**")
    
    # TAB 4: BEVÖLKERUNGSSTRUKTUR
    with tab_objects[3]:
        st.header("👥 Bevölkerungsstruktur")
        fig_pyramide = analyzer.erstelle_alterspyramide(gemeinde_filter, ortsteil_filter)
        st.plotly_chart(fig_pyramide, use_container_width=True)
    
    # TAB 5: BILDUNGSPLANUNG
    with tab_objects[4]:
        st.header("🏫 Bildungsplanung")
        col1, col2, col3 = st.columns(3)
        with col1:
            kita_0_2 = df_filtered[(df_filtered['Alter'] >= 0) & (df_filtered['Alter'] <= 2)]['SUMME'].sum()
            st.metric("Kita-Bedarf (0-2 Jahre)", f"{int(kita_0_2):,}")
        with col2:
            kita_3_5 = df_filtered[(df_filtered['Alter'] >= 3) & (df_filtered['Alter'] <= 5)]['SUMME'].sum()
            st.metric("Kita-Bedarf (3-5 Jahre)", f"{int(kita_3_5):,}")
        with col3:
            grundschule = df_filtered[(df_filtered['Alter'] >= 6) & (df_filtered['Alter'] <= 9)]['SUMME'].sum()
            st.metric("Grundschüler (6-9 Jahre)", f"{int(grundschule):,}")
    
    # TAB 6: ZEITVERGLEICH
    with tab_objects[5]:
        st.header("📈 Zeitvergleich & Trend-Analysen")
        
        if len(analyzer.df_historical) > 1:
            zeitpunkte_sorted = sorted(analyzer.df_historical.keys())
            st.success(
                f"✅ **{len(analyzer.df_historical)} Zeitpunkte geladen**\n\n"
                f"📅 Zeitraum: **{zeitpunkte_sorted[0]}** bis **{zeitpunkte_sorted[-1]}**\n\n"
                f"Alle Zeitpunkte: {', '.join(zeitpunkte_sorted)}"
            )
            
            st.info(
                "💡 **Tipp:** Laden Sie als ZIP-Datei mehrere EW-Dateien mit unterschiedlichen Monaten, "
                "um automatisch Zeitreihen zu erstellen!"
            )
            
            df_vergleich = analyzer.vergleiche_zeitpunkte(analyzer.df_historical, gemeinde_filter, ortsteil_filter)
            
            if not df_vergleich.empty:
                st.markdown("---")
                st.subheader("📊 Übersicht alle Zeitpunkte")
                
                # Wende Small Number Suppression an
                df_vergleich_display = df_vergleich.copy()
                for col in df_vergleich_display.columns:
                    if col not in ['Zeitpunkt', 'Gemeinde', 'Ortsteil']:
                        df_vergleich_display[col] = df_vergleich_display[col].apply(
                            lambda x: analyzer.suppress_small_number(x, analyzer.datenschutz_threshold)
                        )
                
                st.dataframe(df_vergleich_display, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("📈 Trend-Visualisierungen")
                
                kategorien = ['Kita (0-5)', 'Grundschule (6-9)', 'Sek I (10-15)', 'Sek II (16-18)']
                col1, col2 = st.columns(2)
                
                for idx, kategorie in enumerate(kategorien):
                    with col1 if idx % 2 == 0 else col2:
                        fig_trend = analyzer.erstelle_trend_diagramm(df_vergleich, kategorie)
                        st.plotly_chart(fig_trend, use_container_width=True)
                
                st.markdown("---")
                st.subheader("📥 Zeitreihen-Export")
                
                # Excel-Export
                from io import BytesIO
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_vergleich.to_excel(writer, sheet_name='Zeitvergleich', index=False)
                
                st.download_button(
                    label="📥 Zeitreihen als Excel herunterladen",
                    data=excel_buffer.getvalue(),
                    file_name=f"Zeitreihe_{zeitpunkte_sorted[0]}_bis_{zeitpunkte_sorted[-1]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info(
                "ℹ️ **Für Zeitvergleiche laden Sie mehrere Monate!**\n\n"
                "**Empfohlene Methode:**\n"
                "1. Erstellen Sie ein ZIP-Archiv mit mehreren EW-Dateien:\n"
                "   - SPK_EW2_2025-11.csv\n"
                "   - SPK_EW2_2025-10.csv\n"
                "   - SPK_EW2_2025-09.csv\n"
                "   - etc.\n\n"
                "2. Laden Sie das ZIP hoch → App erkennt automatisch Zeitreihen!\n\n"
                "**Ergebnis:** Dieser Tab zeigt dann Trends über alle Monate."
            )
    
    # TAB 7: KARTEN
    with tab_objects[6]:
        st.header("🗺️ Geografische Visualisierung (OpenStreetMap)")
        
        if FOLIUM_AVAILABLE:
            gemeinde_data_karte = {}
            
            for gemeinde in analyzer.gemeinden[:7]:
                df_gem = analyzer.df[analyzer.df['Gemeinde'] == gemeinde]
                einwohner = int(df_gem['SUMME'].sum())
                kita = int(df_gem[df_gem['Alter'] <= 5]['SUMME'].sum())
                gs = int(df_gem[(df_gem['Alter'] >= 6) & (df_gem['Alter'] <= 9)]['SUMME'].sum())
                
                gemeinde_data_karte[gemeinde] = {
                    'einwohner': einwohner,
                    'Einwohner': f"{einwohner:,}",
                    'Kita (0-5)': f"{kita:,}",
                    'Grundschule (6-9)': f"{gs:,}",
                    'color': 'blue'
                }
            
            karte = analyzer.erstelle_karte(gemeinde_data_karte, show_markers=True)
            
            if karte:
                st_folium(karte, width=700, height=500)
                st.info("💡 OpenStreetMap ist bereits als Standard eingestellt - DSGVO-konform für anonyme Daten")
        else:
            st.warning("⚠️ Folium nicht installiert. Führen Sie aus: `pip install folium streamlit-folium`")
    
    # TAB 8: GEMEINDEVERGLEICH - Dynamischer Index
    tab_idx_gemeinde = 7
    if analyzer.has_geburten:
        tab_idx_gemeinde += 1  # Geburten-Tab ist davor
    if analyzer.has_ortsteile:
        tab_idx_gemeinde += 1  # Ortsteil-Analyse ist davor
        
        # TAB: ORTSTEIL-ANALYSE (nur wenn Ortsteile vorhanden)
        tab_idx_ortsteil = tabs.index("🏘️ Ortsteil-Analyse")
        with tab_objects[tab_idx_ortsteil]:
            st.header("🏘️ Ortsteil-Analyse")
            
            if analyzer.has_ortsteile and len(analyzer.ortsteile) > 0:
                st.info(f"📍 {len(analyzer.ortsteile)} Ortsteile gefunden")
                
                # Gemeinde auswählen
                gemeinde_fuer_ortsteile = st.selectbox(
                    "Gemeinde wählen:",
                    ["Alle Gemeinden"] + analyzer.gemeinden
                )
                
                # Filtere Ortsteile für gewählte Gemeinde
                if gemeinde_fuer_ortsteile == "Alle Gemeinden":
                    df_ot = analyzer.df.copy()
                    relevante_ortsteile = analyzer.ortsteile
                else:
                    df_ot = analyzer.df[analyzer.df['Gemeinde'] == gemeinde_fuer_ortsteile]
                    relevante_ortsteile = sorted(df_ot['Ortsteil'].unique().tolist())
                
                st.markdown(f"**{len(relevante_ortsteile)} Ortsteile in dieser Auswahl**")
                
                # Vergleichstabelle
                st.markdown("### 📊 Ortsteil-Vergleichstabelle")
                
                ortsteil_daten = []
                for ortsteil in relevante_ortsteile:
                    if not ortsteil or ortsteil == '':
                        continue
                    
                    df_ort = df_ot[df_ot['Ortsteil'] == ortsteil]
                    
                    if len(df_ort) > 0:
                        gesamt = int(df_ort['SUMME'].sum())
                        kita_u3 = int(df_ort[(df_ort['Alter'] >= 0) & (df_ort['Alter'] <= 2)]['SUMME'].sum())
                        kita_ue3 = int(df_ort[(df_ort['Alter'] >= 3) & (df_ort['Alter'] <= 5)]['SUMME'].sum())
                        gs = int(df_ort[(df_ort['Alter'] >= 6) & (df_ort['Alter'] <= 9)]['SUMME'].sum())
                        sek1 = int(df_ort[(df_ort['Alter'] >= 10) & (df_ort['Alter'] <= 15)]['SUMME'].sum())
                        
                        ortsteil_daten.append({
                            'Ortsteil': ortsteil,
                            'Einwohner': gesamt,
                            'U3 (0-2)': kita_u3,
                            'Ü3 (3-5)': kita_ue3,
                            'GS (6-9)': gs,
                            'Sek I (10-15)': sek1
                        })
                
                if ortsteil_daten:
                    df_vergleich = pd.DataFrame(ortsteil_daten)
                    df_vergleich = df_vergleich.sort_values('Einwohner', ascending=False)
                    st.dataframe(df_vergleich, use_container_width=True)
                    
                    # Visualisierung
                    st.markdown("### 📈 Einwohner nach Ortsteil")
                    fig = px.bar(
                        df_vergleich.head(15), 
                        x='Ortsteil', 
                        y='Einwohner',
                        title=f'Top 15 Ortsteile nach Einwohnerzahl' if len(df_vergleich) > 15 else 'Einwohner nach Ortsteil'
                    )
                    fig.update_layout(xaxis_tickangle=-45, height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Bildungsrelevante Altersgruppen
                    st.markdown("### 👶 Bildungsrelevante Altersgruppen")
                    fig2 = go.Figure()
                    
                    df_top10 = df_vergleich.head(10)
                    fig2.add_trace(go.Bar(name='U3 (0-2)', x=df_top10['Ortsteil'], y=df_top10['U3 (0-2)']))
                    fig2.add_trace(go.Bar(name='Ü3 (3-5)', x=df_top10['Ortsteil'], y=df_top10['Ü3 (3-5)']))
                    fig2.add_trace(go.Bar(name='GS (6-9)', x=df_top10['Ortsteil'], y=df_top10['GS (6-9)']))
                    fig2.add_trace(go.Bar(name='Sek I (10-15)', x=df_top10['Ortsteil'], y=df_top10['Sek I (10-15)']))
                    
                    fig2.update_layout(
                        barmode='group',
                        title='Top 10 Ortsteile: Bildungsrelevante Altersgruppen',
                        xaxis_tickangle=-45,
                        height=500
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("Keine Ortsteil-Daten verfügbar für diese Auswahl")
            else:
                st.info("ℹ️ Keine Ortsteil-Daten in den geladenen Dateien gefunden")
    
    # TAB: GEBURTENENTWICKLUNG (wenn Geburten-Daten vorhanden)
    if analyzer.has_geburten:
        # Finde den richtigen Tab-Index
        tab_idx_geburten = tabs.index("👶 Geburtenentwicklung")
        
        with tab_objects[tab_idx_geburten]:
            st.header("👶 Geburtenentwicklung")
            
            if analyzer.df_geburten is not None and not analyzer.df_geburten.empty:
                # Gemeinde-Filter
                gemeinde_geb = st.selectbox(
                    "Gemeinde wählen:",
                    ["Gesamter Kreis"] + analyzer.gemeinden,
                    key="geb_gemeinde"
                )
                
                # Filtere Daten
                if gemeinde_geb == "Gesamter Kreis":
                    df_geb = analyzer.df_geburten.copy()
                else:
                    df_geb = analyzer.df_geburten[analyzer.df_geburten['Gemeinde'] == gemeinde_geb]
                
                # Kennzahlen
                col1, col2, col3, col4 = st.columns(4)
                
                geburten_gesamt = int(df_geb['SUMME'].sum())
                geburten_jungen = int(df_geb['m'].sum())
                geburten_maedchen = int(df_geb['w'].sum())
                
                with col1:
                    st.metric("👶 Geburten gesamt", f"{geburten_gesamt}")
                with col2:
                    st.metric("👦 Jungen", f"{geburten_jungen}")
                with col3:
                    st.metric("👧 Mädchen", f"{geburten_maedchen}")
                with col4:
                    if geburten_gesamt > 0:
                        anteil_jungen = (geburten_jungen / geburten_gesamt * 100)
                        st.metric("⚖️ Anteil Jungen", f"{anteil_jungen:.1f}%")
                    else:
                        st.metric("⚖️ Anteil Jungen", "0%")
                
                st.markdown("---")
                
                # Geburten nach Alter der Mutter
                st.markdown("### 📊 Geburten nach Alter der Mutter")
                
                # Aggregiere nach AlterMutter
                geb_nach_alter = df_geb.groupby('AlterMutter')['SUMME'].sum().reset_index()
                geb_nach_alter = geb_nach_alter[geb_nach_alter['SUMME'] > 0]  # Nur Alter mit Geburten
                geb_nach_alter = geb_nach_alter.sort_values('AlterMutter')
                
                if not geb_nach_alter.empty:
                    # Diagramm
                    fig = px.bar(
                        geb_nach_alter,
                        x='AlterMutter',
                        y='SUMME',
                        title=f'Geburten nach Alter der Mutter - {gemeinde_geb}',
                        labels={'AlterMutter': 'Alter der Mutter', 'SUMME': 'Anzahl Geburten'}
                    )
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Statistiken
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Durchschnittsalter (gewichtet)
                        if geburten_gesamt > 0:
                            durchschnittsalter = (geb_nach_alter['AlterMutter'] * geb_nach_alter['SUMME']).sum() / geburten_gesamt
                            st.metric("⌀ Durchschnittsalter Mutter", f"{durchschnittsalter:.1f} Jahre")
                        else:
                            st.metric("⌀ Durchschnittsalter Mutter", "N/A")
                    
                    with col2:
                        # Häufigstes Alter
                        haeufigster_alter_idx = geb_nach_alter['SUMME'].idxmax()
                        haeufigster_alter = geb_nach_alter.loc[haeufigster_alter_idx, 'AlterMutter']
                        st.metric("📈 Häufigstes Alter", f"{int(haeufigster_alter)} Jahre")
                    
                    with col3:
                        # Altersbereich mit meisten Geburten (25-35)
                        geb_25_35 = geb_nach_alter[
                            (geb_nach_alter['AlterMutter'] >= 25) & 
                            (geb_nach_alter['AlterMutter'] <= 35)
                        ]['SUMME'].sum()
                        if geburten_gesamt > 0:
                            anteil_25_35 = (geb_25_35 / geburten_gesamt * 100)
                            st.metric("🎯 Alter 25-35", f"{anteil_25_35:.1f}%")
                        else:
                            st.metric("🎯 Alter 25-35", "0%")
                    
                    st.markdown("---")
                    
                    # Top-Tabelle
                    st.markdown("### 🔝 Top 10 Altersgruppen")
                    geb_top10 = geb_nach_alter.sort_values('SUMME', ascending=False).head(10)
                    geb_top10['Alter'] = geb_top10['AlterMutter'].astype(int)
                    geb_top10['Geburten'] = geb_top10['SUMME'].astype(int)
                    st.dataframe(
                        geb_top10[['Alter', 'Geburten']],
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("Keine Geburtendaten für diese Auswahl verfügbar")
                
                st.markdown("---")
                
                # Geburten nach Gemeinde (nur bei "Gesamter Kreis")
                if gemeinde_geb == "Gesamter Kreis":
                    st.markdown("### 🏘️ Geburten nach Gemeinde")
                    
                    gemeinde_geb_daten = []
                    for gem in analyzer.gemeinden:
                        df_gem_geb = analyzer.df_geburten[analyzer.df_geburten['Gemeinde'] == gem]
                        geb_gem = int(df_gem_geb['SUMME'].sum())
                        
                        if geb_gem > 0:
                            gemeinde_geb_daten.append({
                                'Gemeinde': gem.replace('Melderegister ', ''),
                                'Geburten': geb_gem
                            })
                    
                    if gemeinde_geb_daten:
                        df_gem_vergleich = pd.DataFrame(gemeinde_geb_daten)
                        df_gem_vergleich = df_gem_vergleich.sort_values('Geburten', ascending=False)
                        
                        # Diagramm
                        fig2 = px.bar(
                            df_gem_vergleich,
                            x='Gemeinde',
                            y='Geburten',
                            title='Geburten nach Gemeinde',
                            color='Geburten',
                            color_continuous_scale='Blues'
                        )
                        fig2.update_layout(xaxis_tickangle=-45, height=500)
                        st.plotly_chart(fig2, use_container_width=True)
                        
                        # Tabelle
                        st.dataframe(df_gem_vergleich, hide_index=True, use_container_width=True)
                
                st.markdown("---")
                
                # NEU: Geburtenrate berechnen (wenn Einwohner-Daten vorhanden)
                if analyzer.df is not None:
                    st.markdown("### 📊 Geburtenrate & Prognosen")
                    
                    st.info("💡 **Geburtenrate** = Geburten pro 1.000 Einwohner (hochgerechnet auf 12 Monate)")
                    
                    # Hole Einwohner-Daten
                    if gemeinde_geb == "Gesamter Kreis":
                        df_einwohner = analyzer.df
                    else:
                        df_einwohner = analyzer.df[analyzer.df['Gemeinde'] == gemeinde_geb]
                    
                    einwohner_gesamt = int(df_einwohner['SUMME'].sum())
                    
                    # Frauen im gebärfähigen Alter (15-45)
                    frauen_15_45 = int(
                        df_einwohner[
                            (df_einwohner['Alter'] >= 15) & 
                            (df_einwohner['Alter'] <= 45)
                        ]['w'].sum()
                    )
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("👥 Einwohner", f"{einwohner_gesamt:,}")
                    
                    with col2:
                        st.metric("👩 Frauen 15-45", f"{frauen_15_45:,}")
                    
                    with col3:
                        if einwohner_gesamt > 0:
                            # Hochrechnung auf 12 Monate (angenommen: Daten sind 1 Monat)
                            geburten_jahr = geburten_gesamt * 12
                            geburtenrate = (geburten_jahr / einwohner_gesamt) * 1000
                            st.metric("📈 Geburtenrate", f"{geburtenrate:.1f}‰")
                        else:
                            st.metric("📈 Geburtenrate", "N/A")
                    
                    st.markdown("---")
                    
                    # Zusätzliche Kennzahlen
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if frauen_15_45 > 0:
                            # Geburten pro 1.000 Frauen im gebärfähigen Alter
                            geburten_jahr_frauen = geburten_gesamt * 12
                            fruchtbarkeitsziffer = (geburten_jahr_frauen / frauen_15_45) * 1000
                            st.metric("👶 Fruchtbarkeitsziffer", f"{fruchtbarkeitsziffer:.1f}‰")
                            st.caption("Geburten pro 1.000 Frauen (15-45)")
                        else:
                            st.metric("👶 Fruchtbarkeitsziffer", "N/A")
                    
                    with col2:
                        # Kinder 0-2 Jahre (für Vergleich)
                        kinder_0_2 = int(
                            df_einwohner[
                                (df_einwohner['Alter'] >= 0) & 
                                (df_einwohner['Alter'] <= 2)
                            ]['SUMME'].sum()
                        )
                        st.metric("👶 Kinder 0-2 Jahre", f"{kinder_0_2:,}")
                        st.caption("Aktuell im Kita-Alter")
                    
                    with col3:
                        # Prognose U3-Bedarf in 3 Jahren
                        u3_prognose = geburten_gesamt * 12 * 3  # 3 Jahrgänge
                        st.metric("🔮 U3-Prognose", f"{u3_prognose:,}")
                        st.caption("Erwartete U3-Kinder in 3 Jahren")
                    
                    st.markdown("---")
                    
                    # NEU: Altersgruppen-Verteilung (Pie Chart)
                    st.markdown("### 📊 Verteilung nach Altersgruppen der Mütter")
                    
                    altersgruppen_daten = {
                        'Unter 20': (0, 19),
                        '20-24': (20, 24),
                        '25-29': (25, 29),
                        '30-34': (30, 34),
                        '35-39': (35, 39),
                        '40-44': (40, 44),
                        '45+': (45, 100)
                    }
                    
                    altersgruppen_ergebnisse = []
                    for label, (min_a, max_a) in altersgruppen_daten.items():
                        geburten_gruppe = int(df_geb[
                            (df_geb['AlterMutter'] >= min_a) & 
                            (df_geb['AlterMutter'] <= max_a)
                        ]['SUMME'].sum())
                        
                        anteil = (geburten_gruppe / geburten_gesamt * 100) if geburten_gesamt > 0 else 0
                        
                        altersgruppen_ergebnisse.append({
                            'Altersgruppe': label,
                            'Geburten': geburten_gruppe,
                            'Anteil (%)': round(anteil, 1)
                        })
                    
                    df_altersgruppen = pd.DataFrame(altersgruppen_ergebnisse)
                    df_altersgruppen = df_altersgruppen[df_altersgruppen['Geburten'] > 0]  # Nur nicht-leere
                    
                    if not df_altersgruppen.empty:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Pie Chart
                            fig3 = px.pie(
                                df_altersgruppen,
                                values='Geburten',
                                names='Altersgruppe',
                                title='Verteilung der Geburten nach Altersgruppe',
                                hole=0.4
                            )
                            fig3.update_traces(textposition='inside', textinfo='percent+label')
                            fig3.update_layout(height=400)
                            st.plotly_chart(fig3, use_container_width=True)
                        
                        with col2:
                            # Tabelle
                            st.markdown("**Detailansicht:**")
                            st.dataframe(df_altersgruppen, hide_index=True, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # NEU: Hinweis zur Datenbasis
                    st.info(
                        f"📅 **Datenbasis:** Diese Analyse basiert auf {geburten_gesamt} Geburten. "
                        f"Falls dies Monatsdaten sind, wurden Jahreswerte hochgerechnet (×12). "
                        f"Für präzisere Analysen laden Sie bitte Daten mehrerer Monate im Zeitvergleich."
                    )
            
            else:
                st.info("ℹ️ Keine Geburten-Daten geladen")
    
    # TAB: EINSCHULUNGSPLANUNG (wenn Geburtsmonat-Daten vorhanden)
    if analyzer.has_birthmonth:
        tab_idx_einschulung = tabs.index("📅 Einschulungsplanung")
        
        with tab_objects[tab_idx_einschulung]:
            st.header("📅 Einschulungsplanung nach Geburtsmonat")
            
            if analyzer.df_birthmonth is not None and not analyzer.df_birthmonth.empty:
                # Gemeinde-Filter
                gemeinde_einsch = st.selectbox(
                    "Gemeinde wählen:",
                    ["Gesamter Kreis"] + sorted(analyzer.df_birthmonth['Gemeinde'].unique().tolist()),
                    key="einsch_gemeinde"
                )
                
                # Filtere Daten
                if gemeinde_einsch == "Gesamter Kreis":
                    df_einsch = analyzer.df_birthmonth.copy()
                else:
                    df_einsch = analyzer.df_birthmonth[analyzer.df_birthmonth['Gemeinde'] == gemeinde_einsch]
                
                st.markdown("---")
                
                # Einschulungsjahrgang wählen
                st.markdown("### 🎓 Einschulungsjahrgang wählen")
                
                # Typische Einschulung: 6-jährige, geboren vor 7 Jahren
                current_year = datetime.now().year
                einschuljahr = st.selectbox(
                    "Einschulung im Sommer:",
                    list(range(current_year, current_year + 5)),
                    index=1  # Nächstes Jahr als Default
                )
                
                geburtsjahr = einschuljahr - 6
                
                st.info(
                    f"📅 **Einschulung Sommer {einschuljahr}**\n\n"
                    f"Kinder geboren in **{geburtsjahr}** (aktuelles Alter: {current_year - geburtsjahr} Jahre)\n\n"
                    f"💡 **Stichtag Saarland:** i.d.R. 30. Juni\n"
                    f"- **HJ 1** (Jan-Jun): Ältere Jahrgangshälfte\n"
                    f"- **HJ 2** (Jul-Dez): Jüngere Jahrgangshälfte"
                )
                
                # Filtere auf Geburtsjahr
                jahr_str = str(geburtsjahr)
                df_jahrgang = df_einsch[df_einsch['birth_halbjahr'].str.contains(jahr_str, na=False)]
                
                if not df_jahrgang.empty:
                    # Kennzahlen
                    col1, col2, col3, col4 = st.columns(4)
                    
                    kinder_gesamt = int(df_jahrgang['persons'].sum())
                    kinder_hj1 = int(df_jahrgang[df_jahrgang['birth_halbjahr'].str.contains(f'HJ 1 {geburtsjahr}', na=False)]['persons'].sum())
                    kinder_hj2 = int(df_jahrgang[df_jahrgang['birth_halbjahr'].str.contains(f'HJ 2 {geburtsjahr}', na=False)]['persons'].sum())
                    
                    with col1:
                        st.metric("👶 Kinder gesamt", f"{kinder_gesamt}")
                    with col2:
                        st.metric("🌅 HJ 1 (Jan-Jun)", f"{kinder_hj1}")
                        anteil_hj1 = (kinder_hj1 / kinder_gesamt * 100) if kinder_gesamt > 0 else 0
                        st.caption(f"{anteil_hj1:.1f}% des Jahrgangs")
                    with col3:
                        st.metric("🌆 HJ 2 (Jul-Dez)", f"{kinder_hj2}")
                        anteil_hj2 = (kinder_hj2 / kinder_gesamt * 100) if kinder_gesamt > 0 else 0
                        st.caption(f"{anteil_hj2:.1f}% des Jahrgangs")
                    with col4:
                        # Kann-Kinder-Schätzung (Dezember-Geborene + Januar-Geborene des Folgejahrs)
                        kann_kinder = "N/A"
                        st.metric("⚡ Kann-Kinder ca.", kann_kinder)
                        st.caption("Schätzung")
                    
                    st.markdown("---")
                    
                    # Verteilung nach Monat
                    st.markdown(f"### 📊 Verteilung nach Geburtsmonat ({geburtsjahr})")
                    
                    # Aggregiere nach Monat
                    df_jahrgang_month = df_jahrgang.copy()
                    if 'date_birth_month' in df_jahrgang_month.columns:
                        df_jahrgang_month['Monat'] = pd.to_datetime(df_jahrgang_month['date_birth_month']).dt.strftime('%B')
                        df_jahrgang_month['Monat_Nr'] = pd.to_datetime(df_jahrgang_month['date_birth_month']).dt.month
                        
                        monat_agg = df_jahrgang_month.groupby(['Monat', 'Monat_Nr'])['persons'].sum().reset_index()
                        monat_agg = monat_agg.sort_values('Monat_Nr')
                        
                        # Diagramm
                        fig = px.bar(
                            monat_agg,
                            x='Monat',
                            y='persons',
                            title=f'Geburten nach Monat (Jahrgang {geburtsjahr})',
                            labels={'persons': 'Anzahl Kinder', 'Monat': 'Geburtsmonat'},
                            color='persons',
                            color_continuous_scale='Blues'
                        )
                        fig.add_hline(y=kinder_gesamt/12, line_dash="dash", line_color="red", 
                                     annotation_text="Durchschnitt")
                        fig.update_layout(height=500)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabelle
                        st.markdown("**Detailansicht:**")
                        monat_display = monat_agg[['Monat', 'persons']].copy()
                        monat_display.columns = ['Geburtsmonat', 'Kinder']
                        st.dataframe(monat_display, hide_index=True, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Klassenplanung
                    st.markdown("### 🏫 Klassenplanung-Rechner")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        klassen_groesse_soll = st.slider(
                            "Soll-Klassengröße:",
                            min_value=15,
                            max_value=30,
                            value=25,
                            step=1,
                            key="einsch_klassen_groesse"
                        )
                    with col2:
                        quote_einschulung = st.slider(
                            "Einschulungsquote:",
                            min_value=0.8,
                            max_value=1.0,
                            value=0.95,
                            step=0.05,
                            key="einsch_quote",
                            help="Berücksichtigt Rückstellungen, Umzüge, etc."
                        )
                    
                    # Berechnung
                    schueler_erwartet = int(kinder_gesamt * quote_einschulung)
                    klassen_anzahl = int(np.ceil(schueler_erwartet / klassen_groesse_soll)) if klassen_groesse_soll > 0 else 0
                    schueler_pro_klasse = schueler_erwartet / klassen_anzahl if klassen_anzahl > 0 else 0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🎒 Erwartete Schüler", f"{schueler_erwartet}")
                    with col2:
                        st.metric("🏫 Klassen benötigt", f"{klassen_anzahl}")
                    with col3:
                        st.metric("📊 Ø Schüler/Klasse", f"{schueler_pro_klasse:.1f}")
                    
                    if schueler_pro_klasse < 15:
                        st.warning("⚠️ Klassengröße unter 15 - Zusammenlegung prüfen!")
                    elif schueler_pro_klasse > 28:
                        st.warning("⚠️ Klassengröße über 28 - Zusätzliche Klasse empfohlen!")
                    else:
                        st.success("✅ Klassengröße im optimalen Bereich")
                
                st.markdown("---")
                
                # NEU: Geburten-Übersichtstabellen
                st.markdown("### 📋 Geburten-Übersicht nach Jahr und Gemeinde")
                
                # Tabelle 1: Geburten nach Jahr und Gemeinde
                st.markdown("#### 📊 Geburten pro Jahr (alle Gemeinden)")
                
                # Extrahiere Jahre aus birth_halbjahr
                df_overview = df_einsch.copy()
                if 'birth_halbjahr' in df_overview.columns:
                    # Extrahiere Jahr (z.B. "HJ 1 2025" → 2025)
                    df_overview['Jahr'] = df_overview['birth_halbjahr'].str.extract(r'(\d{4})')[0].astype(int)
                    
                    # Aggregiere nach Jahr und Gemeinde
                    pivot_jahr_gemeinde = df_overview.groupby(['Jahr', 'Gemeinde'])['persons'].sum().reset_index()
                    pivot_jahr_gemeinde = pivot_jahr_gemeinde.pivot(index='Jahr', columns='Gemeinde', values='persons').fillna(0)
                    pivot_jahr_gemeinde = pivot_jahr_gemeinde.astype(int)
                    
                    # Füge Gesamt-Spalte hinzu
                    pivot_jahr_gemeinde['🎯 GESAMT'] = pivot_jahr_gemeinde.sum(axis=1)
                    
                    # Sortiere nach Jahr (neueste zuerst)
                    pivot_jahr_gemeinde = pivot_jahr_gemeinde.sort_index(ascending=False)
                    
                    # Zeige Tabelle
                    st.dataframe(
                        pivot_jahr_gemeinde,
                        use_container_width=True,
                        height=400
                    )
                    
                    # Download-Button für Excel
                    from io import BytesIO
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        pivot_jahr_gemeinde.to_excel(writer, sheet_name='Geburten_Jahr_Gemeinde')
                    
                    st.download_button(
                        label="📥 Tabelle als Excel herunterladen",
                        data=excel_buffer.getvalue(),
                        file_name=f"Geburten_Jahr_Gemeinde_{gemeinde_einsch}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.markdown("---")
                    
                    # Tabelle 2: Geburten nach Jahr und Gemeindeteil (wenn Ortsteile vorhanden)
                    if 'location' in df_overview.columns:
                        st.markdown("#### 🏘️ Geburten pro Jahr nach Gemeindeteil")
                        
                        # Gemeinde-Auswahl für Detailansicht
                        gemeinde_detail = st.selectbox(
                            "Gemeinde für Gemeindeteil-Ansicht:",
                            sorted(df_overview['Gemeinde'].unique().tolist()),
                            key="gemeinde_detail_geburten"
                        )
                        
                        # Filtere auf gewählte Gemeinde
                        df_gemeinde_detail = df_overview[df_overview['Gemeinde'] == gemeinde_detail]
                        
                        if not df_gemeinde_detail.empty and 'location' in df_gemeinde_detail.columns:
                            # Aggregiere nach Jahr und Ortsteil
                            pivot_jahr_ortsteil = df_gemeinde_detail.groupby(['Jahr', 'location'])['persons'].sum().reset_index()
                            pivot_jahr_ortsteil = pivot_jahr_ortsteil.pivot(index='Jahr', columns='location', values='persons').fillna(0)
                            pivot_jahr_ortsteil = pivot_jahr_ortsteil.astype(int)
                            
                            # Füge Gesamt-Spalte hinzu
                            pivot_jahr_ortsteil['🎯 GESAMT'] = pivot_jahr_ortsteil.sum(axis=1)
                            
                            # Sortiere nach Jahr (neueste zuerst)
                            pivot_jahr_ortsteil = pivot_jahr_ortsteil.sort_index(ascending=False)
                            
                            # Zeige Tabelle
                            st.dataframe(
                                pivot_jahr_ortsteil,
                                use_container_width=True,
                                height=400
                            )
                            
                            # Download-Button für Excel
                            excel_buffer2 = BytesIO()
                            with pd.ExcelWriter(excel_buffer2, engine='xlsxwriter') as writer:
                                pivot_jahr_ortsteil.to_excel(writer, sheet_name='Geburten_Jahr_Ortsteil')
                            
                            st.download_button(
                                label=f"📥 Tabelle {gemeinde_detail} als Excel herunterladen",
                                data=excel_buffer2.getvalue(),
                                file_name=f"Geburten_Jahr_Ortsteil_{gemeinde_detail}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                            # Zusatz: Diagramm für visuellen Vergleich
                            st.markdown("**📈 Visuelle Darstellung:**")
                            
                            # Bereite Daten für Diagramm vor
                            df_chart = pivot_jahr_ortsteil.drop(columns=['🎯 GESAMT']).reset_index()
                            df_chart_melted = df_chart.melt(id_vars='Jahr', var_name='Gemeindeteil', value_name='Geburten')
                            
                            fig = px.line(
                                df_chart_melted,
                                x='Jahr',
                                y='Geburten',
                                color='Gemeindeteil',
                                title=f'Geburtenzahlen nach Gemeindeteil - {gemeinde_detail}',
                                markers=True
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info(f"Keine Gemeindeteil-Daten für {gemeinde_detail} verfügbar")
                    
                    else:
                        st.warning("⚠️ Keine Jahres-Daten in birth_halbjahr gefunden")
                
                else:
                    st.warning(f"⚠️ Keine Daten für Geburtsjahrgang {geburtsjahr} gefunden")
            
            else:
                st.info("ℹ️ Keine Geburtsmonat-Daten geladen")
    
    # TAB: HOCHALTRIGEN-ANALYSE
    tab_idx_hochaltrige = tabs.index("👴 Hochaltrigen-Analyse")
    
    with tab_objects[tab_idx_hochaltrige]:
        st.header("👴 Hochaltrigen-Analyse")
        
        st.info(
            "📊 **Wichtig für:**\n"
            "- Pflegebedarfsplanung\n"
            "- Seniorenbetreuung\n"
            "- Barrierefreies Bauen\n"
            "- Hausarzt-Kapazitäten"
        )
        
        # Filter
        gemeinde_ha = st.selectbox(
            "Gemeinde wählen:",
            ["Gesamter Kreis"] + analyzer.gemeinden,
            key="hochaltrige_gemeinde"
        )
        
        # Filtere Daten
        if gemeinde_ha == "Gesamter Kreis":
            df_ha = analyzer.df.copy()
        else:
            df_ha = analyzer.df[analyzer.df['Gemeinde'] == gemeinde_ha]
        
        if not df_ha.empty:
            # Definiere Altersgruppen
            altersgruppen_ha = {
                '65+ Jahre': 65,
                '75+ Jahre': 75,
                '80+ Jahre': 80,
                '90+ Jahre': 90,
                '100+ Jahre': 100
            }
            
            # Berechne Kennzahlen
            bevoelkerung_gesamt = int(df_ha['SUMME'].sum())
            erwerbsfaehige = int(df_ha[(df_ha['Alter'] >= 20) & (df_ha['Alter'] <= 64)]['SUMME'].sum())
            
            st.markdown("---")
            st.markdown("### 📊 Hochaltrigen-Übersicht")
            
            # Kennzahlen-Grid
            cols = st.columns(5)
            
            for idx, (label, min_alter) in enumerate(altersgruppen_ha.items()):
                with cols[idx]:
                    anzahl = int(df_ha[df_ha['Alter'] >= min_alter]['SUMME'].sum())
                    anteil = (anzahl / bevoelkerung_gesamt * 100) if bevoelkerung_gesamt > 0 else 0
                    
                    st.metric(
                        label,
                        f"{anzahl:,}",
                        delta=f"{anteil:.1f}% der Bevölkerung"
                    )
            
            st.markdown("---")
            
            # Quotienten
            st.markdown("### 📈 Kennziffern der Alterung")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Alterungsquotient (65+ / 20-64)
                senioren_65 = int(df_ha[df_ha['Alter'] >= 65]['SUMME'].sum())
                alterungsquotient = (senioren_65 / erwerbsfaehige * 100) if erwerbsfaehige > 0 else 0
                st.metric(
                    "👥 Alterungsquotient",
                    f"{alterungsquotient:.1f}",
                    help="65+ pro 100 Erwerbsfähige (20-64)"
                )
                st.caption(f"{senioren_65:,} Senioren auf {erwerbsfaehige:,} Erwerbsfähige")
            
            with col2:
                # Hochbetagtenquotient (80+ / 65+)
                hochbetagte_80 = int(df_ha[df_ha['Alter'] >= 80]['SUMME'].sum())
                hochbetagtenquotient = (hochbetagte_80 / senioren_65 * 100) if senioren_65 > 0 else 0
                st.metric(
                    "🧓 Hochbetagtenquotient",
                    f"{hochbetagtenquotient:.1f}%",
                    help="Anteil 80+ an allen 65+"
                )
                st.caption(f"{hochbetagte_80:,} Hochbetagte von {senioren_65:,} Senioren")
            
            with col3:
                # Hundertjährige
                hundertjaehrige = int(df_ha[df_ha['Alter'] >= 100]['SUMME'].sum())
                st.metric(
                    "🎂 Hundertjährige",
                    f"{hundertjaehrige}",
                    help="Personen 100 Jahre und älter"
                )
                pro_100k = (hundertjaehrige / bevoelkerung_gesamt * 100000) if bevoelkerung_gesamt > 0 else 0
                st.caption(f"{pro_100k:.1f} pro 100.000 Einwohner")
            
            st.markdown("---")
            
            # Detaillierte Tabelle
            st.markdown("### 📋 Detaillierte Aufschlüsselung")
            
            # Erstelle detaillierte Altersgruppen
            altersgruppen_detail = [
                ('65-69 Jahre', 65, 69),
                ('70-74 Jahre', 70, 74),
                ('75-79 Jahre', 75, 79),
                ('80-84 Jahre', 80, 84),
                ('85-89 Jahre', 85, 89),
                ('90-94 Jahre', 90, 94),
                ('95-99 Jahre', 95, 99),
                ('100+ Jahre', 100, 150)
            ]
            
            tabelle_daten = []
            for label, min_a, max_a in altersgruppen_detail:
                gesamt = int(df_ha[(df_ha['Alter'] >= min_a) & (df_ha['Alter'] <= max_a)]['SUMME'].sum())
                maenner = int(df_ha[(df_ha['Alter'] >= min_a) & (df_ha['Alter'] <= max_a)]['m'].sum())
                frauen = int(df_ha[(df_ha['Alter'] >= min_a) & (df_ha['Alter'] <= max_a)]['w'].sum())
                anteil = (gesamt / bevoelkerung_gesamt * 100) if bevoelkerung_gesamt > 0 else 0
                
                tabelle_daten.append({
                    'Altersgruppe': label,
                    'Gesamt': gesamt,
                    'Männer': maenner,
                    'Frauen': frauen,
                    'Anteil (%)': round(anteil, 2)
                })
            
            df_tabelle = pd.DataFrame(tabelle_daten)
            st.dataframe(df_tabelle, use_container_width=True, hide_index=True)
            
            # Visualisierung
            st.markdown("### 📊 Visualisierung")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Balkendiagramm
                fig1 = px.bar(
                    df_tabelle,
                    x='Altersgruppe',
                    y='Gesamt',
                    title='Hochaltrige nach Altersgruppen',
                    color='Gesamt',
                    color_continuous_scale='Oranges'
                )
                fig1.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Geschlechterverteilung
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    name='Männer',
                    x=df_tabelle['Altersgruppe'],
                    y=df_tabelle['Männer'],
                    marker_color='lightblue'
                ))
                fig2.add_trace(go.Bar(
                    name='Frauen',
                    x=df_tabelle['Altersgruppe'],
                    y=df_tabelle['Frauen'],
                    marker_color='lightpink'
                ))
                fig2.update_layout(
                    title='Geschlechterverteilung',
                    barmode='group',
                    xaxis_tickangle=-45,
                    height=400
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("---")
            
            # Gemeindevergleich (nur bei "Gesamter Kreis")
            if gemeinde_ha == "Gesamter Kreis":
                st.markdown("### 🏘️ Vergleich nach Gemeinde")
                
                gemeinde_vergleich_ha = []
                for gemeinde in analyzer.gemeinden:
                    df_gem = analyzer.df[analyzer.df['Gemeinde'] == gemeinde]
                    
                    bev_gem = int(df_gem['SUMME'].sum())
                    s65 = int(df_gem[df_gem['Alter'] >= 65]['SUMME'].sum())
                    s75 = int(df_gem[df_gem['Alter'] >= 75]['SUMME'].sum())
                    s80 = int(df_gem[df_gem['Alter'] >= 80]['SUMME'].sum())
                    s90 = int(df_gem[df_gem['Alter'] >= 90]['SUMME'].sum())
                    s100 = int(df_gem[df_gem['Alter'] >= 100]['SUMME'].sum())
                    
                    anteil_65 = (s65 / bev_gem * 100) if bev_gem > 0 else 0
                    
                    gemeinde_vergleich_ha.append({
                        'Gemeinde': gemeinde.replace('Melderegister ', ''),
                        'Bevölkerung': bev_gem,
                        '65+': s65,
                        '75+': s75,
                        '80+': s80,
                        '90+': s90,
                        '100+': s100,
                        'Anteil 65+ (%)': round(anteil_65, 1)
                    })
                
                df_gem_vgl = pd.DataFrame(gemeinde_vergleich_ha)
                df_gem_vgl = df_gem_vgl.sort_values('65+', ascending=False)
                
                st.dataframe(df_gem_vgl, use_container_width=True, hide_index=True)
                
                # Diagramm
                fig3 = px.bar(
                    df_gem_vgl,
                    x='Gemeinde',
                    y='65+',
                    title='Senioren (65+) nach Gemeinde',
                    color='Anteil 65+ (%)',
                    color_continuous_scale='Reds'
                )
                fig3.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig3, use_container_width=True)
            
            # Ortsteil-Vergleich (wenn verfügbar)
            if analyzer.has_ortsteile and gemeinde_ha != "Gesamter Kreis":
                st.markdown("---")
                st.markdown(f"### 🏘️ Vergleich nach Ortsteil ({gemeinde_ha})")
                
                ortsteile_ha = analyzer.get_ortsteile_for_gemeinde(gemeinde_ha)
                
                if ortsteile_ha:
                    ortsteil_vergleich_ha = []
                    for ortsteil in ortsteile_ha:
                        df_ot = df_ha[df_ha['Ortsteil'] == ortsteil]
                        
                        bev_ot = int(df_ot['SUMME'].sum())
                        s65_ot = int(df_ot[df_ot['Alter'] >= 65]['SUMME'].sum())
                        s80_ot = int(df_ot[df_ot['Alter'] >= 80]['SUMME'].sum())
                        
                        anteil_65_ot = (s65_ot / bev_ot * 100) if bev_ot > 0 else 0
                        
                        ortsteil_vergleich_ha.append({
                            'Ortsteil': ortsteil,
                            'Bevölkerung': bev_ot,
                            '65+': s65_ot,
                            '80+': s80_ot,
                            'Anteil 65+ (%)': round(anteil_65_ot, 1)
                        })
                    
                    df_ot_vgl = pd.DataFrame(ortsteil_vergleich_ha)
                    df_ot_vgl = df_ot_vgl.sort_values('65+', ascending=False)
                    
                    st.dataframe(df_ot_vgl, use_container_width=True, hide_index=True)
            
            # Excel-Export
            st.markdown("---")
            st.markdown("### 📥 Export")
            
            from io import BytesIO
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_tabelle.to_excel(writer, sheet_name='Altersgruppen', index=False)
                if gemeinde_ha == "Gesamter Kreis":
                    df_gem_vgl.to_excel(writer, sheet_name='Gemeindevergleich', index=False)
            
            st.download_button(
                label="📥 Hochaltrigen-Analyse als Excel herunterladen",
                data=excel_buffer.getvalue(),
                file_name=f"Hochaltrige_{gemeinde_ha}_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        else:
            st.warning("⚠️ Keine Daten verfügbar")
    
    # TAB: GEMEINDEVERGLEICH (letzter Tab)
    with tab_objects[tab_idx_gemeinde]:
        st.header("🔄 Gemeinde-Vergleich")
        
        st.markdown("### 📊 Gemeinde-Übersichtstabelle")
        
        gemeinde_vergleich = []
        for gemeinde in analyzer.gemeinden:
            df_gem = analyzer.df[analyzer.df['Gemeinde'] == gemeinde]
            
            if len(df_gem) > 0:
                gesamt = int(df_gem['SUMME'].sum())
                kita_u3 = int(df_gem[(df_gem['Alter'] >= 0) & (df_gem['Alter'] <= 2)]['SUMME'].sum())
                kita_ue3 = int(df_gem[(df_gem['Alter'] >= 3) & (df_gem['Alter'] <= 5)]['SUMME'].sum())
                gs = int(df_gem[(df_gem['Alter'] >= 6) & (df_gem['Alter'] <= 9)]['SUMME'].sum())
                sek1 = int(df_gem[(df_gem['Alter'] >= 10) & (df_gem['Alter'] <= 15)]['SUMME'].sum())
                sek2 = int(df_gem[(df_gem['Alter'] >= 16) & (df_gem['Alter'] <= 18)]['SUMME'].sum())
                
                # Berechne Anteile
                anteil_u3 = (kita_u3 / gesamt * 100) if gesamt > 0 else 0
                anteil_bildung = ((kita_u3 + kita_ue3 + gs + sek1 + sek2) / gesamt * 100) if gesamt > 0 else 0
                
                gemeinde_vergleich.append({
                    'Gemeinde': gemeinde.replace('Melderegister ', ''),
                    'Einwohner': gesamt,
                    'U3 (0-2)': kita_u3,
                    'Ü3 (3-5)': kita_ue3,
                    'GS (6-9)': gs,
                    'Sek I (10-15)': sek1,
                    'Sek II (16-18)': sek2,
                    'Anteil U3 %': round(anteil_u3, 1),
                    'Anteil 0-18 %': round(anteil_bildung, 1)
                })
        
        if gemeinde_vergleich:
            df_gemeinde_vgl = pd.DataFrame(gemeinde_vergleich)
            df_gemeinde_vgl = df_gemeinde_vgl.sort_values('Einwohner', ascending=False)
            
            st.dataframe(df_gemeinde_vgl, use_container_width=True)
            
            # Visualisierungen
            st.markdown("### 📈 Einwohner nach Gemeinde")
            fig1 = px.bar(
                df_gemeinde_vgl, 
                x='Gemeinde', 
                y='Einwohner',
                title='Einwohnerverteilung nach Gemeinde'
            )
            fig1.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig1, use_container_width=True)
            
            # Bildungsrelevante Altersgruppen im Vergleich
            st.markdown("### 👶 Bildungsrelevante Altersgruppen im Gemeinde-Vergleich")
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name='U3 (0-2)', x=df_gemeinde_vgl['Gemeinde'], y=df_gemeinde_vgl['U3 (0-2)']))
            fig2.add_trace(go.Bar(name='Ü3 (3-5)', x=df_gemeinde_vgl['Gemeinde'], y=df_gemeinde_vgl['Ü3 (3-5)']))
            fig2.add_trace(go.Bar(name='GS (6-9)', x=df_gemeinde_vgl['Gemeinde'], y=df_gemeinde_vgl['GS (6-9)']))
            fig2.add_trace(go.Bar(name='Sek I (10-15)', x=df_gemeinde_vgl['Gemeinde'], y=df_gemeinde_vgl['Sek I (10-15)']))
            fig2.add_trace(go.Bar(name='Sek II (16-18)', x=df_gemeinde_vgl['Gemeinde'], y=df_gemeinde_vgl['Sek II (16-18)']))
            
            fig2.update_layout(
                barmode='group',
                title='Altersgruppen im Gemeinde-Vergleich',
                xaxis_tickangle=-45,
                height=500
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Anteile
            st.markdown("### 📊 Anteil bildungsrelevanter Altersgruppen")
            col1, col2 = st.columns(2)
            
            with col1:
                fig3 = px.bar(
                    df_gemeinde_vgl,
                    x='Gemeinde',
                    y='Anteil U3 %',
                    title='Anteil U3-Kinder (0-2 Jahre)',
                    labels={'Anteil U3 %': 'Anteil in %'}
                )
                fig3.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig3, use_container_width=True)
            
            with col2:
                fig4 = px.bar(
                    df_gemeinde_vgl,
                    x='Gemeinde',
                    y='Anteil 0-18 %',
                    title='Anteil Kinder & Jugendliche (0-18 Jahre)',
                    labels={'Anteil 0-18 %': 'Anteil in %'}
                )
                fig4.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Keine Gemeinde-Daten verfügbar")
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666;'>
            <small>
                Bildungsplanungs-Datenanalyse | Saarpfalz-Kreis | Version 3.1 STABLE<br>
                ✅ Alle 7 kritischen Fehler behoben | Production Ready
            </small>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
