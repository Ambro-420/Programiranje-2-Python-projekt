import matplotlib.pyplot as plt
import requests as re
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import numpy as np
from geopy.geocoders import Nominatim
from datetime import datetime
import calendar
import pprint

# pridobivanje podatkov

# Open-Meteo API in geolocator setup
cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)
geolocator = Nominatim(user_agent="my_app")

# ni varovalne mreže, ker geolocator deluje tudi z poštnimi ševilkami
koordinate = geolocator.geocode(input("Željena lokacija: "))
x = round(koordinate.latitude, 4)
y = round(koordinate.longitude, 4)
lokacija = str(koordinate)
print(lokacija)
# datume bomo omejili od 1940-01-01 do 2025-12-31

while True:
    try:
        start_input = input("Vnesi začetno leto (YYYY): ")
        start_year = int(start_input)

        if start_year < 1940 or start_year > 2025:
            raise ValueError("Leto mora biti med 1940 in 2025")

        start_date = datetime(start_year, 1, 1)
        break

    except Exception as e:
        print("Napaka:", e)
        print("Poskusi znova.\n")

    except Exception as e:
        print("Napaka:", e)
        print("Poskusi znova.\n")

while True:
    try:
        end_input = input("Vnesi končno leto (YYYY): ")
        end_year = int(end_input)

        if end_year < 1940 or end_year > 2026:
            raise ValueError("Leto mora biti med 1940 in 2025")

        end_date = datetime(end_year-1, 12, 31)
        break

    except Exception as e:
        print("Napaka:", e)
        print("Poskusi znova.\n")


# dodatna kontrola
if start_date > end_date:
    print("Napaka: začetni datum je večji od končnega!")
else:
    zacetk = str(start_date)[:10]
    konec = str(end_date)[:10]

    # napoved bo le če je končni datum 2025-12-31, 
    # če je manj delamo napoved za leto, ki se je že zgodilo
    mozni_odg = ["da", "ne", "ja"]
    napoved = "ne"

    if konec == "2025-12-31" and int(zacetk[:4]) < 2025:
        while True:
            try:
                risanje_klimo = input("Ali želite klimogram mesta (da/ne): ").strip().lower()
                napoved = input("Ali želite napoved za leto 2026 (da/ne): ").strip().lower()
                
                if (napoved not in mozni_odg) or (risanje_klimo not in mozni_odg):
                    raise ValueError("Vnesite 'da' ali 'ne'.")

                if napoved in ["da", "ja"]:
                    koliko_let = int(input("Koliko let (1-5): "))

                    if koliko_let < 1 or koliko_let > 5:
                        raise ValueError("Število let mora biti med 1 in 5.")

                break

            except Exception as e:
                print("Napaka:", e)
                print("Poskusi znova.\n")
    else:
        risanje_klimo = "da"
        print("OK!")

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
	"latitude": x,
	"longitude": y,
	"start_date": zacetk,
	"end_date": konec,
	"hourly": ["temperature_2m", "rain"],
	"timezone": "auto",
}
responses = openmeteo.weather_api(url, params = params)
# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]

# Process hourly data. The order of variables needs to be the same as requested.
hourly = response.Hourly()
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy() # tabela temperatur
hourly_rain = hourly.Variables(1).ValuesAsNumpy() # tabela rešja

hourly_data = {"date": pd.date_range(
	start = pd.to_datetime(hourly.Time() + response.UtcOffsetSeconds(), unit = "s", utc = True),
	end =  pd.to_datetime(hourly.TimeEnd() + response.UtcOffsetSeconds(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = hourly.Interval()),
	inclusive = "left"
)}
# print(hourly_data)
hourly_data["temperature_2m"] = hourly_temperature_2m
hourly_data["rain"] = hourly_rain

hourly_dataframe = pd.DataFrame(data = hourly_data)
#print(list(hourly_dataframe['date']))

#print(hourly_dataframe['date']) # prikaže vsak dan

# sortiranje podatkov
datumi = []
temp = []
dez = []
dan = []
stevec = 0
podatki = ['date', 'temperature_2m', 'rain']
grupirani = [datumi, temp, dez]
for podatek, grupa in zip(podatki, grupirani):
	for d in hourly_dataframe[podatek]:
		if podatek == 'date':
			dan.append(str(d))
		else:
			dan.append(d)
		stevec += 1
		if stevec == 24:
			stevec = 0
			grupa.append(dan)
			dan = []

# sortiral tablele po dnevih in izračunamo povprečne temp in količino dežja
dnevi = []
povprecna_t_dneva = []
povprecna_d_dneva =  []
letnice = set()
for i in range(len(datumi)):
	povprecna_t_dneva.append(sum(temp[i])/24)
	povprecna_d_dneva.append(sum(dez[i])/24)
	dnevi.append(datumi[i][0][:11])
	letnice.add(int(datumi[i][0][:4]))

# podatke grupiram po letih
leta = sorted(list(letnice))
tabela_let = leta.copy()
tabela_dni_po_letih = []
tabela_t_po_letih = []
tabela_d_po_letih = []
dnevi_v_letu = []
temp_v_letu = []
dez_v_letu = []
for i in range(len(datumi)):

	letnica_dneva = int(dnevi[i][:4])

	if letnica_dneva == leta[0]:
		dnevi_v_letu.append(dnevi[i])
		temp_v_letu.append(povprecna_t_dneva[i])
		dez_v_letu.append(povprecna_d_dneva[i])

	else:
		leta.remove(leta[0])
		tabela_dni_po_letih.append(dnevi_v_letu)
		tabela_t_po_letih.append(temp_v_letu)
		tabela_d_po_letih.append(dez_v_letu)
		dnevi_v_letu = []
		temp_v_letu = []
		dez_v_letu = []
# dodaj še zadnje leto
if dnevi_v_letu:
    tabela_dni_po_letih.append(dnevi_v_letu)
    tabela_t_po_letih.append(temp_v_letu)
    tabela_d_po_letih.append(dez_v_letu)
# podatke grupiramo po mesecih (ne vklučuje porazdelitev po letih)
tabela_dni_po_mesecih = []
tabela_t_po_mesecih = []
tabela_d_po_mesecih = []

for i in range(len(tabela_dni_po_letih)):
    leto = tabela_dni_po_letih[i]
    tabela_dni_po_mesecih.append([leto[0]]) # dodamo leto, seznam za prvi mesec in prvi dan v mesecu
    tabela_t_po_mesecih.append([tabela_t_po_letih[i][0]])
    tabela_d_po_mesecih.append([tabela_d_po_letih[i][0]])
    
    # delamo od drugega dne naprej
    indeks_dan = 1
    while indeks_dan < len(leto):
        danes = leto[indeks_dan]
        vceraj = leto[indeks_dan - 1]
        
        # danasji dez in temperatura
        temperatura = tabela_t_po_letih[i][indeks_dan]
        dez = tabela_d_po_letih[i][indeks_dan]
        
        if danes[5:7] != vceraj[5:7]: # primerjamo mesece
            tabela_dni_po_mesecih.append([danes]) # doda nov seznam za novi mesec
            tabela_t_po_mesecih.append([temperatura])
            tabela_d_po_mesecih.append([dez])
        else:
            tabela_dni_po_mesecih[-1].append(danes)# zadnjemu mesecu dodamo dan
            tabela_t_po_mesecih[-1].append(temperatura)
            tabela_d_po_mesecih[-1].append(dez)
        
        indeks_dan += 1

# tabele so povezane z indeksi
# torej 
#print(tabela_dni_po_letih[0][0], tabela_t_po_letih[0][0], tabela_d_po_letih[0][0])

# TEST ZA MESECE
#print(tabela_let[0])
#print(len(tabela_dni_po_mesecih)) # 120 mesecov v 10 letih
#print(tabela_t_po_mesecih[0])
#print(tabela_d_po_mesecih[0])

povprecna_t_meseca = []
povprecna_d_meseca = []
i = 0
while i != len(tabela_dni_po_mesecih):
	t_meseca = sum(tabela_t_po_mesecih[i])/len(tabela_t_po_mesecih[i])
	d_meseca = sum(tabela_d_po_mesecih[i])/len(tabela_d_po_mesecih[i])
	povprecna_t_meseca.append(t_meseca)
	povprecna_d_meseca.append(d_meseca)
	i += 1

# risanje klimografa

def risanje_klimograma(leto, povp_temp, povp_pad, lokacija):
	"""funkcija izriše klimogam in ga shrani"""
	meseci = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
	x = np.arange(len(meseci))

	fig, ax1 = plt.subplots()

	# Stolpci za padavine
	ax1.bar(x, padavine, color='b')
	ax1.set_yticks([0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35])
	ax1.set_yticklabels([0, 50, 100, 150, 200, 250, 300, 350])
	ax1.set_ylabel('Padavine (mm)', color='b')

	# Druga os za temperaturo
	ax2 = ax1.twinx()
	ax2.plot(x, temperature, color='red', linewidth=2)
	ax2.set_ylabel('Temperatura (°C)', color='red')
	ax2.set_ylim(-10, 40)

	# Osi in oznake
	mesto = str(lokacija.split(",")[0])
	plt.xticks(x, meseci)
	plt.title(f'{mesto} v obdobju {leto} leta')

	plt.savefig(f"klimogram_{mesto}")


# sortiranje po letih
temp_let = []
pad_let = []
povp_temp_leta = [] # povprečna temperatura leta
while len(povprecna_t_meseca) != 0:
    temp_leta = povprecna_t_meseca[0:12]
    temp_let.append(temp_leta)

    povp_t_leta = sum(povprecna_t_meseca[0:12]) / 12
    povp_temp_leta.append(povp_t_leta)

    pad_leta = povprecna_d_meseca[0:12]
    pad_let.append(pad_leta)

    del  povprecna_t_meseca[0:12]
    del povprecna_d_meseca[0:12]

# matriki [[temperature zacetnega leta po mesecih],...,[temp koncnega leta po mesecih]] 
matrika_t = np.array(temp_let)
matrika_d = np.array(pad_let)

# risanje povprecja vnešenh let
stevilo_let = len(tabela_let)

temperature = np.mean(matrika_t, axis=0)
padavine = np.mean(matrika_d, axis=0)
od_do = f"{tabela_let[0]}-{str(int(tabela_let[-1] + 1))}"
if risanje_klimo in ["da", "ja"]:
    risanje_klimograma(od_do, temperature, padavine, lokacija)
    plt.show()


#Napoved
zacetno_leto = 2026

napovedi_t = []
napovedi_d = []

koef_t = []
koef_d = []

if stevilo_let > 1 and napoved in ["da", "ja"]:
    leta_napovedi = [zacetno_leto + i for i in range(koliko_let)]
    matrika_t_po_mesecih = np.transpose(matrika_t) # transponiramo da razdelimo povprečja po mesecih
    matrika_d_po_mesecih = np.transpose(matrika_d)
    # izračun koeficientov samo enkrat
    for i in range(12):
        koef_t.append(np.polyfit(tabela_let, matrika_t_po_mesecih[i], 1))
        koef_d.append(np.polyfit(tabela_let, matrika_d_po_mesecih[i], 1))

    # napovedi
    for leto in leta_napovedi:
        vrstica_t = []
        vrstica_d = []
        
        for i in range(12):
            a_t, b_t = koef_t[i]
            a_d, b_d = koef_d[i]
            
            vrstica_t.append(round(float(a_t * leto + b_t), 1))
            vrstica_d.append(round(float(a_d * leto + b_d) * 1000, 1))
        
        napovedi_t.append(vrstica_t)
        napovedi_d.append(vrstica_d)

    meseci = ["jan", "feb", "mar", "apr", "maj", "jun",
            "jul", "avg", "sep", "okt", "nov", "dec"]

    print("\nNapovedi za temperature (*C): ")
    print(f"{'m/l':<6}", end="")
    for leto in leta_napovedi:
        print(f"{leto:>8}", end="")
    print()

    for m in range(12):
        print(f"{meseci[m]:<6}", end="")
        
        for l in range(len(leta_napovedi)):
            print(f"{napovedi_t[l][m]:>8.1f}", end="")
        
        print()

    print("\nNapovedi za padavine (mm): ")
    print(f"{'m/l':<6}", end="")
    for leto in leta_napovedi:
        print(f"{leto:>8}", end="")
    print()

    for m in range(12):
        print(f"{meseci[m]:<6}", end="")
        
        for l in range(len(leta_napovedi)):
            print(f"{napovedi_d[l][m]:>8.1f}", end="")
        
        print()