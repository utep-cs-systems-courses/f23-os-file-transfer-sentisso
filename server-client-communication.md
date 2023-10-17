<- to server<br>
-> from server

for each uploaded file:
- <- **action** | 1B | "W"
- <- **filename length** | 1B | max 255 characters
- <- **file name** | nB | n = file name length
- -> **confirmation** | 8B | "OK"/"ERROR"
- if OK:
  - <- **file size** | 8B | max 2^64 bytes
  - <- **file content** | nB | n = file size
  - -> **confirmation** | 8B | "OK"/"ERROR"
- elif ERROR:
  - -> **error message length** | 1B | max 255 characters
  - -> **error message** | nB | n = error message length

for each requested file:
- <- **action** | 1B | "R"
- <- **filename length** | 1B | max 255 characters
- <- **file name** | nB | n = file name length
- -> **confirmation** | 8B | "OK"/"ERROR"
- if OK:
  - -> **file size** | 8B | max 2^64 bytes
  - -> **file content** | nB | n = file size
- elif ERROR:
    - -> **error message length** | 1B | max 255 characters
    - -> **error message** | nB | n = error message length