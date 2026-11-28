###################################
# Aktivitäten herunterladen       #
###################################


import datetime  # für alles was mit Datum zusammenhängt
from io import BytesIO  # speichert Bytes im RAM, wird als Dateien angesehen
import zipfile  # für Zipfile öffnen/entpacken
from login import einloggen  # eigene Funktion aus login.py
import os  # Bibliothek für Sachen die mit Betriebssystem zu tun haben (Datei in Ordner löschen usw.)
from garminconnect import Garmin  # Bibliothek mit vielen Methoden für GarminConnect

client = einloggen()  # Login bei Garmin Connect mit meinen Zugangsdaten aus .env

# Ab Wann Dateien geladen werden sollen
activity_start_date = datetime.date(2026, 7, 1)

# Aktivitäten herunterladen (Aktivitäten als Liste, in der Liste die jeweilige Aktivität als Dictionary),
# nur Übersichtsdaten der Aktivität

activities = client.get_activities_by_date(
    activity_start_date.isoformat(), None
)  # None = heute , str(datetime.date.today() wäre auch möglich


# für Duplikatskontrolle, Liste mit allen Dateien
vorhanden = os.listdir("/Users/momogeiser/Momos Sachen/Programmieren/Python/testProjekt/Daten")
# Liste mit den IDs (nicht strip('_ACTIVITY.fit') verwenden, strip löscht
# alle entsprechenden Zeichen), bspw. strip(_ACTIVITY1.fit) löscht auch alle 1 aus der ID
vorhanden_id = [s.removesuffix("_ACTIVITY.fit") for s in vorhanden]

for activity in activities:  # loop durch alle Aktivitäten aus der Liste activities
    activity_id = str(activity["activityId"])  # ID wird von int zu String umgewandelt
    if activity_id not in vorhanden_id:  # nur wenn ID noch nicht vorhanden ist (Duplikatskontrolle)
        data = client.download_activity(  # data ist von Typ bytes
            activity_id,
            dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL,  # ID als String, ORIGINAL für .fit
        )
        # zipfile.ZipFile ist eine Klasse (ein Werkzeug) die mit Zip Dateien umgehen kann / data ist Bytes Objekt,
        # das so nicht gelesen werden kann. BytesIO() ist eine Funktion, die eine normale Datei vortäuscht damit sie entpackt werden kann
        # Logik von with ... as zf: die Bytes Datei aus dem Zip-File wird als Variable zf gespeichert
        with zipfile.ZipFile(BytesIO(data)) as zf:
            # namelist ist eine Methode aus zipfile Paket, hier wird Namen des Zip Inhalts als Liste gespeichert
            name_im_zip = zf.namelist()[0]  # [0] da bei Garmin immer nur eine Datei im Zip
            zf.extract(  # extract ist eine Methode aus zipfile die Zip-Files auspackt
                name_im_zip,
                path="/Users/momogeiser/Momos Sachen/Programmieren/Python/testProjekt/FIT Dateien",
            )
