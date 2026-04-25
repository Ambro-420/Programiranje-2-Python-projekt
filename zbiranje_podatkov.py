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

# datume bomo omejili od 1940 do 2025

while True:
    try:
        date_str = input("Vnesi začetni datum: ")
        parts = date_str.split("-")

        year = int(parts[0])
        if year < 1940 or year > 2025:
            raise ValueError("Leto mora biti med 1940 in 2025")

        if len(parts) == 1:
            start_date = datetime(year, 1, 1)

        elif len(parts) == 2:
            month = int(parts[1])
            if not 1 <= month <= 12:
                raise ValueError("Mesec mora biti med 01 in 12")

            start_date = datetime(year, month, 1)

        elif len(parts) == 3:
            month = int(parts[1])
            day = int(parts[2])

            if not 1 <= month <= 12:
                raise ValueError("Mesec mora biti med 01 in 12")

            start_date = datetime(year, month, day)

        else:
            raise ValueError("Napačen format")

        break  # če uspe → ven iz zanke

    except Exception as e:
        print("Napaka:", e)
        print("Poskusi znova.\n")


while True:
    try:
        date_str = input("Vnesi končni datum: ")
        parts = date_str.split("-")

        year = int(parts[0])
        if year < 1940 or year > 2025:
            raise ValueError("Leto mora biti med 1940 in 2025")

        if len(parts) == 1:
            end_date = datetime(year - 1, 12, 31)

        elif len(parts) == 2:
            month = int(parts[1])
            if not 1 <= month <= 12:
                raise ValueError("Mesec mora biti med 01 in 12")

            last_day = calendar.monthrange(year, month)[1]
            end_date = datetime(year, month, last_day)

        elif len(parts) == 3:
            month = int(parts[1])
            day = int(parts[2])

            if not 1 <= month <= 12:
                raise ValueError("Mesec mora biti med 01 in 12")

            end_date = datetime(year, month, day)

        break

    except Exception as e:
        print("Napaka:", e)
        print("Poskusi znova.\n")


# dodatna kontrola
if start_date > end_date:
    print("Napaka: začetni datum je večji od končnega!")
else:
    print("OK!")
    zacetk = str(start_date)[:10]
    konec = str(end_date)[:10]

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

print(povprecna_t_meseca[0:12])
print(povprecna_d_meseca[0:12])
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
	plt.title(f'Klimogram {mesto} leta {leto}')

	plt.savefig(f"klimogram_{mesto}")

temperature = povprecna_t_meseca[0:12]
padavine = povprecna_d_meseca[0:12]
leto = 2000
risanje_klimograma(leto, temperature, padavine, lokacija)