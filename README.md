Health stats takes samsung galaxy watch data that is exported to google sheets via health sync and loads it into a mysql db on a rpi cluster. It combines this data with cell phone gps data that is logged to google sheets and loaded into mysql. The coordinates from the location data are used to query the Visual Crossing weather api for conditions at the given locations and times. This integrated data is used to present analytics on fitness, sleep, and vitals by location, weather conditions and time of day.

Dashboard Link:
https://datastudio.google.com/reporting/4d204527-a6ef-4860-b02c-73bf58cd1377
