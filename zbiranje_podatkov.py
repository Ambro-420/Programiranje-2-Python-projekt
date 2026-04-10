import matplotlib.pyplot as plt
import requests as re
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry


# pridobivanje podatkov

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
	"latitude": 46.0511,
	"longitude": 14.5051,
	"start_date": "2000-01-01",
	"end_date": "2009-12-31",
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
		dan.append(str(d))
		stevec += 1
		if stevec == 24:
			stevec = 0
			grupa.append(dan)
			dan = []

print(datumi[0], '\n',temp[0], '\n',dez[0])
# podatke grupiram v skupine po mesecih


# risanje klimografa
