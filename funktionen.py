import numpy as np


def erstes_nicht_none(*werte):
    for w in werte:
        if w is not None:
            return w
    return None


def decode_balance(rohwert):
    if rohwert is None or not isinstance(rohwert, (int, float)):
        return None  # z.B. bei "right" ohne Zahl -> ungültig
    if rohwert >= 128:
        rechts = rohwert - 128
        return rechts  # % rechts, links = 100 - rechts
    else:
        links = rohwert
        return 100 - links  # falls das Bit NICHT gesetzt ist (selten bei Garmin)


# def value_by_laps(records, laps, value):
#     runden_dauer = [round(float(x)) for x in laps["runden_dauer_netto"]]  # x ist string, mann muss zuerst float machen
#     # weil x nachkommastellen hat und man es nicht direkt int machen kann. round ohne Kommastelle macht automatisch int

#     value = np.array(records[value])  # alle "Value" records der ganzen fahrt
#     runden_dauer_kum = np.cumsum(
#         runden_dauer
#     )  # Dauer der Runden kummulieren so hat man die Startzeit der Runde (Start Aktivität = Sekunde 0) bspw. [230, 600, 4230, 9803 usw.]
#     start = np.insert(runden_dauer_kum, 0, 0)  # im Array runden_dauer_kum an Stelle 0 eine 0 einsetzen
#     ende = runden_dauer_kum
#     ergebnis = list(zip(start, ende))  # [(Start Runde 1, Ende Runde 1), (Start Runde 2, Ende Runde 2) usw.]

#     value_all_lap = []
#     for i in range(len(ergebnis)):  # iteriert durch alle laps bspw. range(0, 5)
#         value_lap = []
#         for j in range(
#             ergebnis[i][0], ergebnis[i][1]
#         ):  # iteriert durch die indizes der spezifischen lap, bspw. range(600, 4230)
#             value_lap.append(value[j])  # speicher den jeweiligen Watt Wert in der Runden liste
#         value_all_lap.append(value_lap)  # fügt alle Rundenlisten zu einer Liste zusammen
#     return value_all_lap


def value_by_laps(records, laps, value):

    value_all_lap = []
    for j in range(len(laps)):
        if j < len(laps) - 1:
            start = laps["timestamp_start"].iloc[j]
            ende = laps["timestamp_start"].iloc[j + 1]
            value_lap = []
            for i in range(len(records[value])):
                if records["timestamp"].iloc[i] >= start and records["timestamp"].iloc[i] < ende:
                    value_lap.append(records[value].iloc[i])
            value_all_lap.append(value_lap)
        else:  # letzte Runde
            start = laps["timestamp_start"].iloc[j]
            ende = records["timestamp"].iloc[-1]
            value_lap = []
            for i in range(len(records[value])):
                if records["timestamp"].iloc[i] >= start and records["timestamp"].iloc[i] <= ende:
                    value_lap.append(records[value].iloc[i])
            value_all_lap.append(value_lap)
    return value_all_lap


def normalised_power(records, laps=None):
    if laps is None:
        pwr = np.array(records["power"])  # alle Power records der ganzen fahrt
        last30 = []
        for i in range(len(pwr)):
            if i >= 30:
                last30.append(
                    float(pwr[i - 30 : i].mean()) ** 4
                )  # pwr ist ein Array mit allen Watt Records, wird weiter oben bei den Runden erstellt
        pwr_np = np.nanmean(last30) ** (1 / 4)
        return pwr_np
    else:
        pwr_all_lap = value_by_laps(records, laps, "power")

        pwr_np_lap = []
        for i in range(len(pwr_all_lap)):  # loop durch alle Runden
            last_30_lap = []
            if len(pwr_all_lap[i]) >= 30:  # nur für Runden 30s und länger
                for j in range(len(pwr_all_lap[i])):  # loop durch alle Wattwerte dieser Runde
                    if j >= 30:  # die ersten 29s ignorieren
                        last_30_lap.append(
                            float(np.mean(pwr_all_lap[i][j - 30 : j])) ** 4
                        )  # 30s Durchschnitte hoch 4 und in einer Liste abspeichern
            if len(last_30_lap) > 0:
                pwr_np_lap.append(
                    float(np.nanmean(last_30_lap) ** (1 / 4))
                )  # die vierte Wurzel der jeweiligen Durchschnittswerte als Zahl in einer Liste abspeichern
            else:
                pwr_np_lap.append(np.nan)

        return pwr_np_lap
