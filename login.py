###################################
# In Garmin Connect einloggen     #
###################################


from dotenv import load_dotenv  # zum öffnen der Zugansdaten aus der .env Datei
from garminconnect import Garmin  # Bibliothek mit vielen Methoden für GarminConnect
import os  # Bibliothek für Sachen die mit MacOS zu tun haben (Datei in Ordner löschen usw.)

# Name und Passwort gespeichert sicher in separaten file speichern
load_dotenv()


# mit Garmin verbinden
def einloggen():
    # Erstellt ein neues Garmin-Objekt (Verbindung zu Garmin Connect),
    # E-Mail und Passwort werden aus den Umgebungsvariablen (.env Datei) gelesen
    client = Garmin(
        os.getenv("EMAIL"),
        os.getenv("PASSWORD"),
    )
    # Loggt sich mit den obigen Zugangsdaten bei Garmin ein.
    # "~/.garminconnect" ist der Ort, an dem die Sitzung (Session) gespeichert wird,
    # damit man sich beim nächsten Mal nicht zwingend neu einloggen muss
    client.login("~/.garminconnect")
    # Gibt das eingeloggte Garmin-Objekt zurück,
    # damit man in anderen Dateien/Funktionen damit weiterarbeiten kann
    return client
