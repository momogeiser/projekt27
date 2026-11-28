###################################
# Bulk Import fit tcx             #
###################################


import os
import pandas as pd
import glob
import xml.etree.ElementTree as ET
from fitparse import FitFile
import funktionen
import sqlite3
import numpy as np
import statistics
import re  # zum Bereinigen von Strings
import csv  # zum testen: df als csv exportieren
import traceback  # zum debuggen
import xlsxwriter  # zum testen

# lesen von allen Dateinamen, wegen recursive=True liest es auch in allen Unterordner (und unterunterordner usw.)
# in filenames sind die Dateinamen inkl. Pfad als Name abgespeichert
ordner = "/Users/momogeiser/MomosSachen/Programmieren/Python/projekt27/Daten"
# ordner = "/Users/momogeiser/Momos Sachen/Sport/Sport Daten SAVE"

filenames = (
    glob.glob(f"{ordner}/**/*.fit", recursive=True)
    + glob.glob(f"{ordner}/**/*.tcx", recursive=True)
    + glob.glob(f"{ordner}/**/*.gpx", recursive=True)
)


fehlerhafte_dateien = []  # Liste mit Dateien die nicht geladen werden konnten (bspw. fehlerhaftes Datum usw.)

# für den Print wie viele schon importiert wurden
anzahl_files = len(filenames)
anzahl_importe = 0

liste_der_record_dfs = []  # in dieser Liste werden alle Dataframes als Dataframes abgespeichert [df1, df2, df3, ...]
df_alle_records = (
    pd.DataFrame()
)  # die Liste liste_der_record_dfs wird dann hierrein geladen und man hat einen finalen df mit allen Aktivitäten


for file in filenames:
    try:  # falls eine Datei nicht geladen werden kann weil bspw. ein ungültiges Datum usw.

        # substitute aus dem Paket re, \D steht für alle nicht-Zahlen ersetzen, durch "". \d würde alle
        # Buchstaben ersetzen. r steht für raw string und behandelt sonderzeichen (hier "\") als string.
        # os.path.basename(file) bedeutet nur der Dateiname (in file ist der Name inkl. Pfad drin)

        garmin_id = re.sub(r"\D", "", os.path.basename(file))

        if file.endswith(".tcx"):

            #########################
            #       Tcx-Files       #
            #########################

            # # Datei einlesen und als tcx Objekt abspeichern
            tree = ET.parse(file)
            # # Wurzel des XML-Baums aus tcx Objekt abspeichern, darin kann man auf Daten zugreifen
            root = tree.getroot()

            # # die url ist ein Namespace dieses Dokuments (steht ganz am Anfang vom file)
            # # verschiedene Daten haben teilweise verschiedene Namespaces
            # # abspeichern im Dictionary ns bspw. mit dem Key "tcx" damit man später nur tcx: und den <Tag>
            # # schreiben muss anstatt ständig die ganze url. Ich benötige zwei Namespaces:
            ns = {
                "tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
                "ns3": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
            }

            # -------------------------------- #
            #  Aufbereiten der Records (TCX)   #
            # -------------------------------- #

            trackpoints = tree.findall(".//tcx:Trackpoint", ns)

            alle_werte_records = []  # Liste für Werte der einzelnen Trackpoints bzw. Sekunden

            for tp in trackpoints:  # loop durch alle Trackpoints
                time_el = tp.find("tcx:Time", ns)  # den Eintrag mit dem Tag Time
                lat_el = tp.find(
                    ".//tcx:Position/tcx:LatitudeDegrees", ns
                )  # Eintrag mit Position, darin den Eintrag Latitude - beide im selben Namespace tcx
                long_el = tp.find(".//tcx:Position/tcx:LongitudeDegrees", ns)
                alt_el = tp.find(".//tcx:AltitudeMeters", ns)
                dist_el = tp.find(".//tcx:DistanceMeters", ns)
                hr_el = tp.find(".//tcx:HeartRateBpm/tcx:Value", ns)
                cadence_el = tp.find(".//tcx:Cadence", ns)
                bike_cadence_el = tp.find(".//tcx:Cadence/tcx:Value", ns)
                run_cadence_el = tp.find(".//tcx:Extensions/ns3:TPX/ns3:RunCadence", ns)
                cadence = funktionen.erstes_nicht_none(
                    cadence_el, bike_cadence_el, run_cadence_el
                )  # drei unterschiedliche Kadenzen in tcx
                speed_el = tp.find(".//tcx:Extensions/ns3:TPX/ns3:Speed", ns)  # hier zwei verschiedene Namespaces
                pwr_el = tp.find(".//tcx:Extensions/ns3:TPX/ns3:Watts", ns)

                record = {
                    # .text ist ein Attribut des ET Objekts, das nur den Text zwischen den Tags zurückgibt, sonst würde das ganze Objekt gespeichert werden
                    # if time_el is not None else None, ist die überprüfung von NaN, würde sonst zu Fehler und Abbruch füren, so schreibt es einfach NaN hin wenn
                    # der Wert fehlt im Trackpoint
                    "file_type": "tcx",
                    "garmin_id": garmin_id,
                    "timestamp": time_el.text if time_el is not None else None,
                    "position_lat": lat_el.text if lat_el is not None else None,
                    "position_long": long_el.text if long_el is not None else None,
                    "altitude": alt_el.text if alt_el is not None else None,
                    "distance": dist_el.text if dist_el is not None else None,
                    "heart_rate": hr_el.text if hr_el is not None else None,
                    "cadence": cadence.text if cadence is not None else None,
                    "speed": speed_el.text if speed_el is not None else None,
                    "power": pwr_el.text if pwr_el is not None else None,
                }

                alle_werte_records.append(record)  # Werte zu einer Liste hinzufügen

            df_records_tcx = pd.DataFrame(alle_werte_records)
            df_records_tcx = df_records_tcx.drop_duplicates(
                subset=["timestamp"]
            )  # vor und nach der <Lap> hat es je ein identischer record
            df_records_tcx["timestamp"] = pd.to_datetime(df_records_tcx["timestamp"], errors="coerce", utc=True)
            df_records_tcx["timestamp"] = df_records_tcx["timestamp"].dt.tz_convert("Europe/Zurich")

            numeric_cols = [
                "garmin_id",
                "position_lat",
                "position_long",
                "altitude",
                "distance",
                "heart_rate",
                "cadence",
                "speed",
                "power",
            ]
            df_records_tcx[numeric_cols] = df_records_tcx[numeric_cols].apply(pd.to_numeric, errors="coerce")

            diff_alt = df_records_tcx["altitude"].diff()
            diff_dist = df_records_tcx["distance"].diff()
            grade = (diff_alt / diff_dist * 100).replace(
                [np.inf, -np.inf], np.nan
            )  # falls dist=0 würde es "inf" (infinity) und fehler geben

            # -------------------------------- #
            #  Aufbereiten der Runden (TCX)    #
            # -------------------------------- #

            laps = tree.findall(".//tcx:Lap", ns)

            alle_runden_tcx = []  # Liste für Werte der einzelnen Runden
            runden_dauer = []

            for lp in laps:  # loop durch alle Laps
                # In der Wurzel mit .find() nach Attribut aus dem Tag Activity suchen und mit .get() Attributwert auslesen
                # Activity = Tag ; Sport = Attribut davon ; Running = Attributwert von Sport
                lap_start = lp.get("StartTime")
                lp_dauer_n = lp.find(".//tcx:TotalTimeSeconds", ns)  # nettozeit
                lp_distance = lp.find(".//tcx:DistanceMeters", ns)
                lp_max_speed = lp.find(".//tcx:MaximumSpeed", ns)
                lp_calories = lp.find(".//tcx:Calories", ns)
                lp_avg_hr = lp.find(".//tcx:AverageHeartRateBpm/tcx:Value", ns)
                lp_max_hr = lp.find(".//tcx:MaximumHeartRateBpm/tcx:Value", ns)
                lp_avg_cad = lp.find(".//tcx:Cadence", ns)
                lp_avg_speed = lp.find(".//tcx:Extensions/ns3:LX/ns3:AvgSpeed", ns)
                lp_max_cad = lp.find(".//tcx:Extensions/ns3:LX/ns3:MaxBikeCadence", ns)
                lp_avg_pwr = lp.find(".//tcx:Extensions/ns3:LX/ns3:AvgWatts", ns)
                lp_max_pwr = lp.find(".//tcx:Extensions/ns3:LX/ns3:MaxWatts", ns)

                runden = {
                    "timestamp_start": lap_start if lap_start is not None else None,
                    "runden_dauer_netto": lp_dauer_n.text if lp_dauer_n is not None else None,  # netto
                    "runden_distanz": lp_distance.text if lp_distance is not None else None,
                    "runden_max_speed": lp_max_speed.text if lp_max_speed is not None else None,
                    "runden_kalorien": lp_calories.text if lp_calories is not None else None,
                    "runden_avg_puls": lp_avg_hr.text if lp_avg_hr is not None else None,
                    "runden_max_puls": lp_max_hr.text if lp_max_hr is not None else None,
                    "runden_cadence": lp_avg_cad.text if lp_avg_cad is not None else None,
                    "runden_avg_speed": lp_avg_speed.text if lp_avg_speed is not None else None,
                    "runden_max_cadence": lp_max_cad.text if lp_max_cad is not None else None,
                    "runden_avg_power": lp_avg_pwr.text if lp_avg_pwr is not None else None,
                    "runden_max_power": lp_max_pwr.text if lp_max_pwr is not None else None,
                }
                alle_runden_tcx.append(runden)
            df_runden_tcx = pd.DataFrame(alle_runden_tcx)

            df_runden_tcx["timestamp_start"] = pd.to_datetime(
                df_runden_tcx["timestamp_start"], errors="coerce", utc=True
            )
            df_runden_tcx["timestamp_start"] = pd.to_datetime(
                df_runden_tcx["timestamp_start"].dt.tz_convert("Europe/Zurich")
            )

            # ---------- Hinzufügen eines Lap-Index zu den Records ---------- #
            df_runden_tcx["timestamp"] = df_runden_tcx["timestamp_start"]  # timestamp Variable erstellen
            df_runden_tcx["lap"] = df_runden_tcx.index  # Index als Spalte "lap" ist später die Rundenbezeichnung
            df_runden_tcx["lap"] = df_runden_tcx["lap"] + 1  # Plus 1 da Index bei 0 beginnt
            df_records_tcx = pd.merge(
                df_records_tcx, df_runden_tcx[["lap", "timestamp"]], on="timestamp", how="left"
            )  # lap hinzufügen
            df_records_tcx["lap"] = df_records_tcx["lap"].ffill()
            df_runden_tcx = df_runden_tcx.drop(["timestamp"], axis=1)

            # --------------------------------------------------------------- #

            runden_dauer_brutto = []
            for i in range(len(df_runden_tcx)):
                if i < (len(df_runden_tcx) - 1):
                    runden_dauer_brutto.append(
                        (df_runden_tcx["timestamp_start"][i + 1] - df_runden_tcx["timestamp_start"][i]).total_seconds()
                    )
                else:
                    runden_dauer_brutto.append(
                        (
                            df_records_tcx["timestamp"].iloc[len(df_records_tcx["timestamp"]) - 1]
                            - df_runden_tcx["timestamp_start"][i]
                        ).total_seconds()
                    )

            laps_grouped = df_records_tcx.groupby("lap")
            max_alt_lap = laps_grouped["altitude"].max()
            min_alt_lap = laps_grouped["altitude"].min()

            # Anfang: Runden Elevation P und N ################################################

            anstieg_pro_runde = []
            abstieg_pro_runde = []

            # beim Iterieren über ein groupby Objekt bekommt man immer ein Paar zurück: den Namen und die Untergruppe (das ist ein tupel).
            # hier also die Gruppennummer 1,2,3... als Name wie er im Dataframe drinsteht und den Dataframe dieser Gruppe erster Durchgang (1, df_Runde1)
            # zweiter Durchgang (2, df_Runde2), immer ein Tupel bestehend aus Name und Inhalt.
            # Auch wenn man in der Schleife eine der beiden Sachen nicht benötigt (hier Rundennummer) muss man sie hinschreiben.
            # Man kann irgendetwas hinschreiben, Konvention wenn man sie nicht braucht ist eigentlich _ also: "for _, gruppen_df in laps_grouped:"
            for runde, gruppen_df in laps_grouped:
                diff = gruppen_df["altitude"].diff()
                anstieg_pro_runde.append(diff[diff > 0].sum())
                abstieg_pro_runde.append(diff[diff < 0].sum() * -1)

            # Ende: Runden Elevation P und N ################################################

            pwr_np_lap = funktionen.normalised_power(
                df_records_tcx, df_runden_tcx
            )  # df aller records zwingend, df der runden optional für runden np

            vi_lap = []
            for i in range(len(alle_runden_tcx)):
                try:
                    vi_lap.append(float(pwr_np_lap[i]) / float(alle_runden_tcx[i]["runden_avg_power"]))
                except:
                    vi_lap.append(None)
            df_runden_tcx["runden_dauer_brutto"] = runden_dauer_brutto
            df_runden_tcx["runden_np"] = pwr_np_lap
            df_runden_tcx["runden_vi"] = vi_lap
            df_runden_tcx["runden_max_alt"] = max_alt_lap
            df_runden_tcx["runden_min_alt"] = min_alt_lap
            df_runden_tcx["runden_anstieg"] = anstieg_pro_runde
            df_runden_tcx["runden_abstieg"] = abstieg_pro_runde
            numeric_cols = [
                "runden_dauer_netto",
                "runden_dauer_brutto",
                "runden_distanz",
                "runden_max_speed",
                "runden_kalorien",
                "runden_avg_puls",
                "runden_max_puls",
                "runden_cadence",
                "runden_avg_speed",
                "runden_max_cadence",
                "runden_avg_power",
                "runden_max_power",
                "runden_np",
                "runden_vi",
                "runden_max_alt",
                "runden_min_alt",
                "runden_anstieg",
                "runden_abstieg",
            ]
            df_runden_tcx[numeric_cols] = df_runden_tcx[numeric_cols].apply(pd.to_numeric, errors="coerce")

            # --------------------------------------- #
            #  Aufbereiten der Aktivitätsdaten (TCX)  #
            # --------------------------------------- #

            activity_daten_tcx = []

            sportart = root.find(".//tcx:Activity", ns).get("Sport")
            try:
                device = root.find(".//tcx:Creator/tcx:Name", ns).text
            except:
                device = None
            distanz = df_runden_tcx["runden_distanz"].sum()
            dauer_n = df_runden_tcx["runden_dauer_netto"].sum()
            dauer_b = (df_records_tcx["timestamp"].iloc[-1] - df_records_tcx["timestamp"].iloc[0]).seconds
            speed = distanz / dauer_n
            max_speed = df_runden_tcx["runden_max_speed"].max()
            kalorien = df_runden_tcx["runden_kalorien"].sum()
            max_puls = df_runden_tcx["runden_max_puls"].max()
            max_cadence = df_runden_tcx["runden_max_cadence"].max()
            max_power = df_runden_tcx["runden_max_power"].max()
            heart_rate = df_records_tcx.loc[df_records_tcx["heart_rate"] != None, "heart_rate"].mean()
            power = df_records_tcx.loc[df_records_tcx["power"] != None, "power"].mean()
            cadence = df_records_tcx.loc[df_records_tcx["cadence"] != 0, "cadence"].mean()
            # loc benötigt 2 werte (welche zeile, welche spalte). erster Wert
            # hier eine pd.series wo nur werte drin sind die > o sind. in diesen zeilen nimmt es dann cadence. .mean() macht den ø
            diff = df_records_tcx[
                "altitude"
            ].diff()  # diff() berechnet aktueller Wert minus vorheriger in dieser Spalte und speichert es in einer Pandas Series ab
            ascent = (
                diff[diff < 0].sum() * -1
            )  # <0 da der nächste Wert grösser sein soll, also ein Anstieg darstellt. Multiplizieren mit -1
            # um das Vorzeichen zu ändern da Anstieg positiv sein sollte und die Summe der Differenzen zum nächsten
            # Punkt in dieser Berechnung negativ ist
            descent = diff[diff > 0].sum() * -1
            max_alt = max(df_records_tcx["altitude"])
            min_alt = min(df_records_tcx["altitude"])

            vam = ascent / (dauer_n / 3600)

            pwr_np = funktionen.normalised_power(
                df_records_tcx
            )  # df aller records zwingend, df der runden optional für runden np
            vi = pwr_np / power

            # hier noch IF und TSS berechnen, dafür braucht man aber FTP. FTP Wert vom letzten fit file verwenden.

            a_daten_tcx = {
                "sportart": sportart if sportart is not None else None,
                "device": device if device is not None else None,
                "distanz": distanz if distanz is not None else None,
                "dauer_netto": dauer_n if dauer_n is not None else None,
                "dauer_brutto": dauer_b if dauer_b is not None else None,
                "speed": speed if speed is not None else None,
                "max_speed": max_speed if max_speed is not None else None,
                "kalorien": kalorien if kalorien is not None else None,
                "max_puls": max_puls if max_puls is not None else None,
                "max_cadence": max_cadence if max_cadence is not None else None,
                "max_power": max_power if max_power is not None else None,
                "heart_rate": heart_rate if heart_rate is not None else None,
                "power": power if power is not None else None,
                "cadence": cadence if cadence is not None else None,
                "ascent": ascent if ascent is not None else None,
                "descent": descent if descent is not None else None,
                "max_alt": max_alt if max_alt is not None else None,
                "min_alt": min_alt if min_alt is not None else None,
                "vam": vam if vam is not None else None,
                "pwr_np": pwr_np if pwr_np is not None else None,
                "vi": vi if vi is not None else None,
            }
            # ------------------------------------------------- #
            #  Zusammenführen und finalisieren der Daten (TCX)  #
            # ------------------------------------------------- #

            activity_daten_tcx.append(a_daten_tcx)
            df_gesamtdaten_tcx = pd.DataFrame(activity_daten_tcx)

            liste_der_record_dfs.append(df_records_tcx)

            anzahl_importe += 1
            print(f"Importiert: {anzahl_importe} von {anzahl_files}")

        elif file.endswith(".fit"):

            #########################
            #       Fit-Files       #
            #########################

            fitfile = FitFile(file)

            # ------------------------------ #
            #  Dataframe der Records (FIT)   #
            # ------------------------------ #

            alle_records_fit = []

            for record in fitfile.get_messages("record"):  # durch jede Zeile iterieren, 1 pro Sekunde
                values = record.get_values()  # values ist ein Dict mit allen Daten einer Sekunde
                values.update({"garmin_id": garmin_id})  # Platzhalter einfügen
                alle_records_fit.append(values)  # die Werte einer Sekunde in die Liste aller Einträge hinzufügen
            df_records_fit = pd.DataFrame(alle_records_fit)  # Liste aller Einträge zu einem df machen
            df_records_fit["timestamp"] = (
                df_records_fit["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Europe/Zurich")
            )
            if "left_right_balance" in df_records_fit.columns:  # braucht if weil wenn Variable nicht vorhanden = Fehler
                df_records_fit["balance_pct_rechts"] = df_records_fit["left_right_balance"].apply(
                    funktionen.decode_balance
                )  # in left_right_balance sind die Werte als einzelne Bytes abgespeichert. Die Funktion decode_balande
                # wandelt sie um in % der rechten Seite. Kompliziert...
            if "enhanced_speed" in df_records_fit.columns:  # enhanced_speed ist genauere Erfassung als speed (früher).
                if (
                    "speed" in df_records_fit.columns
                ):  # falls enhanced_speed und der alte Wert speed vorhanden sind (gibt Fehler weil später umbenannt und dann 2x speed)
                    df_records_fit = df_records_fit.drop(columns=["speed"])  # wenn beide da speed löschen
                df_records_fit = df_records_fit.rename(columns={"enhanced_speed": "speed"})  # in speed umbenenen
            if (
                "enhanced_altitude" in df_records_fit.columns
            ):  # das gleiche wie bei speed. Höhe wurde früher anders gemessen, heute enhanced_altitude
                if "altitude" in df_records_fit.columns:
                    df_records_fit = df_records_fit.drop(columns=["altitude"])
                df_records_fit = df_records_fit.rename(columns={"enhanced_altitude": "altitude"})
            df_records_fit["file_type"] = "fit"
            gewuenschte_spalten_records = [  # in dieser Liste sind alle Spaltennamen, die in den df kommen sollen
                "garmin_id",
                "file_type",
                "timestamp",
                "position_lat",
                "position_long",
                "distance",
                "speed",
                "altitude",
                "power",
                "balance_pct_rechts",
                "heart_rate",
                "cadence",
                "temperature",
            ]
            df_records_fit = df_records_fit.reindex(
                columns=gewuenschte_spalten_records
            )  # df mit nur den gewünschten Spalten. Ist eine nicht da (bspw. power), gibt es keinen Fehler sondern n.a.

            # ------------------------------------------ #
            #  Events zu den Records hinzufügen (FIT)    #
            # ------------------------------------------ #

            df_records_merged_fit = pd.DataFrame()
            alle_events = []

            for event in fitfile.get_messages("event"):
                values = event.get_values()
                alle_events.append(values)
            df_events = pd.DataFrame(alle_events)
            df_events["timestamp"] = pd.to_datetime(df_events["timestamp"], errors="coerce", utc=True)
            df_events["timestamp"] = df_events["timestamp"].dt.tz_convert("Europe/Zurich")
            gewuenschte_spalten_events = ["timestamp", "rider_position", "front_gear", "rear_gear"]
            df_events = df_events.reindex(columns=gewuenschte_spalten_events)

            # falls zwei events in der selben sekunde passieren (bspw. schalten und aufstehen) werden
            # die events auf die selbe zeile zusammengefasst sonst gibt es später timestamp duplikate.
            # .first() nimmt pro Timestamp den ersten nicht-leeren (non-NaN) Wert je Spalte – NaN-Werte
            # werden dabei übersprungen, nicht einfach die allererste Zeile komplett übernommen.
            # df_events = df_events.groupby("timestamp", as_index=False).first()

            df_records_merged_fit = pd.merge(df_records_fit, df_events, on="timestamp", how="left")
            df_records_merged_fit[["front_gear", "rear_gear", "rider_position"]] = df_records_merged_fit[
                ["front_gear", "rear_gear", "rider_position"]
            ].ffill()
            df_records_merged_fit["rider_position"] = df_records_merged_fit["rider_position"].replace(
                {"transition_to_standing": "standing", "transition_to_seated": "seated"}
            )
            # die dfs in eine Liste speichern [df1, df2, df3, usw.]
            liste_der_record_dfs.append(df_records_merged_fit)

            # ----------------------------- #
            #  Laps zu Records hinzufügen   #
            # ----------------------------- #

            # alle_laps = []
            # for lap in fitfile.get_messages("lap"):
            #     values = lap.get_values()
            #     alle_laps.append(values)
            # df_laps = pd.DataFrame(alle_laps)
            # df_laps = df_laps.drop("timestamp", axis="columns")
            # df_laps = df_laps.rename(columns={"start_time": "timestamp", "message_index": "lap_number"})
            # df_laps["lap_number"] += 1  # beginnt sonst mit 0
            # gewuenschte_spalten_laps = [
            #     "timestamp",
            #     "total_timer_time",
            #     "avg_cadence",
            #     "avg_heart_rate",
            #     "avg_left_pco",
            #     "avg_left_pedal_smoothness",
            #     "avg_left_power_phase",
            #     "avg_left_power_phase_peak",
            #     "avg_left_torque_effectiveness",
            #     "avg_power",
            #     "avg_right_pco",
            #     "avg_right_pedal_smoothness",
            #     "avg_right_power_phase",
            #     "avg_right_power_phase_peak",
            #     "avg_right_torque_effectiveness",
            #     "avg_temperature",
            #     "avg_vam",
            #     "enhanced_avg_speed",
            #     "enhanced_max_speed",
            #     "intensity_factor",
            #     "left_right_balance",
            #     "max_cadence",
            #     "max_heart_rate",
            #     "max_power",
            #     "max_temperature",
            #     "lap_number",
            #     "normalized_power",
            #     "sport",
            #     "stand_count",
            #     "start_position_lat",
            #     "start_position_long",
            #     "sub_sport",
            #     "time_standing",
            #     "total_ascent",
            #     "total_calories",
            #     "total_cycles",
            #     "total_descent",
            #     "total_distance",
            #     "total_elapsed_time",
            #     "total_work",
            #     "end_position_lat",
            #     "end_position_long",
            #     "intensity",
            # ]
            # df_laps = df_laps.reindex(columns=gewuenschte_spalten_laps)
            # df_merge = pd.merge(df_merge, df_laps, on="timestamp", how="left")
            # df_merge[gewuenschte_spalten_laps] = df_merge[gewuenschte_spalten_laps].ffill()

            # lap_number als erste Spalte nach den records (nur zum testen im Excel damit es übersichtlicher ist)
            # col = df_merge.pop("lap_number")  # lap_number aus dem df nehmen und in col abspeichern
            # position = (
            #     len(gewuenschte_spalten_records) + len(gewuenschte_spalten_events) - 1
            # )  # hinter die records und events, - 1 weil Index in Excel eine zusätzliche Spalte ist
            # df_merge.insert(position, "lap_number", col)  # col an der Stelle 16 zum df hinzufügen

            # -------------------------- #
            #  Profil Daten hinzufügen   #
            # -------------------------- #

            # alle_user_profile = []
            # for user_profil in fitfile.get_messages("user_profile"):
            #     values = user_profil.get_values()
            #     alle_user_profile.append(values)
            # df_user_profile = pd.DataFrame(alle_user_profile)

            # alle_zones_target = []
            # for zones_target in fitfile.get_messages("zones_target"):
            #     values = zones_target.get_values()
            #     alle_zones_target.append(values)
            # df_zones_target = pd.DataFrame(alle_zones_target)

            # df_user_data = pd.concat([df_user_profile, df_zones_target], axis=1)

            # df_user_data = df_user_data.rename(columns={"max_heart_rate": "alltime_max_heart_rate"})

            # gewuenschte_spalten_user_data = [
            #     "resting_heart_rate",
            #     "weight",
            #     "alltime_max_heart_rate",
            #     "functional_threshold_power",
            #     "threshold_heart_rate",
            # ]
            # df_user_data = df_user_data.reindex(columns=gewuenschte_spalten_user_data)

            anzahl_importe += 1
            print(f"Importiert: {anzahl_importe} von {anzahl_files}")

    except Exception as e:
        traceback.print_exc()
        fehlerhafte_dateien.append(file)


# axis=0 damit df untereinander zusammengefügt werden, ignore_index=True damit Index im neuen file 0 bis n ist und
# nicht immer wieder bei 0 beginnt bei jedem neu hinzugefügten df
df_alle_records = pd.concat(liste_der_record_dfs, axis=0, ignore_index=True)

df_alle_records["timestamp"] = df_alle_records["timestamp"].dt.tz_localize(
    None
)  # Zeitzone entfernen, sonst kann man df nicht zu excel exportieren


# df_runden_tcx["timestamp_start"] = df_runden_tcx["timestamp_start"].dt.tz_localize(None)


df_alle_records.to_excel("df_alle_records.xlsx")
